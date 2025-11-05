# 新增节点DEBUG级别日志说明

## 📋 修改概述

为以下4个新增节点添加了大模型输入输出的DEBUG级别日志打印功能：

1. ✅ `direct_answer_node` - 直接回答节点
2. ✅ `simple_search_node` - 简单检索节点  
3. ✅ `domain_knowledge_node` - 领域知识节点
4. ✅ `department_node` - 部门专用节点

## 🎯 修改目标

**问题**: 新增节点的大模型输入输出没有打印，不便于调试

**解决方案**: 添加DEBUG级别的日志，在DEBUG模式下打印：
- 🤖 LLM输入（完整Prompt）
- 🤖 LLM输出（完整响应内容）
- 🤖 Agent输入（department_node专用）
- 🤖 Agent输出（department_node专用）

## 📝 修改详情

### 1. direct_answer_node（直接回答节点）

**文件**: `src/graph/nodes.py` 第115-183行

**修改内容**:
```python
# 生成回答
llm_start = time.time()
llm = get_llm_by_type("basic")

# ✅ 新增：DEBUG级别打印LLM输入
if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
    enhanced_logger.logger.debug(
        f"🤖 LLM_INPUT | direct_answer | Prompt长度: {len(answer_prompt)}\n"
        f"{'='*80}\n{answer_prompt}\n{'='*80}"
    )

response = llm.invoke([{"role": "user", "content": answer_prompt}])
answer = response.content if hasattr(response, 'content') else str(response)
llm_duration = time.time() - llm_start

# ✅ 新增：DEBUG级别打印LLM输出
if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
    enhanced_logger.logger.debug(
        f"🤖 LLM_OUTPUT | direct_answer | 响应长度: {len(answer)}\n"
        f"{'='*80}\n{answer}\n{'='*80}"
    )

enhanced_logger.logger.info(
    f"💬 ANSWER_GENERATED | 长度: {len(answer)} | LLM耗时: {llm_duration:.2f}s"
)
```

**日志示例**:
```
[DEBUG] graph.nodes 🤖 LLM_INPUT | direct_answer | Prompt长度: 256
================================================================================
你是一个专业的知识助手。请用简洁准确的语言回答以下通用知识问题。

**用户问题**: 什么是人工智能？

**回答要求**:
1. 直接回答问题，不超过300字
...
================================================================================

[DEBUG] graph.nodes 🤖 LLM_OUTPUT | direct_answer | 响应长度: 189
================================================================================
人工智能（Artificial Intelligence, AI）是计算机科学的一个分支，旨在创建能够模拟、扩展和辅助人类智能的系统...
================================================================================

[INFO] graph.nodes 💬 ANSWER_GENERATED | 长度: 189 | LLM耗时: 1.23s
```

### 2. simple_search_node（简单检索节点）

**文件**: `src/graph/nodes.py` 第186-271行

**修改内容**:
```python
# 生成回答
llm_start = time.time()
llm = get_llm_by_type("basic")

# ✅ 新增：DEBUG级别打印LLM输入
if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
    enhanced_logger.logger.debug(
        f"🤖 LLM_INPUT | simple_search | Prompt长度: {len(answer_prompt)}\n"
        f"{'='*80}\n{answer_prompt}\n{'='*80}"
    )

response = llm.invoke([{"role": "user", "content": answer_prompt}])
answer = response.content if hasattr(response, 'content') else str(response)
llm_duration = time.time() - llm_start

# ✅ 新增：DEBUG级别打印LLM输出
if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
    enhanced_logger.logger.debug(
        f"🤖 LLM_OUTPUT | simple_search | 响应长度: {len(answer)}\n"
        f"{'='*80}\n{answer}\n{'='*80}"
    )

enhanced_logger.logger.info(
    f"💬 ANSWER_GENERATED | 长度: {len(answer)} | LLM耗时: {llm_duration:.2f}s"
)
```

**日志示例**:
```
[INFO] graph.nodes 🔍 SEARCH_COMPLETE | 结果数: 3 | 耗时: 0.45s

[DEBUG] graph.nodes 🤖 LLM_INPUT | simple_search | Prompt长度: 512
================================================================================
你是一个专业的银行业务知识助手。请基于以下搜索结果，简洁准确地回答用户问题。

**用户问题**: 信用卡如何办理？

**搜索结果**:
[
  {"title": "信用卡办理指南", "content": "..."}
]
...
================================================================================

[DEBUG] graph.nodes 🤖 LLM_OUTPUT | simple_search | 响应长度: 234
================================================================================
办理信用卡主要有以下步骤：

1. **选择银行和卡种**：根据个人需求选择合适的信用卡
2. **准备材料**：身份证、收入证明等
...
================================================================================

[INFO] graph.nodes 💬 ANSWER_GENERATED | 长度: 234 | LLM耗时: 1.56s
```

### 3. domain_knowledge_node（领域知识节点）

**文件**: `src/graph/nodes.py` 第362-451行

**修改内容**:
```python
# 生成回答
llm_start = time.time()
llm = get_llm_by_type("basic")

# ✅ 新增：DEBUG级别打印LLM输入
if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
    enhanced_logger.logger.debug(
        f"🤖 LLM_INPUT | domain_knowledge | Prompt长度: {len(answer_prompt)}\n"
        f"{'='*80}\n{answer_prompt}\n{'='*80}"
    )

response = llm.invoke([{"role": "user", "content": answer_prompt}])
answer = response.content if hasattr(response, 'content') else str(response)
llm_duration = time.time() - llm_start

# ✅ 新增：DEBUG级别打印LLM输出
if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
    enhanced_logger.logger.debug(
        f"🤖 LLM_OUTPUT | domain_knowledge | 响应长度: {len(answer)}\n"
        f"{'='*80}\n{answer}\n{'='*80}"
    )

enhanced_logger.logger.info(
    f"💬 ANSWER_GENERATED | 长度: {len(answer)} | LLM耗时: {llm_duration:.2f}s"
)
```

**日志示例**:
```
[INFO] graph.nodes 📚 USING_LOCAL_RESOURCES | 使用本地知识库检索
[INFO] graph.nodes 🔍 SEARCH_COMPLETE | 结果数: 5

[DEBUG] graph.nodes 🤖 LLM_INPUT | domain_knowledge | Prompt长度: 1024
================================================================================
你是一个专业的银行领域知识专家。请基于以下专业知识库的信息，详细准确地回答用户问题。

**用户问题**: 什么是巴塞尔协议III？

**领域知识库信息**:
[...]
================================================================================

[DEBUG] graph.nodes 🤖 LLM_OUTPUT | domain_knowledge | 响应长度: 567
================================================================================
巴塞尔协议III（Basel III）是2010年巴塞尔银行监管委员会发布的国际银行业监管标准...

1. **资本充足率要求**：
   - 核心一级资本充足率不低于6%
   - 一级资本充足率不低于8%
   ...
================================================================================

[INFO] graph.nodes 💬 ANSWER_GENERATED | 长度: 567 | LLM耗时: 2.34s
```

### 4. department_node（部门专用节点）

**文件**: `src/graph/nodes.py` 第454-538行

**修改内容**:
```python
enhanced_logger.logger.info(
    f"🤖 AGENT_CREATED | 耗时: {agent_create_duration:.2f}s"
)

# ✅ 新增：DEBUG级别打印智能体输入
if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
    enhanced_logger.logger.debug(
        f"🤖 AGENT_INPUT | department | 部门: {department} | 查询长度: {len(query)}\n"
        f"{'='*80}\n{query}\n{'='*80}"
    )

# 调用智能体处理请求
invoke_start = time.time()
result = agent.invoke({
    "messages": [{"role": "user", "content": query}]
})
invoke_duration = time.time() - invoke_start

# 提取输出
output = ""
if isinstance(result, dict) and "messages" in result:
    last_message = result["messages"][-1]
    output = last_message.content if hasattr(last_message, 'content') else str(last_message)
else:
    output = str(result)

# ✅ 新增：DEBUG级别打印智能体输出
if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
    enhanced_logger.logger.debug(
        f"🤖 AGENT_OUTPUT | department | 响应长度: {len(output)}\n"
        f"{'='*80}\n{output}\n{'='*80}"
    )

enhanced_logger.logger.info(
    f"💬 DEPARTMENT_RESPONSE | 长度: {len(output)} | 处理耗时: {invoke_duration:.2f}s"
)
```

**日志示例**:
```
[INFO] graph.nodes 🏢 DEPARTMENT_INFO | 部门: retail | 查询: '零售银行产品有哪些...'
[INFO] graph.nodes 📋 DEPARTMENT_CONFIG | 零售银行部门 | 描述: 处理零售银行业务
[INFO] graph.nodes 🤖 AGENT_CREATED | 耗时: 0.12s

[DEBUG] graph.nodes 🤖 AGENT_INPUT | department | 部门: retail | 查询长度: 28
================================================================================
零售银行产品有哪些？
================================================================================

[DEBUG] graph.nodes 🤖 AGENT_OUTPUT | department | 响应长度: 456
================================================================================
零售银行主要产品包括：

1. **存款类产品**
   - 活期存款
   - 定期存款
   - 通知存款
...
================================================================================

[INFO] graph.nodes 💬 DEPARTMENT_RESPONSE | 长度: 456 | 处理耗时: 2.78s
```

## 🎨 日志颜色方案

根据用户偏好，日志输出使用以下配色：

| 日志级别 | 前面部分 | 后面部分 | 说明 |
|---------|---------|---------|------|
| **INFO** | 🟢 绿色 | 🟣 紫色 | 时间戳、级别、模块用绿色，消息用紫色 |
| **DEBUG** | 🔵 青色 | 🟣 紫色 | DEBUG级别用青色标识 |
| **ERROR** | 🔴 红色 | 🟣 紫色 | 错误用红色标识 |

**示例**:
```
12:34:56 [INFO] graph.nodes | 💬 ANSWER_GENERATED | 长度: 234 | LLM耗时: 1.56s
         ^^^^^ ^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
         绿色   绿色          紫色

12:34:57 [DEBUG] graph.nodes | 🤖 LLM_INPUT | direct_answer | Prompt长度: 256
         ^^^^^^ ^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
         青色    青色           紫色
```

## 🚀 使用方法

### 方法1: 通过环境变量控制

```bash
# 启用DEBUG级别日志
export LOG_LEVEL=DEBUG

# 启动应用
python server.py

# 或者在Docker中
docker-compose up
```

### 方法2: 在`.env`文件中配置

```bash
# .env
LOG_LEVEL=DEBUG
```

### 方法3: 临时启用

```bash
# 仅本次运行启用DEBUG
LOG_LEVEL=DEBUG python server.py
```

## 🧪 测试验证

已创建测试脚本 `test_debug_logs.py`，用于验证DEBUG日志功能：

```bash
# 运行测试
python test_debug_logs.py
```

**测试覆盖**:
- ✅ direct_answer_node 的 LLM 输入/输出日志
- ✅ simple_search_node 的 LLM 输入/输出日志
- ✅ domain_knowledge_node 的 LLM 输入/输出日志
- ✅ department_node 的 Agent 输入/输出日志

## 📊 日志级别说明

### INFO 级别（默认）

显示摘要信息，适合生产环境：

```
[INFO] graph.nodes 🔄 NODE_ENTRY | simple_search | 开始简单检索处理
[INFO] graph.nodes ❓ SIMPLE_SEARCH_QUERY | '信用卡如何办理？'
[INFO] graph.nodes 🔍 SEARCH_COMPLETE | 结果数: 3 | 耗时: 0.45s
[INFO] graph.nodes 💬 ANSWER_GENERATED | 长度: 234 | LLM耗时: 1.56s
[INFO] graph.nodes ✅ NODE_EXIT | simple_search | 节点执行完成 | 总耗时: 2.01s
```

### DEBUG 级别（调试）

显示完整的输入输出内容，适合调试和问题排查：

```
[DEBUG] graph.nodes 🤖 LLM_INPUT | simple_search | Prompt长度: 512
================================================================================
你是一个专业的银行业务知识助手。请基于以下搜索结果，简洁准确地回答用户问题。

**用户问题**: 信用卡如何办理？

**搜索结果**:
[
  {
    "title": "信用卡办理指南",
    "content": "办理信用卡需要准备身份证、收入证明等材料..."
  },
  ...
]

**回答要求**:
1. 直接回答问题，不超过300字
2. 基于搜索结果提供准确信息
3. 使用简洁清晰的语言，适合银行业务场景
4. 必要时可以分点列出
5. 如果信息不足，请说明

请提供你的回答：
================================================================================

[DEBUG] graph.nodes 🤖 LLM_OUTPUT | simple_search | 响应长度: 234
================================================================================
办理信用卡主要有以下步骤：

1. **选择银行和卡种**：根据个人需求选择合适的信用卡产品
2. **准备材料**：
   - 身份证原件及复印件
   - 收入证明（工资单、银行流水等）
   - 工作证明
3. **提交申请**：可通过银行网点、官网或手机APP提交
4. **等待审核**：一般需要3-7个工作日
5. **激活使用**：收到卡片后按提示激活即可使用

建议选择适合自己消费习惯的卡种，并注意按时还款以维护良好的信用记录。
================================================================================

[INFO] graph.nodes 💬 ANSWER_GENERATED | 长度: 234 | LLM耗时: 1.56s
```

## 🎯 关键特性

### 1. 条件日志输出

使用 `isEnabledFor(logging.DEBUG)` 判断，避免在非DEBUG模式下产生性能开销：

```python
if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
    # 仅在DEBUG模式下执行
    enhanced_logger.logger.debug(...)
```

**优点**:
- ✅ 生产环境（INFO级别）不会执行debug代码
- ✅ 避免不必要的字符串格式化开销
- ✅ 性能影响最小化

### 2. 分隔线增强可读性

使用 80 个等号作为分隔线：

```python
f"{'='*80}\n{answer_prompt}\n{'='*80}"
```

**效果**:
```
================================================================================
完整的Prompt内容
================================================================================
```

### 3. 长度信息

在日志中显示内容长度，便于评估：

```python
f"🤖 LLM_INPUT | simple_search | Prompt长度: {len(answer_prompt)}\n"
```

**用途**:
- 评估Token消耗
- 发现过长的Prompt
- 优化提示词设计

### 4. 节点标识

每个日志都包含节点名称，便于追踪：

```python
f"🤖 LLM_INPUT | direct_answer | ..."
f"🤖 LLM_INPUT | simple_search | ..."
f"🤖 LLM_INPUT | domain_knowledge | ..."
f"🤖 AGENT_INPUT | department | ..."
```

## 📈 性能影响

### INFO 级别（生产环境）

- ❌ **不会**执行DEBUG日志代码
- ❌ **不会**进行内容格式化
- ✅ 性能影响：**几乎为0**

### DEBUG 级别（调试环境）

- ✅ 执行DEBUG日志代码
- ✅ 打印完整内容
- ⚠️ 性能影响：**轻微**（主要是I/O开销）

**建议**:
- 生产环境：使用 `LOG_LEVEL=INFO`
- 开发环境：使用 `LOG_LEVEL=DEBUG`
- 问题排查：临时启用 `LOG_LEVEL=DEBUG`

## 🔧 故障排查

### 问题1: DEBUG日志没有显示

**检查**:
```bash
# 1. 确认环境变量
echo $LOG_LEVEL

# 2. 确认.env文件
cat .env | grep LOG_LEVEL

# 3. 确认代码中的设置
python -c "import os; print(os.getenv('LOG_LEVEL', 'INFO'))"
```

**解决**:
```bash
# 设置环境变量
export LOG_LEVEL=DEBUG

# 或修改.env文件
echo "LOG_LEVEL=DEBUG" >> .env

# 重启应用
```

### 问题2: 日志输出太多

**解决**:
```bash
# 仅查看特定节点
export LOG_LEVEL=INFO  # 先关闭DEBUG

# 或使用grep过滤
python server.py 2>&1 | grep "simple_search"
```

### 问题3: 日志没有颜色

**原因**: 可能在不支持ANSI的终端中运行

**解决**:
```bash
# 方案1: 使用支持ANSI的终端
# Windows: Windows Terminal, ConEmu
# Linux: 默认终端都支持
# macOS: Terminal.app, iTerm2

# 方案2: 禁用颜色（如果需要）
# 修改 enhanced_logger.py 中的 enable_colors=False
```

## 📚 相关文件

| 文件 | 说明 |
|------|------|
| `src/graph/nodes.py` | 节点实现（已修改） |
| `src/utils/enhanced_logger.py` | 增强日志模块 |
| `test_debug_logs.py` | DEBUG日志测试脚本 |
| `.env` | 环境变量配置 |

## 🎉 总结

✅ **完成的修改**:
1. 为4个新增节点添加了DEBUG级别的LLM输入输出日志
2. 使用条件判断避免性能影响
3. 遵循用户偏好的绿色+紫色配色方案
4. 添加了详细的分隔线和长度信息
5. 创建了测试脚本用于验证

✅ **达到的目标**:
- 在DEBUG模式下可以看到完整的LLM输入（Prompt）
- 在DEBUG模式下可以看到完整的LLM输出（响应）
- 在INFO模式下仍然保持简洁的摘要信息
- 不影响生产环境的性能

✅ **使用建议**:
- 开发调试：`export LOG_LEVEL=DEBUG`
- 生产环境：`export LOG_LEVEL=INFO`
- 问题排查：临时启用DEBUG级别
