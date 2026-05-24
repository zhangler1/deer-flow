# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import base64
from datetime import datetime
import asyncio
import json
import tempfile
from langchain_core.messages.base import BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
import logging
import re
import time
import uuid
from typing import Annotated, Any, List, cast, Dict,Optional
import uuid
from uuid import uuid4
import os
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langgraph.types import Command
from langgraph.store.memory import InMemoryStore
# from langgraph.checkpoint.mongodb import AsyncMongoDBSaver  # removed: 不再使用 MongoDB checkpoint
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from src.config.configuration import get_recursion_limit
from src.config.loader import get_bool_env, get_str_env, load_tool_compression_config
from src.config.report_style import ReportStyle
from src.config.tools import SELECTED_RAG_PROVIDER
from src.graph.builder import build_graph_with_memory
from src.llms.llm import EnhancedLLMWrapper, get_configured_llm_models
from src.podcast.graph.builder import build_graph as build_podcast_graph
from src.ppt.graph.builder import build_graph as build_ppt_graph
from src.prompt_enhancer.graph.builder import build_graph as build_prompt_enhancer_graph
from src.prompt_enhancer.graph.state import PromptEnhancerState
from src.prose.graph.builder import build_graph as build_prose_graph
from src.rag.builder import build_retriever
try:
    from src.rag.milvus import load_examples
except ImportError:
    load_examples = None  # type: ignore[assignment]
from src.rag.retriever import Resource
from src.server.chat_request import (
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatRequest,
    EnhancePromptRequest,
    GeneratePodcastRequest,
    GeneratePPTRequest,
    GenerateProseRequest,
    MarkdownToWordRequest,
    SimpleResearchRequest,
    SimpleResearchResponse,
    # TTSRequest 已删除
)
from src.server.config_request import ConfigResponse
from src.server.mcp_request import MCPServerMetadataRequest, MCPServerMetadataResponse
from src.server.mcp_utils import load_mcp_tools
from src.server.rag_request import (
    RAGConfigResponse,
    RAGResourceRequest,
    RAGResourcesResponse,
)
from src.tools import VolcengineTTS
from src.graph.checkpoint import chat_stream_message
from src.utils.json_utils import sanitize_args
from src.utils.enhanced_logger import get_enhanced_logger, setup_enhanced_logging

logger = logging.getLogger(__name__)

# 初始化增强日志系统，支持从环境变量LOG_FILE读取日志文件路径
log_file = os.getenv('LOG_FILE')  # 例如: logs/deer-flow.log
setup_enhanced_logging(level=logging.INFO, enable_colors=True, log_file=log_file)
enhanced_logger = get_enhanced_logger("deer-flow.api")

# 加载工具结果压缩配置
load_tool_compression_config()

# Track active tool calls for search status
_active_search_calls: Dict[str, Dict[str, str]] = {}

# Track accumulated content for each message to detect round progress
# Key: message_id, Value: accumulated content string
_message_content_buffer: Dict[str, str] = {}

# Track detected round progress for each message
# Key: message_id, Value: tuple (tag, matched_text)
_round_progress_detected: Dict[str, tuple] = {}

INTERNAL_SERVER_ERROR_DETAIL = "Internal Server Error"

app = FastAPI(
    title="DeerFlow API",
    description="API for Deer",
    version="0.1.0",
)

# Add CORS middleware
# It's recommended to load the allowed origins from an environment variable
# for better security and flexibility across different environments.
allowed_origins_str = get_str_env("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

logger.info(f"Allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Restrict to specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Use the configured list of methods
    allow_headers=["*"],  # Now allow all headers, but can be restricted further
)

# Load examples into Milvus if configured
if load_examples is not None:
    load_examples()

in_memory_store = InMemoryStore()
graph = build_graph_with_memory()


@app.get("/health")
async def health_check():
    """Lightweight health probe for container-level liveness checks.

    Returns 200 quickly without touching heavy dependencies; the external
    health-monitor script (scripts/health-monitor.sh) polls this endpoint.
    """
    return {"status": "ok", "service": "deer-flow-backend"}


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, raw_request: Request):
    # Check if MCP server configuration is enabled
    mcp_enabled = get_bool_env("ENABLE_MCP_SERVER_CONFIGURATION", False)

    # Validate MCP settings if provided
    if request.mcp_settings and not mcp_enabled:
        raise HTTPException(
            status_code=403,
            detail="MCP server configuration is disabled. Set ENABLE_MCP_SERVER_CONFIGURATION=true to enable MCP features.",
        )

    # 确保 thread_id 不为 None，如果是 None 或默认值，则生成新的 UUID
    thread_id = request.thread_id
    if thread_id is None or thread_id == "__default__":
        thread_id = str(uuid4())
    
    # 从环境变量读取系统背景上下文
    system_context = get_str_env("SYSTEM_CONTEXT", "")

    # 创建取消事件：客户端断连或显式调用 /api/chat/cancel 时用于通知后端节点中止
    # 采用全局注册表按 thread_id 索引，避免通过 LangGraph config 传递对象引用导致丢失
    from src.graph import cancellation as _cancel_registry
    cancel_event = _cancel_registry.register(thread_id)

    async def _cancellable_stream():
        """包装生成器，检测客户端断连并设置取消信号。"""
        try:
            async for event in _astream_workflow_generator(
                request.model_dump()["messages"],
                thread_id,
                request.resources or [],
                request.max_plan_iterations or 2,
                request.max_step_num or 5,
                request.max_search_results or 2,
                request.max_iteration or 5,
                request.search_engine or "custom_search",
                request.auto_accepted_plan or False,
                request.interrupt_feedback or "",
                request.mcp_settings if (mcp_enabled and request.mcp_settings) else {},
                request.enable_background_investigation or True,
                request.report_style or ReportStyle.ACADEMIC,
                request.enable_deep_thinking or False,
                system_context=system_context,
                force_routing_path=request.force_routing_path,
                guwp_token=request.guwp_token,
                use_budget_controlled_online_search=request.use_budget_controlled_online_search if request.use_budget_controlled_online_search is not None else True,
                use_budget_controlled_bocom_search=request.use_budget_controlled_bocom_search if request.use_budget_controlled_bocom_search is not None else True,
                cancel_event=cancel_event,
            ):
                # 每发送一个 SSE 事件前检查客户端是否断连
                if await raw_request.is_disconnected():
                    logger.info(f"[CLIENT_DISCONNECTED] thread_id={thread_id} | 客户端已断连，停止推送")
                    cancel_event.set()
                    break
                if cancel_event.is_set():
                    logger.info(f"[CANCEL_TRIGGERED] thread_id={thread_id} | cancel_event 已设置，停止推送")
                    break
                yield event
        except asyncio.CancelledError:
            logger.info(f"[STREAM_CANCELLED] thread_id={thread_id} | 流被取消")
        finally:
            cancel_event.set()  # 确保无论如何都通知下游停止
            _cancel_registry.unregister(thread_id)
            logger.debug(f"[STREAM_CLEANUP] thread_id={thread_id} | cancel_event 已设置, registry 已清理")

    return StreamingResponse(
        _cancellable_stream(),
        media_type="text/event-stream",
    )


def _process_tool_call_chunks(tool_call_chunks, extra_headers: Optional[Dict[str, str]] = None):
    """Process tool call chunks and sanitize arguments."""
    chunks = []
    for chunk in tool_call_chunks:
        # Add extra headers info if present and chunk matches bocomsearch
        name = chunk.get("name", "")
        args = chunk.get("args", "")
        if extra_headers and name == "bocomsearch":
            # Inject marker for frontend or downstream to know headers should be applied
            chunk_headers = {"__extra_headers__": extra_headers}
        else:
            chunk_headers = None
        chunks.append(
            {
                "name": name,
                "args": sanitize_args(args),
                "id": chunk.get("id", ""),
                "index": chunk.get("index", 0),
                "type": chunk.get("type", ""),
                "headers": chunk_headers,
            }
        )
    return chunks


@app.post("/api/chat/cancel")
async def chat_cancel(payload: dict):
    """显式取消接口：前端点停止时调用，按 thread_id 主动触发 cancel_event。

    不依赖 TCP 断连检测，避免浏览器 fetch abort 后 keep-alive 连接不关闭导致的失联。
    """
    from src.graph import cancellation as _cancel_registry
    thread_id = (payload or {}).get("thread_id")
    if not thread_id:
        return {"ok": False, "reason": "thread_id required"}
    event = _cancel_registry.get(thread_id)
    if event is None:
        logger.info(f"[CHAT_CANCEL] thread_id={thread_id} | 未找到 cancel_event（任务可能已结束）")
        return {"ok": False, "reason": "not found"}
    event.set()
    logger.info(f"[CHAT_CANCEL] thread_id={thread_id} | 已触发 cancel_event")
    return {"ok": True}


def _get_agent_name(agent, message_metadata):
    """Extract agent name from agent tuple."""
    agent_name = "unknown"
    if agent and len(agent) > 0:
        agent_name = agent[0].split(":")[0] if ":" in agent[0] else agent[0]
    else:
        agent_name = message_metadata.get("langgraph_node", "unknown")
    return agent_name


def _determine_message_tag(agent_name, message_metadata, message_chunk):
    """Determine the tag for the message based on agent, node, and message type."""
    langgraph_node = message_metadata.get("langgraph_node", "")
    
    # Check if round progress has been detected for this message
    message_id = message_chunk.id
    if message_id in _round_progress_detected:
        return _round_progress_detected[message_id]
    
    # Accumulate content and check for round progress pattern ("第X轮研究进展")
    # Only check when content buffer has accumulated at least 30 characters
    if hasattr(message_chunk, 'content') and message_chunk.content:
        # Initialize or update content buffer for this message
        if message_id not in _message_content_buffer:
            _message_content_buffer[message_id] = ""
        _message_content_buffer[message_id] += message_chunk.content
        
        # Only attempt matching when we have accumulated enough content (>=30 chars)
        accumulated_content = _message_content_buffer[message_id]
        if len(accumulated_content) >= 30:
            round_match = re.search(r'第(\d+)轮研究进展', accumulated_content)
            if round_match:
                # Cache the detected result
                result = ("round_progress", round_match.group(0))
                _round_progress_detected[message_id] = result
                # Clear buffer after detection to save memory
                _message_content_buffer.pop(message_id, None)
                return result
    
    # Check for routing phase
    if agent_name in ("router", "direct_answer_node", "simple_search_node", "domain_knowledge_node"):
        return "routing"
    
    # Check for planning phase
    if agent_name == "planner" or langgraph_node == "planner":
        return "planning"
    
    # Check for reporting phase
    if agent_name == "reporter" or langgraph_node == "reporter" or agent_name == "iterative_reporter_node":
        return "reporting"
    
    # Check for iterative research node - default to answering unless tool calls are involved
    if agent_name == "iterative_research_node":
        # If there are tool calls or tool call chunks, don't set tag here
        # (it will be set in _process_message_chunk when handling tool calls)
        if hasattr(message_chunk, 'tool_calls') and message_chunk.tool_calls:
            return None  # Will be set to "searching" in tool_calls handling
        if hasattr(message_chunk, 'tool_call_chunks') and message_chunk.tool_call_chunks:
            return None  # Will be set to "searching" in tool_call_chunks handling
        # Check if has reasoning content - indicates analyzing
        if hasattr(message_chunk, 'additional_kwargs') and message_chunk.additional_kwargs.get("reasoning_content"):
            return "iterative_answering"
        # Default to answering for iterative research
        return "answering"
    
    # Check for researcher - could be searching or analyzing
    if agent_name == "researcher" or langgraph_node == "researcher":
        # If there are tool calls, tag will be set in tool_calls handling
        if hasattr(message_chunk, 'tool_calls') and message_chunk.tool_calls:
            return None
        if hasattr(message_chunk, 'tool_call_chunks') and message_chunk.tool_call_chunks:
            return None
        # Otherwise, it's analyzing/answering
        return "iterative_answering"
    
    # Check for coder
    if agent_name == "coder" or langgraph_node == "coder":
        return "answering"
    
    # Default - no specific tag
    return None


def _create_event_stream_message(
    message_chunk, message_metadata, thread_id, agent_name
):
    """Create base event stream message."""
    event_stream_message = {
        "thread_id": thread_id,
        "agent": agent_name,
        "id": message_chunk.id,
        "role": "assistant",
        "checkpoint_ns": message_metadata.get("checkpoint_ns", ""),
        "langgraph_node": message_metadata.get("langgraph_node", ""),
        "langgraph_path": message_metadata.get("langgraph_path", ""),
        "langgraph_step": message_metadata.get("langgraph_step", ""),
        "content": message_chunk.content,
    }

    # Add optional fields
    if message_chunk.additional_kwargs.get("reasoning_content"):
        event_stream_message["reasoning_content"] = message_chunk.additional_kwargs[
            "reasoning_content"
        ]

    if message_chunk.response_metadata.get("finish_reason"):
        finish_reason = message_chunk.response_metadata.get("finish_reason")
        event_stream_message["finish_reason"] = finish_reason
        
        # Clean up content buffers when message finishes
        message_id = message_chunk.id
        _message_content_buffer.pop(message_id, None)
        _round_progress_detected.pop(message_id, None)
    
    # Add tag based on agent and node information
    tag = _determine_message_tag(agent_name, message_metadata, message_chunk)
    if tag:
        # Check if tag is a tuple (for round_progress with matched text)
        if isinstance(tag, tuple):
            event_stream_message["tag"] = tag[0]
            event_stream_message["round_text"] = tag[1]  # Add the matched "第X轮研究进展" text
        else:
            event_stream_message["tag"] = tag

    return event_stream_message


def _create_interrupt_event(thread_id, event_data):
    """Create interrupt event."""
    try:
        interrupt_obj = event_data["__interrupt__"][0]
        
        # 尝试获取 ID，适配不同版本的 LangGraph API
        interrupt_id = None
        if hasattr(interrupt_obj, 'ns') and interrupt_obj.ns:
            # 旧版本 API：使用 ns 属性
            interrupt_id = interrupt_obj.ns[0]
        elif hasattr(interrupt_obj, 'id'):
            # 新版本 API：使用 id 属性
            interrupt_id = interrupt_obj.id
        elif hasattr(interrupt_obj, 'task_id'):
            # 另一种可能的新版本 API
            interrupt_id = interrupt_obj.task_id
        else:
            # 回退：使用生成的 UUID
            interrupt_id = str(uuid4())
            logger.warning(f"Unable to extract interrupt ID from object {type(interrupt_obj)}, using generated UUID: {interrupt_id}")
        
        # 获取中断内容
        content = ""
        if hasattr(interrupt_obj, 'value'):
            content = interrupt_obj.value
        elif hasattr(interrupt_obj, 'content'):
            content = interrupt_obj.content
        elif hasattr(interrupt_obj, 'message'):
            content = interrupt_obj.message
        else:
            content = str(interrupt_obj)
            logger.warning(f"Unable to extract content from interrupt object {type(interrupt_obj)}, using string representation")
        
        # 区分中断类型：问题澄清 vs 计划确认
        if isinstance(content, dict) and content.get("type") == "clarification":
            # 问题澄清中断：使用 clarification 节点生成的动态选项
            tag = "clarification"
            options = content.get("options", [])
            question = content.get("question", "")
            display_content = question
        else:
            # 计划确认中断：保持原有的硬编码选项
            tag = "waiting_for_feedback"
            options = [
                {"text": "编辑计划", "value": "edit_plan"},
                {"text": "开始研究", "value": "accepted"},
            ]
            display_content = content if isinstance(content, str) else str(content)
        
        return _make_event(
            "interrupt",
            {
                "thread_id": thread_id,
                "id": interrupt_id,
                "role": "assistant",
                "content": display_content,
                "finish_reason": "interrupt",
                "tag": tag,
                "options": options,
            },
        )
    except Exception as e:
        logger.error(f"Error creating interrupt event: {e}, interrupt object type: {type(event_data.get('__interrupt__', [None])[0])}, available attributes: {dir(event_data.get('__interrupt__', [None])[0]) if event_data.get('__interrupt__') else 'N/A'}")
        # 返回一个基本的中断事件作为后备
        return _make_event(
            "interrupt",
            {
                "thread_id": thread_id,
                "id": str(uuid4()),
                "role": "assistant",
                "content": "Plan ready for review",
                "finish_reason": "interrupt",
                "tag": "waiting_for_feedback",  # Add tag for interrupt events
                "options": [
                    {"text": "编辑计划", "value": "edit_plan"},
                    {"text": "开始研究", "value": "accepted"},
                ],
            },
        )


def _process_initial_messages(message, thread_id):
    """Process initial messages and yield formatted events."""
    json_data = json.dumps(
        {
            "thread_id": thread_id,
            "id": "run--" + message.get("id", uuid4().hex),
            "role": "user",
            "content": message.get("content", ""),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    chat_stream_message(
        thread_id, f"event: message_chunk\ndata: {json_data}\n\n", "none"
    )


async def _process_message_chunk(message_chunk, message_metadata, thread_id, agent,
                                                 step_index: int = -1, step_title: str = ""):
    """Process a single message chunk and yield appropriate events."""
    agent_name = _get_agent_name(agent, message_metadata)
    
    # 检测是否为节点跳转事件消息
    if (hasattr(message_chunk, 'name') and message_chunk.name == "node_transition_event" and 
        hasattr(message_chunk, 'additional_kwargs') and 'node_transition' in message_chunk.additional_kwargs):
        
        node_transition = message_chunk.additional_kwargs['node_transition']
        logger.info(f"[节点跳转] 从消息中检测到跳转事件: {node_transition}")
        
        event_payload = {
            "thread_id": thread_id,
            "from": node_transition.get("from"),
            "to": node_transition.get("to"),
            "iteration": node_transition.get("iteration"),
            "reason": node_transition.get("reason", ""),
        }
        logger.info(f"[SSE调试] 即将发送 node_transition 事件，payload: {event_payload}")
        sse_event = _make_event("node_transition", event_payload)
        logger.info(f"[SSE调试] 生成的 SSE 事件内容: {sse_event[:200]}...")
        yield sse_event
        return  # 不再处理这条消息
    
    event_stream_message = _create_event_stream_message(
        message_chunk, message_metadata, thread_id, agent_name
    )

    # 附加当前 plan step 信息（供前端逐步展示）
    # step_index/step_title 由 _stream_graph_events 从 updates 事件推导，per-request 隔离
    # 兼容 subgraph 场景：agent_name 可能是 "ResearchTeam" 或 "researcher"
    langgraph_node = message_metadata.get("langgraph_node", "") if isinstance(message_metadata, dict) else ""
    is_researcher = agent_name == "researcher" or langgraph_node == "researcher"
    if is_researcher and step_index >= 0:
        event_stream_message["step_index"] = step_index
        event_stream_message["step_title"] = step_title
        logger.debug(f"[STEP_TRACK] msg chunk | agent={agent_name} | node={langgraph_node} | step_index={step_index} | step_title={step_title}")

    if isinstance(message_chunk, ToolMessage):
        # Tool Message - Return the result of the tool call
        event_stream_message["tool_call_id"] = message_chunk.tool_call_id
        
        # Check if this is a web_search tool completing and emit search_status completed event
        if message_chunk.tool_call_id in _active_search_calls:
            search_info = _active_search_calls.pop(message_chunk.tool_call_id)
            search_event = {
                "thread_id": thread_id,
                "agent": agent_name,
                "id": message_chunk.id,
                "role": "assistant",
                "query": search_info.get("query", ""),
                "repository": search_info.get("repository"),
                "status": "completed",
            }
            yield _make_event("search_status", search_event)
        
        yield _make_event("tool_call_result", event_stream_message)
    elif isinstance(message_chunk, (AIMessageChunk, AIMessage)):
        # AI Message - Raw message tokens (support both AIMessageChunk and AIMessage)
        if hasattr(message_chunk, 'tool_calls') and message_chunk.tool_calls:
            # AI Message - Tool Call
            event_stream_message["tool_calls"] = message_chunk.tool_calls
            # ⚠️ 注意：这里的 guwp-token 用于前端展示，不影响后端工具调用
            # 后端工具通过 state["guwp_token"] 获取 token
            event_stream_message["tool_call_chunks"] = _process_tool_call_chunks(
                message_chunk.tool_call_chunks,
                extra_headers={"guwp-token": ""},  # 前端不需要看到真实 token
            )
            
            # Set tag based on tool name
            # Default to searching, but check for specific tool types
            tag = "searching"  # default for online_search
            for tool_call in message_chunk.tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name == "crawl_tool":
                    tag = "crawling"
                    break
                elif tool_name == "online_search" or tool_name == "web_search":
                    tag = "searching"
            event_stream_message["tag"] = tag
            
            # Check if this is an online_search, bocomsearch or web_search tool call and emit search_status event
            for tool_call in message_chunk.tool_calls:
                if tool_call.get("name") in ["web_search", "online_search", "bocomsearch"]:
                    # Extract query and repository from tool call args
                    args = tool_call.get("args", {})
                    query = args.get("query", "")
                    repository = args.get("repository", "")
                    
                    # Track this search call
                    tool_call_id = tool_call.get("id", "")
                    if tool_call_id:
                        _active_search_calls[tool_call_id] = {
                            "query": query,
                            "repository": repository or tool_call.get("name", ""),
                        }
                    
                    # Emit search started event
                    search_event = {
                        "thread_id": thread_id,
                        "agent": agent_name,
                        "id": message_chunk.id,
                        "role": "assistant",
                        "query": query,
                        "repository": repository or tool_call.get("name", ""),
                        "status": "started",
                    }
                    yield _make_event("search_status", search_event)
            
            yield _make_event("tool_calls", event_stream_message)
        elif hasattr(message_chunk, 'tool_call_chunks') and message_chunk.tool_call_chunks:
            # AI Message - Tool Call Chunks
            # ⚠️ 注意：这里的 guwp-token 用于前端展示，不影响后端工具调用
            # 后端工具通过 state["guwp_token"] 获取 token
            event_stream_message["tool_call_chunks"] = _process_tool_call_chunks(
                message_chunk.tool_call_chunks,
                extra_headers={"guwp-token": ""},  # 前端不需要看到真实 token
            )
            
            # Check tool_call_chunk name and set tag accordingly
            for chunk in message_chunk.tool_call_chunks:
                chunk_name = None
                # Support both object attribute and dict format
                if isinstance(chunk, dict):
                    chunk_name = chunk.get("name", "")
                elif hasattr(chunk, "name"):
                    chunk_name = getattr(chunk, "name", "")
                
                if chunk_name == "web_search":
                    event_stream_message["tag"] = "searching"
                    break
                elif chunk_name == "crawl_tool":
                    event_stream_message["tag"] = "crawling"
                    break
            
            yield _make_event("tool_call_chunks", event_stream_message)
        else:
            # AI Message - Raw message tokens
            yield _make_event("message_chunk", event_stream_message)


async def _stream_graph_events(
    graph_instance, workflow_input, workflow_config, thread_id
):
    """Stream events from the graph and process them.

    内置心跳机制：当 LangGraph 工作流长时间无输出时（如 LLM 推理、搜索等待），
    自动发送 SSE ping 事件保持连接活跃，防止中间代理（nginx 等）因超时断开连接。
    """
    event_count = 0
    last_event_time = time.time()

    # 心跳间隔（秒）：每 30 秒发送一次 ping，远小于 nginx proxy_read_timeout
    HEARTBEAT_INTERVAL = 30

    # 追踪当前 plan step 信息
    _step_index = -1
    _step_title = ""
    _cached_plan_steps = None

    try:
        # 使用显式异步迭代 + 超时心跳机制
        stream_iterator = graph_instance.astream(
            workflow_input,
            config=workflow_config,
            stream_mode=["messages", "updates"],
            subgraphs=True,
        ).__aiter__()

        while True:
            try:
                agent, _, event_data = await asyncio.wait_for(
                    stream_iterator.__anext__(),
                    timeout=HEARTBEAT_INTERVAL
                )
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                # 超时未收到事件，发送心跳 ping 保持连接
                ping_event = _make_event("ping", {
                    "thread_id": thread_id,
                    "timestamp": time.time(),
                })
                logger.debug(f"[HEARTBEAT] thread_id={thread_id} | 发送 ping 心跳")
                yield ping_event
                continue

            event_count += 1
            current_time = time.time()
            last_event_time = current_time

            if isinstance(event_data, dict):

                # 1) 中断事件优先处理
                if "__interrupt__" in event_data:
                    yield _create_interrupt_event(thread_id, event_data)
                    continue

                # 2) 处理迭代研究节点跳转事件（不通过 update.messages，而是独立事件）
                node_transition = event_data.get("node_transition")
                if node_transition:
                    # 这里 node_transition 由 iterative_research_node 写入
                    iteration = node_transition.get("iteration")
                    from_node = node_transition.get("from")
                    to_node = node_transition.get("to")
                    reason = node_transition.get("reason", "")

                    event_payload = {
                        "thread_id": thread_id,
                        "from": from_node,
                        "to": to_node,
                        "iteration": iteration,
                        "reason": reason,
                    }
                    logger.info(f"[STREAM_EVENT] thread_id={thread_id} | 事件类型: node_transition |  payload: {event_payload}")
                    sse_event = _make_event("node_transition", event_payload)
                    yield sse_event

                # 3) 从 updates 事件中提取 plan step 信息
                # 上一个节点执行完 → State 已更新 → 当前 step 自然确定
                # LangGraph updates 事件结构: {nodeName: {field: value, ...}}
                for _node_name, _node_update in event_data.items():
                    if not isinstance(_node_update, dict):
                        continue
                    if "next_step_index" in _node_update:
                        # 优先使用下一步信息（utils.py 已算好，无需 SSE 层推导）
                        _next_idx = _node_update["next_step_index"]
                        if _next_idx is not None and _next_idx >= 0:
                            _step_index = _next_idx
                            _step_title = _node_update.get("next_step_title", "")
                            logger.info(f"[STEP_TRACK] thread_id={thread_id} | next_step: index={_step_index} | title={_step_title}")
                    elif "current_step_index" in _node_update:
                        # Fallback: 如果没有 next_step_index，从 current_step_index 推算
                        # current_step_index 是刚完成的步骤索引，下一步需要 +1
                        _step_index = _node_update["current_step_index"] + 1
                        _step_title = ""  # 清空，下面从 plan 中取
                        logger.info(f"[STEP_TRACK] thread_id={thread_id} | fallback: current_step_index={_node_update['current_step_index']} | _step_index={_step_index}")
                
                    # 4) 从 current_plan 中补充 step_title
                    #    - plan 刚创建时：step_index < 0，取第一步
                    #    - step 完成后：step_index 已更新，取对应步骤的标题
                    if "current_plan" in _node_update:
                        plan_obj = _node_update["current_plan"]
                        steps = None
                        if hasattr(plan_obj, 'steps'):
                            steps = plan_obj.steps
                        elif isinstance(plan_obj, dict) and 'steps' in plan_obj:
                            steps = plan_obj['steps']
                        if steps:
                            _cached_plan_steps = steps  # 缓存用于 fallback
                            if _step_index < 0:
                                # plan 刚创建，从第一步开始
                                _step_index = 0
                            # 从 plan 中取当前 step_index 对应的标题
                            if _step_index < len(steps) and not _step_title:
                                target_step = steps[_step_index]
                                _step_title = getattr(target_step, 'title', None) or (target_step.get('title', '') if isinstance(target_step, dict) else '')
                    break  # 只处理第一个节点更新

                # 其他 update 目前不需要转成事件，直接忽略
                continue

            message_chunk, message_metadata = cast(
                tuple[BaseMessage, dict[str, Any]], event_data
            )

            # 记录接收到消息块
            agent_name = _get_agent_name(agent, message_metadata)
            # 仅在 agent_name 不常见时记录（调试 subgraph 场景），避免每条 chunk 都打日志
            if agent_name not in ("researcher", "reporter", "planner", "unknown") and agent and len(agent) > 1:
                logger.info(f"[STEP_TRACK] thread_id={thread_id} | agent_tuple={agent} | agent_name={agent_name} | _step_index={_step_index}")

            # Fallback: 如果 researcher 消息到达但 _step_index 未更新（updates 时序竞争），
            # 从缓存的 plan steps 和 State 中的 current_step_index 推算
            _msg_node = message_metadata.get("langgraph_node", "") if isinstance(message_metadata, dict) else ""
            _is_researcher = agent_name == "researcher" or _msg_node == "researcher"
            if _is_researcher and _step_index < 0 and _cached_plan_steps:
                _step_index = 0
                if not _step_title and len(_cached_plan_steps) > 0:
                    first_step = _cached_plan_steps[0]
                    _step_title = getattr(first_step, 'title', None) or (first_step.get('title', '') if isinstance(first_step, dict) else '')
                logger.info(f"[STEP_TRACK] thread_id={thread_id} | fallback: _step_index={_step_index} | _step_title={_step_title}")

            async for event in _process_message_chunk(
                message_chunk, message_metadata, thread_id, agent,
                step_index=_step_index, step_title=_step_title
            ):
                yield event

    except Exception as e:
        logger.exception(f"[STREAM_ERROR] thread_id={thread_id} | 图执行出错 | 已处理事件数: {event_count}")
        # 错误分类：给前端友好文案，同时在聊天区追加一条系统消息
        error_type, user_message = _classify_stream_error(e)
        import uuid as _uuid
        error_msg_id = f"error-{_uuid.uuid4().hex[:12]}"
        # 1) 向聊天区追加一条 coordinator 消息（用户能直接看到原因）
        yield _make_event(
            "message_chunk",
            {
                "thread_id": thread_id,
                "agent": "coordinator",
                "id": error_msg_id,
                "role": "assistant",
                "content": user_message,
                "finish_reason": "stop",
            },
        )
        # 2) 再发一个 error 事件（带分类）供前端弹 toast
        yield _make_event(
            "error",
            {
                "thread_id": thread_id,
                "error": user_message,
                "error_type": error_type,
                "raw": str(e)[:500],  # 原始异常文本，方便排查（截断）
            },
        )
    finally:
        total_duration = time.time() - last_event_time




async def _astream_workflow_generator(
    messages: List[dict],  # 对话消息列表（OpenAI格式），会被转交到 LangGraph 工作流
    thread_id: str,  # 会话/线程ID，用于在前后端关联同一轮流式事件
    resources: List[Resource],  # 研究可用的外部资源（如链接、上下文等）
    max_plan_iterations: int,  # 规划节点的最大迭代次数
    max_step_num: int,  # 单个研究计划中允许的最大步骤数
    max_search_results: int,  # 每次搜索的最大返回条数
    max_iteration: int,  # 迭代研究节点的最大迭代轮数
    search_engine: str,  # 选用的搜索引擎（custom_search/tavily/...）
    auto_accepted_plan: bool,  # 是否自动接受规划（否则会发起中断等待用户确认）
    interrupt_feedback: str,  # 用户对规划的中断反馈（用于恢复时合并到输入）
    mcp_settings: dict,  # MCP 工具的动态配置（服务、工具、环境变量等）
    enable_background_investigation: bool,  # 是否在规划前先做背景调研
    report_style: ReportStyle,  # 报告风格（学术/科普/新闻等）
    enable_deep_thinking: bool,  # 是否启用“深度思考”（切换到 reasoning 模型等）
    system_context: str = "",  # 系统背景上下文
    force_routing_path: str = None,  # 🐛 调试模式：强制路由路径
    guwp_token: Optional[str] = None,
    use_budget_controlled_online_search: bool = True,  # 是否使用预算控制的在线搜索
    use_budget_controlled_bocom_search: bool = True,  # 是否使用预算控制的交行搜索
    cancel_event: asyncio.Event = None,  # 客户端断连取消信号
):
    # Process initial messages
    for message in messages:
        if isinstance(message, dict) and "content" in message:
            _process_initial_messages(message, thread_id)

    # ⚠️ 不再设置全局环境变量（避免多用户并发冲突）
    # 改为通过 workflow_input["guwp_token"] 传递到 state，确保线程安全

    # Prepare workflow input
    workflow_input = {
        "messages": messages,
        "plan_iterations": 0,
        "final_report": "",
        "current_plan": None,
        "observations": [],
        "auto_accepted_plan": auto_accepted_plan,
        "enable_background_investigation": enable_background_investigation,
        "research_topic": messages[-1]["content"] if messages else "",
        "system_context": system_context,  # 将系统背景传递给工作流
        "force_routing_path": force_routing_path,  # 🐛 调试模式
        # 确保迭代研究的状态字段被正确初始化
        "iteration_count": 0,
        "iteration_history": [],
        "report_style": report_style.value,  # 将报告风格传递到 state，用于 researcher_node 动态选择工具
        "guwp_token": guwp_token,  # ✅ 通过 state 传递 token，确保线程安全
    }
    if not auto_accepted_plan and interrupt_feedback:
        resume_msg = f"[{interrupt_feedback}]"
        if messages:
            resume_msg += f" {messages[-1]['content']}"
        workflow_input = Command(resume=resume_msg)

    # Prepare workflow config
    workflow_config = {
        "thread_id": thread_id,
        "configurable": {
            "resources": resources,
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "max_search_results": max_search_results,
            "max_iteration": max_iteration,
            "search_engine": search_engine,
            "mcp_settings": mcp_settings,
            "report_style": report_style.value,
            "enable_deep_thinking": enable_deep_thinking,
            "system_context": system_context,  # 将系统背景传递到配置中
            "use_budget_controlled_online_search": use_budget_controlled_online_search,
            "use_budget_controlled_bocom_search": use_budget_controlled_bocom_search,
            "cancel_event": cancel_event,  # 客户端断连取消信号，reporter 节点检测
        },
        "recursion_limit": get_recursion_limit(),
    }

    checkpoint_saver = get_bool_env("LANGGRAPH_CHECKPOINT_SAVER", False)
    checkpoint_url = get_str_env("LANGGRAPH_CHECKPOINT_DB_URL", "")
    # 注：新版 langgraph-checkpoint-postgres 的 from_conn_string() 不再接受
    # psycopg 级别的 kwargs（如 autocommit / row_factory / prepare_threshold），
    # 内部已自动启用 autocommit=True。如需自定义连接参数，
    # 请改用 AsyncConnectionPool + AsyncPostgresSaver(pool)。
    if checkpoint_saver and checkpoint_url != "":
        if checkpoint_url.startswith("postgresql://"):
            logger.info("start async postgres checkpointer.")
            async with AsyncPostgresSaver.from_conn_string(
                checkpoint_url
            ) as checkpointer:
                await checkpointer.setup()
                graph.checkpointer = checkpointer
                graph.store = in_memory_store
                async for event in _stream_graph_events(
                    graph, workflow_input, workflow_config, thread_id
                ):
                    yield event
        else:
            logger.warning(f"Unsupported checkpoint URL scheme: {checkpoint_url}. Only postgresql:// is supported.")
            async for event in _stream_graph_events(
                graph, workflow_input, workflow_config, thread_id
            ):
                yield event
    else:
        # Use graph without checkpointer
        async for event in _stream_graph_events(
            graph, workflow_input, workflow_config, thread_id
        ):
            yield event


def _classify_stream_error(exc: Exception) -> tuple[str, str]:
    """将流式图执行错误分类并给出前端友好文案。

    Returns:
        (error_type, user_message)
        - error_type: 错误分类标识（前端可据此分支展示 UI）
        - user_message: 面向用户的友好文案（将作为 coordinator 消息在聊天区显示）
    """
    text = (str(exc) or "").lower()
    exc_name = type(exc).__name__
    # 1) LLM 网络/鉴权问题（ELLM / DeepSeek / OpenAI 等大模型服务不通）
    llm_markers = (
        "ellm apikeymanager",
        "no api key available",
        "name resolution",
        "temporary failure in name resolution",
        "connection refused",
        "connect call failed",
        "read timed out",
        "connecttimeout",
        "connecterror",
    )
    if any(m in text for m in llm_markers) or exc_name in (
        "ConnectError", "ConnectTimeout", "ReadTimeout",
    ):
        return (
            "llm_unavailable",
            "⚠️ 大模型服务暂时不可用（连接失败或鉴权异常），请稍后重试。如持续出现请联系管理员。",
        )
    # 2) 模型返回体解析出错
    if "json" in text and ("parse" in text or "decode" in text):
        return (
            "llm_output_invalid",
            "⚠️ 大模型返回的内容无法解析，已中断本次研究。请重试；若问题较复杂可尝试简化提问。",
        )
    # 3) 推理/调用超时
    if "timeout" in text or exc_name == "TimeoutError":
        return (
            "timeout",
            "⚠️ 本次研究执行超时，可能是模型或搜索响应较慢，请重试。",
        )
    # 4) 其他未知错误
    return (
        "unknown",
        f"⚠️ 本次研究执行失败：{str(exc)[:200]}",
    )


def _make_event(event_type: str, data: Dict[str, Any]):
    if data.get("content") == "":
        data.pop("content")
    # Ensure JSON serialization with proper encoding
    try:
        json_data = json.dumps(data, ensure_ascii=False)

        finish_reason = data.get("finish_reason", "")

        # 添加详细日志：记录每个 SSE 事件的发送
        thread_id = data.get("thread_id", "unknown")
        event_preview = f"{event_type}"
        if event_type == "message_chunk":
            agent = data.get("agent", "unknown")
            content_len = len(data.get("content", ""))
            event_preview = f"message_chunk(agent={agent}, content_len={content_len})"
        elif event_type == "tool_calls":
            agent = data.get("agent", "unknown")
            tool_count = len(data.get("tool_calls", []))
            event_preview = f"tool_calls(agent={agent}, count={tool_count})"
        elif event_type == "tool_call_result":
            agent = data.get("agent", "unknown")
            event_preview = f"tool_call_result(agent={agent})"

        chat_stream_message(
            thread_id,
            f"event: {event_type}\ndata: {json_data}\n\n",
            finish_reason,
        )

        # 在发送后立即记录日志
        logger.debug(f"[SSE_SEND] thread_id={thread_id} | event={event_preview} | data_size={len(json_data)}")

        return f"event: {event_type}\ndata: {json_data}\n\n"
    except (TypeError, ValueError) as e:
        logger.error(f"Error serializing event data: {e}")
        # Return a safe error event
        error_data = json.dumps({"error": "Serialization failed"}, ensure_ascii=False)
        return f"event: error\ndata: {error_data}\n\n"




# ============================================================
# Markdown 转 Word 代理接口
# ============================================================

EASYPARSE_SERVICE_URL = os.getenv("EASYPARSE_SERVICE_URL", "http://nginx")


@app.post("/api/markdown/to_word")
async def markdown_to_word(request: MarkdownToWordRequest):
    """
    将 Markdown 内容转换为 Word 文档

    调用 easyparse 服务进行转换，通过 nginx 负载均衡分发到 easyparse 实例。
    调用链: 后端 → nginx(/markdown_to_word) → easyparse 集群
    EASYPARSE_SERVICE_URL 默认 http://nginx，拼接后请求 nginx 的负载均衡路由。
    """
    easyparse_url = f"{EASYPARSE_SERVICE_URL}/markdown_to_word"

    # 将 markdown 内容写入临时文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(request.content)
        tmp_path = tmp.name

    try:
        # 内网服务间调用，必须显式禁用代理：
        # 1) trust_env=False 让 httpx 忽略环境变量 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY 等
        # 2) proxy=None 双保险，避免任何隐式代理注入
        # 否则内网调用 http://nginx 会被容器 env 里的 SOCKS/HTTP 代理劫持，
        # 触发 socksio.exceptions.ProtocolError: Malformed reply
        async with httpx.AsyncClient(
            timeout=60.0,
            trust_env=False,
            proxy=None,
        ) as client:
            with open(tmp_path, "rb") as f:
                response = await client.post(
                    easyparse_url,
                    files={"file": ("report.md", f, "text/markdown")},
                )

        if response.status_code != 200:
            logger.error(f"easyparse 转换失败: status={response.status_code}")
            raise HTTPException(
                status_code=502,
                detail=f"Markdown 转 Word 失败: easyparse 返回 {response.status_code}",
            )

        filename = request.filename or "research-report"

        return Response(
            content=response.content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.docx"',
            },
        )
    except httpx.ConnectError:
        logger.error(f"无法连接 easyparse 服务: {EASYPARSE_SERVICE_URL}")
        raise HTTPException(
            status_code=503,
            detail=f"无法连接 easyparse 服务({EASYPARSE_SERVICE_URL})，请确认服务已启动",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Markdown 转 Word 异常: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.post("/api/ppt/generate")
async def generate_ppt(request: GeneratePPTRequest):
    try:
        report_content = request.content
        print(report_content)
        workflow = build_ppt_graph()
        # 创建正确的 PPTState 输入
        from src.ppt.graph.state import PPTState
        ppt_input: PPTState = {
            "messages": [],  # MessagesState 需要 messages 字段
            "input": report_content,
            "generated_file_path": "",
            "ppt_content": "",
            "ppt_file_path": ""
        }
        final_state = workflow.invoke(ppt_input)
        generated_file_path = final_state["generated_file_path"]
        with open(generated_file_path, "rb") as f:
            ppt_bytes = f.read()
        return Response(
            content=ppt_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
    except Exception as e:
        logger.exception(f"Error occurred during ppt generation: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)



@app.post("/api/prompt/enhance")
async def enhance_prompt(request: EnhancePromptRequest):
    try:
        sanitized_prompt = request.prompt.replace("\r\n", "").replace("\n", "")
        logger.info(f"Enhancing prompt: {sanitized_prompt}")

        # Convert string report_style to ReportStyle enum
        report_style = None
        if request.report_style:
            try:
                # Handle both uppercase and lowercase input
                style_mapping = {
                    "ACADEMIC": ReportStyle.ACADEMIC,
                    "POPULAR_SCIENCE": ReportStyle.POPULAR_SCIENCE,
                    "NEWS": ReportStyle.NEWS,
                    "SOCIAL_MEDIA": ReportStyle.SOCIAL_MEDIA,
                    "BUSINESS_MARKETING": ReportStyle.BUSINESS_MARKETING,
                    "BUSINESS_MARKETING_CLIENT": ReportStyle.BUSINESS_MARKETING_CLIENT,
                }
                report_style = style_mapping.get(
                    request.report_style.upper(), ReportStyle.ACADEMIC
                )
            except Exception:
                # If invalid style, default to ACADEMIC
                report_style = ReportStyle.ACADEMIC
        else:
            report_style = ReportStyle.ACADEMIC

        workflow = build_prompt_enhancer_graph()
        # 创建符合 PromptEnhancerState 类型的输入
        prompt_enhancer_input: PromptEnhancerState = {
            "prompt": request.prompt,
            "context": request.context,
            "report_style": report_style,
            "output": None,  # 初始化输出字段
        }
        final_state = workflow.invoke(prompt_enhancer_input)
        return {"result": final_state["output"]}
    except Exception as e:
        logger.exception(f"Error occurred during prompt enhancement: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/mcp/server/metadata", response_model=MCPServerMetadataResponse)
async def mcp_server_metadata(request: MCPServerMetadataRequest):
    """Get information about an MCP server."""
    # Check if MCP server configuration is enabled
    if not get_bool_env("ENABLE_MCP_SERVER_CONFIGURATION", False):
        raise HTTPException(
            status_code=403,
            detail="MCP server configuration is disabled. Set ENABLE_MCP_SERVER_CONFIGURATION=true to enable MCP features.",
        )

    try:
        # Set default timeout with a longer value for this endpoint
        timeout = 300  # Default to 300 seconds for this endpoint

        # Use custom timeout from request if provided
        if request.timeout_seconds is not None:
            timeout = request.timeout_seconds

        # Load tools from the MCP server using the utility function
        tools = await load_mcp_tools(
            server_type=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            headers=request.headers,
            timeout_seconds=timeout,
        )

        # Create the response with tools
        response = MCPServerMetadataResponse(
            transport=request.transport,
            command=request.command,
            args=request.args,
            url=request.url,
            env=request.env,
            headers=request.headers,
            tools=tools,
        )

        return response
    except Exception as e:
        logger.exception(f"Error in MCP server metadata endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.get("/api/rag/config", response_model=RAGConfigResponse)
async def rag_config():
    """Get the config of the RAG."""
    return RAGConfigResponse(provider=SELECTED_RAG_PROVIDER)


@app.get("/api/rag/resources", response_model=RAGResourcesResponse)
async def rag_resources(request: Annotated[RAGResourceRequest, Query()]):
    """Get the resources of the RAG."""
    retriever = build_retriever()
    if retriever:
        return RAGResourcesResponse(resources=retriever.list_resources(request.query))
    return RAGResourcesResponse(resources=[])


@app.get("/api/config", response_model=ConfigResponse)
async def config():
    """Get the config of the server."""
    return ConfigResponse(
        rag=RAGConfigResponse(provider=SELECTED_RAG_PROVIDER),
        models=get_configured_llm_models(),
    )


def get_node_id() -> str:
    # 容器 ID 通常存储在 /proc/self/cgroup 或环境变量中
    # 方案 1：从环境变量获取（推荐，需启动时注入）
    node_id = os.getenv("NODE_ID")
    if node_id:
        return node_id
    
    # 方案 2：从 /proc/self/cgroup 解析（适用于未注入环境变量的场景）
    try:
        with open("/proc/self/cgroup", "r") as f:
            for line in f:
                if "docker" in line:
                    # 提取容器 ID（通常是最后一段的前 12 位）
                    container_id = line.strip().split("/")[-1].split(".")[0][:12]
                    return f"docker-{container_id}"
    except Exception:
        pass
    
    #  fallback：生成临时 ID（不推荐，可能重复）
    return f"temp-{uuid.uuid4().hex[:8]}"

# 生成对话 ID 时传入 node_id
def generate_conversation_id(
    model_prefix: str = "chatcmpl",
    node_id: Optional[str] = None
) -> str:
    """
    生成符合大模型服务端标准的唯一对话ID
    
    参数:
        model_prefix: 模型类型前缀（如"chatcmpl"表示聊天补全，"imgcmpl"表示图像生成）
        node_id: 服务节点标识（分布式部署时用于区分不同服务节点）
    
    返回:
        全局唯一的对话ID字符串
    """
    # 1. 时间戳部分：使用人类可读的日期时间格式，确保时序唯一性
    from datetime import datetime
    now: datetime = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H %M")  # 格式：2003-mm-dd hh mm
    
    # 2. 随机部分：基于UUIDv4，确保同一时间戳内的唯一性（122位二进制≈30位十六进制）
    # 取前16位十六进制字符（64位），平衡唯一性和长度
    random_str = uuid.uuid4().hex[:16]
    
    # 3. 可选的服务节点标识（分布式部署时使用）
    node_id=get_node_id()
    node_suffix = f"-{node_id}" if node_id else ""
    
    # 组合生成最终ID
    return f"{model_prefix}-{timestamp_str}-{random_str}{node_suffix}"

# 该接口功能被更强大的 /api/research/simple/stream 替代

@app.post("/api/research/simple/stream")
async def simple_research_stream(request: SimpleResearchRequest):
    """
    简化流式研究接口：使用完整的 LangGraph 工作流，返回原生SSE格式
    
    - 移除双模式选择，统一使用 LangGraph 工作流
    - 支持与 /api/chat/stream 一致的完整功能
    - 保持所有参数可定制
    - 提供 SSE 实时事件流
    """
    # 生成唯一的对话 ID
    conversation_id = generate_conversation_id(model_prefix="deep-research")
    
    # 确保 thread_id 不为 None
    thread_id = request.thread_id
    if thread_id is None or thread_id == "__default__":
        thread_id = conversation_id
    
    enhanced_logger.set_session_context(
        session_id=conversation_id,
        user_query=request.messages[-1].get("content", "") if request.messages else ""
    )
    
    enhanced_logger.log_node_entry("simple_research_stream", {
        "conversation_id": conversation_id,
        "thread_id": thread_id,
        "messages_count": len(request.messages) if request.messages else 0,
        "max_search_results": request.max_search_results,
        "search_engine": request.search_engine,
        "enable_deep_thinking": request.enable_deep_thinking
    })
    
    # 使用完整的 LangGraph 工作流（原生 SSE 格式）
    return StreamingResponse(
        _full_workflow_sse_generator(
            request=request,
            thread_id=thread_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.post("/api/research/simple/stream/openai")
async def simple_research_stream_openai(request: SimpleResearchRequest):
    """
    OpenAI格式的简化流式研究接口

    - 返回OpenAI兼容的SSE流式响应
    - 包含id、object、created、model、choices等OpenAI标准字段
    - 保持与/api/research/simple/stream相同的功能
    - 为需要OpenAI格式的客户端提供兼容性
    - 🐛 支持调试模式：使用 force_routing_path 参数测试迭代研究等功能
      可选值：direct_answer, simple_search, iterative_research, deep_research
    """
    # 生成唯一的对话 ID
    conversation_id = generate_conversation_id(model_prefix="deep-research-openai-stream")
    
    # 确保 thread_id 不为 None
    thread_id = request.thread_id
    if thread_id is None or thread_id == "__default__":
        thread_id = conversation_id
    
    enhanced_logger.set_session_context(
        session_id=conversation_id,
        user_query=request.messages[-1].get("content", "") if request.messages else ""
    )
    
    enhanced_logger.log_node_entry("simple_research_stream_openai", {
        "conversation_id": conversation_id,
        "thread_id": thread_id,
        "messages_count": len(request.messages) if request.messages else 0,
        "max_search_results": request.max_search_results,
        "search_engine": request.search_engine,
        "enable_deep_thinking": request.enable_deep_thinking,
        "format": "openai_compatible",
        "force_routing_path": request.force_routing_path  # 🐛 调试模式：记录强制路由路径
    })

    # 记录是否启用强制路由
    if request.force_routing_path:
        enhanced_logger.logger.info(f"🔀 OPENAI_FORCE_ROUTING | conversation_id: {conversation_id} | 路由到: {request.force_routing_path}")
    
    # 使用完整的 LangGraph 工作流（OpenAI 兼容格式）
    return StreamingResponse(
        _full_workflow_openai_generator(
            request=request,
            thread_id=thread_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


async def _full_workflow_sse_generator(
    request: SimpleResearchRequest,
    thread_id: str
):
    """
    完整工作流SSE生成器：使用完整的 LangGraph 工作流，返回原生SSE格式事件流
    
    功能说明：
    - 支持智能路由（direct_answer/simple_search/deep_research）
    - 返回原生 SSE 格式事件（event: message_chunk\ndata: {...}\n\n）
    - 与 /api/chat/stream 保持一致
    将 SimpleResearchRequest 参数转换并调用现有的 _astream_workflow_generator
    """
    enhanced_logger.log_step_execution(
        step_number=1,
        step_title="🚀 智能研究工作流启动",
        step_type="workflow_initialization",
        agent_name="workflow_orchestrator"  # 工作流协调器（非真实Agent，仅用于日志标记）
    )
    
    try:
        # 转换消息格式
        messages = []
        for msg in request.messages:
            if isinstance(msg, dict):
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            else:
                messages.append(msg)
        
        enhanced_logger.logger.info(f"🔄 SIMPLE_RESEARCH_START | {thread_id} | 消息数量: {len(messages)}")

        # 记录是否启用强制路由
        if request.force_routing_path:
            enhanced_logger.logger.info(f"🔀 FORCE_ROUTING_ENABLED | 路由到: {request.force_routing_path}")

        # 直接调用 _astream_workflow_generator
        async for event in _astream_workflow_generator(
            messages=messages,
            thread_id=thread_id,
            resources=request.resources or [],
            max_plan_iterations=request.max_plan_iterations or 2,
            max_step_num=request.max_step_num or 5,
            max_search_results=request.max_search_results or 1,
            max_iteration=request.max_iteration or 5,
            search_engine=request.search_engine or "custom_search",
            auto_accepted_plan=request.auto_accepted_plan if request.auto_accepted_plan is not None else True,
            interrupt_feedback=request.interrupt_feedback or "",
            mcp_settings=request.mcp_settings or {},
            enable_background_investigation=request.enable_background_investigation or True,
            report_style=request.report_style or ReportStyle.ACADEMIC,
            enable_deep_thinking=request.enable_deep_thinking or False,
            system_context=get_str_env("SYSTEM_CONTEXT", ""),  # 从环境变量读取
            force_routing_path=request.force_routing_path,  # 🐛 调试模式：支持测试迭代研究
        ):
            yield event
            
        enhanced_logger.log_step_execution(
            step_number=2,
            step_title="✅ 智能研究工作流完成",
            step_type="workflow_completion",
            agent_name="workflow_orchestrator"  # 工作流协调器（非真实Agent，仅用于日志标记）
        )
        
    except Exception as e:
        enhanced_logger.logger.error(f"❌ SIMPLE_RESEARCH_ERROR | {thread_id} | 工作流失败: {str(e)}")
        yield _make_stream_event("error", {
            "error": f"简化研究流程失败: {str(e)}",
            "thread_id": thread_id
        })


async def _full_workflow_openai_generator(
    request: SimpleResearchRequest,
    thread_id: str
):
    """
    完整工作流OpenAI生成器：使用完整的 LangGraph 工作流，返回OpenAI兼容格式
    
    功能说明：
    - 支持智能路由（direct_answer/simple_search/deep_research）
    - 返回 OpenAI chat.completion.chunk 格式（data: {...}\n\n）
    - 自动过滤 <think>...</think> 标签内的思考内容
    - 返回所有输出节点的信息（reporter/coordinator/各路径节点）
    """
    import time
    import re
    
    # 初始化OpenAI格式基本信息（所有chunk共享相同的基础信息）
    base_timestamp = int(time.time())
    base_response = {
        "id": thread_id,
        "object": "chat.completion.chunk",
        "created": base_timestamp,
        "model": "deep-research-openai-stream",
        "choices": []
    }
    
    enhanced_logger.log_step_execution(
        step_number=1,
        step_title="🔄 OpenAI兼容格式转换启动",
        step_type="openai_stream_initialization",
        agent_name="OpenAI兼容格式输出"  # 格式转换器（非真实Agent，仅用于日志标记）
    )

    # 🐛 记录强制路由路径（调试模式）
    if request.force_routing_path:
        enhanced_logger.logger.info(f"🔀 OPENAI_FORCE_ROUTING | thread_id: {thread_id} | 路由到: {request.force_routing_path}")

    # 用于累积内容，以便处理跨chunk的<think>标签
    content_buffer = ""
    in_think_tag = False
    
    def filter_think_tags(text: str) -> str:
        """
        过滤<think>...</think>标签及其内部内容
        使用正则表达式删除所有思考标签块
        """
        # 使用正则表达式删除<think>...</think>标签及其内容
        # re.DOTALL 使得 . 匹配包括换行符在内的所有字符
        filtered_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        return filtered_text
    
    try:
        # 发送初始chunk（包含role信息）
        start_chunk = {
            **base_response,
            "choices": [{
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": ""
                },
                "finish_reason": None
            }]
        }
        yield _make_openai_stream_event(start_chunk)
        
        # 使用与/api/research/simple/stream完全相同的流程
        # 调用完整工作流SSE生成器，确保流程100%一致
        async for raw_event in _full_workflow_sse_generator(request, thread_id):
            # 解析SSE事件
            if raw_event.startswith("event: "):
                lines = raw_event.strip().split("\n")
                event_type = lines[0].replace("event: ", "")
                
                if len(lines) > 1 and lines[1].startswith("data: "):
                    try:
                        event_data = json.loads(lines[1].replace("data: ", ""))
                        
                        # 处理所有输出节点的消息
                        # - reporter: 深度研究报告
                        # - coordinator: 深度研究协调/追问
                        # - direct_answer_assistant: 直接回答
                        # - simple_search_assistant: 简单检索
                        # - iterative_research_node: 迭代研究节点
                        # - iterative_reporter_node: 迭代研究报告节点
                        agent = event_data.get("agent", "")
                        allowed_agents = [
                            "reporter",                    # 深度研究报告
                            "coordinator",                # 深度研究协调
                            "direct_answer_node",         # 直接回答节点
                            "simple_search_node",         # 简单检索节点
                            "iterative_research_node",    # 迭代研究节点
                            "iterative_reporter_node"     # 迭代研究报告节点
                        ]
                        if agent not in allowed_agents:
                            enhanced_logger.logger.debug(f"⚠️ FILTERED_AGENT | 过滤非输出agent: {agent}")
                            continue                        
                        enhanced_logger.logger.debug(f"✅ PROCESSING_AGENT | 处理agent: {agent} | event_type: {event_type}")
                        
                        if event_type == "message_chunk" and "content" in event_data:
                            content = event_data.get("content", "")
                            if content:
                                # 累积内容到缓冲区
                                content_buffer += content
                                
                                # 检查是否有完整的<think>...</think>标签
                                # 如果缓冲区包含完整的think标签，则过滤并发送
                                if "</think>" in content_buffer:
                                    # 过滤掉think标签
                                    filtered_content = filter_think_tags(content_buffer)
                                    
                                    # 如果过滤后有内容，则发送
                                    if filtered_content:
                                        content_chunk = {
                                            **base_response,
                                            "choices": [{
                                                "index": 0,
                                                "delta": {
                                                    "content": filtered_content
                                                },
                                                "finish_reason": event_data.get("finish_reason") if event_data.get("finish_reason") == "stop" else None
                                            }]
                                        }
                                        yield _make_openai_stream_event(content_chunk)
                                    
                                    # 清空缓冲区
                                    content_buffer = ""
                                elif "<think>" not in content_buffer:
                                    # 如果缓冲区没有think标签开始标记，说明是正常内容，直接发送
                                    content_chunk = {
                                        **base_response,
                                        "choices": [{
                                            "index": 0,
                                            "delta": {
                                                "content": content_buffer
                                            },
                                            "finish_reason": event_data.get("finish_reason") if event_data.get("finish_reason") == "stop" else None
                                        }]
                                    }
                                    yield _make_openai_stream_event(content_chunk)
                                    content_buffer = ""
                                # 否则，继续累积内容，等待完整的think标签
                        
                        elif event_type == "error":
                            # 处理错误事件（不过滤，错误信息需要返回）
                            error_msg = event_data.get("error", "发生未知错误")
                            error_chunk = {
                                **base_response,
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "content": f"\n\n**错误:** {error_msg}"
                                    },
                                    "finish_reason": "stop"
                                }]
                            }
                            yield _make_openai_stream_event(error_chunk)
                            return
                            
                    except json.JSONDecodeError:
                        enhanced_logger.logger.warning(f"无法解析事件数据: {lines[1] if len(lines) > 1 else 'No data'}")
        
        # 流结束前，处理缓冲区中剩余的内容
        if content_buffer:
            # 过滤掉可能残留的think标签
            filtered_content = filter_think_tags(content_buffer)
            if filtered_content:
                remaining_chunk = {
                    **base_response,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": filtered_content
                        },
                        "finish_reason": None
                    }]
                }
                yield _make_openai_stream_event(remaining_chunk)
        
        # 发送结束chunk，包含usage信息
        final_chunk = {
            **base_response,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }],
            "usage": {
                "completion_tokens": 0,  # 实际应该计算token数量
                "prompt_tokens": 0,     # 实际应该计算token数量
                "total_tokens": 0       # completion_tokens + prompt_tokens
            }
        }
        yield _make_openai_stream_event(final_chunk)
        
        enhanced_logger.log_step_execution(
            step_number=2,
            step_title="✅ OpenAI兼容格式转换完成",
            step_type="openai_stream_completion",
            agent_name="OpenAI兼容格式输出器"  # 格式转换器（非真实Agent，仅用于日志标记）
        )
        
    except Exception as e:
        enhanced_logger.logger.error(f"❌ OPENAI_STREAM_ERROR | {thread_id} | OpenAI格式转换失败: {str(e)}")
        error_chunk = {
            **base_response,
            "choices": [{
                "index": 0,
                "delta": {
                    "content": f"\n\n**系统错误:** 处理失败: {str(e)}"
                },
                "finish_reason": "stop"
            }]
        }
        yield _make_openai_stream_event(error_chunk)


def _make_openai_stream_event(data: Dict[str, Any]) -> str:
    """
    创建OpenAI标准的SSE流式事件
    按照OpenAI标准，每个chunk都以'data: '开头，以\n\n结尾
    """
    try:
        json_data = json.dumps(data, ensure_ascii=False)
        return f"data: {json_data}\n\n"
    except (TypeError, ValueError) as e:
        enhanced_logger.logger.error(f"OpenAI事件序列化失败: {e}")
        error_data = json.dumps({"error": "序列化失败"}, ensure_ascii=False)
        return f"data: {error_data}\n\n"


def _make_stream_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    创建SSE格式的流式事件
    """
    try:
        json_data = json.dumps(data, ensure_ascii=False)
        return f"event: {event_type}\ndata: {json_data}\n\n"
    except (TypeError, ValueError) as e:
        enhanced_logger.logger.error(f"流式事件序列化失败: {e}")
        error_data = json.dumps({"error": "序列化失败"}, ensure_ascii=False)
        return f"event: error\ndata: {error_data}\n\n"
