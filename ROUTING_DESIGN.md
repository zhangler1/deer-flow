# DeerFlow 智能路由系统设计方案

## 📋 设计概述

本方案为DeerFlow添加智能路由系统，支持根据用户部门和问题复杂度自动选择最优处理路径。

## 🎯 核心目标

1. **部门级分类**：根据用户部门（技术部、市场部、财务部等）路由到专门节点
2. **复杂度分类**：区分简单问答和深度研究任务
3. **路径多样化**：支持简单问答路径、深度研究路径、部门专用路径

## 🏗️ 架构设计

### 新增组件

```
┌─────────────────────────────────────────────────────────────┐
│                      User Input                              │
│              (提示词 + 部门信息)                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Router Node (路由节点)                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Classifier Model (分类模型)                          │  │
│  │  - 问题复杂度评估                                      │  │
│  │  - 部门适配性分析                                      │  │
│  │  - 路径推荐                                            │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────┬───────────────┬──────────────┬──────────────────┘
            │               │              │
            ▼               ▼              ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Simple QA    │  │ Deep Research│  │ Department   │
    │ 简单问答路径  │  │ 深度研究路径  │  │ Specific     │
    │              │  │              │  │ 部门专用路径  │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Direct Answer│  │ Multi-Agent  │  │ Custom Agent │
    │ 直接回答      │  │ Research     │  │ 部门智能体    │
    └──────────────┘  └──────────────┘  └──────────────┘
```

## 📊 数据模型扩展

### State 扩展
```python
class State(MessagesState):
    # 现有字段...
    locale: str = "en-US"
    research_topic: str = ""
    
    # 新增字段
    user_department: str = ""  # 用户部门
    query_complexity: str = "unknown"  # simple/medium/complex
    routing_path: str = "auto"  # simple_qa/deep_research/department_specific
    department_context: dict = {}  # 部门特定上下文
```

### 分类结果模型
```python
@dataclass
class RouteDecision:
    """路由决策结果"""
    path: str  # 路由路径：simple_qa, deep_research, department_specific
    complexity: str  # 复杂度：simple, medium, complex
    department_match: bool  # 部门匹配度
    confidence: float  # 置信度
    reasoning: str  # 决策理由
```

## 🔧 实现细节

### 1. 路由节点 (Router Node)

```python
# src/graph/nodes.py

def router_node(
    state: State, config: RunnableConfig
) -> Command[Literal["simple_qa_node", "coordinator", "department_node"]]:
    """智能路由节点，分析用户请求并决定处理路径"""
    
    enhanced_logger.logger.info("🔀 NODE_ENTRY | router | 开始路由分析")
    
    # 提取用户信息
    user_query = state.get("research_topic") or state["messages"][-1].content
    user_department = state.get("user_department", "general")
    
    # 调用分类模型
    route_decision = classify_request(
        query=user_query,
        department=user_department,
        config=config
    )
    
    # 记录路由决策
    enhanced_logger.logger.info(
        f"🎯 ROUTING_DECISION | 路径: {route_decision.path} | "
        f"复杂度: {route_decision.complexity} | "
        f"置信度: {route_decision.confidence:.2f} | "
        f"理由: {route_decision.reasoning}"
    )
    
    # 更新状态
    state_update = {
        "query_complexity": route_decision.complexity,
        "routing_path": route_decision.path,
    }
    
    # 根据决策路由
    if route_decision.path == "simple_qa":
        return Command(update=state_update, goto="simple_qa_node")
    elif route_decision.path == "department_specific":
        return Command(update=state_update, goto="department_node")
    else:  # deep_research
        return Command(update=state_update, goto="coordinator")
```

### 2. 分类模型 (Classifier)

```python
# src/graph/classifier.py

from pydantic import BaseModel, Field
from src.llms.llm import get_llm_by_type

class RouteDecision(BaseModel):
    """路由决策模型"""
    path: str = Field(description="路由路径: simple_qa, deep_research, department_specific")
    complexity: str = Field(description="问题复杂度: simple, medium, complex")
    department_match: bool = Field(description="是否需要部门专用处理")
    confidence: float = Field(description="决策置信度 0-1")
    reasoning: str = Field(description="决策理由")

def classify_request(query: str, department: str, config: RunnableConfig) -> RouteDecision:
    """使用LLM对用户请求进行分类"""
    
    classification_prompt = f"""你是一个智能路由分类器。分析用户的查询请求，并决定最合适的处理路径。

用户部门: {department}
用户查询: {query}

请根据以下规则进行分类:

1. **简单问答 (simple_qa)**: 
   - 事实性问题，可通过单次搜索回答
   - 定义、解释类问题
   - 简单计算或数据查询
   - 例如: "什么是AI?"、"今天天气如何?"、"Python如何定义函数?"

2. **深度研究 (deep_research)**:
   - 需要多步骤分析的复杂问题
   - 需要综合多个来源信息
   - 研究性、分析性问题
   - 例如: "分析AI在医疗行业的应用趋势"、"对比三种技术方案的优劣"

3. **部门专用 (department_specific)**:
   - 与特定部门高度相关的专业问题
   - 需要部门特定知识库或工具
   - 技术部: 代码分析、系统架构
   - 市场部: 市场调研、竞品分析
   - 财务部: 财务分析、成本核算

请提供你的分类决策和理由。
"""

    llm = get_llm_by_type("basic").with_structured_output(RouteDecision)
    result = llm.invoke([{"role": "user", "content": classification_prompt}])
    
    return result
```

### 3. 简单问答节点 (Simple QA Node)

```python
# src/graph/nodes.py

def simple_qa_node(state: State, config: RunnableConfig) -> Command[Literal["__end__"]]:
    """简单问答节点 - 单次搜索并直接回答"""
    
    enhanced_logger.logger.info("🔄 NODE_ENTRY | simple_qa | 开始简单问答处理")
    start_time = time.time()
    
    configurable = Configuration.from_runnable_config(config)
    query = state.get("research_topic") or state["messages"][-1].content
    
    # 单次搜索
    search_results = get_web_search_tool(
        max_results=3,  # 简单问答只需少量结果
        search_engine=configurable.search_engine,
        custom_search_repository=configurable.custom_search_repository
    ).invoke(query)
    
    # 构建回答提示词
    answer_prompt = f"""基于以下搜索结果，简洁准确地回答用户问题。

用户问题: {query}

搜索结果:
{json.dumps(search_results, ensure_ascii=False, indent=2)}

请提供简洁、准确的答案，不超过200字。如果搜索结果不足以回答问题，请说明。
"""
    
    # 生成回答
    llm = get_llm_by_type("basic")
    response = llm.invoke([{"role": "user", "content": answer_prompt}])
    answer = response.content if hasattr(response, 'content') else str(response)
    
    duration = time.time() - start_time
    enhanced_logger.logger.info(
        f"✅ NODE_EXIT | simple_qa | 节点执行完成 | 耗时: {duration:.2f}s"
    )
    
    return Command(
        update={
            "final_report": answer,
            "messages": [AIMessage(content=answer)]
        },
        goto="__end__"
    )
```

### 4. 部门专用节点 (Department Node)

```python
# src/graph/nodes.py

def department_node(
    state: State, config: RunnableConfig
) -> Command[Literal["__end__"]]:
    """部门专用处理节点"""
    
    enhanced_logger.logger.info("🔄 NODE_ENTRY | department | 开始部门专用处理")
    
    department = state.get("user_department", "general")
    query = state.get("research_topic") or state["messages"][-1].content
    
    # 根据部门选择专用工具和提示词
    department_config = get_department_config(department)
    
    # 使用部门专用智能体
    agent = create_department_agent(
        department=department,
        tools=department_config["tools"],
        prompt_template=department_config["prompt"]
    )
    
    result = agent.invoke({
        "messages": [{"role": "user", "content": query}],
        "department_context": department_config["context"]
    })
    
    enhanced_logger.logger.info("✅ NODE_EXIT | department | 部门专用处理完成")
    
    return Command(
        update={"final_report": result["output"]},
        goto="__end__"
    )

def get_department_config(department: str) -> dict:
    """获取部门专用配置"""
    
    configs = {
        "tech": {
            "tools": [python_repl_tool, get_web_search_tool(5, "tavily")],
            "prompt": "你是技术部的专业助手，擅长代码分析、系统架构设计和技术方案评估。",
            "context": {"domain": "technology", "expertise": ["coding", "architecture"]}
        },
        "marketing": {
            "tools": [get_web_search_tool(7, "tavily")],
            "prompt": "你是市场部的专业助手，擅长市场分析、竞品研究和营销策略。",
            "context": {"domain": "marketing", "expertise": ["analysis", "strategy"]}
        },
        "finance": {
            "tools": [python_repl_tool, get_web_search_tool(5, "tavily")],
            "prompt": "你是财务部的专业助手，擅长财务分析、成本核算和数据报表。",
            "context": {"domain": "finance", "expertise": ["analysis", "reporting"]}
        },
        "general": {
            "tools": [get_web_search_tool(5, "tavily")],
            "prompt": "你是一个通用助手，提供各类问题的专业解答。",
            "context": {"domain": "general", "expertise": ["general"]}
        }
    }
    
    return configs.get(department, configs["general"])
```

### 5. 图构建器更新

```python
# src/graph/builder.py

def _build_base_graph():
    """构建包含智能路由的基础图"""
    builder = StateGraph(State)
    
    # 起始节点改为router
    builder.add_edge(START, "router")
    
    # 添加路由节点
    builder.add_node("router", router_node)
    
    # 添加简单问答节点
    builder.add_node("simple_qa_node", simple_qa_node)
    
    # 添加部门专用节点
    builder.add_node("department_node", department_node)
    
    # 原有的深度研究路径节点
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("background_investigator", background_investigation_node)
    builder.add_node("planner", planner_node)
    builder.add_node("reporter", reporter_node)
    builder.add_node("research_team", research_team_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("human_feedback", human_feedback_node)
    
    # 深度研究路径的边（保持不变）
    builder.add_edge("background_investigator", "planner")
    builder.add_conditional_edges(
        "research_team",
        continue_to_running_research_team,
        ["planner", "researcher", "reporter"],
    )
    builder.add_edge("reporter", END)
    
    # 简单问答和部门节点直接结束
    builder.add_edge("simple_qa_node", END)
    builder.add_edge("department_node", END)
    
    return builder
```

## 🎨 前端集成

### 用户界面更新

```typescript
// web/src/core/types/routing.ts

export interface RoutingSettings {
  enableSmartRouting: boolean;  // 是否启用智能路由
  defaultPath: 'auto' | 'simple_qa' | 'deep_research';
  userDepartment: string;  // 用户部门
}

// web/src/app/settings/tabs/routing-tab.tsx

export const RoutingTab = ({ settings, onChange }) => {
  return (
    <div className="flex flex-col gap-4">
      <FormField name="enableSmartRouting">
        <Switch 
          checked={settings.enableSmartRouting}
          onChange={(checked) => onChange({ enableSmartRouting: checked })}
        />
        <Label>启用智能路由</Label>
      </FormField>
      
      <FormField name="userDepartment">
        <Select 
          value={settings.userDepartment}
          onChange={(value) => onChange({ userDepartment: value })}
        >
          <SelectItem value="general">通用</SelectItem>
          <SelectItem value="tech">技术部</SelectItem>
          <SelectItem value="marketing">市场部</SelectItem>
          <SelectItem value="finance">财务部</SelectItem>
        </Select>
        <Label>所属部门</Label>
      </FormField>
    </div>
  );
};
```

### API 更新

```python
# src/server/chat_request.py

class ChatRequest(BaseModel):
    messages: Optional[List[ChatMessage]] = Field(...)
    
    # 新增路由相关字段
    enable_smart_routing: Optional[bool] = Field(
        True, description="是否启用智能路由"
    )
    user_department: Optional[str] = Field(
        "general", description="用户所属部门"
    )
    preferred_path: Optional[str] = Field(
        "auto", description="首选路径: auto/simple_qa/deep_research"
    )
```

## 📈 配置示例

### conf.yaml 扩展

```yaml
# 智能路由配置
ROUTING:
  enabled: true
  classifier_model: "basic"  # 用于分类的LLM模型
  
  # 复杂度阈值
  complexity_thresholds:
    simple_max_words: 20  # 简单问题最大词数
    simple_keywords:  # 简单问题关键词
      - "什么是"
      - "如何"
      - "定义"
      - "解释"
    
  # 部门配置
  departments:
    tech:
      name: "技术部"
      keywords: ["代码", "架构", "算法", "数据库", "API"]
      tools: ["python_repl", "web_search"]
    marketing:
      name: "市场部"
      keywords: ["市场", "营销", "竞品", "用户", "推广"]
      tools: ["web_search"]
    finance:
      name: "财务部"
      keywords: ["财务", "成本", "预算", "报表", "分析"]
      tools: ["python_repl", "web_search"]
```

## 🧪 测试用例

### 简单问答测试
```python
# 测试输入
query = "什么是Python?"
department = "general"

# 期望输出
expected_path = "simple_qa"
expected_complexity = "simple"
```

### 深度研究测试
```python
# 测试输入
query = "分析AI在医疗行业的应用现状和未来发展趋势"
department = "general"

# 期望输出
expected_path = "deep_research"
expected_complexity = "complex"
```

### 部门专用测试
```python
# 测试输入
query = "设计一个用户认证系统的数据库架构"
department = "tech"

# 期望输出
expected_path = "department_specific"
expected_complexity = "medium"
```

## 🔄 迁移步骤

1. **创建新文件**
   - `src/graph/classifier.py` - 分类器实现
   - `src/graph/department_agents.py` - 部门智能体
   - `src/config/routing.py` - 路由配置加载

2. **更新现有文件**
   - `src/graph/types.py` - 扩展State
   - `src/graph/nodes.py` - 添加新节点
   - `src/graph/builder.py` - 更新图构建
   - `src/server/chat_request.py` - 扩展请求模型

3. **前端更新**
   - `web/src/core/types/routing.ts` - 类型定义
   - `web/src/app/settings/tabs/routing-tab.tsx` - 路由设置UI
   - `web/src/core/api/chat.ts` - API调用更新

4. **配置文件**
   - `conf.yaml` - 添加路由配置

## 📊 性能优化

1. **缓存分类结果**: 相似查询使用缓存的分类结果
2. **并行处理**: 分类和背景调研可以并行执行
3. **快速失败**: 简单问答路径快速响应，提升用户体验

## 🎯 预期收益

1. ✅ **响应速度提升**: 简单问题通过快速路径，1-2秒内响应
2. ✅ **资源优化**: 避免简单问题占用复杂流程资源
3. ✅ **专业性提升**: 部门专用路径提供更专业的服务
4. ✅ **用户体验**: 智能选择合适的处理方式
