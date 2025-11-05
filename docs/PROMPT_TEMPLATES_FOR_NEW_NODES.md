# 新增节点 Prompt 模板配置说明

## 📋 问题说明

### 当前状况

新增的4个节点（`direct_answer_node`, `simple_search_node`, `domain_knowledge_node`, `department_node`）目前**直接在代码中硬编码 Prompt**，而不是使用项目的 Prompt 模板系统。

### 为什么这是个问题？

| 问题 | 影响 |
|------|------|
| **不符合架构设计** | 其他节点（coordinator, planner, researcher, reporter）都使用模板系统 |
| **维护困难** | Prompt 修改需要改代码，无法灵活配置 |
| **测试困难** | 无法独立测试 Prompt 效果 |
| **缺乏版本控制** | Prompt 变更与代码耦合 |
| **协作不便** | 非技术人员无法优化 Prompt |

### 对比：现有节点的做法

**✅ 现有节点（如 coordinator）**:
```python
# src/graph/nodes.py
messages = apply_prompt_template("coordinator", dict(state))
response = llm.invoke(messages)
```

**❌ 新增节点（如 direct_answer）**:
```python
# src/graph/nodes.py
answer_prompt = f"""你是一个专业的知识助手。请用简洁准确的语言回答以下通用知识问题。

**用户问题**: {query}

**回答要求**:
1. 直接回答问题，不超过300字
...（硬编码在代码中）
"""
response = llm.invoke([{"role": "user", "content": answer_prompt}])
```

---

## ✅ 解决方案

### 1️⃣ 创建 Prompt 模板文件

我已经为4个节点创建了完整的 Prompt 模板：

| 节点 | 模板文件 | 特点 |
|------|----------|------|
| `direct_answer_node` | [`src/prompts/direct_answer.md`](file:///home/llm/zhangle/deer-flow/src/prompts/direct_answer.md) | 通用知识，简洁回答 |
| `simple_search_node` | [`src/prompts/simple_search.md`](file:///home/llm/zhangle/deer-flow/src/prompts/simple_search.md) | 银行业务，单次检索 |
| `domain_knowledge_node` | [`src/prompts/domain_knowledge.md`](file:///home/llm/zhangle/deer-flow/src/prompts/domain_knowledge.md) | 专业知识，详细解析 |
| `department_node` | [`src/prompts/department.md`](file:///home/llm/zhangle/deer-flow/src/prompts/department.md) | 部门定制，场景适配 |

### 2️⃣ 模板特点

#### 📝 direct_answer.md (115行)
```markdown
# 直接回答助手 - Direct Answer Assistant

你是一个专业的知识助手，擅长利用通用知识直接回答用户的常识性问题。

## 你的角色
- **定位**: 通用知识助手
- **特点**: 快速、准确、简洁
- **目标**: 基于LLM的通用知识库直接提供答案，无需额外检索

## 回答准则

{% if system_context %}
## 系统背景上下文
{{ system_context }}
{% endif %}

### 1. 字数限制
- 回答不超过 **300字**
...
```

**关键特性**:
- ✅ 支持 `system_context` 变量
- ✅ 支持 `messages` 变量（用户问题）
- ✅ 支持 `CURRENT_TIME` 变量
- ✅ 提供详细的回答示例
- ✅ 明确角色定位和回答准则

#### 📝 simple_search.md (176行)
```markdown
# 简单检索助手 - Simple Search Assistant

你是一个专业的银行业务知识助手，擅长基于搜索结果快速回答银行业务的常规问题。

## 你的角色
- **定位**: 银行业务问答专家（主流路径）
- **特点**: 快速、准确、业务导向
...

### 1. 信息来源

你将收到以下搜索结果作为信息来源：

**搜索结果内容**:
{{ search_results if search_results else "暂无搜索结果" }}
...
```

**关键特性**:
- ✅ 支持 `search_results` 变量（搜索结果）
- ✅ 银行业务场景优化
- ✅ 提供结构化回答指导
- ✅ 包含信息不足时的处理方式

#### 📝 domain_knowledge.md (290行)
```markdown
# 领域知识助手 - Domain Knowledge Assistant

你是一个专业的银行领域知识专家，擅长处理高度专业化的银行业务知识问题。

## 你的角色
- **定位**: 银行专业知识专家
- **特点**: 深度、专业、权威
...

**知识库内容**:
{{ search_results if search_results else "暂无知识库内容" }}

{% if resources %}
**本地资源**: 已配置 {{ resources|length }} 个专业知识资源
{% else %}
**知识来源**: 专业网络检索（针对性搜索）
{% endif %}
...
```

**关键特性**:
- ✅ 支持 `resources` 变量（本地知识库）
- ✅ 支持 `search_results` 变量
- ✅ 字数限制更宽松（500-800字）
- ✅ 提供详细的专业示例（如巴塞尔协议、SWIFT报文）

#### 📝 department.md (467行)
```markdown
# 部门专用助手 - Department Assistant

你是一个针对特定部门优化的银行业务助手，能够根据用户所属部门提供定制化的服务。

## 支持的部门类型

### 1. 零售业务部门 (retail)
### 2. 对公业务部门 (corporate)
### 3. 风险管理部门 (risk)
### 4. 金融市场部门 (market)
### 5. 运营管理部门 (operation)
### 6. 科技部门 (technology)
### 7. 综合/其他 (general)

**用户部门**: {{ user_department if user_department else "general" }}

{% if department_context %}
**部门上下文**:
{{ department_context }}
{% endif %}
...
```

**关键特性**:
- ✅ 支持 `user_department` 变量
- ✅ 支持 `department_context` 变量
- ✅ 针对7种部门提供定制化指导
- ✅ 包含每个部门的专业示例

---

## 🔧 如何修改节点代码

### 修改步骤

#### 1. direct_answer_node

**修改前** (硬编码):
```python
def direct_answer_node(state: State, config: RunnableConfig) -> Command[Literal["__end__"]]:
    # ...
    answer_prompt = f"""你是一个专业的知识助手。请用简洁准确的语言回答以下通用知识问题。

**用户问题**: {query}

**回答要求**:
1. 直接回答问题，不超过300字
...
"""
    response = llm.invoke([{"role": "user", "content": answer_prompt}])
```

**修改后** (使用模板):
```python
def direct_answer_node(state: State, config: RunnableConfig) -> Command[Literal["__end__"]]:
    # ...
    configurable = Configuration.from_runnable_config(config)
    
    # 使用 Prompt 模板
    try:
        messages_for_llm = apply_prompt_template(
            "direct_answer",
            dict(state),
            configurable
        )
    except Exception as e:
        logger.error(f"应用Prompt模板失败: {e}")
        # 备用方案
        messages_for_llm = [
            {"role": "user", "content": f"请简洁准确地回答以下问题（不超过300字）: {query}"}
        ]
    
    response = llm.invoke(messages_for_llm)
```

#### 2. simple_search_node

**需要添加的数据**:
```python
# 准备模板变量
state_with_search = dict(state)
state_with_search['search_results'] = search_results  # 添加搜索结果

messages_for_llm = apply_prompt_template(
    "simple_search",
    state_with_search,
    configurable
)
```

#### 3. domain_knowledge_node

**需要添加的数据**:
```python
# 准备模板变量
state_with_knowledge = dict(state)
state_with_knowledge['search_results'] = search_results
# resources 已经在 state 中

messages_for_llm = apply_prompt_template(
    "domain_knowledge",
    state_with_knowledge,
    configurable
)
```

#### 4. department_node

**需要添加的数据**:
```python
# 准备模板变量
state_with_department = dict(state)
state_with_department['search_results'] = search_results
# user_department 和 department_context 已经在 state 中

messages_for_llm = apply_prompt_template(
    "department",
    state_with_department,
    configurable
)
```

---

## 📊 模板变量映射

### 所有节点共用的变量

| 变量名 | 来源 | 说明 |
|--------|------|------|
| `messages` | `state['messages']` | 用户对话消息 |
| `system_context` | `state['system_context']` 或 `configurable.system_context` | 系统背景上下文 |
| `CURRENT_TIME` | 自动注入 | 当前时间 |

### direct_answer 特定变量

| 变量名 | 来源 | 说明 |
|--------|------|------|
| `messages[-1].content` | `state['messages']` | 最新用户问题 |

### simple_search 特定变量

| 变量名 | 来源 | 说明 |
|--------|------|------|
| `search_results` | 添加到 state | 搜索结果（JSON格式） |

### domain_knowledge 特定变量

| 变量名 | 来源 | 说明 |
|--------|------|------|
| `search_results` | 添加到 state | 知识库搜索结果 |
| `resources` | `state['resources']` | 本地知识资源列表 |

### department 特定变量

| 变量名 | 来源 | 说明 |
|--------|------|------|
| `user_department` | `state['user_department']` | 用户所属部门 |
| `department_context` | `state['department_context']` | 部门特定上下文 |
| `search_results` | 添加到 state | 搜索结果 |

---

## ✅ 优势对比

### 修改前（硬编码）

| 方面 | 问题 |
|------|------|
| **Prompt 修改** | ❌ 需要修改代码，重新部署 |
| **版本控制** | ❌ Prompt 变更与代码耦合 |
| **测试** | ❌ 无法独立测试 Prompt |
| **协作** | ❌ 非技术人员无法优化 |
| **多语言支持** | ❌ 困难 |
| **A/B测试** | ❌ 不支持 |

### 修改后（使用模板）

| 方面 | 优势 |
|------|------|
| **Prompt 修改** | ✅ 只需修改 .md 文件，重启服务 |
| **版本控制** | ✅ Prompt 独立版本管理 |
| **测试** | ✅ 可以独立测试不同版本 |
| **协作** | ✅ 产品经理可以直接优化 |
| **多语言支持** | ✅ 容易支持 |
| **A/B测试** | ✅ 可以切换不同模板 |

---

## 🎯 实施建议

### 阶段1：验证模板（推荐先做）

1. **测试单个节点**
   ```python
   # 测试 direct_answer 模板
   from src.prompts.template import get_prompt_template
   
   template_content = get_prompt_template("direct_answer")
   print(template_content)
   ```

2. **验证变量替换**
   ```python
   from src.prompts.template import apply_prompt_template
   
   test_state = {
       "messages": [{"role": "user", "content": "什么是人工智能？"}],
       "system_context": "这是测试背景"
   }
   
   messages = apply_prompt_template("direct_answer", test_state)
   print(messages)
   ```

### 阶段2：逐个节点迁移

**建议顺序**:
1. ✅ direct_answer_node（最简单，无额外变量）
2. ✅ simple_search_node（需要添加 search_results）
3. ✅ domain_knowledge_node（需要添加 search_results 和 resources）
4. ✅ department_node（最复杂，多个变量）

### 阶段3：测试和验证

1. **单元测试**
   - 测试模板加载
   - 测试变量替换
   - 测试异常处理

2. **集成测试**
   - 测试完整节点执行
   - 验证输出质量
   - 对比修改前后效果

3. **回归测试**
   - 确保原有功能不受影响
   - 验证各路径正常工作

---

## 📝 模板维护指南

### 修改 Prompt 模板

1. **编辑模板文件**
   ```bash
   # 例如修改 direct_answer 模板
   vim src/prompts/direct_answer.md
   ```

2. **测试模板**
   ```bash
   # 运行测试脚本
   python test_prompt_templates.py
   ```

3. **重启服务**
   ```bash
   # 重启后端服务
   python -m src.server.app
   ```

### 版本控制

```bash
# 提交 Prompt 变更
git add src/prompts/direct_answer.md
git commit -m "优化 direct_answer 模板的回答结构"

# 代码和 Prompt 分开管理
git log --oneline -- src/prompts/
```

### A/B 测试

```python
# 可以创建多个版本
src/prompts/
  ├── direct_answer.md        # 版本A
  ├── direct_answer_v2.md     # 版本B
  
# 在代码中动态选择
template_name = "direct_answer" if use_version_a else "direct_answer_v2"
messages = apply_prompt_template(template_name, state, configurable)
```

---

## 📚 相关文件

### 新创建的文件
- [`src/prompts/direct_answer.md`](file:///home/llm/zhangle/deer-flow/src/prompts/direct_answer.md) - 115行
- [`src/prompts/simple_search.md`](file:///home/llm/zhangle/deer-flow/src/prompts/simple_search.md) - 176行
- [`src/prompts/domain_knowledge.md`](file:///home/llm/zhangle/deer-flow/src/prompts/domain_knowledge.md) - 290行
- [`src/prompts/department.md`](file:///home/llm/zhangle/deer-flow/src/prompts/department.md) - 467行

### 需要修改的文件
- [`src/graph/nodes.py`](file:///home/llm/zhangle/deer-flow/src/graph/nodes.py) - 4个节点函数

### 参考文件
- [`src/prompts/template.py`](file:///home/llm/zhangle/deer-flow/src/prompts/template.py) - 模板加载器
- [`src/prompts/coordinator.md`](file:///home/llm/zhangle/deer-flow/src/prompts/coordinator.md) - 参考示例
- [`src/prompts/planner.md`](file:///home/llm/zhangle/deer-flow/src/prompts/planner.md) - 参考示例

---

## 🎬 下一步行动

### 立即可做
1. ✅ 已创建4个 Prompt 模板文件
2. ⏳ 修改 nodes.py 中的4个节点函数
3. ⏳ 测试模板加载和变量替换
4. ⏳ 验证节点执行效果

### 长期优化
1. 📝 收集用户反馈，优化 Prompt 内容
2. 🔄 支持多语言模板（中文/英文）
3. 📊 建立 Prompt 效果评估机制
4. 🧪 实施 A/B 测试框架

---

## 版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| 1.0 | 2025-11-05 | 创建4个节点的 Prompt 模板，编写实施指南 |

---

**总结**: 我已经为4个新增节点创建了完整的 Prompt 模板，现在需要修改 `src/graph/nodes.py` 文件，让这些节点使用模板系统而不是硬编码 Prompt。这样可以提高可维护性、支持协作和版本控制。
