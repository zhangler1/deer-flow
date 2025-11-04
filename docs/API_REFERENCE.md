# DeerFlow API 接口文档

## 概述

DeerFlow 是一个基于 LangGraph 的智能研究助手系统，提供多种研究和内容生成功能。本文档涵盖所有 API 接口的详细说明和使用示例。

**服务地址**: `http://localhost:8000`  
**协议**: HTTP/HTTPS  
**数据格式**: JSON  
**流式协议**: Server-Sent Events (SSE)

---

## 目录

1. [核心研究接口](#核心研究接口)
   - [流式聊天接口](#1-流式聊天接口-apichatstream)
   - [简化流式研究接口](#2-简化流式研究接口-apiresearchsimplestream)
   - [OpenAI 兼容流式接口](#3-openai-兼容流式接口-apiresearchsimplestreamopenai)

2. [内容生成接口](#内容生成接口)
   - [PPT 生成接口](#1-ppt-生成接口-apipptgenerate)
   - [提示词增强接口](#2-提示词增强接口-apipromptenhance)

3. [配置管理接口](#配置管理接口)
   - [系统配置接口](#1-系统配置接口-apiconfig)
   - [RAG 配置接口](#2-rag-配置接口-apiragconfig)
   - [RAG 资源接口](#3-rag-资源接口-apiragresources)

4. [MCP 服务器接口](#mcp-服务器接口)
   - [MCP 服务器元数据接口](#1-mcp-服务器元数据接口-apimcpservermetadata)

---

## 核心研究接口

### 1. 流式聊天接口 `/api/chat/stream`

**完整的 LangGraph 工作流接口**，支持4种智能路由路径，提供最强大的研究能力。

#### 请求

**方法**: `POST`  
**Content-Type**: `application/json`

**请求参数**:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "分析金融科技对传统银行的影响趋势"
    }
  ],
  "resources": [],
  "debug": false,
  "thread_id": "__default__",
  "max_plan_iterations": 1,
  "max_step_num": 3,
  "max_search_results": 3,
  "search_engine": "custom_search",
  "custom_search_repository": null,
  "auto_accepted_plan": false,
  "interrupt_feedback": null,
  "mcp_settings": {},
  "enable_background_investigation": true,
  "report_style": "academic",
  "enable_deep_thinking": false
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `messages` | Array | 是 | - | 对话消息列表，OpenAI 格式 |
| `resources` | Array | 否 | `[]` | RAG 资源列表 |
| `debug` | Boolean | 否 | `false` | 是否启用调试日志 |
| `thread_id` | String | 否 | `__default__` | 会话标识符，用于多轮对话 |
| `max_plan_iterations` | Integer | 否 | `1` | 最大计划迭代次数 |
| `max_step_num` | Integer | 否 | `3` | 计划中的最大步骤数 |
| `max_search_results` | Integer | 否 | `3` | 每次搜索的最大结果数 |
| `search_engine` | String | 否 | `custom_search` | 搜索引擎 (tavily, duckduckgo, brave_search, arxiv, wikipedia, custom_search) |
| `custom_search_repository` | String | 否 | `null` | 自定义搜索仓库 ID |
| `auto_accepted_plan` | Boolean | 否 | `false` | 是否自动接受计划（跳过人工审核） |
| `interrupt_feedback` | String | 否 | `null` | 用户对计划的中断反馈 |
| `mcp_settings` | Object | 否 | `{}` | MCP 服务器设置 |
| `enable_background_investigation` | Boolean | 否 | `true` | 是否启用背景调研 |
| `report_style` | String | 否 | `academic` | 报告风格 (academic, popular_science, news, social_media) |
| `enable_deep_thinking` | Boolean | 否 | `false` | 是否启用深度思考模式 |

#### 响应

**Content-Type**: `text/event-stream` (SSE)

**事件类型**:

- `message_chunk`: AI 消息片段
- `tool_calls`: 工具调用信息
- `tool_call_result`: 工具执行结果
- `interrupt`: 计划审核中断
- `error`: 错误信息

**响应示例**:

```
event: message_chunk
data: {"thread_id":"abc123","agent":"coordinator","role":"assistant","content":"正在为您研究..."}

event: tool_call_result
data: {"thread_id":"abc123","agent":"researcher","tool_call_id":"call_1","content":"...搜索结果..."}

event: message_chunk
data: {"thread_id":"abc123","agent":"reporter","role":"assistant","content":"# 研究报告\n\n..."}
```

#### curl 示例

```bash
# 基础用法 - 深度研究模式
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "分析金融科技对传统银行的影响趋势"
      }
    ],
    "search_engine": "tavily",
    "max_step_num": 5,
    "auto_accepted_plan": true,
    "enable_background_investigation": true
  }'

# 简单问答 - 通过智能路由自动选择 simple_search 路径
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "信用卡如何申请？"
      }
    ],
    "search_engine": "custom_search",
    "max_search_results": 3
  }'

# 通用知识 - 通过智能路由自动选择 direct_answer 路径
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "什么是汽车？"
      }
    ]
  }'

# 专业领域 - 通过智能路由自动选择 domain_knowledge 路径
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "SWIFT报文MT103的字段详细说明"
      }
    ],
    "resources": [
      {
        "type": "local",
        "path": "/path/to/knowledge/base"
      }
    ]
  }'

# 多轮对话
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "conversation_001",
    "messages": [
      {
        "role": "user",
        "content": "介绍一下区块链技术"
      },
      {
        "role": "assistant",
        "content": "区块链是一种分布式账本技术..."
      },
      {
        "role": "user",
        "content": "它在金融领域有什么应用？"
      }
    ]
  }'
```

---

### 2. 简化流式研究接口 `/api/research/simple/stream`

**简化版研究接口**，直接使用 LangGraph 工作流，适合需要快速研究结果的场景。

#### 请求

**方法**: `POST`  
**Content-Type**: `application/json`

**请求参数**: 与 `/api/chat/stream` 完全一致

```json
{
  "messages": [
    {
      "role": "user",
      "content": "2024年人工智能发展趋势"
    }
  ],
  "search_engine": "tavily",
  "max_search_results": 5,
  "auto_accepted_plan": true,
  "enable_deep_thinking": false
}
```

#### 响应

**Content-Type**: `text/event-stream` (SSE)

响应格式与 `/api/chat/stream` 相同。

#### curl 示例

```bash
# 基础用法
curl -X POST http://localhost:8000/api/research/simple/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "2024年人工智能发展趋势"
      }
    ],
    "search_engine": "tavily",
    "max_search_results": 5,
    "auto_accepted_plan": true
  }'

# 使用自定义搜索引擎
curl -X POST http://localhost:8000/api/research/simple/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "信用卡申请流程"
      }
    ],
    "search_engine": "custom_search",
    "custom_search_repository": "bank_knowledge",
    "max_step_num": 3
  }'

# 启用深度思考模式
curl -X POST http://localhost:8000/api/research/simple/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "分析量子计算对密码学的影响"
      }
    ],
    "enable_deep_thinking": true,
    "max_plan_iterations": 2,
    "max_step_num": 5
  }'
```

---

### 3. OpenAI 兼容流式接口 `/api/research/simple/stream/openai`

**OpenAI 格式兼容接口**，返回符合 OpenAI chat.completion.chunk 格式的流式响应。

#### 请求

**方法**: `POST`  
**Content-Type**: `application/json`

**请求参数**: 与 `/api/research/simple/stream` 完全一致

#### 响应

**Content-Type**: `text/event-stream` (SSE)

**OpenAI 标准格式**:

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deep-research-openai-stream","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deep-research-openai-stream","choices":[{"index":0,"delta":{"content":"研究"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deep-research-openai-stream","choices":[{"index":0,"delta":{"content":"报告"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"deep-research-openai-stream","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"completion_tokens":0,"prompt_tokens":0,"total_tokens":0}}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String | 会话 ID |
| `object` | String | 固定为 `chat.completion.chunk` |
| `created` | Integer | Unix 时间戳（秒） |
| `model` | String | 固定为 `deep-research-openai-stream` |
| `choices[].index` | Integer | 选择项索引（通常为 0） |
| `choices[].delta.role` | String | 角色（仅第一个 chunk 包含） |
| `choices[].delta.content` | String | 内容片段 |
| `choices[].finish_reason` | String | 结束原因（最后一个 chunk 为 "stop"） |
| `usage` | Object | Token 使用统计（最后一个 chunk 包含） |

#### curl 示例

```bash
# 基础用法
curl -X POST http://localhost:8000/api/research/simple/stream/openai \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "介绍一下区块链技术"
      }
    ],
    "search_engine": "tavily",
    "auto_accepted_plan": true
  }'

# 与 OpenAI SDK 兼容用法（Python）
# 注意：需要自定义 base_url
```

**Python SDK 示例**:

```python
import requests
import json

url = "http://localhost:8000/api/research/simple/stream/openai"
headers = {"Content-Type": "application/json"}
data = {
    "messages": [
        {
            "role": "user",
            "content": "2024年AI发展趋势"
        }
    ],
    "search_engine": "tavily",
    "auto_accepted_plan": True
}

response = requests.post(url, headers=headers, json=data, stream=True)

for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            chunk = json.loads(line_str[6:])
            if chunk['choices'][0]['delta'].get('content'):
                print(chunk['choices'][0]['delta']['content'], end='', flush=True)
```

---

## 内容生成接口

### 1. PPT 生成接口 `/api/ppt/generate`

根据研究报告内容生成 PowerPoint 演示文稿。

#### 请求

**方法**: `POST`  
**Content-Type**: `application/json`

```json
{
  "content": "# 研究报告标题\n\n## 第一部分\n内容...\n\n## 第二部分\n内容..."
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `content` | String | 是 | Markdown 格式的报告内容 |

#### 响应

**Content-Type**: `application/vnd.openxmlformats-officedocument.presentationml.presentation`

返回 `.pptx` 文件的二进制数据。

#### curl 示例

```bash
# 生成 PPT 并保存
curl -X POST http://localhost:8000/api/ppt/generate \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# AI发展趋势报告\n\n## 概述\n人工智能正在快速发展...\n\n## 关键技术\n- 深度学习\n- 强化学习\n- 大语言模型"
  }' \
  --output report.pptx

echo "PPT已保存到 report.pptx"
```

---

### 2. 提示词增强接口 `/api/prompt/enhance`

优化和增强用户提示词，使其更适合研究任务。

#### 请求

**方法**: `POST`  
**Content-Type**: `application/json`

```json
{
  "prompt": "AI 发展",
  "context": "需要写一份学术报告",
  "report_style": "academic"
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | String | 是 | - | 原始提示词 |
| `context` | String | 否 | `""` | 使用场景的额外上下文 |
| `report_style` | String | 否 | `academic` | 报告风格 (academic, popular_science, news, social_media) |

#### 响应

**Content-Type**: `application/json`

```json
{
  "result": "请深入研究人工智能在2020-2024年间的主要技术发展趋势，包括但不限于深度学习、强化学习、大语言模型等领域的突破性进展，并分析这些技术对学术界和产业界的影响。"
}
```

#### curl 示例

```bash
# 基础用法
curl -X POST http://localhost:8000/api/prompt/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "AI 发展",
    "context": "需要写一份学术报告",
    "report_style": "academic"
  }'

# 不同风格示例
curl -X POST http://localhost:8000/api/prompt/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "区块链技术",
    "report_style": "popular_science"
  }'

# 社交媒体风格
curl -X POST http://localhost:8000/api/prompt/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "量子计算",
    "context": "写一篇公众号文章",
    "report_style": "social_media"
  }'
```

---

## 配置管理接口

### 1. 系统配置接口 `/api/config`

获取系统的完整配置信息，包括 RAG、模型和搜索仓库配置。

#### 请求

**方法**: `GET`

#### 响应

**Content-Type**: `application/json`

```json
{
  "rag": {
    "provider": "milvus"
  },
  "models": [
    {
      "name": "gpt-4",
      "type": "BASIC_MODEL",
      "provider": "openai"
    }
  ],
  "custom_search_repositories": [
    {
      "id": "bank_knowledge",
      "name": "银行知识库",
      "description": "交通银行内部知识库",
      "repository": "http://example.com/search"
    }
  ]
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `rag.provider` | String | RAG 提供商 (milvus, chroma, etc.) |
| `models` | Array | 配置的 LLM 模型列表 |
| `custom_search_repositories` | Array | 自定义搜索仓库列表 |

#### curl 示例

```bash
# 获取系统配置
curl -X GET http://localhost:8000/api/config

# 格式化输出
curl -X GET http://localhost:8000/api/config | jq .

# 只获取模型配置
curl -X GET http://localhost:8000/api/config | jq '.models'

# 只获取搜索仓库配置
curl -X GET http://localhost:8000/api/config | jq '.custom_search_repositories'
```

---

### 2. RAG 配置接口 `/api/rag/config`

获取 RAG（检索增强生成）的配置信息。

#### 请求

**方法**: `GET`

#### 响应

**Content-Type**: `application/json`

```json
{
  "provider": "milvus"
}
```

#### curl 示例

```bash
# 获取 RAG 配置
curl -X GET http://localhost:8000/api/rag/config
```

---

### 3. RAG 资源接口 `/api/rag/resources`

查询可用的 RAG 资源。

#### 请求

**方法**: `GET`

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | String | 否 | 搜索查询词 |

#### 响应

**Content-Type**: `application/json`

```json
{
  "resources": [
    {
      "type": "document",
      "path": "/path/to/doc1.pdf",
      "metadata": {
        "title": "文档标题"
      }
    }
  ]
}
```

#### curl 示例

```bash
# 获取所有资源
curl -X GET "http://localhost:8000/api/rag/resources"

# 搜索特定资源
curl -X GET "http://localhost:8000/api/rag/resources?query=银行规章"

# URL 编码查询
curl -X GET "http://localhost:8000/api/rag/resources?query=%E9%93%B6%E8%A1%8C"
```

---

## MCP 服务器接口

### 1. MCP 服务器元数据接口 `/api/mcp/server/metadata`

获取 MCP（Model Context Protocol）服务器的元数据信息。

**前置条件**: 需要在环境变量中设置 `ENABLE_MCP_SERVER_CONFIGURATION=true`

#### 请求

**方法**: `POST`  
**Content-Type**: `application/json`

```json
{
  "transport": "stdio",
  "command": "mcp-server",
  "args": ["--config", "/path/to/config"],
  "url": null,
  "env": {},
  "headers": {},
  "timeout_seconds": 300
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `transport` | String | 是 | - | 传输协议类型 (stdio, http) |
| `command` | String | 否 | `null` | 命令路径 |
| `args` | Array | 否 | `[]` | 命令参数 |
| `url` | String | 否 | `null` | HTTP URL（transport=http 时使用） |
| `env` | Object | 否 | `{}` | 环境变量 |
| `headers` | Object | 否 | `{}` | HTTP 头（transport=http 时使用） |
| `timeout_seconds` | Integer | 否 | `300` | 超时时间（秒） |

#### 响应

**Content-Type**: `application/json`

```json
{
  "transport": "stdio",
  "command": "mcp-server",
  "args": ["--config", "/path/to/config"],
  "url": null,
  "env": {},
  "headers": {},
  "tools": [
    {
      "name": "tool_name",
      "description": "工具描述",
      "parameters": {}
    }
  ]
}
```

#### curl 示例

```bash
# stdio 传输方式
curl -X POST http://localhost:8000/api/mcp/server/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "transport": "stdio",
    "command": "mcp-server",
    "args": ["--config", "/etc/mcp/config.json"],
    "timeout_seconds": 300
  }'

# HTTP 传输方式
curl -X POST http://localhost:8000/api/mcp/server/metadata \
  -H "Content-Type: application/json" \
  -d '{
    "transport": "http",
    "url": "http://mcp-server:8080",
    "headers": {
      "Authorization": "Bearer token123"
    },
    "timeout_seconds": 60
  }'
```

---

## 智能路由机制

DeerFlow 使用智能路由系统，根据用户问题自动选择最合适的处理路径：

### 路径类型

| 路径 | 适用场景 | 特点 |
|------|----------|------|
| **direct_answer** | 通用知识问题 | 不走检索，直接回答，速度最快 |
| **simple_search** | 常规业务问题 | 单次检索+回答，主流路径 |
| **domain_knowledge** | 专业领域问题 | 使用专业知识库，深度回答 |
| **deep_research** | 复杂研究任务 | 完整研究流程，质量最高 |

### 示例

```bash
# direct_answer 路径 - 通用知识
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"什么是汽车？"}]}'

# simple_search 路径 - 常规问题
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"信用卡如何申请？"}]}'

# domain_knowledge 路径 - 专业知识
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages":[{"role":"user","content":"SWIFT报文MT103的字段说明"}],
    "resources":[{"type":"local","path":"/knowledge"}]
  }'

# deep_research 路径 - 深度研究
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages":[{"role":"user","content":"分析金融科技对传统银行的影响趋势"}],
    "max_step_num":5,
    "enable_background_investigation":true
  }'
```

---

## 错误处理

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| `200` | 请求成功 |
| `403` | 功能未启用（如 MCP 配置未开启） |
| `422` | 请求参数验证失败 |
| `500` | 服务器内部错误 |

### 错误响应格式

```json
{
  "detail": "错误详细信息"
}
```

### SSE 错误事件

```
event: error
data: {"thread_id":"xxx","error":"错误信息"}
```

---

## 最佳实践

### 1. 参数调优建议

**快速研究**:
```json
{
  "max_step_num": 3,
  "max_search_results": 3,
  "auto_accepted_plan": true,
  "enable_background_investigation": false
}
```

**深度研究**:
```json
{
  "max_plan_iterations": 2,
  "max_step_num": 5,
  "max_search_results": 5,
  "enable_background_investigation": true,
  "enable_deep_thinking": true
}
```

**银行业务场景**:
```json
{
  "search_engine": "custom_search",
  "custom_search_repository": "bank_knowledge",
  "resources": [{"type": "local", "path": "/bank/knowledge"}]
}
```

### 2. 流式输出处理

**Bash 示例**:
```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"AI趋势"}]}'
```

**Python 示例**:
```python
import requests
import json

url = "http://localhost:8000/api/chat/stream"
data = {"messages": [{"role": "user", "content": "AI趋势"}]}

with requests.post(url, json=data, stream=True) as response:
    for line in response.iter_lines():
        if line:
            # 解析 SSE 事件
            line_str = line.decode('utf-8')
            if line_str.startswith('event: '):
                event_type = line_str[7:]
            elif line_str.startswith('data: '):
                event_data = json.loads(line_str[6:])
                print(event_data.get('content', ''), end='', flush=True)
```

### 3. 会话管理

保持多轮对话：
```bash
THREAD_ID="conv_$(date +%s)"

# 第一轮
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d "{
    \"thread_id\": \"$THREAD_ID\",
    \"messages\": [{\"role\":\"user\",\"content\":\"介绍区块链\"}]
  }"

# 第二轮（使用相同 thread_id）
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d "{
    \"thread_id\": \"$THREAD_ID\",
    \"messages\": [
      {\"role\":\"user\",\"content\":\"介绍区块链\"},
      {\"role\":\"assistant\",\"content\":\"区块链是...\"},
      {\"role\":\"user\",\"content\":\"在金融领域的应用？\"}
    ]
  }"
```

---

## 附录

### A. 报告风格说明

| 风格 | 值 | 适用场景 |
|------|------|----------|
| 学术风格 | `academic` | 研究论文、学术报告 |
| 科普风格 | `popular_science` | 科普文章、技术博客 |
| 新闻风格 | `news` | 新闻报道、快讯 |
| 社交媒体 | `social_media` | 公众号、微博、短视频 |

### B. 搜索引擎说明

| 引擎 | 值 | 特点 |
|------|------|------|
| Tavily | `tavily` | AI 优化搜索，适合研究 |
| DuckDuckGo | `duckduckgo` | 隐私保护，通用搜索 |
| Brave Search | `brave_search` | 独立索引，快速响应 |
| arXiv | `arxiv` | 学术论文搜索 |
| Wikipedia | `wikipedia` | 百科知识搜索 |
| 自定义搜索 | `custom_search` | 企业内部知识库 |

### C. 环境变量配置

```bash
# 基础配置
ALLOWED_ORIGINS=http://localhost:3000
LANGGRAPH_CHECKPOINT_SAVER=false

# MCP 配置
ENABLE_MCP_SERVER_CONFIGURATION=false

# 数据库配置（可选）
LANGGRAPH_CHECKPOINT_DB_URL=postgresql://user:pass@host:5432/db
# 或
LANGGRAPH_CHECKPOINT_DB_URL=mongodb://host:27017/db

# 递归限制
AGENT_RECURSION_LIMIT=50
```

---

## 技术支持

- **项目地址**: [DeerFlow GitHub](https://github.com/your-org/deer-flow)
- **文档版本**: v0.1.0
- **更新日期**: 2025-01-04

---

**注意事项**:
1. 所有接口均支持 CORS，允许的源由 `ALLOWED_ORIGINS` 环境变量配置
2. 流式接口使用 SSE 协议，客户端需支持 `text/event-stream`
3. `report_style` 参数必须使用小写格式
4. MCP 相关功能需要显式启用环境变量
5. 建议在生产环境使用 checkpoint 数据库以支持会话持久化
