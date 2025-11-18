# 研究智能体消息过滤功能

## 功能概述

该功能允许你过滤掉研究智能体（researcher）在执行研究任务时的流式消息，这些消息仅在后台处理，不会返回给前端。这样可以减少前端接收到的中间过程消息，只显示最终的研究报告结果。

## 使用场景

在深度研究（deep research）工作流中，research team 会调用 researcher 智能体执行具体的研究步骤：

1. **研究智能体（researcher）** - 使用搜索引擎和爬虫工具收集信息
2. **编码智能体（coder）** - 执行代码分析和数学计算

这些智能体在执行过程中会产生大量的中间消息，包括：
- 工具调用过程
- 搜索结果
- 思考过程
- 中间分析结果

## 工作原理

### 代码位置

- **调用大模型的位置**: [`src/graph/nodes.py`](../src/graph/nodes.py) 中的 `_execute_agent_step` 函数（第1318行）
  ```python
  result = await agent.ainvoke(
      input=agent_input, config={"recursion_limit": recursion_limit}
  )
  ```

- **过滤消息的位置**: [`src/server/app.py`](../src/server/app.py) 中的 `_process_message_chunk` 函数（第272行）
  ```python
  # 过滤掉 researcher 节点的消息（仅在后台处理，不返回前端）
  filter_researcher = get_bool_env("FILTER_RESEARCHER_MESSAGES", True)
  if filter_researcher and agent_name == "researcher":
      # 记录日志但不返回给前端
      enhanced_logger.logger.debug(
          f"🔇 FILTERED_MESSAGE | researcher | 消息已过滤（不返回前端）"
      )
      return  # 不yield任何事件，直接返回
  ```

### 消息流转过程

```
┌─────────────────┐
│ ResearchTeam    │
│   (节点)        │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ _execute_agent_step                     │
│ - 调用 researcher agent                 │
│ - 执行 agent.ainvoke() 调用大模型       │
│ - 返回 Command 包含消息                 │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ graph.astream()                          │
│ - 以流式模式处理消息                     │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ _stream_graph_events                     │
│ - 处理图中的所有事件                     │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ _process_message_chunk                   │
│ - 🎯 过滤检查点：检查 agent_name         │
│ - 如果是 "researcher" 且过滤开启         │
│   则不返回消息（直接 return）            │
│ - 否则正常处理并yield事件                │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ 前端接收 SSE 事件流                      │
│ - 不会收到 researcher 的中间消息         │
│ - 只收到最终的报告结果                   │
└─────────────────────────────────────────┘
```

## 配置方法

### 环境变量配置

在 `.env` 文件中添加或修改以下配置：

```bash
# 消息过滤配置
# 过滤掉研究智能体（researcher）的流式消息，仅在后台处理，不返回给前端
# 设置为 true 可以减少前端接收到的中间过程消息，只显示最终结果
# 设置为 false 可以看到研究智能体的完整执行过程
FILTER_RESEARCHER_MESSAGES=true
```

### 配置选项

- **`FILTER_RESEARCHER_MESSAGES=true`** (默认)
  - 过滤掉 researcher 智能体的所有流式消息
  - 前端只显示最终的研究报告
  - 适合生产环境，提供简洁的用户体验

- **`FILTER_RESEARCHER_MESSAGES=false`**
  - 显示 researcher 智能体的完整执行过程
  - 前端可以看到搜索、分析等中间步骤
  - 适合开发调试，了解完整的工作流程

## 效果对比

### 启用过滤 (FILTER_RESEARCHER_MESSAGES=true)

前端接收到的消息流：
```
1. 路由节点 → 选择深度研究路径
2. 协调者节点 → 理解用户需求
3. 规划者节点 → 制定研究计划
4. [researcher 节点的消息被过滤，不显示]
5. 报告者节点 → 生成最终报告
```

### 禁用过滤 (FILTER_RESEARCHER_MESSAGES=false)

前端接收到的消息流：
```
1. 路由节点 → 选择深度研究路径
2. 协调者节点 → 理解用户需求
3. 规划者节点 → 制定研究计划
4. researcher 节点 → 调用搜索工具
5. researcher 节点 → 分析搜索结果 1
6. researcher 节点 → 分析搜索结果 2
7. researcher 节点 → 分析搜索结果 3
8. researcher 节点 → 生成研究总结
9. 报告者节点 → 生成最终报告
```

## 日志记录

无论是否过滤，所有消息都会记录到日志中：

```log
# 当过滤启用时，会看到以下日志：
🔇 FILTERED_MESSAGE | researcher | 消息已过滤（不返回前端） | 内容长度: 1234
```

可以通过查看日志文件来了解 researcher 的完整执行过程：
```bash
tail -f logs/deer-flow.log | grep "researcher"
```

## 扩展功能

如果需要过滤其他智能体的消息，可以修改 `_process_message_chunk` 函数中的过滤逻辑：

```python
# 示例：过滤多个智能体
filtered_agents = ["researcher", "coder"]  # 添加需要过滤的智能体
if filter_researcher and agent_name in filtered_agents:
    enhanced_logger.logger.debug(
        f"🔇 FILTERED_MESSAGE | {agent_name} | 消息已过滤（不返回前端）"
    )
    return
```

或者创建更细粒度的过滤规则：

```python
# 示例：只过滤工具调用消息，保留文本消息
if filter_researcher and agent_name == "researcher":
    if isinstance(message_chunk, ToolMessage):
        # 只过滤工具调用结果
        enhanced_logger.logger.debug("🔇 FILTERED_TOOL_MESSAGE | researcher")
        return
    # 文本消息仍然返回
```

## 注意事项

1. **后台处理不受影响**：即使消息被过滤，researcher 智能体仍然正常执行，结果会保存在 state 中供后续节点使用
2. **日志完整性**：所有消息都会记录到日志，方便调试和问题排查
3. **性能优化**：过滤消息可以减少网络传输和前端渲染的负担
4. **用户体验**：启用过滤后，用户只看到最终结果，界面更简洁

## 相关文件

- [`src/server/app.py`](../src/server/app.py) - 消息过滤实现
- [`src/graph/nodes.py`](../src/graph/nodes.py) - 智能体调用和消息生成
- [`src/config/loader.py`](../src/config/loader.py) - 环境变量加载
- [`.env`](../.env) - 环境变量配置文件
