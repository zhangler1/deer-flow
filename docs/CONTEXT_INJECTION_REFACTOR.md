# 系统背景注入机制重构总结

## 🎯 重构目标

将系统背景注入机制从 **API层直接修改用户消息** 重构为 **通过State传递，在Prompt Template中按需使用**。

## 📋 重构前后对比

### ❌ 重构前（存在问题）

```python
# src/server/app.py - API层直接修改用户消息
if system_context and messages:
    first_user_message = messages[0]
    if isinstance(first_user_message, dict) and first_user_message.get("role") == "user":
        original_content = first_user_message.get("content", "")
        # ❌ 直接修改用户消息
        first_user_message["content"] = f"[系统背景上下文: {system_context}]\n\n{original_content}"
```

**问题**：
1. ❌ **影响智能路由** - Router节点收到的是已修改的消息，导致分类不准确
2. ❌ **污染原始数据** - 用户消息被永久修改，无法恢复
3. ❌ **职责不清** - API层不应修改业务逻辑相关内容
4. ❌ **缺乏灵活性** - 硬编码格式，无法按节点定制

### ✅ 重构后（推荐方案）

```python
# src/server/app.py - 只传递system_context，不修改消息
if system_context:
    enhanced_logger.logger.info(
        f"🏛️ SYSTEM_CONTEXT | 系统背景已配置: {system_context} | "
        f"将通过State传递给工作流节点"
    )

# 通过State和Configuration传递
workflow_input = {
    "system_context": system_context,  # 传递给State
    # ...
}

workflow_config = {
    "configurable": {
        "system_context": system_context,  # 传递给Configuration
        # ...
    }
}
```

**优势**：
1. ✅ **不影响智能路由** - Router基于原始问题分类
2. ✅ **保持数据纯净** - 用户消息始终保持原始状态
3. ✅ **职责清晰** - API层只负责参数传递
4. ✅ **灵活可控** - 各节点在Prompt Template中按需使用

## 🔧 重构内容

### 1. 移除API层的消息修改

**文件**: [`src/server/app.py`](file:///home/llm/zhangle/deer-flow/src/server/app.py)

**修改前**:
```python
# 在第一条用户消息中添加系统背景
if system_context and messages:
    enhanced_logger.logger.info(f"🏛️ SYSTEM_CONTEXT | 注入系统背景上下文: {system_context}")
    first_user_message = messages[0]
    if isinstance(first_user_message, dict) and first_user_message.get("role") == "user":
        original_content = first_user_message.get("content", "")
        first_user_message["content"] = f"[系统背景上下文: {system_context}]\n\n{original_content}"
        enhanced_logger.logger.info(f"✅ CONTEXT_INJECTED | 背景已注入到用户消息中")
```

**修改后**:
```python
# system_context 通过 State 和 Configuration 传递给各节点
# 各节点在 Prompt Template 中按需使用，不在此处修改用户消息
if system_context:
    enhanced_logger.logger.info(
        f"🏛️ SYSTEM_CONTEXT | 系统背景已配置: {system_context} | "
        f"将通过State传递给工作流节点"
    )
```

**影响**: 不再修改用户消息，保持原始数据纯净

### 2. 更新配置类注释

**文件**: [`src/config/configuration.py`](file:///home/llm/zhangle/deer-flow/src/config/configuration.py)

**修改前**:
```python
system_context: str = ""  # 系统背景上下文，会自动添加到用户查询中
```

**修改后**:
```python
system_context: str = ""  # 系统背景上下文，通过State传递给各节点，在Prompt Template中按需使用
```

### 3. 更新State类注释

**文件**: [`src/graph/types.py`](file:///home/llm/zhangle/deer-flow/src/graph/types.py)

**修改前**:
```python
system_context: str = ""  # 系统背景上下文，会自动添加到所有查询中
```

**修改后**:
```python
system_context: str = ""  # 系统背景上下文，各节点在Prompt Template中按需使用（不修改用户消息）
```

## 📊 数据流向对比

### 重构前

```
用户请求
  ↓
API 接口
  ↓
_astream_workflow_generator
  ├─ ❌ 修改 messages[0]["content"]  ← 污染原始数据
  ├─ 传递到 State.system_context
  └─ 传递到 Configuration.system_context
  ↓
LangGraph 工作流
  ├─ Router (收到已修改的消息) ❌ 影响分类
  ├─ Coordinator
  ├─ Planner
  └─ ...
```

### 重构后

```
用户请求
  ↓
API 接口
  ↓
_astream_workflow_generator
  ├─ ✅ 保持 messages 原始不变
  ├─ 传递到 State.system_context
  └─ 传递到 Configuration.system_context
  ↓
LangGraph 工作流
  ├─ Router (基于原始消息分类) ✅ 准确
  ├─ Coordinator (在Prompt中使用背景)
  ├─ Planner (在Prompt中使用背景)
  └─ ...
```

## 🎨 各节点使用建议

### Router 节点 - ❌ 不使用

**原因**: 需要基于原始用户问题进行准确分类

```python
# router_node 不使用 system_context
def router_node(state: State, config: RunnableConfig):
    user_query = state.get("research_topic") or state["messages"][-1].content
    # 直接使用原始问题进行分类
    route_decision = classify_request(query=user_query, ...)
    return Command(goto=route_decision.path)
```

### Coordinator 节点 - ✅ 使用

**原因**: 需要理解业务背景以决定工作流走向

```markdown
<!-- src/prompts/coordinator.md -->
你是一个专业的研究协调员。

{% if system_context %}
**系统背景**: {{ system_context }}
{% endif %}

**用户查询**: {{ research_topic }}

请分析用户需求...
```

### Planner 节点 - ✅ 使用

**原因**: 需要制定针对特定背景的研究计划

```markdown
<!-- src/prompts/planner.md -->
{% if system_context %}
**业务背景**: {{ system_context }}

请基于以上业务背景制定研究计划。
{% endif %}

**研究主题**: {{ research_topic }}
```

### Researcher 节点 - ✅ 使用

**原因**: 执行领域相关的搜索

```python
# 在搜索查询中包含背景信息
def researcher_node(state: State, config: RunnableConfig):
    system_context = state.get("system_context", "")
    search_query = state.get("research_topic", "")
    
    if system_context:
        # 增强搜索查询
        enhanced_query = f"{system_context} {search_query}"
        search_results = search_tool.invoke(enhanced_query)
```

### Reporter 节点 - ✅ 使用

**原因**: 撰写符合特定背景的报告

```markdown
<!-- src/prompts/reporter.md -->
{% if system_context %}
**报告背景**: {{ system_context }}

请确保报告内容与以上背景相关。
{% endif %}

**研究发现**: {{ observations }}
```

## ✅ 重构验证

### 测试用例 1: 通用知识问题

```python
# 输入
messages = [{"role": "user", "content": "什么是汽车？"}]
system_context = "问题关于交通银行"

# 预期行为
# 1. Router 基于原始问题 "什么是汽车？" 进行分类
# 2. 路由到 direct_answer_node（不需要银行背景）
# 3. Direct Answer 节点可能不使用 system_context
```

### 测试用例 2: 银行业务问题

```python
# 输入
messages = [{"role": "user", "content": "信用卡如何申请？"}]
system_context = "问题关于交通银行"

# 预期行为
# 1. Router 基于原始问题 "信用卡如何申请？" 进行分类
# 2. 路由到 simple_search_node
# 3. Simple Search 在搜索时包含 "交通银行" 背景
# 4. 回答包含交通银行信用卡申请流程
```

### 测试用例 3: 深度研究问题

```python
# 输入
messages = [{"role": "user", "content": "分析金融科技对传统银行的影响"}]
system_context = "问题关于交通银行"

# 预期行为
# 1. Router 基于原始问题进行分类
# 2. 路由到 deep_research (coordinator)
# 3. Coordinator 在 Prompt 中看到 "问题关于交通银行"
# 4. Planner 制定针对交通银行的研究计划
# 5. Researcher 搜索交通银行相关案例
# 6. Reporter 从交通银行视角撰写报告
```

## 📝 后续工作（可选）

### 1. 更新 Prompt Templates

需要在以下模板中添加 `system_context` 支持：

- [ ] `src/prompts/coordinator.md`
- [ ] `src/prompts/planner.md`
- [ ] `src/prompts/researcher.md`
- [ ] `src/prompts/reporter.md`

**示例模板**:
```markdown
{% if system_context %}
**系统背景**: {{ system_context }}

请基于以上业务背景进行处理。
{% endif %}

**用户查询**: {{ research_topic }}
```

### 2. 验证 apply_prompt_template 传递

确保 `src/prompts/template.py` 中的 `apply_prompt_template` 函数正确传递 `system_context`:

```python
def apply_prompt_template(template_name, state, config):
    template_vars = {
        "system_context": state.get("system_context", ""),
        "research_topic": state.get("research_topic", ""),
        # ... 其他变量
    }
    # 渲染模板
    return render_template(template_name, **template_vars)
```

### 3. 配置化设计（未来增强）

```yaml
# conf.yaml (可选)
SYSTEM_CONTEXT:
  enabled: true
  default: "问题关于交通银行"
  use_in_nodes:
    - coordinator
    - planner
    - researcher
    - reporter
  exclude_nodes:
    - router
```

## 🎯 重构总结

### 核心改进

1. ✅ **移除消息修改** - 不再在API层修改用户消息
2. ✅ **保持数据纯净** - messages 始终保持原始状态
3. ✅ **智能路由准确** - Router基于原始问题分类
4. ✅ **灵活按需使用** - 各节点在Prompt中决定是否使用背景

### 关键原则

- **API层职责**: 参数验证、数据传递、流式输出
- **State职责**: 状态管理、数据共享
- **Prompt职责**: 业务逻辑、背景应用

### 兼容性

- ✅ **向后兼容** - 不影响现有API调用
- ✅ **行为改进** - 智能路由更准确
- ✅ **功能增强** - 节点可按需使用背景

---

**重构日期**: 2025-01-05  
**影响文件**: 
- `src/server/app.py` (✅ 已修改)
- `src/config/configuration.py` (✅ 已修改)
- `src/graph/types.py` (✅ 已修改)

**下一步**: 根据需要更新各节点的 Prompt Templates
