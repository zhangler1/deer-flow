# Researcher节点卡住问题修复方案

## 问题描述

用户报告两个现象:
1. **Qwen3 0.6B**: researcher可以返回,但不进行检索
2. **Qwen2.5 72B**: 进行了检索但卡在researcher → research_team转换

## 根本原因

### 原因1: ReAct Agent缺少明确的终止指令

当前`researcher.md` prompt中虽然限制了"最多2次搜索",但没有明确告诉模型:
- ✅ **何时停止工具调用**
- ✅ **如何表示任务完成**
- ✅ **最终输出的格式要求**

LangGraph的`create_react_agent`依赖模型自主判断何时停止,但不同模型的理解能力不同:
- **小模型(0.6B)**: 理解能力弱,直接跳过工具调用
- **大模型(72B)**: 调用工具后不知何时结束,陷入循环

### 原因2: 递归限制可能过高

当前默认递归限制为25次:
```python
default_recursion_limit = 25
```

这给了模型太多"尝试"的机会,导致:
- 模型可能重复调用工具
- 即使找到答案也不停止
- 超时或资源耗尽

### 原因3: Prompt缺少"完成信号"

ReAct Agent需要模型明确输出"我已完成"的信号,当前prompt缺少这方面的指导。

## 解决方案

### 方案A: 优化Researcher Prompt (推荐)

在`src/prompts/researcher.md`中添加明确的终止指令:

```markdown
# 执行规则

1. **搜索限制**: 严格最多执行2次搜索操作
2. **完成条件**: 满足以下任一条件时,立即停止工具调用并输出最终报告:
   - 已完成2次搜索
   - 收集到足够信息回答问题
   - 工具返回错误或无结果
3. **终止信号**: 当你准备好提供最终答案时,**直接输出Markdown格式的研究报告**,不要再调用任何工具

# 输出格式

**重要**: 当你收集完信息后,直接输出以下格式的Markdown文本,这将标志任务完成:

```markdown
## 问题陈述
[重新陈述问题]

## 研究发现
[你的发现]

## 结论
[综合回应]

## 参考文献
- [来源标题](URL)
```

**不要**在输出最终报告后继续调用工具。
```

### 方案B: 降低递归限制

修改`src/graph/nodes.py`中的递归限制:

```python
# 当前值
default_recursion_limit = 25

# 建议修改为
default_recursion_limit = 10  # 对于2次搜索+输出,10次足够
```

或通过环境变量设置:
```bash
export AGENT_RECURSION_LIMIT=10
```

### 方案C: 添加超时保护

在`_execute_agent_step`中添加超时机制:

```python
import asyncio

# 设置超时时间(例如60秒)
try:
    result = await asyncio.wait_for(
        agent.ainvoke(input=agent_input, config={"recursion_limit": recursion_limit}),
        timeout=60.0
    )
except asyncio.TimeoutError:
    enhanced_logger.logger.error(f"❌ AGENT_TIMEOUT | {agent_name} | 执行超时")
    # 返回部分结果或错误提示
    response_content = "研究超时,请重试或简化问题"
```

### 方案D: 强制工具调用次数限制

修改`create_react_agent`的配置,添加max_iterations参数:

```python
# 在src/agents/agents.py中
return create_react_agent(
    name=agent_name,
    model=chat_model,
    tools=tools,
    prompt=lambda state: apply_prompt_template(prompt_template, state),
    max_iterations=5,  # 强制最多5轮迭代
)
```

注意: LangGraph的`create_react_agent`可能不支持此参数,需要查看文档。

## 推荐实施步骤

### 步骤1: 立即修复 - 优化Prompt (最有效)

修改`src/prompts/researcher.md`,添加明确的终止指令和输出格式要求。

### 步骤2: 安全措施 - 降低递归限制

设置环境变量:
```bash
export AGENT_RECURSION_LIMIT=10
```

### 步骤3: 长期优化 - 添加超时保护

在代码中添加超时机制,防止无限等待。

## 验证方法

修复后,观察日志中是否出现:

```
✅ AGENT_COMPLETE | researcher | 智能体执行完成 | 耗时: X.XXs
✅ STEP_COMPLETE | researcher | 步骤执行完成: '步骤标题'
✅ AGENT_STEP_EXIT | researcher | 步骤执行总耗时: X.XXs
✅ NODE_EXIT | researcher | 节点执行完成 | 总耗时: X.XXs
🔀 TRANSITION_DECISION | research_team → reporter | 原因: 所有步骤已完成
```

如果卡住,会看到:
- 长时间没有`AGENT_COMPLETE`日志
- 或持续出现工具调用日志但没有结束

## 调试技巧

1. **查看日志**:
```bash
# 查看researcher节点的执行流程
tail -f logs/app.log | grep "researcher"
```

2. **检查execution_res**:
在`_execute_agent_step`的第760行后添加调试日志:
```python
current_step.execution_res = response_content
print(f"DEBUG: Step '{current_step.title}' execution_res length: {len(response_content)}")
print(f"DEBUG: execution_res content preview: {response_content[:200]}")
```

3. **验证状态转换**:
在`continue_to_running_research_team`中添加调试:
```python
print(f"DEBUG: Checking steps completion...")
for i, step in enumerate(plan_steps):
    has_res = bool(getattr(step, 'execution_res', None))
    print(f"DEBUG: Step {i+1} '{step.title}' - has result: {has_res}")
```

## 常见错误模式

### 错误1: 模型重复调用同一工具
**症状**: 日志中出现多次相同的web_search调用
**原因**: 模型认为结果不够,继续搜索
**解决**: 加强prompt中"2次搜索后必须输出"的指令

### 错误2: 模型在工具调用后不输出
**症状**: 工具调用成功但没有最终输出
**原因**: 模型不知道如何结束ReAct循环
**解决**: 在prompt中明确"输出Markdown报告即表示完成"

### 错误3: execution_res为空
**症状**: 步骤标记为完成但内容为空
**原因**: 模型只调用了工具,没有生成总结
**解决**: 要求模型"基于工具结果生成完整报告"

## 参考资料

- LangGraph ReAct Agent文档: https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/
- 记忆知识: "Planner与Researcher协作机制"
- 相关issue: Researcher无限循环问题
