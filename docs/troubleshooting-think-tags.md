# 🔍 问题诊断：为什么框架调用 Planner 会输出 `<think>` 标签

## 📋 问题描述

用户报告：普通调用 LLM 的 planner 时没有 `<think>` 标签，但在 DeerFlow 框架中使用 planner 时就会出现思考标签。

## 🎯 根本原因

### 1️⃣ 前端深度思考开关

DeerFlow 前端聊天界面有一个 **"深度思考"（Deep Thinking）** 功能开关：

- **位置**：`web/src/app/chat/components/input-box.tsx` 第 292-319 行
- **UI 表现**：💡 图标按钮，激活时显示蓝色边框
- **参数名**：`enable_deep_thinking`
- **默认值**：`false`
- **持久化**：保存在浏览器 `localStorage` 中（key: `deerflow.settings`）

```typescript
// web/src/core/store/settings-store.ts
const DEFAULT_SETTINGS: SettingsState = {
  general: {
    enableDeepThinking: false,  // 默认关闭
    // ...
  },
};
```

### 2️⃣ 后端 LLM 类型切换

当前端传递 `enable_deep_thinking=true` 时，后端 planner 节点会切换 LLM 类型：

```python
# src/graph/nodes.py 第 715-722 行
if configurable.enable_deep_thinking:
    llm = get_llm_by_type("reasoning")  # 使用 DeepSeek/DashScope 等 reasoning 模型
    enhanced_logger.logger.info("🧠 PLANNER_CONFIG | 使用 reasoning LLM（已禁用 thinking 模式避免 <think> 标签）")
elif AGENT_LLM_MAP["planner"] == "basic":
    llm = get_llm_by_type("basic")
    enhanced_logger.logger.info("🔧 PLANNER_CONFIG | 使用basic LLM不带structured_output，启用字段修复机制")
else:
    llm = get_llm_by_type(AGENT_LLM_MAP["planner"])
```

### 3️⃣ Reasoning 模型的 Thinking 特性

Reasoning 模型（如 DeepSeek-R1、DashScope Reasoning）支持输出思考过程：

- **DeepSeek**：通过 `extra_body.enable_thinking` 控制
- **DashScope**：通过 `extra_body.enable_thinking` 控制
- **默认行为**：某些模型可能默认输出 `<think>` 标签

### 4️⃣ 参数传递链路

```
用户点击💡按钮
    ↓
前端 localStorage 保存 enableDeepThinking=true
    ↓
前端调用 chatStream() 传递 enable_deep_thinking=true
    ↓
后端接收 ChatStreamRequest.enable_deep_thinking=true
    ↓
传递给 LangGraph Configuration.enable_deep_thinking=true
    ↓
planner_node 使用 reasoning LLM
    ↓
LLM 输出包含 <think>...</think>
```

## 🔧 解决方案

### 方案 1：前端关闭深度思考开关（立即生效）

**操作步骤**：

1. 打开 DeerFlow 聊天界面
2. 找到输入框上方的 **💡 深度思考** 按钮
3. 如果按钮是**高亮状态**（蓝色边框），点击关闭它
4. 刷新页面，重新提问

**验证**：按钮应该变成普通的灰色边框状态。

---

### 方案 2：清除浏览器设置（推荐）

**浏览器控制台操作**：

```javascript
// 打开浏览器开发者工具（F12）
// 在 Console 中执行：
localStorage.removeItem('deerflow.settings');
location.reload();
```

**手动操作**：

1. 打开浏览器开发者工具（F12）
2. 切换到 **Application** 标签
3. 左侧菜单：**Storage** → **Local Storage** → 选择你的域名
4. 找到 `deerflow.settings`，右键删除
5. 刷新页面

---

### 方案 3：后端强制禁用 Thinking 模式（已实施）

**修改内容**：`src/llms/llm.py` 第 283-302 行

```python
# DashScope reasoning 模型
if "base_url" in merged_conf and "dashscope." in merged_conf["base_url"]:
    merged_conf["extra_body"] = {"enable_thinking": False}  # 🎯 强制禁用
    return ChatDashscope(**merged_conf)

# DeepSeek reasoning 模型
if llm_type == "reasoning":
    merged_conf["api_base"] = merged_conf.pop("base_url", None)
    if "extra_body" not in merged_conf:
        merged_conf["extra_body"] = {}
    merged_conf["extra_body"]["enable_thinking"] = False  # 🎯 强制禁用
    return ChatDeepSeek(**merged_conf)
```

**需要重启服务**：

```bash
# 停止服务
pkill -f "python.*main.py"

# 重新启动
python main.py
```

---

### 方案 4：SSE 输出层过滤（已实施，双重保险）

**修改内容**：`src/server/app.py` 第 171-221 行

即使 LLM 输出了 `<think>` 标签，SSE 层也会过滤：

```python
# app.py _create_event_stream_message 函数
if agent_name == "planner" or langgraph_node == "planner":
    if content:
        # 1. 过滤 <think> 标签
        if "<think>" in str(content).lower():
            from src.utils.text_utils import remove_think_tags
            logger.info(f"[SSE_FILTER] Filtering <think> tags from planner response")
            content = remove_think_tags(content)
            
        # 2. 过滤 Markdown 代码块
        if "```" in str(content):
            from src.utils.text_utils import remove_markdown_code_blocks
            logger.info(f"[SSE_FILTER] Filtering markdown code blocks from planner response")
            content = remove_markdown_code_blocks(content)
```

---

## 🔍 诊断方法

### 1. 检查前端设置

**浏览器控制台**：

```javascript
// 查看当前设置
JSON.parse(localStorage.getItem('deerflow.settings'))

// 应该看到：
{
  "general": {
    "enableDeepThinking": false,  // ✅ 应该是 false
    "autoAcceptedPlan": false,
    // ...
  }
}
```

### 2. 检查后端日志

启动服务后，查看日志中的关键信息：

```bash
# 查看 planner 使用的 LLM 类型
grep "PLANNER_CONFIG" logs/app.log

# 应该看到以下之一：
# ✅ 正常：使用 basic/advanced LLM
# 🧠 PLANNER_CONFIG | 使用 basic LLM不带structured_output，启用字段修复机制

# ⚠️ 异常：使用 reasoning LLM
# 🧠 PLANNER_CONFIG | 使用 reasoning LLM（已禁用 thinking 模式避免 <think> 标签）
```

### 3. 检查前端请求

**浏览器 Network 标签**：

1. 打开开发者工具 → **Network** 标签
2. 发送一条消息
3. 找到 `/api/chat/stream` 请求
4. 查看 **Payload** / **Request Payload**
5. 检查 `enable_deep_thinking` 字段：

```json
{
  "messages": [...],
  "enable_deep_thinking": false,  // ✅ 应该是 false
  "thread_id": "...",
  // ...
}
```

---

## 🎓 技术原理

### 为什么框架调用和普通调用不同？

| 对比项 | 普通 API 调用 | DeerFlow 框架调用 |
|--------|--------------|------------------|
| **LLM 类型** | 固定使用某个模型 | 根据 `enable_deep_thinking` 动态切换 |
| **参数控制** | 手动设置 `enable_thinking` | 前端 UI 控制（可能被用户开启） |
| **持久化** | 无（代码硬编码） | 有（浏览器 localStorage） |
| **用户感知** | 开发者控制 | 用户点击按钮就会改变 |

### 为什么需要深度思考功能？

深度思考（Deep Thinking）使用 Reasoning 模型进行更深入的规划分析：

- **优势**：更详细的研究计划，考虑更多边缘情况
- **劣势**：
  - 速度较慢
  - 可能输出 `<think>` 标签污染 JSON
  - 成本更高

**建议**：
- ✅ 简单问题：关闭深度思考，使用 basic/advanced LLM
- 🧠 复杂研究：开启深度思考，使用 reasoning LLM（但需要过滤 `<think>` 标签）

---

## ✅ 验证修复

修复后，验证以下内容：

1. **前端**：💡 深度思考按钮是灰色（未激活）
2. **localStorage**：`enableDeepThinking: false`
3. **后端日志**：使用 basic/advanced LLM，而不是 reasoning LLM
4. **前端收到的内容**：不包含 `<think>` 标签
5. **JSON 解析**：planner 返回的 JSON 可以正常解析

---

## 📝 总结

**问题根源**：用户（或测试时）点击了前端的 **💡 深度思考** 按钮，导致：
- `enableDeepThinking` 被保存为 `true` 在 localStorage
- 后端切换到 reasoning LLM
- Reasoning LLM 可能输出 `<think>` 标签

**根本解决**：
- ✅ 前端关闭深度思考开关
- ✅ 清除 localStorage 设置
- ✅ 后端强制禁用 thinking 模式（多层防护）

**防护机制**（三层）：
1. **LLM 配置层**：`llm.py` 强制 `enable_thinking=False`
2. **节点处理层**：`nodes.py` 过滤 `<think>` 标签用于 JSON 解析
3. **SSE 输出层**：`app.py` 二次过滤确保前端收到干净数据

---

## 🔗 相关文件

- `/web/src/app/chat/components/input-box.tsx` - 前端深度思考按钮
- `/web/src/core/store/settings-store.ts` - 前端设置存储
- `/src/graph/nodes.py` - Planner 节点 LLM 类型选择
- `/src/llms/llm.py` - LLM 配置和 thinking 模式控制
- `/src/server/app.py` - SSE 输出过滤
- `/src/utils/text_utils.py` - 文本过滤工具函数
