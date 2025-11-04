# DeerFlow 智能路由系统 - 快速参考卡

## 🎯 4种路径速查

### 1️⃣ 直接回答 (direct_answer)
```
📌 定位: 通用常识，快速响应
🎯 场景: 基础概念、定义类问题
⚡ 特点: 不走检索，直接LLM回答
📊 复杂度: simple
🔍 检索: ❌ 否
⏱️ 速度: <1秒
📝 长度: 100-300字
📈 占比: ~10%

示例:
  ✅ "什么是汽车？"
  ✅ "地球有多大？"
  ✅ "1+1等于几？"
```

### 2️⃣ 简单检索 (simple_search) ⭐ **主流路径**
```
📌 定位: 银行业务，单次检索
🎯 场景: 常规金融产品和业务查询
⚡ 特点: 一次检索，快速答案
📊 复杂度: medium
🔍 检索: ✅ 单次（3-5条）
⏱️ 速度: 2-3秒
📝 长度: 200-300字
📈 占比: ~65% ⭐

示例:
  ✅ "信用卡如何申请？"
  ✅ "个人贷款需要什么条件？"
  ✅ "网上银行如何开通？"
```

### 3️⃣ 深度研究 (deep_research)
```
📌 定位: 复杂分析，多轮研究
🎯 场景: 趋势分析、对比研究
⚡ 特点: 完整流程，详细报告
📊 复杂度: complex
🔍 检索: ✅ 多次
⏱️ 速度: 30-60秒
📝 长度: 800-2000字
📈 占比: ~15%

示例:
  ✅ "分析金融科技对传统银行的影响"
  ✅ "对比国内外数字货币政策"
  ✅ "研究普惠金融发展现状"
```

### 4️⃣ 领域知识 (domain_knowledge)
```
📌 定位: 专业知识，知识库
🎯 场景: 高度专业化的银行知识
⚡ 特点: 知识库优先，详细解答
📊 复杂度: expert
🔍 检索: ✅ 专业库
⏱️ 速度: 3-5秒
📝 长度: 400-600字
📈 占比: ~10%

示例:
  ✅ "SWIFT报文MT103字段说明"
  ✅ "交通银行沃德卡积分规则"
  ✅ "反洗钱可疑交易监测规则"
```

---

## 🔑 RouteDecision 模型

```python
class RouteDecision(BaseModel):
    path: Literal[
        "direct_answer",      # 直接回答
        "simple_search",      # 简单检索 ⭐
        "deep_research",      # 深度研究
        "domain_knowledge"    # 领域知识
    ]
    
    complexity: Literal[
        "simple",    # 简单通用
        "medium",    # 适中专业 ⭐
        "complex",   # 复杂分散
        "expert"     # 专家集中
    ]
    
    needs_search: bool      # 是否需要检索
    confidence: float       # 置信度 0-1
    reasoning: str          # 决策理由
```

---

## 📊 分类规则速查

### 优先级
```
直接回答 < 简单检索 ⭐ < 深度研究 < 领域知识
```

### 关键词映射

#### 🟡 直接回答关键词
```
通用: 什么是汽车、什么是互联网、什么是Python
常识: 地球有多大、1+1
非银行: 汽车、地理、历史、科学
```

#### 🟢 简单检索关键词 (主流)
```
产品: 信用卡、贷款、理财、存款
业务: 如何申请、如何开通、需要什么条件
服务: 网上银行、手机银行、转账
```

#### 🔵 深度研究关键词
```
分析: 分析、研究、对比、比较
评估: 评估、趋势、影响、发展
综合: 现状、未来、多维度
```

#### 🔴 领域知识关键词
```
规则: 积分规则、监测规则、内部流程
专业: SWIFT、MT103、风险评级
监管: 反洗钱、监管要求、技术标准
```

---

## 🚀 使用示例

### 基本调用
```python
from src.graph.classifier import classify_request

# 调用分类器
result = classify_request(
    query="信用卡如何申请？",
    department="general",
    enable_smart_routing=True
)

# 查看结果
print(f"路径: {result.path}")
print(f"复杂度: {result.complexity}")
print(f"需要检索: {result.needs_search}")
print(f"置信度: {result.confidence}")
print(f"理由: {result.reasoning}")
```

### 完整工作流
```python
from src.graph.builder import graph

# 配置
config = {
    "configurable": {
        "thread_id": "thread_001",
        "enable_smart_routing": True
    }
}

# 调用
result = graph.invoke(
    {
        "messages": [{"role": "user", "content": "信用卡如何申请？"}],
        "research_topic": "信用卡如何申请？"
    },
    config=config
)

print(result["final_report"])
```

---

## 🛠️ 配置选项

### 启用/禁用智能路由
```python
# 启用（默认）
{"enable_smart_routing": True}

# 禁用（使用simple_search）
{"enable_smart_routing": False}
```

### 指定部门（可选）
```python
{"user_department": "credit_card"}
{"user_department": "general"}  # 默认
```

---

## 📁 核心文件位置

```
src/graph/
├── classifier.py       # 分类器核心
│   ├── RouteDecision   # 决策模型
│   ├── classify_request()  # 主函数
│   └── _fallback_classification()  # 后备
│
├── nodes.py           # 节点实现
│   ├── router_node()
│   ├── direct_answer_node()
│   ├── simple_search_node()
│   ├── domain_knowledge_node()
│   └── coordinator() → 深度研究
│
├── builder.py         # 图构建
│   └── _build_base_graph()
│
└── types.py           # 状态定义
    └── State
```

---

## 🔍 调试技巧

### 查看分类决策
```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.INFO)

result = classify_request(query)
# 会输出详细的分类过程
```

### 查看路由流程
```python
# 检查enhanced_logger输出
# 会显示：
# 🔍 CLASSIFIER_START
# ✅ CLASSIFIER_RESULT
# 🎯 ROUTING_DECISION
# ✅ NODE_EXIT
```

---

## ⚡ 性能优化建议

### 1. 缓存分类结果
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_classify(query: str):
    return classify_request(query)
```

### 2. 批量处理
```python
queries = ["查询1", "查询2", "查询3"]
results = [classify_request(q) for q in queries]
```

### 3. 异步调用
```python
import asyncio

async def classify_async(queries):
    tasks = [async_classify(q) for q in queries]
    return await asyncio.gather(*tasks)
```

---

## 📈 监控指标

### 关键指标
```
✅ 路径分布统计
✅ 平均响应时间
✅ 分类准确率
✅ 资源使用率
✅ 错误率
```

### 日志关键字
```
CLASSIFIER_START    - 分类开始
CLASSIFIER_RESULT   - 分类结果
ROUTING_DECISION    - 路由决策
NODE_ENTRY          - 节点进入
NODE_EXIT           - 节点退出
```

---

## ❓ 常见问题

### Q1: 如何强制使用特定路径？
```python
# 禁用智能路由，手动设置
config = {
    "enable_smart_routing": False,
    "routing_path": "simple_search"
}
```

### Q2: 分类错误怎么办？
```python
# 查看reasoning了解原因
print(result.reasoning)

# 检查置信度
if result.confidence < 0.7:
    print("低置信度，可能需要人工确认")
```

### Q3: 如何添加自定义关键词？
```python
# 修改 _fallback_classification 函数
# 在对应的关键词列表中添加
simple_search_keywords = [
    "信用卡", "贷款",
    "你的关键词"  # 添加这里
]
```

---

## 🎓 最佳实践

### ✅ DO
- 使用智能路由（默认启用）
- 信任LLM分类（通常很准确）
- 监控路径分布和性能
- 根据实际情况调整关键词

### ❌ DON'T
- 不要过度依赖规则分类
- 不要忽略置信度低的情况
- 不要频繁修改分类逻辑
- 不要跳过测试直接上线

---

## 📞 获取帮助

### 文档
- 📖 完整文档: `docs/routing_4_paths.md`
- 📊 对比文档: `docs/routing_comparison.md`
- 🔄 流程图: `docs/routing_flowchart.md`

### 测试
- 🧪 模型测试: `test_route_model.py`
- 🔬 完整测试: `test_routing_paths.py`

### 代码
- 💻 分类器: `src/graph/classifier.py`
- 🔧 节点: `src/graph/nodes.py`
- 🏗️ 构建器: `src/graph/builder.py`

---

**版本:** v2.0  
**更新:** 2025-11-04  
**状态:** ✅ 生产就绪
