# 系统背景上下文注入机制分析

## 📊 当前实现概览

### 注入位置

系统背景上下文 (`system_context`) 目前在 **API 层**注入，具体位置在 [`src/server/app.py`](file:///home/llm/zhangle/deer-flow/src/server/app.py#L369-L378) 的 `_astream_workflow_generator` 函数中。

```python
# 在第一条用户消息中添加系统背景
if system_context and messages:
    enhanced_logger.logger.info(f"🏛️ SYSTEM_CONTEXT | 注入系统背景上下文: {system_context}")
    first_user_message = messages[0]
    if isinstance(first_user_message, dict) and first_user_message.get("role") == "user":
        original_content = first_user_message.get("content", "")
        # 将系统背景添加在用户问题之前
        first_user_message["content"] = f"[系统背景上下文: {system_context}]\n\n{original_content}"
        enhanced_logger.logger.info(f"✅ CONTEXT_INJECTED | 背景已注入到用户消息中")
```

### 数据流向

```
用户请求
  ↓
API 接口 (/api/chat/stream)
  ↓
_astream_workflow_generator
  ├─ 注入 system_context 到第一条用户消息  ← 【当前注入点】
  ├─ 传递到 workflow_input["system_context"]
  └─ 传递到 workflow_config["configurable"]["system_context"]
  ↓
LangGraph 工作流
  ├─ State.system_context
  └─ Configuration.system_context
  ↓
各个节点（router, coordinator, planner, researcher, reporter）
```

---

## 🎯 问题分析

### ⚠️ 当前方案的问题

#### 1. **注入时机过早，影响智能路由**

**问题**：在 API 层直接修改用户消息，会影响智能路由分类器的判断。

```python
# 修改前：原始用户问题
"信用卡如何申请？"

# 修改后：包含系统背景
"[系统背景上下文: 问题关于交通银行]\n\n信用卡如何申请？"
```

**影响**：
- ❌ 智能路由分类器 ([`classifier.py`](file:///home/llm/zhangle/deer-flow/src/graph/classifier.py)) 收到的是**已修改的消息**
- ❌ 可能导致分类不准确（长度增加、关键词稀释）
- ❌ 路由决策基于污染的输入

#### 2. **消息内容被永久修改**

**问题**：直接修改 `messages[0]["content"]` 是**原地修改**，会影响后续所有节点。

```python
# API 层修改后，所有节点看到的都是修改后的消息
first_user_message["content"] = f"[系统背景上下文: {system_context}]\n\n{original_content}"
```

**影响**：
- ❌ 无法恢复原始问题
- ❌ 所有智能体都看到带系统背景的问题
- ❌ 可能干扰 LLM 的理解（特别是简单问题）

#### 3. **职责不清晰**

**问题**：API 层不应该修改业务逻辑相关的内容。

- ❌ API 层应该负责：请求解析、参数验证、流式输出
- ❌ 不应该负责：消息内容修改、业务逻辑处理

#### 4. **缺乏灵活性**

**问题**：硬编码的注入格式，不同场景无法定制。

```python
# 固定格式
f"[系统背景上下文: {system_context}]\n\n{original_content}"
```

**影响**：
- ❌ 不同节点可能需要不同的背景格式
- ❌ 某些节点可能不需要背景
- ❌ 无法根据路径动态调整

---

## ✅ 推荐方案

### 方案 1：在 Prompt Template 中注入（推荐） ⭐️

**原理**：在各个节点的 Prompt 模板中引用 `system_context`，而不是修改用户消息。

#### 实现方式

1. **保持用户消息原始**
   ```python
   # app.py - 移除消息修改代码
   # ❌ 删除以下代码
   # first_user_message["content"] = f"[系统背景上下文: {system_context}]\n\n{original_content}"
   
   # ✅ 只传递 system_context 到配置
   workflow_input = {
       "system_context": system_context,
       # ...
   }
   ```

2. **在 Prompt Template 中使用**
   ```markdown
   <!-- coordinator.md -->
   {% if system_context %}
   **系统背景**: {{ system_context }}
   {% endif %}
   
   **用户查询**: {{ messages[-1].content }}
   ```

3. **各节点按需使用**
   - ✅ Router 节点：不使用，保持原始问题用于分类
   - ✅ Coordinator 节点：使用，理解业务背景
   - ✅ Planner 节点：使用，生成针对性计划
   - ✅ Researcher 节点：使用，执行领域相关搜索
   - ✅ Reporter 节点：使用，撰写符合背景的报告

#### 优势

- ✅ **不修改用户消息**，保持数据纯净
- ✅ **智能路由不受影响**，基于原始问题分类
- ✅ **灵活可控**，每个节点决定是否使用
- ✅ **职责清晰**，API 层只传递参数
- ✅ **易于测试**，可以单独测试每个节点

---

### 方案 2：在 State 中动态组装

**原理**：在每个节点执行时，动态组装包含背景的消息。

#### 实现方式

```python
# nodes.py - 在需要的节点中动态组装
def coordinator_node(state: State, config: RunnableConfig):
    system_context = state.get("system_context", "")
    user_query = state["messages"][-1].content
    
    # 动态组装提示
    if system_context:
        enhanced_prompt = f"系统背景: {system_context}\n\n用户问题: {user_query}"
    else:
        enhanced_prompt = user_query
    
    # 使用组装后的提示
    messages = [{"role": "user", "content": enhanced_prompt}]
    response = llm.invoke(messages)
    # ...
```

#### 优势

- ✅ 不修改原始消息
- ✅ 每个节点可以自定义格式
- ✅ 按需组装

#### 劣势

- ❌ 代码重复（每个节点都要组装）
- ❌ 不如 Prompt Template 优雅

---

### 方案 3：在智能路由后注入（折中方案）

**原理**：先完成智能路由分类，再根据路径决定是否注入背景。

#### 实现方式

```python
# router_node 执行后，根据路径注入
def router_node(state: State, config: RunnableConfig):
    # 1. 基于原始消息进行分类
    route_decision = classify_request(state["messages"][-1].content)
    
    # 2. 如果需要系统背景（如深度研究、领域知识）
    if route_decision.path in ["deep_research", "domain_knowledge"]:
        system_context = state.get("system_context", "")
        if system_context:
            # 此时才注入背景
            state["messages"][-1].content = f"[{system_context}] {state['messages'][-1].content}"
    
    # 3. 返回路由决策
    return Command(goto=route_decision.path)
```

#### 优势

- ✅ 智能路由不受影响
- ✅ 按路径决定是否注入

#### 劣势

- ❌ 仍然修改了消息
- ❌ 逻辑复杂

---

## 📋 对比表

| 方案 | 智能路由影响 | 消息纯净度 | 灵活性 | 实现复杂度 | 推荐度 |
|------|-------------|-----------|--------|-----------|--------|
| **当前方案**（API层注入） | ❌ 严重 | ❌ 污染 | ❌ 低 | ⭐ 简单 | ⭐ 不推荐 |
| **方案1**（Prompt模板） | ✅ 无影响 | ✅ 纯净 | ✅✅ 高 | ⭐⭐ 中等 | ⭐⭐⭐⭐⭐ **强烈推荐** |
| **方案2**（State动态组装） | ✅ 无影响 | ✅ 纯净 | ✅ 中 | ⭐⭐⭐ 复杂 | ⭐⭐⭐ 推荐 |
| **方案3**（路由后注入） | ✅ 无影响 | ⚠️ 部分污染 | ✅ 中 | ⭐⭐ 中等 | ⭐⭐ 可选 |

---

## 🔧 推荐实施步骤

### 步骤 1：移除 API 层的消息修改

```python
# src/server/app.py - 删除以下代码
# if system_context and messages:
#     first_user_message["content"] = f"[系统背景上下文: {system_context}]\n\n{original_content}"
```

### 步骤 2：更新 Prompt Templates

在需要系统背景的 Prompt 模板中添加：

```markdown
<!-- src/prompts/coordinator.md -->
{% if SYSTEM_CONTEXT %}
**系统背景**: {{ SYSTEM_CONTEXT }}
{% endif %}

**用户查询**: {{ research_topic }}
```

### 步骤 3：在 apply_prompt_template 中传递

```python
# src/prompts/utils.py (假设存在此文件)
def apply_prompt_template(template_name, state):
    template_vars = {
        "SYSTEM_CONTEXT": state.get("system_context", ""),
        "research_topic": state.get("research_topic", ""),
        # ... 其他变量
    }
    # 渲染模板
    return render_template(template_name, **template_vars)
```

### 步骤 4：测试验证

1. **验证智能路由**：确保分类基于原始问题
2. **验证节点输出**：确认背景正确传递
3. **验证多轮对话**：确保背景不重复添加

---

## 🎯 最佳实践建议

### 1. 系统背景的使用原则

- ✅ **Router节点**：不使用，保持分类准确性
- ✅ **Coordinator节点**：使用，理解业务上下文
- ✅ **Planner节点**：使用，制定针对性计划
- ✅ **Researcher节点**：使用，执行领域搜索
- ✅ **Reporter节点**：使用，撰写相关报告

### 2. 配置化设计

```yaml
# conf.yaml
SYSTEM_CONTEXT:
  enabled: true
  default: "问题关于交通银行"
  inject_at_nodes:
    - coordinator
    - planner
    - researcher
    - reporter
  exclude_nodes:
    - router
```

### 3. 日志跟踪

```python
enhanced_logger.logger.info(
    f"🏛️ SYSTEM_CONTEXT | 节点: {node_name} | "
    f"使用背景: {bool(system_context)} | "
    f"背景内容: {system_context[:50]}..."
)
```

---

## 📊 影响范围分析

### 受影响的文件

1. **[`src/server/app.py`](file:///home/llm/zhangle/deer-flow/src/server/app.py)** - 需要移除消息修改代码
2. **[`src/graph/types.py`](file:///home/llm/zhangle/deer-flow/src/graph/types.py)** - State 定义（保持不变）
3. **[`src/config/configuration.py`](file:///home/llm/zhangle/deer-flow/src/config/configuration.py)** - Configuration 定义（保持不变）
4. **`src/prompts/*.md`** - 需要更新 Prompt 模板
5. **`src/prompts/utils.py`** - 需要更新模板渲染逻辑

### 兼容性影响

- ✅ **向后兼容**：不影响现有 API 调用
- ✅ **行为改进**：智能路由更准确
- ✅ **功能增强**：节点可以按需使用背景

---

## 🔍 测试用例

### 用例 1：通用知识问题（不应受背景影响）

```bash
# 问题
"什么是汽车？"

# 期望路由
direct_answer

# 期望行为
- Router 基于原始问题分类
- Direct Answer 节点可能不使用背景
```

### 用例 2：银行业务问题（应使用背景）

```bash
# 问题
"信用卡如何申请？"

# 系统背景
"问题关于交通银行"

# 期望路由
simple_search

# 期望行为
- Router 基于原始问题分类
- Simple Search 节点使用背景进行搜索
- 回答包含交通银行相关信息
```

### 用例 3：深度研究问题（全程使用背景）

```bash
# 问题
"分析金融科技对传统银行的影响"

# 系统背景
"问题关于交通银行"

# 期望路由
deep_research

# 期望行为
- Router 基于原始问题分类
- Coordinator 理解交通银行背景
- Planner 制定针对交通银行的计划
- Researcher 搜索交通银行相关案例
- Reporter 撰写交通银行视角的报告
```

---

## 💡 结论

### 当前方案的主要问题

1. ❌ **注入时机过早**，影响智能路由准确性
2. ❌ **修改用户消息**，污染原始数据
3. ❌ **职责不清**，API 层不应处理业务逻辑
4. ❌ **缺乏灵活性**，无法按节点定制

### 推荐改进方案

**采用方案 1（Prompt Template 注入）**：

- ✅ 在 Prompt 模板中引用 `system_context`
- ✅ 保持用户消息原始不变
- ✅ 各节点按需使用背景
- ✅ 智能路由不受影响

### 实施优先级

1. **高优先级**：移除 API 层的消息修改
2. **高优先级**：更新 Coordinator/Planner 的 Prompt 模板
3. **中优先级**：更新 Researcher/Reporter 的 Prompt 模板
4. **低优先级**：配置化设计、日志增强

---

**文档版本**: v1.0  
**创建日期**: 2025-01-04  
**作者**: DeerFlow Team
