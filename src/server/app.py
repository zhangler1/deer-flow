# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import base64
from datetime import datetime
import asyncio
import json
import mimetypes
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
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langgraph.types import Command
from langgraph.store.memory import InMemoryStore
# from langgraph.checkpoint.mongodb import AsyncMongoDBSaver  # removed: 不再使用 MongoDB checkpoint
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from src.config.configuration import get_recursion_limit
from src.config.loader import get_bool_env, get_str_env, load_tool_compression_config, load_yaml_config
from src.config.report_style import ReportStyle
from src.config.tools import SELECTED_RAG_PROVIDER
from src.graph.builder import build_graph_with_memory
from src.llms.llm import EnhancedLLMWrapper, get_configured_llm_models, get_reporter_model_options, get_llm_by_type
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
    DocumentUploadResponse,
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
from src.utils.enhanced_logger import get_enhanced_logger, get_log_level_from_env, setup_enhanced_logging, current_thread_id
from src.server.auth_middleware import GuwpTokenAuthMiddleware
from src.server.dashboard_router import router as dashboard_router
from src.server.report_history_router import router as report_history_router

logger = logging.getLogger(__name__)

# 初始化增强日志系统，支持从环境变量LOG_FILE读取日志文件路径
log_file = os.getenv('LOG_FILE')  # 例如: logs/deer-flow.log
setup_enhanced_logging(level=get_log_level_from_env(), enable_colors=True, log_file=log_file)
enhanced_logger = get_enhanced_logger("deer-flow.api")

# 加载工具结果压缩配置
load_tool_compression_config()


# ─── 后台系统监控（每 60 秒输出一次系统资源，用于排查 OOM / 资源耗尽）───
async def _system_monitor():
    """后台系统监控，不依赖任何请求上下文"""
    while True:
        await asyncio.sleep(60)
        try:
            rss = vms = "N/A"
            with open('/proc/self/status') as _f:
                for _l in _f:
                    if _l.startswith('VmRSS:'):
                        rss = _l.strip().split()[1] + " kB"
                    elif _l.startswith('VmSize:'):
                        vms = _l.strip().split()[1] + " kB"
            enhanced_logger.logger.info(f"📊 SYS_MONITOR | RSS={rss} | VmSize={vms}")
        except OSError:
            pass

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


@app.on_event("startup")
async def _start_background_monitor():
    """启动后台系统监控任务"""
    asyncio.create_task(_system_monitor())


@app.on_event("startup")
async def _ensure_reports_table():
    """确保 reports 表存在"""
    try:
        from src.storage import report_repository
        await report_repository.ensure_table()
    except Exception as e:
        logger.warning(f"reports 表初始化失败（数据库可能未配置）: {e}")


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

# guwpToken 用户认证中间件：从 Cookie 解析 token 并注入用户信息
app.add_middleware(GuwpTokenAuthMiddleware)

# 注册数据看板 API 路由
app.include_router(dashboard_router)

# 注册用户历史报告 API 路由
app.include_router(report_history_router)

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


# 默认预估报告生成时长（毫秒），当无历史数据时使用此兜底值
_DEFAULT_ESTIMATED_DURATION_MS = 120_000  # 2 分钟


@app.get("/api/research/avg-duration")
async def get_avg_duration():
    """返回历史报告平均耗时（毫秒），供前端估算进度百分比。

    始终返回 200；数据库不可用时 avg_duration_ms=0，前端可回退到 default_duration_ms。
    """
    try:
        from src.storage import report_repository
        avg_ms = await report_repository.get_avg_duration_ms()
        return {
            "avg_duration_ms": avg_ms,
            "default_duration_ms": _DEFAULT_ESTIMATED_DURATION_MS,
        }
    except Exception as _e:
        logger.debug(f"[AVG_DURATION] 查询失败（数据库可能未配置）: {_e}")
        return {
            "avg_duration_ms": 0,
            "default_duration_ms": _DEFAULT_ESTIMATED_DURATION_MS,
        }


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
        # 在请求 Task（Task A）的 context 中设置 thread_id，
        # 后续所有 asyncio.create_task() 创建的子 Task 都会继承此上下文，
        # 使得 enhanced_logger（基于 ContextVar）在所有日志中打印正确的 thread_id。
        current_thread_id.set(thread_id)
        _event_count = 0
        _stream_start = time.time()
        _exit_reason = "normal"
        _graph_task: asyncio.Task | None = None

        async def _check_disconnect() -> bool:
            """检查客户端是否已断开，断开则设置cancel_event并返回True"""
            if await raw_request.is_disconnected():
                enhanced_logger.logger.info(
                    f"[CLIENT_DISCONNECTED] thread_id={thread_id} | "
                    f"客户端已断连，停止推送 | 已发送事件数={_event_count}"
                )
                cancel_event.set()
                return True
            return False

        try:
            graph_gen = _astream_workflow_generator(
                request.model_dump()["messages"],
                thread_id,
                request.resources or [],
                request.max_plan_iterations or 2,
                request.max_step_num or 5,
                request.max_search_results or int(os.getenv("ONLINE_SEARCH_MAX_RESULTS", "2")),
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
                user_info=raw_request.state.user_info,
                use_budget_controlled_online_search=request.use_budget_controlled_online_search if request.use_budget_controlled_online_search is not None else True,
                use_budget_controlled_bocom_search=request.use_budget_controlled_bocom_search if request.use_budget_controlled_bocom_search is not None else True,
                cancel_event=cancel_event,
                reporter_model=request.reporter_model or "",
                document_contexts=request.document_contexts or [],
            )
            generator = graph_gen.__aiter__()
            _graph_task = asyncio.create_task(generator.__anext__())

            while True:
                try:
                    event = await _graph_task
                except StopAsyncIteration:
                    break

                _event_count += 1
                if await _check_disconnect():
                    break
                if cancel_event.is_set():
                    enhanced_logger.logger.info(
                        f"[CANCEL_TRIGGERED] thread_id={thread_id} | "
                        f"cancel_event 已设置，停止推送 | 已发送事件数={_event_count}"
                    )
                    _exit_reason = "cancel_triggered"
                    break
                yield event

                # 预取下个事件
                _graph_task = asyncio.create_task(generator.__anext__())

        except asyncio.CancelledError:
            _exit_reason = "cancelled"
            enhanced_logger.logger.warning(
                f"[STREAM_CANCELLED] thread_id={thread_id} | 流被取消 | "
                f"总耗时={time.time()-_stream_start:.2f}s | 总事件数={_event_count}"
            )
        except GeneratorExit:
            _exit_reason = "generator_exit"
            raise  # GeneratorExit 必须重新抛出
        finally:
            # 取消仍在运行的 graph_task（清理孤儿任务）
            if _graph_task is not None and not _graph_task.done():
                _graph_task.cancel()
            cancel_event.set()  # 确保无论如何都通知下游停止
            _cancel_registry.unregister(thread_id)
            _stream_total = time.time() - _stream_start
            enhanced_logger.logger.info(
                f"✅ STREAM_FINISHED | thread_id={thread_id} | "
                f"reason={_exit_reason} | "
                f"总耗时={_stream_total:.2f}s | 总事件数={_event_count}"
            )

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
    if agent_name in ("router", "domain_knowledge_node"):
        return "routing"
    
    # Check for planning phase
    if agent_name == "planner" or langgraph_node == "planner":
        return "planning"
    
    # Check for reporting phase
    if agent_name == "reporter" or langgraph_node == "reporter":
        return "reporting"
    
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
            # 问题澄清中断：传递 questions 数组（问卷模式）
            tag = "clarification"
            questions = content.get("questions", [])
            # 兼容旧的单问题格式
            if not questions and content.get("question"):
                questions = [{"question": content["question"], "options": content.get("options", [])}]
            display_content = questions[0]["question"] if questions else ""
        else:
            # 计划确认中断：保持原有的硬编码选项
            tag = "waiting_for_feedback"
            questions = None
            display_content = content if isinstance(content, str) else str(content)
        
        event_data = {
            "thread_id": thread_id,
            "id": interrupt_id,
            "role": "assistant",
            "content": display_content,
            "finish_reason": "interrupt",
            "tag": tag,
        }
        
        if tag == "clarification":
            # 问卷模式：传递 questions 数组
            event_data["questions"] = questions
        else:
            # 计划确认：传递 options 列表
            event_data["options"] = [
                {"text": "编辑计划", "value": "edit_plan"},
                {"text": "开始研究", "value": "accepted"},
            ]
        
        return _make_event("interrupt", event_data)
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
        sse_event = _make_event("node_transition", event_payload)
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
        
        # 调试日志：记录 tool_call_result 发送
        _tool_name = getattr(message_chunk, 'name', 'unknown')
        _content_len = len(str(message_chunk.content)) if message_chunk.content else 0
        logger.info(f"[TOOL_RESULT_SEND] thread_id={thread_id} | agent={agent_name} | "
                    f"tool_name={_tool_name} | tool_call_id={message_chunk.tool_call_id} | "
                    f"msg_id={message_chunk.id} | content_len={_content_len}")
        
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
            
            # 调试日志：详细记录每次 tool_calls 事件的发送
            _tc_names = [tc.get('name', '?') for tc in message_chunk.tool_calls]
            _tc_ids = [tc.get('id', '?') for tc in message_chunk.tool_calls]
            logger.info(f"[TOOL_CALLS_SEND] thread_id={thread_id} | agent={agent_name} | msg_id={message_chunk.id} | "
                        f"tool_count={len(message_chunk.tool_calls)} | names={_tc_names} | ids={_tc_ids}")
            
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
                if tool_call.get("name") in ["web_search", "online_search", "vector_search"]:
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
    graph_instance, workflow_input, workflow_config, thread_id,
    user_name: str = "", user_code: str = "",
    branch_id: int = None, login_name: str = "",
    linked_org_name: str = "",
    stream_start_time: float = None,
):
    """Stream events from the graph and process them.

    内置心跳机制：当 LangGraph 工作流长时间无输出时（如 LLM 推理、搜索等待），
    自动发送 SSE ping 事件保持连接活跃，防止中间代理（nginx 等）因超时断开连接。
    """
    event_count = 0
    last_event_time = time.time()
    if stream_start_time is None:
        stream_start_time = time.time()

    # 心跳间隔（秒）：每 30 秒发送一次 ping，远小于 nginx proxy_read_timeout
    HEARTBEAT_INTERVAL = 30

    # 追踪当前 plan step 信息
    _step_index = -1
    _step_title = ""
    _cached_plan_steps = None

    # ─── 报告内容追踪（用于生成完成后保存到 MinIO + DB）───
    _reporter_content_from_state: str = ""  # 从 reporter 节点的状态更新中获取完整报告
    _reporter_finished = False
    _report_cancelled = False  # 报告是否被用户取消

    # ─── Token 追踪：累计 researcher / reporter 输出字符数 ───
    _researcher_total_chars = 0  # researcher 节点所有 AIMessageChunk 的字符总数
    _reporter_total_chars = 0    # reporter 节点所有 AIMessageChunk 的字符总数

    # 去重：记录已通过流式 chunk 发送过内容的消息 ID
    # LangGraph messages 流会发两次同一消息：1) LLM 流式 AIMessageChunk  2) 状态写回的完整 AIMessage
    # 前端 mergeMessage 用 += 拼接，如果不去重会导致内容翻倍
    _streamed_message_ids: set = set()

    try:
        # 使用显式异步迭代 + 超时心跳机制
        # 注意：不能用 asyncio.wait_for，因为超时会 cancel __anext__() 导致迭代器损坏
        stream_iterator = graph_instance.astream(
            workflow_input,
            config=workflow_config,
            stream_mode=["messages", "updates"],
            subgraphs=True,
        ).__aiter__()

        pending_next = None  # 缓存正在等待的 __anext__ 任务

        while True:
            if pending_next is None:
                pending_next = asyncio.ensure_future(stream_iterator.__anext__())

            done, _ = await asyncio.wait(
                {pending_next}, timeout=HEARTBEAT_INTERVAL
            )

            if done:
                # 事件已到达
                pending_next = None
                try:
                    agent, _, event_data = done.pop().result()
                except StopAsyncIteration:
                    break
            else:
                # 超时未收到事件，发送心跳 ping 保持连接（不取消 pending_next）
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

                    # 4.1) 发送阶段进度事件（phase_progress）
                    # 在检测到工作流节点活动时，将当前阶段、步骤索引推送给前端，
                    # 用于正计时 + 进度百分比展示。
                    _PHASE_NODES = (
                        "coordinator", "background_investigator", "planner",
                        "researcher", "research_team", "reporter",
                    )
                    if _node_name in _PHASE_NODES:
                        # 将 research_team 统一映射为 researcher（前端展示更清晰）
                        _phase_name = "researcher" if _node_name == "research_team" else _node_name
                        # 从缓存的 plan steps 中提取当前步骤标题
                        _current_step_title = _step_title or ""
                        if not _current_step_title and _cached_plan_steps and 0 <= _step_index < len(_cached_plan_steps):
                            _target = _cached_plan_steps[_step_index]
                            _current_step_title = getattr(_target, 'title', None) or (_target.get('title', '') if isinstance(_target, dict) else '')
                        # 提取所有步骤标题（供前端按索引查找）
                        _all_step_titles = []
                        if _cached_plan_steps:
                            for _s in _cached_plan_steps:
                                _t = getattr(_s, 'title', None) or (_s.get('title', '') if isinstance(_s, dict) else '')
                                _all_step_titles.append(_t or '')
                        yield _make_event("phase_progress", {
                            "thread_id": thread_id,
                            "phase": _phase_name,
                            "step_index": _step_index,
                            "total_steps": len(_cached_plan_steps) if _cached_plan_steps else 0,
                            "step_title": _current_step_title,
                            "step_titles": _all_step_titles,
                        })

                    break  # 只处理第一个节点更新

                # 5) 检测 reporter 节点输出的 reference_index，发送 SSE 事件给前端
                for _node_name_ri, _node_update_ri in event_data.items():
                    if not isinstance(_node_update_ri, dict):
                        continue
                    _ref_index = _node_update_ri.get("reference_index")
                    if _ref_index and isinstance(_ref_index, list) and len(_ref_index) > 0:
                        logger.info(f"[REFERENCE_INDEX] thread_id={thread_id} | 发送 reference_index 事件 | 条数: {len(_ref_index)}")
                        # 打印完整索引列表，便于核对推送给前端的链接与编号
                        logger.debug(
                            f"\n{'='*60}\nSSE reference_index 推送给前端的完整列表\n{'='*60}"
                        )
                        for _item in _ref_index:
                            logger.debug(
                                f"  [{_item.get('index', '?'):>3}] {_item.get('title', '')} -> {_item.get('url', '')}"
                            )
                        logger.debug(f"{'='*60}")
                        yield _make_event("reference_index", {
                            "thread_id": thread_id,
                            "references": _ref_index,
                        })
                        break

                # 6) Fallback: 从 updates 中提取 ToolMessages 并发送 tool_call_result 事件
                # 当 ReactLoop 内部的 ToolMessages 通过 Command update 写入状态时，
                # 如果 LangGraph 不通过 "messages" stream 单独发出它们，这里作为兜底处理
                for _node_name_fb, _node_update_fb in event_data.items():
                    if not isinstance(_node_update_fb, dict):
                        continue
                    update_messages = _node_update_fb.get("messages")
                    if not update_messages or not isinstance(update_messages, list):
                        continue
                    for _upd_msg in update_messages:
                        if isinstance(_upd_msg, ToolMessage):
                            _tool_name = getattr(_upd_msg, 'name', 'unknown')
                            _content_preview = str(_upd_msg.content)[:200] if _upd_msg.content else ''
                            logger.info(f"[TOOL_RESULT_FROM_UPDATE] tool={_tool_name} | tool_call_id={_upd_msg.tool_call_id} | content_preview={_content_preview}")
                            _agent_name_fb = _get_agent_name(agent, {})
                            _tool_event = {
                                "thread_id": thread_id,
                                "agent": _agent_name_fb,
                                "id": _upd_msg.id,
                                "role": "assistant",
                                "content": _upd_msg.content,
                                "tool_call_id": _upd_msg.tool_call_id,
                            }
                            yield _make_event("tool_call_result", _tool_event)
                    break

                # 7) 检测 reporter 节点的状态更新完成（兜底机制）
                # reporter 节点返回 {"final_report": ..., "reference_index": ...}
                # 这是状态更新，不是 LLM 流式响应，所以没有 finish_reason
                for _node_name_rpt, _node_update_rpt in event_data.items():
                    if _node_name_rpt == "reporter" and isinstance(_node_update_rpt, dict):
                        if "final_report" in _node_update_rpt:
                            _reporter_finished = True
                            _report_content_from_state = _node_update_rpt.get("final_report", "")
                            _report_cancelled = _node_update_rpt.get("report_cancelled", False)
                            enhanced_logger.logger.info(
                                f"[REPORTER_FINISHED_FROM_UPDATE] thread_id={thread_id} | "
                                f"检测到 reporter 状态更新 | content_length={len(_report_content_from_state)} | cancelled={_report_cancelled}"
                            )
                        break

                # 其他 update 目前不需要转成事件，直接忽略
                continue

            message_chunk, message_metadata = cast(
                tuple[BaseMessage, dict[str, Any]], event_data
            )

            # 去重：跳过已通过流式 chunk 发送过的完整 AIMessage（避免前端内容翻倍）
            msg_id = getattr(message_chunk, 'id', None)
            if isinstance(message_chunk, AIMessage) and not isinstance(message_chunk, AIMessageChunk):
                if msg_id and msg_id in _streamed_message_ids:
                    logger.info(f"[DEDUP] thread_id={thread_id} | ✅ 命中去重，跳过完整消息 id={msg_id}")
                    continue
                else:
                    logger.info(f"[DEDUP] thread_id={thread_id} | ❌ 未命中去重 | id={msg_id} | type={type(message_chunk).__name__} | 已记录IDs={list(_streamed_message_ids)[:5]}")
            elif isinstance(message_chunk, AIMessageChunk) and msg_id:
                _streamed_message_ids.add(msg_id)
                logger.debug(f"[DEDUP] thread_id={thread_id} | 记录流式chunk id={msg_id}")

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

            # ─── Token 追踪：仅从流式 AIMessageChunk 累加（避免 AIMessage 重复计入）───
            if isinstance(message_chunk, AIMessageChunk) and hasattr(message_chunk, 'content') and message_chunk.content:
                _chunk_len = len(message_chunk.content)
                if agent_name == "researcher":
                    _researcher_total_chars += _chunk_len
                elif agent_name == "reporter":
                    _reporter_total_chars += _chunk_len

            # ─── 检测 reporter 完成标志（通过 LLM finish_reason）───
            _msg_node_rt = message_metadata.get("langgraph_node", "") if isinstance(message_metadata, dict) else ""
            if (_msg_node_rt == "reporter" or agent_name == "reporter") and hasattr(message_chunk, 'content') and message_chunk.content:
                # 检测 reporter 完成
                if hasattr(message_chunk, 'response_metadata') and message_chunk.response_metadata.get('finish_reason'):
                    _reporter_finished = True

    except Exception as e:
        enhanced_logger.logger.error(
            f"[STREAM_ERROR] thread_id={thread_id} | 图执行出错 | "
            f"已处理事件数={event_count} | 距上次事件={time.time()-last_event_time:.1f}s | "
            f"{type(e).__name__}: {str(e)[:200]}"
        )
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

        # ─── 报告生成完成：同步保存到 MinIO + DB + 埋点日志 ───
        if _reporter_finished and _report_content_from_state:
            full_report = _report_content_from_state
            if full_report.strip():
                try:
                    from src.server.report_service import handle_report_completed, extract_report_title
                    title = extract_report_title(full_report)
                    end_time = time.time()
                    duration_ms = int((end_time - stream_start_time) * 1000)
                    # 根据取消标志决定报告状态
                    report_status = "cancelled" if _report_cancelled else "completed"
                    # 同步等待保存完成，确保后续 API（PUT/chat）能查到记录
                    await handle_report_completed(
                        thread_id=thread_id,
                        report_content=full_report,
                        title=title,
                        login_name=login_name,
                        user_name=user_name,
                        user_code=user_code,
                        branch_id=branch_id,
                        linked_org_name=linked_org_name,
                        duration_ms=duration_ms,
                        report_type="research",
                        status=report_status,
                        start_timestamp=stream_start_time,
                        end_timestamp=end_time,
                        researcher_chars=_researcher_total_chars,
                        reporter_chars=_reporter_total_chars,
                    )
                except Exception as _report_err:
                    logger.error(f"[REPORT_SERVICE] 报告保存失败 | thread_id={thread_id} | {_report_err}")




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
    user_info=None,  # UserInfo 对象，来自 auth_middleware（request.state.user_info）
    use_budget_controlled_online_search: bool = True,  # 是否使用预算控制的在线搜索
    use_budget_controlled_bocom_search: bool = True,  # 是否使用预算控制的交行搜索
    cancel_event: asyncio.Event = None,  # 客户端断连取消信号
    reporter_model: str = "",  # 用户选择的 reporter 模型 key
    document_contexts: List = None,  # 用户上传的文档上下文
):
    # 设置 thread_id 到 contextvars，该请求链路内所有日志自动携带此 ID
    current_thread_id.set(thread_id)

    # ── guwp_token 接收日志：确认前端是否成功传递 token ──
    _token_len = len(guwp_token) if guwp_token else 0
    logger.info(
        f"🔑 [guwptoken] GUWP_TOKEN_RECV | thread_id={thread_id} | "
        f"token={'有' if guwp_token else '无'} | "
        f"token_len={_token_len} | "
        f"token_value={'(空)' if not guwp_token else guwp_token}"
    )

    # Process initial messages
    for message in messages:
        if isinstance(message, dict) and "content" in message:
            _process_initial_messages(message, thread_id)

    # ⚙️ 不再设置全局环境变量（避免多用户并发冲突）
    # 改为通过 workflow_input["guwp_token"] 传递到 state，确保线程安全
    
    # 将用户上传的文档原文和摘要分开处理
    document_original_text = ""
    document_summary_text = ""
    if document_contexts:
        logger.info(f"📄 DOCUMENT_CONTEXTS_DEBUG | 文档数量: {len(document_contexts)}")
        for i, doc in enumerate(document_contexts):
            doc_dict = doc if isinstance(doc, dict) else doc.dict()
            fname = doc_dict.get("filename", "unknown")
            content = doc_dict.get("content", "")
            logger.info(f"📄 DOCUMENT_CONTEXTS_DEBUG | 文档[{i}] filename='{fname}' | content长度={len(content)} | content前100字: {content[:100]}")
        doc_sections = []
        for doc in document_contexts:
            doc_dict = doc if isinstance(doc, dict) else doc.dict()
            fname = doc_dict.get("filename", "unknown")
            content = doc_dict.get("content", "")
            doc_sections.append(f"[附件文档 - {fname}]\n{content}\n[/附件文档]")
        document_original_text = "\n\n".join(doc_sections)
        logger.info(f"📄 DOCUMENT_CONTEXTS_DEBUG | document_original_text 总长度: {len(document_original_text)}")
        
        # 用 LLM 生成文档摘要，供 researcher 节点使用（减轻上下文负担）
        try:
            from src.config.agents import LLMType
            summary_llm = get_llm_by_type("basic")
            summary_prompt = (
                "请对以下文档内容生成一份简洁的摘要（1000字以内），保留核心观点、关键数据和主要结论：\n\n"
                f"{document_original_text}"
            )
            from langchain_core.messages import HumanMessage as _HumanMessage, SystemMessage as _SystemMessage
            summary_messages = [
                _SystemMessage(content="你是一个文档摘要生成助手，请用简洁的语言提取文档的核心内容。"),
                _HumanMessage(content=summary_prompt),
            ]
            summary_result = summary_llm.invoke(summary_messages)
            document_summary_text = summary_result.content if hasattr(summary_result, 'content') else str(summary_result)
            logger.info(f"文档摘要生成成功，摘要长度: {len(document_summary_text)}")
        except Exception as e:
            logger.warning(f"文档摘要生成失败，回退使用截断原文作为摘要: {e}")
            # 回退策略：截取前 500 字作为摘要
            document_summary_text = document_original_text[:500] + ("\n\n[... 文档内容已截断 ...]" if len(document_original_text) > 500 else "")
    
    # system_context 仅保留非文档的系统背景上下文
    full_system_context = system_context

    # Prepare workflow input
    workflow_input = {
        "messages": messages,
        "plan_iterations": 0,
        # "final_report": "",
        "current_plan": None,
        "observations": [],
        "auto_accepted_plan": auto_accepted_plan,
        "enable_background_investigation": enable_background_investigation,
        "research_topic": messages[-1]["content"] if messages else "",
        "system_context": full_system_context,  # 系统背景上下文（不含文档内容）
        "force_routing_path": force_routing_path,  # 🐛 调试模式
        # 确保迭代研究的状态字段被正确初始化
        "iteration_count": 0,
        "iteration_history": [],
        "report_style": report_style.value,  # 将报告风格传递到 state，用于 researcher_node 动态选择工具
        "guwp_token": guwp_token,  # ✅ 通过 state 传递 token，确保线程安全
    }
    # 仅在本次请求带有文档时才写入，避免后续追问覆盖已有文档摘要
    if document_summary_text:
        workflow_input["document_summary"] = document_summary_text

    else:
        logger.info(f"📄 DOCUMENT_WORKFLOW_DEBUG | document_summary_text 为空，未写入 workflow_input（依赖 checkpoint 保留已有值）")
    if document_original_text:
        workflow_input["document_original"] = document_original_text
    if not auto_accepted_plan and interrupt_feedback:
        resume_msg = f"[{interrupt_feedback}]"
        if messages:
            resume_msg += f" {messages[-1]['content']}"
        logger.info(f"⚠️ DOCUMENT_WORKFLOW_DEBUG | interrupt_feedback 触发! workflow_input 将被替换为 Command(resume=...) | interrupt_feedback='{interrupt_feedback}' | 文档摘要是否已设置: {bool(document_summary_text)}")
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
            "system_context": full_system_context,  # 系统背景上下文（不含文档内容，文档由各节点自行注入）
            "use_budget_controlled_online_search": use_budget_controlled_online_search,
            "use_budget_controlled_bocom_search": use_budget_controlled_bocom_search,
            "cancel_event": cancel_event,  # 客户端断连取消信号，reporter 节点检测
            "reporter_model": reporter_model,
        },
        "recursion_limit": get_recursion_limit(),
    }

    checkpoint_saver = get_bool_env("LANGGRAPH_CHECKPOINT_SAVER", False)
    checkpoint_url = get_str_env("LANGGRAPH_CHECKPOINT_DB_URL", "")

    # ===== 工作流启动日志：帮助排查 thread_id 复用导致 state 残留问题 =====
    _wf_input_type = type(workflow_input).__name__
    _wf_plan = "N/A"
    if isinstance(workflow_input, dict):
        _wf_plan = str(workflow_input.get("current_plan", "None"))[:50]
    logger.info(
        f"🚀 WORKFLOW_START | thread_id={thread_id} | "
        f"checkpoint_saver={checkpoint_saver} | "
        f"input_type={_wf_input_type} | "
        f"current_plan_in_input={_wf_plan} | "
        f"research_topic={workflow_input.get('research_topic', 'N/A')[:80] if isinstance(workflow_input, dict) else 'Command'}"
    )
    # 注：新版 langgraph-checkpoint-postgres 的 from_conn_string() 不再接受
    # psycopg 级别的 kwargs（如 autocommit / row_factory / prepare_threshold），
    # 内部已自动启用 autocommit=True。如需自定义连接参数，
    # 请改用 AsyncConnectionPool + AsyncPostgresSaver(pool)。
    # ─── 解析用户信息（直接从 auth_middleware 注入的 request.state.user_info 获取）───
    _user_code = ""
    _user_name = ""
    _branch_id = None
    _login_name = ""
    _linked_org_name = ""
    if user_info and user_info.is_authenticated:
        _user_code = user_info.user_code
        _user_name = user_info.user_name
        _branch_id = user_info.branch_id
        _login_name = user_info.login_name
        _linked_org_name = user_info.linked_org_name
        logger.info(
            f"[REPORT_USER_INFO] source={user_info.source} | login_name={_login_name} | "
            f"user_code={_user_code} | user_name={_user_name} | branch_id={_branch_id}"
        )
    else:
        logger.warning(
            f"[REPORT_USER_INFO] 用户信息未认证 | user_info={'None' if user_info is None else 'not_authenticated'} | "
            f"guwp_token={'有' if guwp_token else '无'} | 报告将以空用户信息保存"
        )

    _stream_start = time.time()

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
                    graph, workflow_input, workflow_config, thread_id,
                    user_name=_user_name, user_code=_user_code,
                    branch_id=_branch_id, login_name=_login_name,
                    linked_org_name=_linked_org_name,
                    stream_start_time=_stream_start,
                ):
                    yield event
        else:
            logger.warning(f"Unsupported checkpoint URL scheme: {checkpoint_url}. Only postgresql:// is supported.")
            async for event in _stream_graph_events(
                graph, workflow_input, workflow_config, thread_id,
                user_name=_user_name, user_code=_user_code,
                branch_id=_branch_id, login_name=_login_name,
                linked_org_name=_linked_org_name,
                stream_start_time=_stream_start,
            ):
                yield event
    else:
        # Use graph without checkpointer
        async for event in _stream_graph_events(
            graph, workflow_input, workflow_config, thread_id,
            user_name=_user_name, user_code=_user_code,
            branch_id=_branch_id, login_name=_login_name,
            linked_org_name=_linked_org_name,
            stream_start_time=_stream_start,
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
ENCRYPT_API_URL = os.getenv(
    "ENCRYPT_API_URL",
    "http://eaip-chn-slb-7006.bocomm.com/ELLM.ELLM-OFFICE.V-1.0/pptEncryptFile.upload",
)

# 文档上传支持的文件类型
ALLOWED_UPLOAD_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
    "txt", "md", "csv", "json", "xml", "html",
}
# 文档上传最大文件大小 (50MB)
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024


# ============================================================
# 文档上传解析接口
# ============================================================

@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    接收用户上传的文件，调用 Easyparse 解析为文本，返回解析结果。

    调用链: 前端 → 后端 /api/documents/upload → Easyparse /convert → 返回解析文本
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")

    # 文件类型校验
    file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{file_ext}. Allowed: {', '.join('.' + e for e in sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
        )

    # 读取文件内容并校验大小
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file_size} bytes. Maximum allowed: {MAX_UPLOAD_SIZE_BYTES} bytes (50MB)"
        )

    # 调用 Easyparse /convert 接口解析文件
    easyparse_url = f"{EASYPARSE_SERVICE_URL}/convert"
    try:
        async with httpx.AsyncClient(
            timeout=120.0,
            trust_env=False,
            proxy=None,
        ) as client:
            response = await client.post(
                easyparse_url,
                files={"file": (file.filename, file_content, file.content_type or "application/octet-stream")},
            )

        if response.status_code != 200:
            logger.error(f"Easyparse conversion failed: status={response.status_code}, detail={response.text[:200]}")
            raise HTTPException(
                status_code=502,
                detail=f"Document parsing failed: easyparse returned {response.status_code}"
            )

        # Easyparse 返回纯文本文件
        parsed_content = response.text

        # 截断过长内容（防止单文档擑爆上下文）
        MAX_CONTENT_CHARS = 50000  # ~16k tokens
        if len(parsed_content) > MAX_CONTENT_CHARS:
            parsed_content = parsed_content[:MAX_CONTENT_CHARS] + "\n\n[... 文档内容已截断，原文过长 ...]"

        doc_id = str(uuid4())
        return DocumentUploadResponse(
            id=doc_id,
            filename=file.filename,
            content=parsed_content,
            size=file_size,
            file_type=file_ext,
        )

    except httpx.ConnectError:
        logger.error(f"Cannot connect to easyparse service: {EASYPARSE_SERVICE_URL}")
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to document parsing service ({EASYPARSE_SERVICE_URL}). Please ensure it is running."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


# ============================================================
# Markdown 转 Word 代理接口
# ============================================================

@app.post("/api/markdown/to_word")
async def markdown_to_word(request: MarkdownToWordRequest):
    """
    将 Markdown 内容转换为 Word 文档

    调用 easyparse 服务进行转换，通过 nginx 负载均衡分发到 easyparse 实例。
    调用链: 后端 → nginx(/markdown_to_word) → easyparse 集群
    EASYPARSE_SERVICE_URL 默认 http://nginx，拼接后请求 nginx 的负载均衡路由。
    """
    easyparse_url = f"{EASYPARSE_SERVICE_URL}/markdown_to_word"

    # 读取 DOCX_FOOTER 配置，决定是否向 easyparse 透传页脚文案
    docx_footer_config = load_yaml_config(os.path.join(os.getcwd(), "conf.yaml")).get("DOCX_FOOTER", {})
    footer_data = {}
    if docx_footer_config.get("enabled", True) and docx_footer_config.get("text"):
        footer_data["footer_text"] = docx_footer_config["text"]
        footer_data["footer_enabled"] = "true"
    elif not docx_footer_config.get("enabled", True):
        # enabled=false 时传 footer_enabled=false，显式禁用页脚
        footer_data["footer_enabled"] = "false"

    logger.info(f"Using easyparse footer text: {footer_data.get('footer_text', 'none')}")

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
                    data=footer_data,
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


# ─── 文件加密辅助函数 ───

async def _encrypt_docx(
    docx_bytes: bytes,
    filename: str,
    encrypt_api_url: str,
    guwp_token: str,
) -> tuple[bytes, str] | None:
    """
    将 docx 文件上传至加密服务进行加密。

    Args:
        docx_bytes: easyparse 返回的原始 docx 字节流
        filename: 文件名（不含扩展名）
        encrypt_api_url: 加密服务 URL
        guwp_token: GUWP 鉴权令牌

    Returns:
        (加密后的文件字节流, 加密服务返回的原始文件名)；失败返回 None
    """
    if not encrypt_api_url or not guwp_token:
        logger.warning("加密服务 URL 或 GUWP_TOKEN 未配置，跳过加密")
        return None

    # 将 docx 写入临时文件，供加密服务 multipart 上传
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_docx:
        tmp_docx.write(docx_bytes)
        tmp_docx_path = tmp_docx.name

    try:
        mime_type = (
            mimetypes.guess_type(tmp_docx_path)[0]
            or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        async with httpx.AsyncClient(
            timeout=60.0, trust_env=False, proxy=None
        ) as client:
            with open(tmp_docx_path, "rb") as f:
                encrypt_response = await client.post(
                    encrypt_api_url,
                    headers={
                        "Accept": "*/*",
                        "guwp-token": guwp_token,
                    },
                    files={"file": (f"{filename}.docx", f, mime_type)},
                )

        if encrypt_response.status_code == 200:
            content_type = encrypt_response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                # 加密服务返回 JSON 错误信息
                logger.error(f"加密服务返回错误: {encrypt_response.text[:500]}")
                return None

            # 从加密服务响应头提取原始文件名（含扩展名）
            disposition = encrypt_response.headers.get("Content-Disposition", "")
            encrypted_filename = f"{filename}.docx"  # fallback
            if "filename=" in disposition:
                encrypted_filename = disposition.split("filename=")[-1].strip('"')

            logger.info(
                f"加密服务返回文件，大小: {len(encrypt_response.content)} 字节，"
                f"文件名: {encrypted_filename}"
            )
            return encrypt_response.content, encrypted_filename
        else:
            logger.error(
                f"加密服务请求失败: status={encrypt_response.status_code}, "
                f"response={encrypt_response.text[:500]}"
            )
            return None

    except httpx.ConnectError:
        logger.error(f"无法连接加密服务: {encrypt_api_url}")
        return None
    except Exception as e:
        logger.exception(f"加密过程异常: {e}")
        return None
    finally:
        try:
            os.unlink(tmp_docx_path)
        except OSError:
            pass


# ─── Markdown 转 Word（加密版） ───

@app.post("/api/markdown/to_word/encrypted")
async def markdown_to_word_encrypted(request: MarkdownToWordRequest, raw_request: Request):
    """
    将 Markdown 内容转换为加密 Word 文档。

    流程：
    1. 调用 easyparse 服务将 markdown 转为 docx
    2. 将 docx 上传至加密服务进行加密
    3. 返回加密后的 docx；加密失败时自动降级返回未加密 docx
    """
    easyparse_url = f"{EASYPARSE_SERVICE_URL}/markdown_to_word"

    # 读取 DOCX_FOOTER 配置
    docx_footer_config = load_yaml_config(
        os.path.join(os.getcwd(), "conf.yaml")
    ).get("DOCX_FOOTER", {})
    footer_data = {}
    if docx_footer_config.get("enabled", True) and docx_footer_config.get("text"):
        footer_data["footer_text"] = docx_footer_config["text"]
        footer_data["footer_enabled"] = "true"
    elif not docx_footer_config.get("enabled", True):
        footer_data["footer_enabled"] = "false"

    logger.info(
        f"[encrypted] Using easyparse footer text: "
        f"{footer_data.get('footer_text', 'none')}"
    )

    # 将 markdown 写入临时文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(request.content)
        tmp_path = tmp.name

    try:
        # Step 1: 调用 easyparse 将 markdown 转为 docx
        async with httpx.AsyncClient(
            timeout=60.0, trust_env=False, proxy=None
        ) as client:
            with open(tmp_path, "rb") as f:
                response = await client.post(
                    easyparse_url,
                    files={"file": ("report.md", f, "text/markdown")},
                    data=footer_data,
                )

        if response.status_code != 200:
            logger.error(
                f"[encrypted] easyparse 转换失败: status={response.status_code}"
            )
            raise HTTPException(
                status_code=502,
                detail=f"Markdown 转 Word 失败: easyparse 返回 {response.status_code}",
            )

        docx_bytes = response.content
        filename = request.filename or "research-report"

        # Step 2: 上传至加密服务进行加密
        # 优先从 Cookie（auth 中间件注入 raw_request.state），降级读环境变量
        guwp_token = raw_request.state.guwp_token or os.getenv("GUWP_TOKEN", "")

        encrypted_result = await _encrypt_docx(
            docx_bytes, filename, ENCRYPT_API_URL, guwp_token
        )

        if encrypted_result is not None:
            # 加密成功，使用加密服务返回的原始文件名
            encrypted_bytes, encrypted_filename = encrypted_result
            # 在 .edlp 扩展名前插入 .docx，使下载文件名体现原始文档格式
            encrypted_filename = encrypted_filename.replace('.edlp', '.docx.edlp')
            logger.info(f"[encrypted] 文件加密成功: {encrypted_filename}")
            return Response(
                content=encrypted_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="{encrypted_filename}"',
                },
            )
        else:
            # 加密失败，不降级，直接报错
            logger.error(f"[encrypted] 加密失败，请求的加密文件不可用")
            raise HTTPException(status_code=502, detail="文档下载失败")

    except httpx.ConnectError:
        logger.error(
            f"[encrypted] 无法连接 easyparse 服务: {EASYPARSE_SERVICE_URL}"
        )
        raise HTTPException(
            status_code=503,
            detail=f"无法连接 easyparse 服务({EASYPARSE_SERVICE_URL})，请确认服务已启动",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[encrypted] Markdown 转 Word 加密异常: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.post("/api/prose/generate")
async def generate_prose(request: GenerateProseRequest):
    try:
        workflow = build_prose_graph()
        prose_input = {
            "messages": [],
            "content": request.prompt,
            "option": request.option,
            "command": request.command or "",
            "output": "",
        }

        async def event_generator():
            try:
                async for _node, events in workflow.astream(
                    prose_input,
                    stream_mode="messages",
                    subgraphs=True,
                ):
                    for event in events:
                        if hasattr(event, "content") and event.content:
                            yield f"data: {event.content}\n\n"
            except Exception as e:
                logger.exception(f"Error during prose streaming: {str(e)}")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.exception(f"Error occurred during prose generation: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


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
                    "INDUSTRY_RESEARCH": ReportStyle.INDUSTRY_RESEARCH,
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
        reporter_options=get_reporter_model_options(),
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
async def simple_research_stream(request: SimpleResearchRequest, raw_request: Request):
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
            thread_id=thread_id,
            user_info=raw_request.state.user_info,
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
    thread_id: str,
    user_info=None,  # UserInfo 对象，来自 auth_middleware
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
            max_search_results=request.max_search_results or int(os.getenv("ONLINE_SEARCH_MAX_RESULTS", "2")),
            max_iteration=request.max_iteration or 5,
            search_engine=request.search_engine or "custom_search",
            auto_accepted_plan=request.auto_accepted_plan if request.auto_accepted_plan is not None else True,
            interrupt_feedback=request.interrupt_feedback or "",
            mcp_settings=request.mcp_settings or {},
            enable_background_investigation=request.enable_background_investigation or True,
            report_style=request.report_style or ReportStyle.ACADEMIC,
            enable_deep_thinking=request.enable_deep_thinking or False,
                        reporter_model=request.reporter_model or "",
            system_context=get_str_env("SYSTEM_CONTEXT", ""),  # 从环境变量读取
            force_routing_path=request.force_routing_path,  # 🐛 调试模式：支持测试强制路由
            user_info=user_info,
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
                        agent = event_data.get("agent", "")
                        allowed_agents = [
                            "reporter",                    # 深度研究报告
                            "coordinator",                # 深度研究协调
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
