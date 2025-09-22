# DeerFlow 聊天 API 文档

<cite>
**本文档中引用的文件**
- [chat_request.py](file://src/server/chat_request.py)
- [app.py](file://src/server/app.py)
- [chat.ts](file://web/src/core/api/chat.ts)
- [fetch-stream.ts](file://web/src/core/sse/fetch-stream.ts)
- [types.ts](file://web/src/core/api/types.ts)
- [input-box.tsx](file://web/src/app/chat/components/input-box.tsx)
- [main.tsx](file://web/src/app/chat/main.tsx)
</cite>

## 目录
1. [简介](#简介)
2. [API 端点概览](#api-端点概览)
3. [POST /api/chat/stream](#post-apichatstream)
4. [请求参数详解](#请求参数详解)
5. [响应格式与 SSE 流](#响应格式与-sse-流)
6. [前端客户端实现](#前端客户端实现)
7. [错误处理与状态码](#错误处理与状态码)
8. [认证与安全](#认证与安全)
9. [性能优化](#性能优化)
10. [故障排除指南](#故障排除指南)

## 简介

DeerFlow 聊天 API 是一个基于流式传输的对话系统，支持实时消息交互、多模态内容处理和智能研究功能。该 API 基于 FastAPI 构建，采用 Server-Sent Events (SSE) 技术实现实时通信，并提供了完整的 TypeScript 客户端封装。

主要特性：
- **流式响应**：支持实时消息流传输
- **多模态输入**：支持文本、图像等多种内容类型
- **智能研究**：集成搜索引擎和知识库检索
- **会话管理**：支持持久化对话历史
- **工具调用**：支持多种外部工具集成

## API 端点概览

DeerFlow 提供以下核心 API 端点：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/chat/stream` | POST | 流式聊天对话 |
| `/api/tts` | POST | 文本转语音 |
| `/api/podcast/generate` | POST | 播客生成 |
| `/api/ppt/generate` | POST | PPT 生成 |
| `/api/prose/generate` | POST | 文章生成 |
| `/api/prompt/enhance` | POST | 提示词增强 |
| `/api/mcp/server/metadata` | POST | MCP 服务器元数据 |
| `/api/rag/config` | GET | RAG 配置 |
| `/api/rag/resources` | GET | RAG 资源 |
| `/api/config` | GET | 服务器配置 |

## POST /api/chat/stream

### HTTP 方法与 URL 模式

- **方法**: POST
- **URL**: `/api/chat/stream`
- **内容类型**: `application/json`
- **媒体类型**: `text/event-stream`

### 请求头

```http
Content-Type: application/json
Cache-Control: no-cache
```

### 请求体结构

```typescript
interface ChatRequest {
  messages: ChatMessage[];           // 对话历史
  resources?: Resource[];            // 使用的研究资源
  debug?: boolean;                   // 是否启用调试日志
  thread_id?: string;               // 会话标识符，默认为 "__default__"
  max_plan_iterations?: number;     // 最大计划迭代次数，默认为 1
  max_step_num?: number;            // 计划中的最大步骤数，默认为 3
  max_search_results?: number;      // 最大搜索结果数，默认为 3
  search_engine?: string;           // 搜索引擎类型，默认为 "tavily"
  custom_search_repository?: string; // 自定义搜索仓库 ID
  auto_accepted_plan?: boolean;     // 是否自动接受计划，默认为 false
  interrupt_feedback?: string;      // 用户对计划的中断反馈
  mcp_settings?: object;            // MCP 设置
  enable_background_investigation?: boolean; // 启用背景调查，默认为 true
  report_style?: ReportStyle;       // 报告风格，默认为 ACADEMIC
  enable_deep_thinking?: boolean;   // 启用深度思考，默认为 false
}

interface ChatMessage {
  role: "user" | "assistant";       // 角色：用户或助手
  content: string | ContentItem[];  // 内容：字符串或内容项列表
}

interface ContentItem {
  type: string;                     // 内容类型（text, image 等）
  text?: string;                    // 文本内容（如果类型为 'text'）
  image_url?: string;               // 图像 URL（如果类型为 'image'）
}
```

### 请求示例

#### 普通消息请求

```json
{
  "messages": [
    {
      "role": "user",
      "content": "请帮我写一篇关于人工智能的文章"
    }
  ],
  "thread_id": "session-12345",
  "max_plan_iterations": 2,
  "report_style": "ACADEMIC"
}
```

#### 多模态消息请求

```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "请分析这张图片的内容"
        },
        {
          "type": "image",
          "image_url": "https://example.com/image.jpg"
        }
      ]
    }
  ],
  "search_engine": "tavily",
  "max_search_results": 5
}
```

#### 流式消息请求

```json
{
  "messages": [
    {
      "role": "user",
      "content": "解释量子计算的基本原理"
    }
  ],
  "auto_accepted_plan": false,
  "interrupt_feedback": "accepted",
  "enable_deep_thinking": true
}
```

**章节来源**
- [chat_request.py](file://src/server/chat_request.py#L1-L116)
- [app.py](file://src/server/app.py#L75-L110)

## 请求参数详解

### 核心参数

| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `messages` | `ChatMessage[]` | [] | 对话历史记录 |
| `thread_id` | `string` | "__default__" | 会话唯一标识符 |
| `max_plan_iterations` | `number` | 1 | 最大计划迭代次数 |
| `max_step_num` | `number` | 3 | 单个计划的最大步骤数 |
| `max_search_results` | `number` | 3 | 搜索结果的最大数量 |
| `search_engine` | `string` | "tavily" | 搜索引擎类型 |
| `report_style` | `ReportStyle` | "ACADEMIC" | 报告风格 |

### 搜索引擎选项

支持的搜索引擎类型：
- `"tavily"` - Tavily 搜索引擎
- `"duckduckgo"` - DuckDuckGo 搜索引擎
- `"brave_search"` - Brave 搜索引擎
- `"arxiv"` - ArXiv 学术论文搜索
- `"wikipedia"` - 维基百科搜索
- `"custom_search"` - 自定义搜索引擎

### 报告风格选项

| 风格 | 描述 |
|------|------|
| `ACADEMIC` | 学术风格报告 |
| `POPULAR_SCIENCE` | 科普风格报告 |
| `NEWS` | 新闻风格报告 |
| `SOCIAL_MEDIA` | 社交媒体风格报告 |

### MCP 设置

MCP (Model Context Protocol) 设置用于配置外部工具和服务：

```typescript
interface MCPSettings {
  servers: Record<string, {
    enabled_tools: string[];
    add_to_agents: string[];
  }>;
}
```

**章节来源**
- [chat_request.py](file://src/server/chat_request.py#L30-L85)

## 响应格式与 SSE 流

### SSE 事件类型

DeerFlow 支持多种 SSE 事件类型，每种事件都有特定的数据结构：

#### 1. message_chunk 事件

```typescript
interface MessageChunkEvent {
  type: "message_chunk";
  data: {
    id: string;                              // 消息唯一标识符
    thread_id: string;                       // 会话标识符
    agent: string;                           // 执行代理名称
    role: "user" | "assistant" | "tool";     // 角色
    content?: string;                        // 消息内容
    reasoning_content?: string;              // 推理内容（可选）
    finish_reason?: "stop" | "tool_calls" | "interrupt"; // 结束原因
    tool_calls?: ToolCall[];                 // 工具调用（可选）
    tool_call_chunks?: ToolCallChunk[];      // 工具调用块（可选）
  };
}
```

#### 2. tool_calls 事件

```typescript
interface ToolCallsEvent {
  type: "tool_calls";
  data: {
    id: string;
    thread_id: string;
    agent: string;
    role: "assistant";
    tool_calls: ToolCall[];
    tool_call_chunks: ToolCallChunk[];
  };
}
```

#### 3. tool_call_chunks 事件

```typescript
interface ToolCallChunksEvent {
  type: "tool_call_chunks";
  data: {
    id: string;
    thread_id: string;
    agent: string;
    role: "assistant";
    tool_call_chunks: ToolCallChunk[];
  };
}
```

#### 4. tool_call_result 事件

```typescript
interface ToolCallResultEvent {
  type: "tool_call_result";
  data: {
    id: string;
    thread_id: string;
    agent: string;
    role: "tool";
    tool_call_id: string;                    // 工具调用 ID
    content?: string;                        // 工具返回结果
  };
}
```

#### 5. interrupt 事件

```typescript
interface InterruptEvent {
  type: "interrupt";
  data: {
    id: string;
    thread_id: string;
    agent: string;
    role: "assistant";
    content: string;                         // 中断内容
    finish_reason: "interrupt";              // 中断结束原因
    options: Option[];                       // 可选操作
  };
}
```

### SSE 数据格式

每个 SSE 事件遵循标准格式：

```http
event: <event_type>
data: <JSON_data>

```

### 响应示例

#### 消息流响应

```http
event: message_chunk
data: {"id":"msg-123","thread_id":"session-12345","agent":"planner","role":"assistant","content":"好的，我理解您想了解"}

event: message_chunk
data: {"id":"msg-123","thread_id":"session-12345","agent":"planner","role":"assistant","content":"人工智能的基本概念"}

event: message_chunk
data: {"id":"msg-123","thread_id":"session-12345","agent":"planner","role":"assistant","content":"。让我为您制定一个详细的研究计划。"}
```

#### 工具调用响应

```http
event: tool_calls
data: {"id":"msg-456","thread_id":"session-12345","agent":"researcher","role":"assistant","tool_calls":[{"type":"tool_call","id":"call-789","name":"search","args":{"query":"人工智能基础"}}],"tool_call_chunks":[{"type":"tool_call_chunk","index":0,"id":"call-789","name":"search","args":"{\"query\":\"人工智能基础\"}"}}]}
```

#### 中断响应

```http
event: interrupt
data: {"id":"msg-789","thread_id":"session-12345","agent":"coordinator","role":"assistant","content":"您的研究计划已准备好，请确认是否继续","finish_reason":"interrupt","options":[{"text":"编辑计划","value":"edit_plan"},{"text":"开始研究","value":"accepted"}]}
```

#### 完成响应

```http
event: message_chunk
data: {"id":"msg-123","thread_id":"session-12345","agent":"reporter","role":"assistant","content":"以上就是关于人工智能的基础知识总结。","finish_reason":"stop"}
```

**章节来源**
- [app.py](file://src/server/app.py#L150-L250)
- [types.ts](file://web/src/core/api/types.ts#L1-L85)

## 前端客户端实现

### 客户端封装

前端使用 TypeScript 实现了完整的 API 客户端封装，位于 `web/src/core/api/chat.ts`。

#### 流式聊天函数

```typescript
async function* chatStream(
  userMessage: string,
  params: {
    thread_id: string;
    resources?: Array<Resource>;
    auto_accepted_plan: boolean;
    max_plan_iterations: number;
    max_step_num: number;
    max_search_results?: number;
    search_engine?: string;
    custom_search_repository?: string;
    interrupt_feedback?: string;
    enable_deep_thinking?: boolean;
    enable_background_investigation: boolean;
    report_style?: "academic" | "popular_science" | "news" | "social_media";
    mcp_settings?: {
      servers: Record<string, {
        enabled_tools: string[];
        add_to_agents: string[];
      }>;
    };
  },
  options: { abortSignal?: AbortSignal } = {},
): AsyncIterable<ChatEvent>
```

### SSE 流解析

前端使用 `fetch-stream.ts` 解析 SSE 流：

```typescript
export async function* fetchStream(
  url: string,
  init: RequestInit,
): AsyncIterable<StreamEvent> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache",
    },
    ...init,
  });
  
  const reader = response.body
    ?.pipeThrough(new TextDecoderStream())
    .getReader();
    
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += value;
    while (true) {
      const index = buffer.indexOf("\n\n");
      if (index === -1) break;
      
      const chunk = buffer.slice(0, index);
      buffer = buffer.slice(index + 2);
      const event = parseEvent(chunk);
      if (event) yield event;
    }
  }
}
```

### 事件类型映射

前端定义了完整的事件类型映射：

```typescript
type ChatEvent =
  | MessageChunkEvent
  | ToolCallsEvent
  | ToolCallChunksEvent
  | ToolCallResultEvent
  | InterruptEvent;
```

### React 组件集成

在聊天界面中，React 组件通过以下方式集成 API：

```typescript
// 在组件中使用流式聊天
const handleSendMessage = useCallback(async (message: string) => {
  const stream = chatStream(message, {
    thread_id: sessionId,
    auto_accepted_plan: false,
    max_plan_iterations: 3,
    report_style: "ACADEMIC"
  });
  
  for await (const event of stream) {
    // 处理不同类型的事件
    switch (event.type) {
      case "message_chunk":
        // 更新消息显示
        break;
      case "tool_calls":
        // 显示工具调用
        break;
      case "interrupt":
        // 显示中断选项
        break;
    }
  }
}, []);
```

**章节来源**
- [chat.ts](file://web/src/core/api/chat.ts#L1-L198)
- [fetch-stream.ts](file://web/src/core/sse/fetch-stream.ts#L1-L74)
- [input-box.tsx](file://web/src/app/chat/components/input-box.tsx#L1-L411)

## 错误处理与状态码

### HTTP 状态码

| 状态码 | 描述 | 场景 |
|--------|------|------|
| 200 | 成功 | 请求成功处理 |
| 400 | Bad Request | 请求参数无效 |
| 403 | Forbidden | MCP 功能被禁用 |
| 429 | Too Many Requests | 请求频率过高 |
| 500 | Internal Server Error | 服务器内部错误 |

### 错误响应格式

```typescript
interface ErrorResponse {
  detail: string;  // 错误详情
}
```

### 常见错误场景

#### 1. MCP 服务器配置禁用

```json
{
  "detail": "MCP server configuration is disabled. Set ENABLE_MCP_SERVER_CONFIGURATION=true to enable MCP features."
}
```

#### 2. TTS 配置缺失

```json
{
  "detail": "VOLCENGINE_TTS_APPID is not set"
}
```

#### 3. 内部服务器错误

```json
{
  "detail": "Internal Server Error"
}
```

### 错误处理策略

前端实现了完整的错误处理机制：

```typescript
try {
  const stream = fetchStream(resolveServiceURL("chat/stream"), {
    body: JSON.stringify({
      messages: [{ role: "user", content: userMessage }],
      ...params,
    }),
    signal: options.abortSignal,
  });
  
  for await (const event of stream) {
    yield {
      type: event.event,
      data: JSON.parse(event.data),
    } as ChatEvent;
  }
} catch (e) {
  console.error(e);
  // 显示错误提示给用户
}
```

**章节来源**
- [app.py](file://src/server/app.py#L75-L110)
- [chat.ts](file://web/src/core/api/chat.ts#L35-L45)

## 认证与安全

### CORS 配置

API 支持跨域请求，配置如下：

```python
allowed_origins_str = get_str_env("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

### 环境变量配置

关键的安全相关环境变量：

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `ALLOWED_ORIGINS` | 允许的 CORS 原始地址 | "http://localhost:3000" |
| `ENABLE_MCP_SERVER_CONFIGURATION` | 启用 MCP 服务器配置 | false |
| `VOLCENGINE_TTS_APPID` | Volcengine TTS 应用 ID | - |
| `VOLCENGINE_TTS_ACCESS_TOKEN` | Volcengine TTS 访问令牌 | - |

### 安全最佳实践

1. **生产环境配置**：在生产环境中设置适当的 `ALLOWED_ORIGINS`
2. **MCP 功能控制**：通过环境变量控制 MCP 功能的启用
3. **敏感信息保护**：确保 TTS 配置信息不暴露在前端
4. **请求验证**：后端对所有请求参数进行验证

## 性能优化

### 连接复用

API 设计支持连接复用，减少连接建立开销：

```python
# 使用 StreamingResponse 支持长连接
return StreamingResponse(
    _astream_workflow_generator(...),
    media_type="text/event-stream",
)
```

### 流式解析优化

前端实现了高效的流式解析：

```typescript
// 使用 TextDecoderStream 进行流式解码
const reader = response.body
  ?.pipeThrough(new TextDecoderStream())
  .getReader();

// 缓冲区处理，避免频繁的字符串分割
let buffer = "";
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  buffer += value;
  // 批量处理多个事件
  while (true) {
    const index = buffer.indexOf("\n\n");
    if (index === -1) break;
    
    const chunk = buffer.slice(0, index);
    buffer = buffer.slice(index + 2);
    yield parseEvent(chunk);
  }
}
```

### 批量消息处理

支持批量处理多个消息：

```typescript
// 批量发送消息
const messages = [
  { role: "user", content: "第一句话" },
  { role: "user", content: "第二句话" }
];

const stream = chatStream(messages, {
  thread_id: sessionId,
  auto_accepted_plan: false
});
```

### 缓存策略

前端实现了 Replay 缓存机制：

```typescript
const replayCache = new Map<string, string>();

export async function fetchReplay(url: string) {
  if (replayCache.has(url)) {
    return replayCache.get(url)!;
  }
  
  const text = await fetch(url).then(r => r.text());
  replayCache.set(url, text);
  return text;
}
```

### 性能监控

建议的性能监控指标：

1. **响应时间**：从发送请求到接收第一个事件的时间
2. **吞吐量**：每秒处理的消息数量
3. **连接数**：同时活跃的连接数量
4. **内存使用**：流处理器的内存占用

## 故障排除指南

### 常见问题与解决方案

#### 1. 连接超时

**症状**：客户端无法建立 SSE 连接
**可能原因**：
- 网络防火墙阻止连接
- 服务器配置错误
- CORS 配置不当

**解决方案**：
```bash
# 检查服务器日志
tail -f logs/server.log

# 验证 CORS 配置
curl -I http://your-api-domain.com/api/chat/stream \
  -H "Origin: http://your-frontend-domain.com"
```

#### 2. 流式传输中断

**症状**：SSE 连接意外断开
**可能原因**：
- 服务器负载过高
- 客户端网络不稳定
- 代理服务器超时

**解决方案**：
```typescript
// 实现重连机制
async function reconnectChatStream() {
  let retries = 0;
  const maxRetries = 5;
  
  while (retries < maxRetries) {
    try {
      const stream = chatStream(message, params);
      for await (const event of stream) {
        // 处理事件
      }
      break; // 连接成功，退出循环
    } catch (error) {
      retries++;
      if (retries >= maxRetries) {
        throw new Error('Max retries reached');
      }
      await new Promise(resolve => setTimeout(resolve, 1000 * retries));
    }
  }
}
```

#### 3. 内容解析错误

**症状**：无法正确解析 SSE 事件
**可能原因**：
- 服务器返回格式错误
- 字符编码问题
- 缓冲区溢出

**解决方案**：
```typescript
// 添加错误边界
function parseEvent(chunk: string) {
  try {
    let resultEvent = "message";
    let resultData: string | null = null;
    
    for (const line of chunk.split("\n")) {
      const pos = line.indexOf(": ");
      if (pos === -1) continue;
      
      const key = line.slice(0, pos);
      const value = line.slice(pos + 2);
      
      if (key === "event") {
        resultEvent = value;
      } else if (key === "data") {
        resultData = value;
      }
    }
    
    if (resultEvent === "message" && resultData === null) {
      return undefined;
    }
    
    return { event: resultEvent, data: resultData };
  } catch (error) {
    console.error('Failed to parse event:', error);
    return undefined;
  }
}
```

#### 4. MCP 配置问题

**症状**：MCP 功能无法使用
**可能原因**：
- 环境变量未设置
- MCP 服务器不可达
- 权限配置错误

**解决方案**：
```bash
# 检查环境变量
echo $ENABLE_MCP_SERVER_CONFIGURATION

# 验证 MCP 服务器
curl -X POST http://your-api-domain.com/api/mcp/server/metadata \
  -H "Content-Type: application/json" \
  -d '{"transport": "http", "url": "http://mcp-server:8000"}'
```

### 调试工具

#### 1. 服务器端调试

```python
# 启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 在关键位置添加日志
logger.debug(f"Processing chat request: {request.model_dump()}")
```

#### 2. 客户端调试

```typescript
// 启用详细日志
const DEBUG_CHAT_API = process.env.NODE_ENV === 'development';

if (DEBUG_CHAT_API) {
  console.log('Sending chat request:', { userMessage, params });
}

// 监控事件流
for await (const event of stream) {
  if (DEBUG_CHAT_API) {
    console.log('Received event:', event.type, event.data);
  }
  yield event;
}
```

#### 3. 网络诊断

```bash
# 检查网络连接
ping your-api-domain.com

# 测试 API 端点
curl -v http://your-api-domain.com/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}]}'

# 检查 SSE 连接
curl -N http://your-api-domain.com/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}]}'
```

### 监控与告警

建议实施的监控指标：

1. **连接成功率**：成功建立 SSE 连接的比例
2. **响应延迟**：从请求到接收第一个事件的时间
3. **错误率**：各种错误的发生频率
4. **资源使用**：CPU 和内存使用情况
5. **用户活跃度**：并发用户数量和会话持续时间

通过这些监控指标，可以及时发现和解决潜在的问题，确保系统的稳定性和可靠性。