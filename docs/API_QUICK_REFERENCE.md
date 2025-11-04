# DeerFlow API 快速参考卡片

## 🚀 快速开始

```bash
# 启动服务
cd /home/llm/zhangle/deer-flow
python -m src.server.app

# 运行测试工具（交互模式）
./test_all_apis.sh

# 运行所有测试
./test_all_apis.sh all
```

---

## 📋 核心接口速查

### 1️⃣ 流式聊天接口（最强大）

```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你的问题"}],
    "search_engine": "tavily",
    "max_step_num": 3
  }'
```

**特点**: 智能路由 → 4种处理路径

---

### 2️⃣ 简化流式接口（快速研究）

```bash
curl -X POST http://localhost:8000/api/research/simple/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "研究问题"}],
    "auto_accepted_plan": true
  }'
```

**特点**: 自动接受计划，快速输出

---

### 3️⃣ OpenAI兼容接口（标准格式）

```bash
curl -X POST http://localhost:8000/api/research/simple/stream/openai \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "问题"}]
  }'
```

**特点**: 符合OpenAI标准，易集成

---

## 🎯 智能路由 - 4种路径

| 路径 | 触发条件 | 示例问题 | 特点 |
|------|----------|----------|------|
| **Direct Answer** | 通用知识 | "什么是汽车？" | ⚡️ 最快 |
| **Simple Search** | 常规问题 | "信用卡如何申请？" | 🔍 单次检索 |
| **Domain Knowledge** | 专业领域 | "SWIFT MT103字段说明" | 📚 知识库 |
| **Deep Research** | 复杂研究 | "分析金融科技影响" | 🎓 最详细 |

---

## 🛠️ 常用参数

### 核心参数

```json
{
  "search_engine": "tavily",           // 搜索引擎
  "max_step_num": 3,                   // 最大步骤数
  "max_search_results": 3,             // 每步搜索结果数
  "auto_accepted_plan": true,          // 自动接受计划
  "enable_background_investigation": true  // 背景调研
}
```

### 报告风格

```json
{
  "report_style": "academic"  // academic | popular_science | news | social_media
}
```

### 高级功能

```json
{
  "enable_deep_thinking": true,     // 深度思考模式
  "thread_id": "conv_123",          // 多轮对话ID
  "resources": [...]                 // 本地资源/知识库
}
```

---

## 🔧 配置接口

### 获取系统配置

```bash
curl http://localhost:8000/api/config | jq .
```

### 获取RAG配置

```bash
curl http://localhost:8000/api/rag/config | jq .
```

---

## 📝 内容生成

### PPT生成

```bash
curl -X POST http://localhost:8000/api/ppt/generate \
  -H "Content-Type: application/json" \
  -d '{"content": "# 标题\n\n## 内容..."}' \
  --output report.pptx
```

### 提示词增强

```bash
curl -X POST http://localhost:8000/api/prompt/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "AI发展",
    "report_style": "academic"
  }' | jq -r '.result'
```

---

## 🎨 流式输出处理

### Bash处理SSE

```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [...]}'
```

**关键**: `-N` 参数禁用缓冲

### Python处理SSE

```python
import requests
import json

with requests.post(url, json=data, stream=True) as r:
    for line in r.iter_lines():
        if line.startswith(b'data: '):
            data = json.loads(line[6:])
            print(data.get('content', ''), end='')
```

---

## 📊 性能优化建议

### ⚡️ 快速模式（< 10秒）

```json
{
  "max_step_num": 2,
  "max_search_results": 3,
  "auto_accepted_plan": true,
  "enable_background_investigation": false
}
```

### 🎯 平衡模式（10-30秒）

```json
{
  "max_step_num": 3,
  "max_search_results": 3,
  "auto_accepted_plan": true,
  "enable_background_investigation": true
}
```

### 🔬 深度模式（30-60秒+）

```json
{
  "max_plan_iterations": 2,
  "max_step_num": 5,
  "max_search_results": 5,
  "enable_background_investigation": true,
  "enable_deep_thinking": true
}
```

---

## 🌐 搜索引擎对比

| 引擎 | 特点 | 适用场景 |
|------|------|----------|
| **tavily** | AI优化，精准 | 研究、分析 |
| **custom_search** | 企业知识库 | 内部业务 |
| **duckduckgo** | 通用、隐私 | 一般查询 |
| **brave_search** | 快速响应 | 实时信息 |
| **arxiv** | 学术论文 | 科研 |
| **wikipedia** | 百科知识 | 基础概念 |

---

## ⚠️ 常见问题

### 1. 连接失败

```bash
# 检查服务状态
curl http://localhost:8000/api/config

# 查看日志
tail -f /path/to/logs
```

### 2. 参数错误

- ✅ `report_style: "academic"` (小写)
- ❌ `report_style: "ACADEMIC"` (大写会报错)

### 3. 流式输出断开

```bash
# 使用 -N 参数
curl -N -X POST ...
```

### 4. CORS错误

```bash
# 设置环境变量
export ALLOWED_ORIGINS="http://localhost:3000,http://your-domain.com"
```

---

## 📚 完整文档

- **详细API文档**: `/docs/API_REFERENCE.md`
- **测试工具**: `./test_all_apis.sh`
- **测试结果**: `./api_test_results/`

---

## 🔗 快速链接

```bash
# 服务地址
http://localhost:8000

# API文档（Swagger）
http://localhost:8000/docs

# 健康检查
http://localhost:8000/api/config
```

---

## 💡 最佳实践

1. **多轮对话**: 使用相同的 `thread_id`
2. **自定义知识库**: 设置 `custom_search_repository`
3. **调试模式**: 设置 `debug: true` 查看详细日志
4. **资源限制**: 根据需求调整 `max_step_num` 和 `max_search_results`
5. **错误处理**: 监听 `event: error` 类型的SSE事件

---

**版本**: v0.1.0  
**更新**: 2025-01-04
