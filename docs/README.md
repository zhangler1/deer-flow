# DeerFlow API 文档索引

欢迎使用 DeerFlow 智能研究助手系统！本目录包含完整的 API 接口文档和测试工具。

---

## 📚 文档目录

### 1. [API 完整参考文档](./API_REFERENCE.md) ⭐️

**最详细的接口文档**，包含：
- ✅ 所有 API 接口的详细说明
- ✅ 完整的请求/响应示例
- ✅ curl 命令示例
- ✅ 参数说明和类型定义
- ✅ 错误处理和最佳实践
- ✅ 智能路由机制详解

**适合**: 首次使用、完整参考、深入学习

---

### 2. [API 快速参考卡片](./API_QUICK_REFERENCE.md) 🚀

**一页纸速查表**，包含：
- ⚡️ 最常用接口的快速示例
- ⚡️ 4种智能路由路径对比
- ⚡️ 核心参数配置建议
- ⚡️ 性能优化技巧
- ⚡️ 常见问题解决方案

**适合**: 日常开发、快速查询、问题排查

---

### 3. [API 测试指南](./API_TESTING_GUIDE.md)

**测试流程和工具说明**，包含：
- 🧪 测试环境配置
- 🧪 4种路径的测试用例
- 🧪 Python/Shell 测试脚本
- 🧪 故障排查指南

**适合**: 功能测试、集成验证

---

## 🛠️ 测试工具

### [测试脚本 - test_all_apis.sh](../test_all_apis.sh)

**一键测试所有接口**

```bash
# 交互模式（推荐）
./test_all_apis.sh

# 运行所有测试
./test_all_apis.sh all

# 测试特定接口
./test_all_apis.sh chat       # 流式聊天接口
./test_all_apis.sh simple     # 简化研究接口
./test_all_apis.sh openai     # OpenAI兼容接口
./test_all_apis.sh config     # 配置接口
```

**功能**:
- ✅ 支持交互式菜单选择
- ✅ 支持命令行参数调用
- ✅ 自动保存测试结果
- ✅ 彩色输出（绿色+紫色）
- ✅ 测试4种智能路由路径

---

### [Python 测试脚本 - test_4_paths_api.py](../test_4_paths_api.py)

**Python 版本的测试工具**

```bash
python test_4_paths_api.py
```

**功能**:
- ✅ 测试4种智能路由路径
- ✅ SSE 流式输出解析
- ✅ 彩色终端输出
- ✅ 详细的结果展示

---

### [Shell 测试脚本 - test_4_paths_curl.sh](../test_4_paths_curl.sh)

**纯 curl 命令测试**

```bash
./test_4_paths_curl.sh
```

**功能**:
- ✅ 使用纯 curl 命令
- ✅ 测试4种路由路径
- ✅ 无需额外依赖

---

## 🎯 快速上手

### 第一步：启动服务

```bash
cd /home/llm/zhangle/deer-flow
python -m src.server.app
```

### 第二步：测试接口

```bash
# 方式1：使用测试工具（推荐）
./test_all_apis.sh

# 方式2：手动 curl
curl http://localhost:8000/api/config
```

### 第三步：选择合适的接口

根据你的需求选择：

| 场景 | 推荐接口 | 文档链接 |
|------|----------|----------|
| **通用研究任务** | `/api/chat/stream` | [详细说明](./API_REFERENCE.md#1-流式聊天接口-apichatstream) |
| **快速问答** | `/api/research/simple/stream` | [详细说明](./API_REFERENCE.md#2-简化流式研究接口-apiresearchsimplestream) |
| **OpenAI集成** | `/api/research/simple/stream/openai` | [详细说明](./API_REFERENCE.md#3-openai-兼容流式接口-apiresearchsimplestreamopenai) |
| **PPT生成** | `/api/ppt/generate` | [详细说明](./API_REFERENCE.md#1-ppt-生成接口-apipptgenerate) |
| **提示词优化** | `/api/prompt/enhance` | [详细说明](./API_REFERENCE.md#2-提示词增强接口-apipromptenhance) |

---

## 📊 接口概览

### 核心研究接口（3个）

1. **`POST /api/chat/stream`** - 完整功能，智能路由
2. **`POST /api/research/simple/stream`** - 简化版本，快速研究
3. **`POST /api/research/simple/stream/openai`** - OpenAI兼容格式

### 内容生成接口（2个）

4. **`POST /api/ppt/generate`** - 生成PPT演示文稿
5. **`POST /api/prompt/enhance`** - 提示词增强优化

### 配置管理接口（3个）

6. **`GET /api/config`** - 系统完整配置
7. **`GET /api/rag/config`** - RAG配置信息
8. **`GET /api/rag/resources`** - RAG资源列表

### MCP服务器接口（1个）

9. **`POST /api/mcp/server/metadata`** - MCP服务器元数据

---

## 🔄 智能路由系统

DeerFlow 的核心特性：**根据问题自动选择最优处理路径**

```
                    用户问题
                       ↓
                  智能路由器
                   /  |  \  \
                  /   |   \  \
    通用知识 ←→ 常规问题 ←→ 专业领域 ←→ 复杂研究
       ↓           ↓           ↓           ↓
  Direct      Simple      Domain        Deep
  Answer      Search    Knowledge     Research
    (最快)      (平衡)      (精准)        (最全)
```

**详细说明**: [API完整参考 - 智能路由机制](./API_REFERENCE.md#智能路由机制)

---

## 💡 使用建议

### 🆕 新手入门

1. 阅读 → [API 快速参考卡片](./API_QUICK_REFERENCE.md)
2. 运行 → `./test_all_apis.sh`（交互模式）
3. 尝试 → 修改测试脚本中的问题

### 🔧 日常开发

1. 使用 → [API 快速参考卡片](./API_QUICK_REFERENCE.md) 速查
2. 参考 → [API 完整参考文档](./API_REFERENCE.md) 深入了解
3. 调试 → 运行测试脚本验证功能

### 🐛 问题排查

1. 检查 → 服务是否启动（`curl http://localhost:8000/api/config`）
2. 查看 → [常见问题](./API_QUICK_REFERENCE.md#-常见问题)
3. 运行 → `./test_all_apis.sh` 验证各接口状态

---

## 📦 测试结果

所有测试脚本的输出保存在：

```
api_test_results/
├── chat_stream.txt                 # 流式聊天接口结果
├── simple_stream.txt               # 简化研究接口结果
├── openai_stream.txt               # OpenAI接口结果
├── prompt_enhance.json             # 提示词增强结果
├── generated.pptx                  # 生成的PPT文件
├── config.json                     # 系统配置
├── route_direct_answer.txt         # Direct Answer路径测试
├── route_simple_search.txt         # Simple Search路径测试
├── route_domain_knowledge.txt      # Domain Knowledge路径测试
└── route_deep_research.txt         # Deep Research路径测试
```

---

## 🌐 相关链接

- **项目主页**: [DeerFlow GitHub](https://github.com/your-org/deer-flow)
- **在线文档**: [官方文档站](https://docs.deerflow.ai)
- **问题反馈**: [GitHub Issues](https://github.com/your-org/deer-flow/issues)

---

## 📝 版本信息

- **API 版本**: v0.1.0
- **文档版本**: v0.1.0
- **更新日期**: 2025-01-04
- **维护者**: DeerFlow Team

---

## 🤝 贡献指南

欢迎提交文档改进建议：

1. Fork 项目
2. 修改文档
3. 提交 Pull Request

---

## 📄 许可证

MIT License

Copyright (c) 2025 Bytedance Ltd. and/or its affiliates

---

**快速开始**: 从 [API 快速参考卡片](./API_QUICK_REFERENCE.md) 开始 🚀
