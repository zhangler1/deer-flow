# Planner 节点双重输出和 Interrupt 卡住问题修复总结

## 问题描述

用户报告了两个问题：
1. **planner 节点双重输出**："多主题深度研究计划也输出了两遍"
2. **interrupt 事件导致前端灰色**："卡在 human_feedback，前端是灰色的"

## 根本原因分析

### 1. Planner 双重输出问题

**原因**：与智能路由节点相同的问题

- **LangGraph 的流式机制**：`stream_mode=["messages", "updates"]` 会自动捕获两种输出
  - 第一次：LLM 响应时，LangGraph 自动捕获 `AIMessageChunk`（流式输出）
  - 第二次：节点返回时，手动添加的 `messages: [AIMessage(...)]` 导致重复输出

- **问题位置**：`/src/graph/nodes.py` 的 `planner_node` 函数中三处返回语句
  - **第 770 行**：`goto="human_feedback"` 时（计划包含未执行步骤）
  - **第 783 行**：`goto="reporter"` 时（所有步骤已执行完成）
  - **第 802 行**：`goto="human_feedback"` 时（需要人工审核计划）

### 2. Interrupt 前端灰色问题

**原因**：前端无法正确识别 interrupt 状态

- **问题位置**：`/web/src/core/messages/merge-message.ts` 的 `mergeInterruptMessage` 函数
- **缺失字段**：只设置了 `isStreaming=false` 和 `options`，但没有设置 `finishReason='interrupt'`
- **影响**：前端 UI 无法正确判断消息是否为 interrupt 状态，导致显示灰色

```typescript
// 修改前
function mergeInterruptMessage(message: Message, event: InterruptEvent) {
  message.isStreaming = false;
  message.options = event.data.options;
  // ❌ 缺少 message.finishReason = 'interrupt'
}
```

## 修复方案

### 修复 1：移除 Planner 节点的 messages 更新（3 处）

**文件**：`/src/graph/nodes.py`

#### 第一处修复（第 767-773 行）
```python
# 修改前
return Command(
    update={
        "messages": [AIMessage(content=full_response, name="planner")],  # ❌ 导致双重输出
        "current_plan": new_plan,
    },
    goto="human_feedback",
)

# 修改后
return Command(
    update={
        "current_plan": new_plan,
        # 不添加 messages，让 LangGraph 自动捕获流式响应（避免双重输出）
    },
    goto="human_feedback",
)
```

#### 第二处修复（第 776-782 行）
```python
# 修改前
return Command(
    update={
        "messages": [AIMessage(content=full_response, name="planner")],  # ❌ 导致双重输出
        "current_plan": new_plan,
    },
    goto="reporter",
)

# 修改后
return Command(
    update={
        "current_plan": new_plan,
        # 不添加 messages，让 LangGraph 自动捕获流式响应（避免双重输出）
    },
    goto="reporter",
)
```

#### 第三处修复（第 797-803 行）
```python
# 修改前
return Command(
    update={
        "messages": [AIMessage(content=full_response, name="planner")],  # ❌ 导致双重输出
        "current_plan": full_response,
    },
    goto="human_feedback",
)

# 修改后
return Command(
    update={
        "current_plan": full_response,
        # 不添加 messages，让 LangGraph 自动捕获流式响应（避免双重输出）
    },
    goto="human_feedback",
)
```

### 修复 2：补充 Interrupt 事件的 finishReason 字段

**文件**：`/web/src/core/messages/merge-message.ts`

```typescript
// 修改前（第 101-104 行）
function mergeInterruptMessage(message: Message, event: InterruptEvent) {
  message.isStreaming = false;
  message.options = event.data.options;
  // ❌ 缺少 finishReason
}

// 修改后
function mergeInterruptMessage(message: Message, event: InterruptEvent) {
  message.isStreaming = false;
  message.finishReason = "interrupt";  // ✅ 设置 finishReason 为 interrupt
  message.options = event.data.options;
}
```

## 修复后的流程

### 正常的流式输出流程（无重复）

1. **LLM 响应流式输出**
   - LangGraph 自动捕获 `AIMessageChunk`
   - 前端接收 `message_chunk` 事件
   - 逐步累积消息内容

2. **节点完成**
   - 节点返回 `Command` 只更新状态（不添加 messages）
   - LangGraph 不会产生额外的消息事件

3. **前端显示**
   - 只显示一次完整的流式输出
   - 无重复内容

### Interrupt 事件正确处理流程

1. **后端发送 interrupt 事件**
   ```python
   {
       "type": "interrupt",
       "data": {
           "id": "...",
           "thread_id": "...",
           "role": "assistant",
           "content": "...",
           "finish_reason": "interrupt",  # ← 关键字段
           "options": [...]
       }
   }
   ```

2. **前端接收并合并**
   ```typescript
   mergeInterruptMessage(message, event) {
     message.isStreaming = false;
     message.finishReason = "interrupt";  // ✅ 正确设置
     message.options = event.data.options;
   }
   ```

3. **前端 UI 显示**
   - `useLastInterruptMessage()` 检查 `finishReason === "interrupt"`
   - 正确显示交互按钮（"Edit plan", "Start research"）
   - 前端不再是灰色，显示正常

## 验证方法

### 1. 验证双重输出已修复

**测试步骤**：
1. 启动后端和前端服务
2. 发送一个需要多主题深度研究的问题
3. 观察 planner 节点的输出

**预期结果**：
- 后端日志显示一次完整的流式输出
- 前端只显示一次"多主题深度研究计划"
- 无重复内容

### 2. 验证 interrupt 事件正常工作

**测试步骤**：
1. 发送一个需要人工审核的问题
2. 等待 planner 节点完成并跳转到 human_feedback
3. 观察前端显示

**预期结果**：
- 前端显示正常（非灰色）
- 显示"Edit plan"和"Start research"按钮
- 按钮可以正常点击交互

## 相关文件

### 后端修改
- `/src/graph/nodes.py` - 移除 planner_node 的 3 处 messages 更新

### 前端修改
- `/web/src/core/messages/merge-message.ts` - 添加 finishReason 字段

## 技术总结

### LangGraph 流式机制最佳实践

✅ **推荐做法**：
- 节点返回时只更新状态字段（如 `current_plan`），不添加 `messages`
- 让 LangGraph 自动捕获 LLM 的流式响应
- 对于非 LLM 调用（如分类模型），使用日志输出而非添加到 messages

❌ **避免做法**：
- 不要在节点返回时手动添加 `messages: [AIMessage(...)]`
- 不要同时依赖自动捕获和手动添加

### Interrupt 事件处理最佳实践

✅ **完整的 interrupt 消息结构**：
```typescript
{
  isStreaming: false,
  finishReason: "interrupt",  // ← 必须字段
  options: [...],             // ← 交互选项
  content: "...",
}
```

### 已修复的节点列表

1. ✅ direct_answer_node（智能路由）
2. ✅ simple_search_node（智能路由）
3. ✅ domain_knowledge_node（智能路由）
4. ✅ department_node（智能路由）
5. ✅ planner_node（深度研究计划）

## 后续建议

1. **代码审查**：检查其他节点是否存在相同问题
2. **单元测试**：为流式输出和 interrupt 事件添加测试用例
3. **文档更新**：在开发文档中记录这个最佳实践
4. **监控告警**：添加前端监控，检测 finishReason 缺失的情况

---

**修复日期**：2025-11-17
**修复人员**：AI Assistant
**验证状态**：待用户验证
