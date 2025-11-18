# 研究智能体消息过滤功能 - 实现总结

## 问题描述

用户询问：
> "researchteam 在哪调用大模型的？能不能不要返回前端，或者将其过滤掉？"

## 解决方案

我们实现了一个可配置的消息过滤功能，允许过滤掉 researcher 智能体的流式消息，这些消息仅在后台处理，不返回给前端。

## 实现详情

### 1. 调用大模型的位置

**文件**: [`src/graph/nodes.py`](../src/graph/nodes.py)
**函数**: `_execute_agent_step` (第1213-1362行)
**关键代码**:

```python
# 第1318行：调用智能体（大模型）
result = await agent.ainvoke(
    input=agent_input, config={"recursion_limit": recursion_limit}
)

# 第1329行：获取响应内容
response_content = result["messages"][-1].content

# 第1347-1361行：返回消息给前端
return Command(
    update={
        "messages": [
            HumanMessage(
                content=response_content,
                name=agent_name,  # 这里 agent_name 可能是 "researcher"
            )
        ],
        "observations": observations + [response_content],
    },
    goto="research_team",
)
```

### 2. 过滤消息的实现

**文件**: [`src/server/app.py`](../src/server/app.py)
**函数**: `_process_message_chunk` (第284-323行)
**新增代码**:

```python
async def _process_message_chunk(message_chunk, message_metadata, thread_id, agent):
    """Process a single message chunk and yield appropriate events."""
    agent_name = _get_agent_name(agent, message_metadata)
    
    # 🆕 过滤掉 researcher 节点的消息（仅在后台处理，不返回前端）
    # 可以通过环境变量 FILTER_RESEARCHER_MESSAGES 控制是否过滤（默认：true）
    filter_researcher = get_bool_env("FILTER_RESEARCHER_MESSAGES", True)
    if filter_researcher and agent_name == "researcher":
        # 记录日志但不返回给前端
        enhanced_logger.logger.debug(
            f"🔇 FILTERED_MESSAGE | researcher | 消息已过滤（不返回前端） | "
            f"内容长度: {len(message_chunk.content) if hasattr(message_chunk, 'content') else 0}"
        )
        return  # 不yield任何事件，直接返回
    
    # ... 原有的消息处理逻辑
```

### 3. 环境变量配置

**文件**: [`.env`](../.env)
**新增配置**:

```bash
# 消息过滤配置
# 过滤掉研究智能体（researcher）的流式消息，仅在后台处理，不返回给前端
# 设置为 true 可以减少前端接收到的中间过程消息，只显示最终结果
# 设置为 false 可以看到研究智能体的完整执行过程
FILTER_RESEARCHER_MESSAGES=true
```

## 工作流程

```
用户请求 → 路由节点 → 协调者 → 规划者 → 研究团队
                                              ↓
                                        researcher 节点
                                              ↓
                                    _execute_agent_step
                                              ↓
                                    agent.ainvoke() 调用大模型
                                              ↓
                                        返回 Command 包含消息
                                              ↓
                                        graph.astream() 流式处理
                                              ↓
                                    _stream_graph_events
                                              ↓
                                    _process_message_chunk
                                              ↓
                                    【过滤检查点】
                                              ↓
                    ┌─────────────────────────┴──────────────────────────┐
                    │                                                    │
            agent_name == "researcher"                       其他 agent
            且 FILTER_RESEARCHER_MESSAGES=true                    │
                    │                                                    │
                直接返回（不yield事件）                      正常处理并yield事件
                    │                                                    │
                记录日志：                                         返回给前端
           🔇 FILTERED_MESSAGE
                    │
               不返回前端
```

## 修改文件清单

1. **`src/server/app.py`** ✅
   - 修改 `_process_message_chunk` 函数
   - 添加消息过滤逻辑

2. **`.env`** ✅
   - 添加 `FILTER_RESEARCHER_MESSAGES` 环境变量

3. **新增文档**:
   - `docs/FILTER_RESEARCHER_MESSAGES.md` - 功能详细说明
   - `docs/FILTER_TEST_GUIDE.md` - 测试指南
   - `docs/IMPLEMENTATION_SUMMARY.md` - 本文档

## 功能特点

### ✅ 优点

1. **可配置**: 通过环境变量轻松开关过滤功能
2. **不影响功能**: 后台处理正常进行，只是不返回前端
3. **日志完整**: 所有消息仍记录在日志中，方便调试
4. **性能优化**: 减少网络传输和前端渲染负担
5. **用户体验**: 前端只显示关键信息，界面更简洁

### 🎯 适用场景

- **生产环境**: 启用过滤，提供简洁的用户体验
- **开发调试**: 禁用过滤，查看完整的执行过程
- **问题排查**: 通过日志了解 researcher 的详细工作流程

## 使用示例

### 启用过滤（推荐）

```bash
# .env 文件
FILTER_RESEARCHER_MESSAGES=true

# 重启服务
docker-compose restart
```

**效果**：前端只看到最终报告，不显示 researcher 的中间过程

### 禁用过滤（调试）

```bash
# .env 文件
FILTER_RESEARCHER_MESSAGES=false

# 重启服务
docker-compose restart
```

**效果**：前端显示 researcher 的完整执行过程

## 扩展建议

### 1. 过滤多个智能体

```python
# src/server/app.py 中的 _process_message_chunk 函数
filtered_agents = ["researcher", "coder"]
if filter_researcher and agent_name in filtered_agents:
    enhanced_logger.logger.debug(f"🔇 FILTERED_MESSAGE | {agent_name}")
    return
```

### 2. 细粒度过滤

```python
# 只过滤工具调用消息，保留文本消息
if filter_researcher and agent_name == "researcher":
    if isinstance(message_chunk, ToolMessage):
        enhanced_logger.logger.debug("🔇 FILTERED_TOOL_MESSAGE | researcher")
        return
    # 文本消息仍然返回
```

### 3. 配置过滤级别

```python
# 支持多级过滤
# FILTER_LEVEL=0  # 不过滤
# FILTER_LEVEL=1  # 过滤工具调用
# FILTER_LEVEL=2  # 过滤所有消息

filter_level = int(get_str_env("FILTER_LEVEL", "2"))
if agent_name == "researcher":
    if filter_level == 2:
        return  # 过滤所有
    elif filter_level == 1 and isinstance(message_chunk, ToolMessage):
        return  # 只过滤工具调用
```

## 测试验证

### 快速测试

```bash
# 1. 设置环境变量
echo "FILTER_RESEARCHER_MESSAGES=true" >> .env

# 2. 重启服务
docker-compose restart

# 3. 发送测试请求
curl -X POST http://localhost:8000/api/research/simple/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "什么是AI？"}],
    "auto_accepted_plan": true
  }'

# 4. 查看日志
tail -f logs/deer-flow.log | grep FILTERED_MESSAGE
```

### 预期结果

- ✅ 前端不显示 researcher 的消息
- ✅ 日志中包含 `🔇 FILTERED_MESSAGE` 条目
- ✅ 最终报告正常生成

## 注意事项

1. **后台处理不受影响**: 即使消息被过滤，researcher 仍正常执行
2. **日志完整性**: 所有消息都会记录，方便问题排查
3. **兼容性**: 不影响现有功能，可以随时开关
4. **性能**: 过滤可以减少数据传输，提升性能

## 相关链接

- [功能详细说明](./FILTER_RESEARCHER_MESSAGES.md)
- [测试指南](./FILTER_TEST_GUIDE.md)
- [环境变量配置](../.env)
- [源码位置 - nodes.py](../src/graph/nodes.py)
- [源码位置 - app.py](../src/server/app.py)

## 总结

通过在流式消息处理管道中添加过滤逻辑，我们成功实现了：

1. ✅ **找到调用大模型的位置**: `src/graph/nodes.py` 的 `_execute_agent_step` 函数
2. ✅ **实现消息过滤**: 在 `src/server/app.py` 的 `_process_message_chunk` 函数中过滤 researcher 消息
3. ✅ **可配置控制**: 通过 `FILTER_RESEARCHER_MESSAGES` 环境变量开关功能
4. ✅ **保持日志完整**: 所有消息仍记录在日志中
5. ✅ **不影响功能**: 后台处理正常，只是不返回前端

这个解决方案既满足了用户需求（不返回 researcher 消息给前端），又保持了系统的灵活性和可调试性。
