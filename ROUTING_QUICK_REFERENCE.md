# DeerFlow 智能路由系统 - 快速参考

## 🚀 一分钟快速开始

```bash
# 运行测试
python test_routing_system.py

# 查看设计文档
cat ROUTING_DESIGN.md

# 查看使用指南
cat ROUTING_USAGE_GUIDE.md
```

## 🎯 三种处理路径

| 路径 | 触发条件 | 响应时间 | 适用场景 |
|------|---------|---------|---------|
| **简单问答** | 简短事实性问题 | 1-3秒 | "什么是...?" "如何...?" |
| **深度研究** | 复杂分析问题 | 30-60秒 | "分析...趋势" "研究..." |
| **部门专用** | 专业领域问题 | 10-25秒 | 技术、市场、财务问题 |

## 💼 五个部门

```
general      → 通用问题
tech         → 代码、架构、技术方案
marketing    → 市场、营销、竞品分析
finance      → 财务、成本、投资分析
hr           → 招聘、培训、绩效管理
```

## 📝 API使用示例

### Python API
```python
from src.graph import build_graph_with_memory

graph = build_graph_with_memory()

result = graph.invoke({
    "messages": [{"role": "user", "content": "你的问题"}],
    "user_department": "tech",  # 选择部门
    "enable_smart_routing": True  # 启用智能路由
})

print(result["final_report"])
```

### HTTP API
```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你的问题"}],
    "user_department": "tech",
    "enable_smart_routing": true
  }'
```

## 🔧 核心文件

```
src/graph/
├── classifier.py           # 分类器逻辑
├── department_agents.py    # 部门配置
├── nodes.py               # 路由节点（router_node, simple_qa_node, department_node）
├── types.py               # State扩展
└── builder.py             # 图构建更新

docs/
├── ROUTING_DESIGN.md              # 设计文档
├── ROUTING_USAGE_GUIDE.md         # 使用指南
├── ROUTING_IMPLEMENTATION_SUMMARY.md  # 实现总结
└── ROUTING_QUICK_REFERENCE.md     # 快速参考（本文件）

test_routing_system.py     # 测试脚本
```

## ⚙️ 配置示例

### .env 配置
```bash
ENABLE_SMART_ROUTING=true
DEFAULT_USER_DEPARTMENT=general
```

### 代码配置
```python
# 禁用智能路由
enable_smart_routing=False

# 强制使用特定路径
routing_path="simple_qa"  # 或 "deep_research" 或 "department_specific"

# 选择部门
user_department="tech"  # 或 "marketing", "finance", "hr", "general"
```

## 🎨 路由决策流程

```
用户请求
  ↓
router_node（路由节点）
  ↓
classify_request()（分类）
  ↓
判断路径
  ├─ simple_qa → 快速搜索 → 简洁回答
  ├─ deep_research → 多步研究 → 详细报告
  └─ department_specific → 专用智能体 → 专业解答
```

## 📊 性能指标

| 指标 | 简单问答 | 深度研究 | 部门专用 |
|------|---------|---------|---------|
| 平均响应时间 | 2秒 | 45秒 | 15秒 |
| 搜索次数 | 1次 | 3-5次 | 1-2次 |
| 输出长度 | ~200字 | ~2000字 | ~500字 |
| Token消耗 | 低 | 高 | 中 |

## 🔍 问题分类规则

### 简单问答 (simple_qa)
- ✅ "什么是...?"
- ✅ "如何...?"（单步操作）
- ✅ 定义、解释类
- ✅ 问题长度 < 30字

### 深度研究 (deep_research)
- ✅ "分析...趋势"
- ✅ "研究...现状"
- ✅ "对比...优劣"
- ✅ 问题长度 > 50字

### 部门专用 (department_specific)
- ✅ 包含部门关键词
- ✅ 专业领域问题
- ✅ 需要专用工具

## 💡 使用技巧

1. **简单问题**: 直接提问，无需背景
   ```
   ❌ "我想了解一下人工智能是什么，请详细说明"
   ✅ "什么是人工智能?"
   ```

2. **复杂分析**: 提供充分背景
   ```
   ❌ "AI应用?"
   ✅ "分析AI在医疗诊断中的应用现状、技术挑战和未来趋势"
   ```

3. **部门专用**: 选对部门
   ```
   tech: "优化数据库查询性能"
   marketing: "分析竞品营销策略"
   finance: "计算项目NPV和IRR"
   ```

## ⚡ 快速调试

### 查看路由决策
```python
from src.graph.classifier import classify_request

decision = classify_request(
    query="你的问题",
    department="general"
)

print(f"路径: {decision.path}")
print(f"复杂度: {decision.complexity}")
print(f"置信度: {decision.confidence}")
print(f"理由: {decision.reasoning}")
```

### 查看部门列表
```python
from src.graph.department_agents import get_available_departments

departments = get_available_departments()
for dept in departments:
    print(f"{dept['id']}: {dept['name']}")
```

## 🐛 常见问题

**Q: 为什么分类不准确?**  
A: 检查问题描述是否清晰，或手动指定 `routing_path`

**Q: 如何禁用智能路由?**  
A: 设置 `enable_smart_routing=False`

**Q: 如何添加新部门?**  
A: 编辑 `src/graph/department_agents.py` 中的 `DEPARTMENT_CONFIGS`

**Q: 性能如何优化?**  
A: 简单问题用simple_qa路径，缓存常见问题

## 📚 更多资源

- 📖 [完整设计文档](./ROUTING_DESIGN.md)
- 📘 [详细使用指南](./ROUTING_USAGE_GUIDE.md)
- 📝 [实现总结](./ROUTING_IMPLEMENTATION_SUMMARY.md)
- 🧪 [测试脚本](./test_routing_system.py)

---

**提示**: 使用 `python test_routing_system.py` 快速验证功能是否正常工作！
