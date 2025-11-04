# DeerFlow 智能路由系统使用指南

## 📚 目录

1. [系统概述](#系统概述)
2. [快速开始](#快速开始)
3. [使用示例](#使用示例)
4. [API参考](#api参考)
5. [配置说明](#配置说明)
6. [常见问题](#常见问题)

## 系统概述

DeerFlow智能路由系统是一个基于用户部门和问题复杂度的智能分流系统，能够自动选择最优的处理路径：

- **简单问答路径**: 快速响应简单事实性问题（1-3秒）
- **深度研究路径**: 处理复杂的研究分析任务（原有功能）
- **部门专用路径**: 为特定部门提供专业化服务

### 架构图

```
用户请求 → 路由节点 → 分类器 → 选择路径
                                 ├─ 简单问答 → 单次搜索 → 快速回答
                                 ├─ 深度研究 → 多智能体协作 → 详细报告
                                 └─ 部门专用 → 专用智能体 → 专业服务
```

## 快速开始

### 1. 运行测试

```bash
# 测试智能路由系统
python test_routing_system.py
```

### 2. 基本使用

#### Python API调用

```python
from src.graph import build_graph_with_memory

# 创建工作流图
graph = build_graph_with_memory()

# 简单问答示例
simple_result = graph.invoke({
    "messages": [{"role": "user", "content": "什么是Python?"}],
    "user_department": "general",
    "enable_smart_routing": True
})

# 深度研究示例
research_result = graph.invoke({
    "messages": [{"role": "user", "content": "分析AI在医疗行业的应用"}],
    "user_department": "general",
    "enable_smart_routing": True
})

# 部门专用示例
tech_result = graph.invoke({
    "messages": [{"role": "user", "content": "设计用户认证系统架构"}],
    "user_department": "tech",
    "enable_smart_routing": True
})
```

#### HTTP API调用

```bash
# 简单问答请求
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "什么是Python?"}],
    "user_department": "general",
    "enable_smart_routing": true
  }'

# 部门专用请求
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "优化数据库查询性能"}],
    "user_department": "tech",
    "enable_smart_routing": true
  }'
```

## 使用示例

### 示例1: 简单问答

**适用场景**: 快速获取事实性信息

```python
# 用户输入
query = "什么是机器学习?"
department = "general"

# 路由决策
# → 路径: simple_qa
# → 复杂度: simple
# → 响应时间: ~2秒

# 输出结果
"""
机器学习是人工智能的一个子领域，它使计算机能够从数据中学习并改进，
而无需明确编程。主要包括监督学习、无监督学习和强化学习三大类。
"""
```

### 示例2: 深度研究

**适用场景**: 需要深入分析和综合多个来源

```python
# 用户输入
query = "分析人工智能在医疗诊断中的应用现状、技术挑战和未来发展方向"
department = "general"

# 路由决策
# → 路径: deep_research
# → 复杂度: complex
# → 响应时间: ~30-60秒

# 处理流程:
# 1. 背景调研 → 收集相关信息
# 2. 制定计划 → 分解研究步骤
# 3. 执行研究 → 多智能体协作
# 4. 生成报告 → 综合分析结果
```

### 示例3: 技术部专用

**适用场景**: 技术人员的专业问题

```python
# 用户输入
query = "设计一个高并发的用户认证系统，需要考虑安全性和性能"
department = "tech"

# 路由决策
# → 路径: department_specific
# → 复杂度: medium
# → 可用工具: Python REPL, Web搜索
# → 响应时间: ~10-20秒

# 专用智能体特点:
# - 技术领域专业知识
# - 代码分析和生成能力
# - 架构设计经验
```

### 示例4: 市场部专用

**适用场景**: 市场营销相关问题

```python
# 用户输入
query = "分析竞品在社交媒体上的营销策略和用户互动情况"
department = "marketing"

# 路由决策
# → 路径: department_specific
# → 复杂度: medium
# → 可用工具: Web搜索（更多结果）
# → 响应时间: ~15-25秒

# 专用智能体特点:
# - 市场分析专业知识
# - 用户洞察能力
# - 营销策略规划
```

### 示例5: 财务部专用

**适用场景**: 财务分析和计算

```python
# 用户输入
query = "基于以下数据计算项目的NPV和IRR，并分析投资可行性"
department = "finance"

# 路由决策
# → 路径: department_specific
# → 复杂度: medium
# → 可用工具: Python REPL（财务计算）, Web搜索
# → 响应时间: ~10-20秒

# 专用智能体特点:
# - 财务分析专业知识
# - Python数值计算能力
# - 风险评估经验
```

## API参考

### ChatRequest 扩展字段

```python
class ChatRequest(BaseModel):
    # ... 原有字段 ...
    
    # 智能路由相关字段
    enable_smart_routing: Optional[bool] = Field(
        True, 
        description="是否启用智能路由"
    )
    user_department: Optional[str] = Field(
        "general", 
        description="用户所属部门: general/tech/marketing/finance/hr"
    )
    preferred_path: Optional[str] = Field(
        "auto", 
        description="首选路径: auto/simple_qa/deep_research"
    )
```

### State 扩展字段

```python
class State(MessagesState):
    # ... 原有字段 ...
    
    # 智能路由字段
    user_department: str = "general"          # 用户部门
    query_complexity: str = "unknown"         # 查询复杂度
    routing_path: str = "auto"                # 路由路径
    enable_smart_routing: bool = True         # 是否启用智能路由
    department_context: dict = {}             # 部门上下文
```

### 可用部门列表

| 部门ID | 名称 | 描述 | 可用工具 |
|--------|------|------|----------|
| `general` | 通用 | 通用问题处理 | Web搜索 |
| `tech` | 技术部 | 代码分析、架构设计 | Web搜索, Python REPL |
| `marketing` | 市场部 | 市场分析、营销策略 | Web搜索（增强） |
| `finance` | 财务部 | 财务分析、成本核算 | Web搜索, Python REPL |
| `hr` | 人力资源部 | 招聘、培训、绩效 | Web搜索 |

## 配置说明

### 环境变量

在 `.env` 文件中添加：

```bash
# 智能路由配置
ENABLE_SMART_ROUTING=true          # 启用智能路由
DEFAULT_USER_DEPARTMENT=general    # 默认用户部门
ROUTING_CLASSIFIER_MODEL=basic     # 分类器使用的模型
```

### conf.yaml 配置

```yaml
# 智能路由配置
ROUTING:
  enabled: true
  classifier_model: "basic"
  
  # 复杂度阈值
  complexity_thresholds:
    simple_max_words: 20
    simple_keywords:
      - "什么是"
      - "如何"
      - "定义"
  
  # 部门配置
  departments:
    tech:
      name: "技术部"
      keywords: ["代码", "架构", "算法"]
      max_search_results: 5
    marketing:
      name: "市场部"
      keywords: ["市场", "营销", "竞品"]
      max_search_results: 7
```

### 前端配置

在设置页面添加路由选项：

```typescript
// 用户设置
interface UserSettings {
  department: 'general' | 'tech' | 'marketing' | 'finance' | 'hr';
  enableSmartRouting: boolean;
  preferredPath: 'auto' | 'simple_qa' | 'deep_research';
}
```

## 常见问题

### Q1: 什么时候使用智能路由？

**A**: 智能路由适用于以下场景：
- 用户提问复杂度差异较大
- 需要快速响应简单问题
- 有明确的部门分工和专业需求
- 希望优化系统资源使用

### Q2: 如何禁用智能路由？

**A**: 有两种方式：

方式1 - 请求级别禁用：
```python
result = graph.invoke({
    "messages": [...],
    "enable_smart_routing": False  # 禁用智能路由
})
```

方式2 - 全局禁用（环境变量）：
```bash
ENABLE_SMART_ROUTING=false
```

### Q3: 分类器如何工作？

**A**: 分类器使用LLM进行智能分类，考虑以下因素：
1. 问题长度和复杂度
2. 关键词匹配
3. 部门相关性
4. 历史分类结果（如果有缓存）

如果LLM不可用，会降级到基于规则的分类方法。

### Q4: 如何自定义部门配置？

**A**: 编辑 `src/graph/department_agents.py`：

```python
DEPARTMENT_CONFIGS["custom_dept"] = {
    "name": "自定义部门",
    "description": "部门描述",
    "keywords": ["关键词1", "关键词2"],
    "tools_config": {
        "python_repl": True,
        "web_search": True,
        "max_search_results": 5
    },
    "prompt_template": "你的提示词模板...",
    "context": {
        "domain": "custom",
        "expertise": ["skill1", "skill2"]
    }
}
```

### Q5: 路由决策不准确怎么办？

**A**: 可以采取以下措施：
1. 检查查询关键词是否清晰
2. 手动指定 `preferred_path` 参数
3. 调整分类提示词以提高准确性
4. 查看分类日志了解决策过程
5. 为特定场景添加规则

### Q6: 性能优化建议？

**A**: 
- **简单问答**: 平均响应时间 1-3秒
- **深度研究**: 平均响应时间 30-60秒
- **部门专用**: 平均响应时间 10-25秒

优化建议：
- 缓存常见问题的分类结果
- 并行执行分类和背景调研
- 为简单问答限制搜索结果数量
- 使用更快的LLM模型进行分类

### Q7: 如何监控路由效果？

**A**: 系统提供详细的日志：

```python
# 查看路由日志
enhanced_logger.logger.info(
    f"🎯 ROUTING_DECISION | 路径: {path} | "
    f"复杂度: {complexity} | 置信度: {confidence}"
)
```

可以收集以下指标：
- 各路径的使用频率
- 平均响应时间
- 用户满意度
- 路由准确率

## 高级用法

### 1. 混合路径

某些复杂场景可能需要先简单问答，再深度研究：

```python
# 第一步：快速获取基础信息
simple_result = graph.invoke({
    "messages": [{"role": "user", "content": "什么是区块链?"}],
    "routing_path": "simple_qa"  # 强制使用简单问答
})

# 第二步：深入研究
research_result = graph.invoke({
    "messages": [
        {"role": "user", "content": "什么是区块链?"},
        {"role": "assistant", "content": simple_result["final_report"]},
        {"role": "user", "content": "请深入分析其应用前景"}
    ],
    "routing_path": "deep_research"  # 强制使用深度研究
})
```

### 2. 跨部门协作

```python
# 技术和市场部门协作
tech_analysis = graph.invoke({
    "messages": [{"role": "user", "content": "技术可行性分析"}],
    "user_department": "tech"
})

market_analysis = graph.invoke({
    "messages": [{"role": "user", "content": "市场需求分析"}],
    "user_department": "marketing"
})

# 综合两个分析结果...
```

### 3. 自定义路由策略

```python
from src.graph.classifier import classify_request

def custom_routing_strategy(query, department):
    """自定义路由策略"""
    
    # 获取默认分类
    decision = classify_request(query, department)
    
    # 自定义规则
    if "紧急" in query:
        decision.path = "simple_qa"  # 紧急问题快速响应
    elif len(query) > 200:
        decision.path = "deep_research"  # 长问题深度研究
    
    return decision
```

## 总结

DeerFlow智能路由系统通过自动分析用户请求，选择最优处理路径，实现：

✅ **快速响应**: 简单问题1-3秒内回答  
✅ **专业服务**: 部门定制化的专业支持  
✅ **深度分析**: 复杂问题的全面研究  
✅ **资源优化**: 合理分配计算资源  
✅ **用户体验**: 智能选择合适的处理方式  

开始使用智能路由，让DeerFlow更智能、更高效！
