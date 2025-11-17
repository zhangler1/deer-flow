# 智能路由节点内联显示实现说明

## 概述
智能路由节点（direct_answer_node、simple_search_node、domain_knowledge_node、department_node）现在会像 coordinator 节点处理简单问题（如"你好"）一样，直接在对话框中以普通消息气泡的形式显示，而不是弹出右侧面板。

## 实现原理

### 1. 消息类型定义
**文件**: `/web/src/core/messages/types.ts`

在 Message 接口的 agent 字段中添加了智能路由节点类型：
```typescript
agent?:
  | "coordinator"
  | "planner"
  | "researcher"
  | "coder"
  | "reporter"
  | "podcast"
  | "direct_answer_node"      // 直接回答节点
  | "simple_search_node"      // 简单检索节点
  | "domain_knowledge_node"   // 领域知识节点
  | "department_node";        // 部门专用节点
```

### 2. API 事件类型定义
**文件**: `/web/src/core/api/types.ts`

更新了后端事件流的 agent 类型定义，确保前端能正确接收智能路由节点的消息。

### 3. 消息过滤逻辑
**文件**: `/web/src/app/chat/components/message-list-view.tsx`

在 `visibleMessages` 的过滤条件中添加了智能路由节点类型（第 91-113 行）：
```typescript
// 检查是否应该渲染这个消息
// 用户消息、coordinator、planner、podcast、深度研究节点、智能路由节点都应该显示
if (!(
  message.role === "user" ||
  message.agent === "coordinator" ||
  message.agent === "planner" ||
  message.agent === "podcast" ||
  message.agent === "direct_answer_node" ||
  message.agent === "simple_search_node" ||
  message.agent === "domain_knowledge_node" ||
  message.agent === "department_node" ||
  startOfResearch
)) {
  return null;
}
```

### 4. 消息渲染逻辑
**文件**: `/web/src/app/chat/components/message-list-view.tsx`

在 `MessageListItem` 组件中（第 175-220 行），智能路由节点会走 `else` 分支，使用 `MessageBubble` 组件渲染为普通消息气泡：

```typescript
// planner → 使用 PlanCard（卡片）
if (message.agent === "planner") {
  content = <PlanCard ... />;
}
// podcast → 使用 PodcastCard（卡片）
else if (message.agent === "podcast") {
  content = <PodcastCard ... />;
}
// 深度研究起始节点 → 使用 ResearchCard（卡片）
else if (startOfResearch) {
  content = <ResearchCard ... />;
}
// 其他节点（包括 coordinator 和智能路由节点）→ 使用 MessageBubble（气泡）
else {
  content = (
    <MessageBubble message={message}>
      <Markdown>{message?.content}</Markdown>
    </MessageBubble>
  );
}
```

### 5. 状态管理
**文件**: `/web/src/core/store/store.ts`

在 `appendMessage` 函数中，智能路由节点不会触发右侧面板弹出：
```typescript
function appendMessage(message: Message) {
  // 只有深度研究节点使用 Research Panel
  const deepResearchAgents = ["coder", "reporter", "researcher", "planner"];
  
  if (message.agent && deepResearchAgents.includes(message.agent)) {
    // 触发右侧面板
    if (!getOngoingResearchId()) {
      appendResearch(id);
      openResearch(id);
    }
  }
  // 智能路由节点直接作为普通消息显示，不触发任何特殊处理
  
  useStore.getState().appendMessage(message);
}
```

## 展示效果

### 深度研究模式（使用右侧面板）
- **触发条件**: planner、researcher、coder、reporter 节点
- **显示方式**: 左侧显示 ResearchCard，右侧弹出 ResearchBlock 面板
- **用例**: 复杂问题、需要多步骤检索和分析

### 智能路由模式（内联显示）
- **触发条件**: coordinator、direct_answer_node、simple_search_node、domain_knowledge_node、department_node
- **显示方式**: 直接在左侧消息列表中显示为 AI 回复气泡
- **用例**: 简单问题（如"你好"）、直接回答、快速检索

## 示例对比

### 用户输入: "你好"
```
Coordinator → direct_answer_node
显示效果: 左侧显示一个 AI 回复气泡，内容为简单的问候语
不弹出右侧面板 ✓
```

### 用户输入: "深入分析 XXX 的技术架构"
```
Coordinator → planner → researcher → reporter
显示效果: 左侧显示 ResearchCard，右侧弹出详细的研究面板
展示完整的研究过程 ✓
```

## 测试建议

1. **简单问题测试**: 输入"你好"、"谢谢"等，应该看到普通消息气泡
2. **直接回答测试**: 输入简单的事实性问题，direct_answer_node 应该内联显示
3. **简单检索测试**: 输入需要快速查询的问题，simple_search_node 应该内联显示
4. **深度研究测试**: 输入复杂的研究问题，应该弹出右侧面板

## 注意事项

- 所有智能路由节点的 `role` 应该设置为 `"assistant"`，以便使用正确的消息气泡样式
- 消息内容支持 Markdown 格式
- 流式传输时会实时更新消息内容（通过 `message.isStreaming` 控制）
