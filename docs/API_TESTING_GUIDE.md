# DeerFlow 4种路径智能路由系统 - API测试指南

## 📡 可用的测试接口

### 主接口：`/api/chat/stream`

这是**主要的测试接口**，支持4种路径的智能路由系统。

**接口信息：**
- **URL:** `POST http://localhost:8000/api/chat/stream`
- **类型:** 流式接口（Server-Sent Events）
- **用途:** 发送用户查询，系统自动路由到4种路径之一

**支持的4种路径：**

1. **direct_answer** - 直接回答（通用知识）
2. **simple_search** - 简单检索（主流路径⭐）
3. **deep_research** - 深度研究（复杂分析）
4. **domain_knowledge** - 领域知识（专业知识库）

---

## 🚀 快速开始

### 方法1：使用Python测试脚本（推荐）

```bash
# 1. 启动后端服务
cd /home/llm/zhangle/deer-flow
source .venv/bin/activate
python -m src.server.app

# 2. 新开终端，运行测试脚本
cd /home/llm/zhangle/deer-flow
python3 test_4_paths_api.py
```

**特点：**
- ✅ 自动测试所有4种路径
- ✅ 绿色+紫色配色终端输出
- ✅ 解析流式响应
- ✅ 显示路由决策结果

### 方法2：使用curl脚本

```bash
# 运行curl测试脚本
./test_4_paths_curl.sh
```

**特点：**
- ✅ 纯Shell脚本，无需Python
- ✅ 绿色+紫色配色
- ✅ 快速验证接口可用性

### 方法3：手动curl测试

#### 测试1：直接回答路径

```bash
curl -X POST "http://localhost:8000/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "什么是汽车？"}
    ],
    "thread_id": "test_direct",
    "auto_accepted_plan": true,
    "enable_background_investigation": false
  }'
```

**期望结果：** 路由到 `direct_answer_node`，不调用检索工具

#### 测试2：简单检索路径（主流）

```bash
curl -X POST "http://localhost:8000/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "信用卡如何申请？"}
    ],
    "thread_id": "test_simple",
    "auto_accepted_plan": true,
    "enable_background_investigation": false
  }'
```

**期望结果：** 路由到 `simple_search_node`，单次检索

#### 测试3：深度研究路径

```bash
curl -X POST "http://localhost:8000/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "分析金融科技对传统银行的影响趋势"}
    ],
    "thread_id": "test_deep",
    "auto_accepted_plan": true,
    "enable_background_investigation": false
  }'
```

**期望结果：** 路由到 `coordinator`，进入深度研究流程

#### 测试4：领域知识路径

```bash
curl -X POST "http://localhost:8000/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "SWIFT报文MT103的字段详细说明"}
    ],
    "thread_id": "test_domain",
    "auto_accepted_plan": true,
    "enable_background_investigation": false
  }'
```

**期望结果：** 路由到 `domain_knowledge_node`，使用专业知识库

---

## 📊 请求参数说明

### 必需参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `messages` | Array | 消息列表，至少包含一条用户消息 |
| `messages[].role` | String | 消息角色，通常为 "user" |
| `messages[].content` | String | 用户查询内容 |

### 可选参数（影响路由）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `thread_id` | String | 自动生成 | 会话ID |
| `max_plan_iterations` | Integer | 1 | 最大计划迭代次数 |
| `max_step_num` | Integer | 3 | 最大步骤数 |
| `max_search_results` | Integer | 3 | 最大搜索结果数 |
| `search_engine` | String | "custom_search" | 搜索引擎 |
| `auto_accepted_plan` | Boolean | false | 自动接受计划（测试时建议true） |
| `enable_background_investigation` | Boolean | true | 启用背景调研（测试时建议false以加快速度） |
| `enable_smart_routing` | Boolean | true | 启用智能路由 |

---

## 🔍 如何查看路由结果

### 1. 服务端日志（最详细）

启动服务后，终端会显示**绿色+紫色**的增强日志：

```
🔀 NODE_ENTRY | router | 开始智能路由分析
🔍 CLASSIFIER_START | 查询: '信用卡如何申请？' | 部门: general
✅ CLASSIFIER_RESULT | 路径: simple_search | 复杂度: medium | 置信度: 0.85
🎯 ROUTING_DECISION | 路径: simple_search | 复杂度: medium | 需要检索: True
✅ NODE_EXIT | router | 路由决策完成 | 耗时: 0.15s
🔄 NODE_ENTRY | simple_search | 开始简单检索处理
```

**关键日志标记：**
- `🔀 NODE_ENTRY | router` - 进入路由节点
- `🔍 CLASSIFIER_START` - 开始分类
- `✅ CLASSIFIER_RESULT` - 分类结果（**核心**）
- `🎯 ROUTING_DECISION` - 路由决策（**核心**）
- `🔄 NODE_ENTRY | xxx` - 进入具体路径节点

### 2. 客户端响应（SSE事件流）

流式响应中会包含路由信息（如果有）：

```json
event: message_chunk
data: {"thread_id":"xxx","langgraph_node":"router","routing_path":"simple_search"}

event: message_chunk
data: {"thread_id":"xxx","langgraph_node":"simple_search_node","content":"..."}
```

**关键字段：**
- `langgraph_node` - 当前执行的节点名称
- `routing_path` - 路由路径（如果在状态中）
- `content` - 节点输出内容

### 3. 使用测试脚本

Python测试脚本会自动解析并显示：

```
🎯 检测到路由决策: simple_search
📍 当前节点: simple_search_node
✅ 路由路径匹配！
```

---

## 📝 测试用例参考

### 直接回答路径测试用例

```
✅ "什么是汽车？"
✅ "地球有多大？"
✅ "1+1等于几？"
✅ "Python是什么编程语言？"
```

### 简单检索路径测试用例（主流）

```
✅ "信用卡如何申请？"
✅ "个人贷款需要什么条件？"
✅ "网上银行如何开通？"
✅ "手机银行转账限额是多少？"
✅ "定期存款利率是多少？"
```

### 深度研究路径测试用例

```
✅ "分析金融科技对传统银行的影响趋势"
✅ "对比国内外数字货币政策的异同"
✅ "研究普惠金融在农村地区的发展现状"
✅ "评估开放银行API的安全风险"
```

### 领域知识路径测试用例

```
✅ "SWIFT报文MT103的字段详细说明"
✅ "交通银行沃德财富卡的积分规则"
✅ "理财产品风险评级R3是什么标准？"
✅ "反洗钱可疑交易监测规则"
```

---

## 🛠️ 故障排查

### 问题1：连接失败

**症状：** `Connection refused` 或 `Failed to connect`

**解决方案：**
```bash
# 1. 检查服务是否启动
ps aux | grep "python.*app.py"

# 2. 检查端口是否被占用
lsof -i :8000

# 3. 重新启动服务
cd /home/llm/zhangle/deer-flow
source .venv/bin/activate
python -m src.server.app
```

### 问题2：路由到错误的路径

**症状：** 路由路径与期望不符

**解决方案：**
1. 查看服务端日志中的 `CLASSIFIER_RESULT`
2. 检查分类器的 `confidence` 置信度
3. 如果置信度低（<0.7），可能使用了规则后备分类
4. 调整查询内容，使用更明确的关键词

### 问题3：未看到路由信息

**症状：** 响应中没有 `routing_path` 字段

**解决方案：**
1. 路由信息主要在服务端日志中
2. 检查 `langgraph_node` 字段识别当前节点
3. 使用Python测试脚本可以更好地解析响应

---

## 📈 性能基准

| 路径 | 平均响应时间 | 检索次数 | 适用场景占比 |
|------|--------------|----------|--------------|
| direct_answer | <1秒 | 0次 | ~10% |
| simple_search | 2-3秒 | 1次 | ~65% ⭐ |
| deep_research | 30-60秒 | 多次 | ~15% |
| domain_knowledge | 3-5秒 | 1次 | ~10% |

---

## 🎯 最佳实践

### 测试环境配置

```bash
# .env 文件配置
ALLOWED_ORIGINS=http://localhost:3000
ENABLE_SMART_ROUTING=true  # 启用智能路由
```

### 推荐的测试顺序

1. **先测试direct_answer** - 最快，验证基础功能
2. **再测试simple_search** - 主流路径，最重要
3. **测试domain_knowledge** - 验证专业知识处理
4. **最后测试deep_research** - 最慢，验证复杂流程

### 调试技巧

1. **启用详细日志**
   ```bash
   export LOG_LEVEL=DEBUG
   python -m src.server.app
   ```

2. **使用固定thread_id**
   - 便于追踪单次请求的完整流程
   - 示例：`"thread_id": "test_debug_001"`

3. **关闭background_investigation**
   - 测试时设置 `"enable_background_investigation": false`
   - 加快响应速度，便于快速迭代

---

## 📞 获取帮助

### 相关文档

- **设计文档:** [docs/routing_4_paths.md](routing_4_paths.md)
- **对比文档:** [docs/routing_comparison.md](routing_comparison.md)
- **流程图:** [docs/routing_flowchart.md](routing_flowchart.md)
- **快速参考:** [docs/QUICK_REFERENCE.md](QUICK_REFERENCE.md)

### 核心文件

- **分类器:** `src/graph/classifier.py`
- **路由节点:** `src/graph/nodes.py`
- **API接口:** `src/server/app.py`
- **图构建:** `src/graph/builder.py`

### 常见问题

**Q: 如何强制使用某个路径？**
A: 暂不支持手动指定路径，系统会根据查询内容自动分类。如需测试特定路径，请使用该路径的典型查询。

**Q: 分类不准确怎么办？**
A: 查看日志中的分类理由（`reasoning`），调整查询内容或优化分类器的关键词规则。

**Q: 如何添加新的测试用例？**
A: 修改 `test_4_paths_api.py` 中的 `test_cases` 列表即可。

---

**版本:** v2.0  
**更新日期:** 2025-11-04  
**状态:** ✅ 已验证可用
