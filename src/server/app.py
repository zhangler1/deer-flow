# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import base64
from datetime import datetime
import json
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
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langgraph.types import Command
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.mongodb import AsyncMongoDBSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from src.config.configuration import get_recursion_limit
from src.config.loader import get_bool_env, get_str_env
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
from src.rag.milvus import load_examples
from src.rag.retriever import Resource
from src.server.chat_request import (
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatRequest,
    EnhancePromptRequest,
    GeneratePodcastRequest,
    GeneratePPTRequest,
    GenerateProseRequest,
    SimpleResearchRequest,
    SimpleResearchResponse,
    # TTSRequest 已删除
)
from src.server.config_request import ConfigResponse, CustomSearchRepositoryConfig
from src.server.mcp_request import MCPServerMetadataRequest, MCPServerMetadataResponse
from src.server.mcp_utils import load_mcp_tools
from src.server.rag_request import (
    RAGConfigResponse,
    RAGResourceRequest,
    RAGResourcesResponse,
)
from src.tools import VolcengineTTS
from src.tools.custom_search import get_available_repositories
from src.graph.checkpoint import chat_stream_message
from src.utils.json_utils import sanitize_args
from src.utils.enhanced_logger import get_enhanced_logger, setup_enhanced_logging
from src.config.custom_search import get_custom_search_config

logger = logging.getLogger(__name__)

# 初始化增强日志系统，支持从环境变量LOG_FILE读取日志文件路径
log_file = os.getenv('LOG_FILE')  # 例如: logs/deer-flow.log
setup_enhanced_logging(level=logging.INFO, enable_colors=True, log_file=log_file)
enhanced_logger = get_enhanced_logger("deer-flow.api")

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
load_examples()

in_memory_store = InMemoryStore()
graph = build_graph_with_memory()


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
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

    return StreamingResponse(
        _astream_workflow_generator(
            request.model_dump()["messages"],
            thread_id,
            request.resources or [],
            request.max_plan_iterations or 1,
            request.max_step_num or 3,
            request.max_search_results or 3,
            request.max_iteration or 5,
            request.search_engine or "custom_search",
            request.custom_search_repository or "",
            request.auto_accepted_plan or False,
            request.interrupt_feedback or "",
            request.mcp_settings if (mcp_enabled and request.mcp_settings) else {},
            request.enable_background_investigation or True,
            request.report_style or ReportStyle.ACADEMIC,
            request.enable_deep_thinking or False,
            system_context=system_context,  # 从环境变量读取
            force_routing_path=request.force_routing_path,  # 🐛 调试模式
        ),
        media_type="text/event-stream",
    )


def _process_tool_call_chunks(tool_call_chunks):
    """Process tool call chunks and sanitize arguments."""
    chunks = []
    for chunk in tool_call_chunks:
        chunks.append(
            {
                "name": chunk.get("name", ""),
                "args": sanitize_args(chunk.get("args", "")),
                "id": chunk.get("id", ""),
                "index": chunk.get("index", 0),
                "type": chunk.get("type", ""),
            }
        )
    return chunks


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
        
        return _make_event(
            "interrupt",
            {
                "thread_id": thread_id,
                "id": interrupt_id,
                "role": "assistant",
                "content": content,
                "finish_reason": "interrupt",
                "tag": "waiting_for_feedback",  # Add tag for interrupt events
                "options": [
                    {"text": "Edit plan", "value": "edit_plan"},
                    {"text": "Start research", "value": "accepted"},
                ],
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
                    {"text": "Edit plan", "value": "edit_plan"},
                    {"text": "Start research", "value": "accepted"},
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


async def _process_message_chunk(message_chunk, message_metadata, thread_id, agent):
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
            event_stream_message["tool_call_chunks"] = _process_tool_call_chunks(
                message_chunk.tool_call_chunks
            )
            
            # Set tag based on tool name
            # Default to searching, but check for specific tool types
            tag = "searching"  # default for web_search
            for tool_call in message_chunk.tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name == "crawl_tool":
                    tag = "crawling"
                    break
                elif tool_name == "web_search":
                    tag = "searching"
            event_stream_message["tag"] = tag
            
            # Check if this is a web_search tool call and emit search_status event
            for tool_call in message_chunk.tool_calls:
                if tool_call.get("name") == "web_search":
                    # Extract query and repository from tool call args
                    args = tool_call.get("args", {})
                    query = args.get("query", "")
                    repository_id = args.get("repository_id", "")
                    
                    # Get repository name from config if available
                    repository_name = None
                    if repository_id:
                        try:
                            custom_search_config = get_custom_search_config()
                            repo_config = custom_search_config.get_repository(repository_id)
                            if repo_config:
                                repository_name = repo_config.name
                        except Exception:
                            pass
                    
                    # Track this search call
                    tool_call_id = tool_call.get("id", "")
                    if tool_call_id:
                        _active_search_calls[tool_call_id] = {
                            "query": query,
                            "repository": repository_name or repository_id,
                        }
                    
                    # Emit search started event
                    search_event = {
                        "thread_id": thread_id,
                        "agent": agent_name,
                        "id": message_chunk.id,
                        "role": "assistant",
                        "query": query,
                        "repository": repository_name or repository_id if repository_id else None,
                        "status": "started",
                    }
                    yield _make_event("search_status", search_event)
            
            yield _make_event("tool_calls", event_stream_message)
        elif hasattr(message_chunk, 'tool_call_chunks') and message_chunk.tool_call_chunks:
            # AI Message - Tool Call Chunks
            event_stream_message["tool_call_chunks"] = _process_tool_call_chunks(
                message_chunk.tool_call_chunks
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
    """Stream events from the graph and process them."""
    try:
        async for agent, _, event_data in graph_instance.astream(
            workflow_input,
            config=workflow_config,
            stream_mode=["messages", "updates"],
            subgraphs=True,
        ):
            if isinstance(event_data, dict):
                # 调试：打印接收到的状态更新
                logger.info(f"[SSE调试] 状态更新事件 keys: {list(event_data.keys())}")
                
                # 1) 中断事件优先处理
                if "__interrupt__" in event_data:
                    yield _create_interrupt_event(thread_id, event_data)
                    continue
                logger.info(f"[SSE调试] 状态更新事件内容: {event_data}")

                # 2) 处理迭代研究节点跳转事件（不通过 update.messages，而是独立事件）
                node_transition = event_data.get("node_transition")
                logger.info(f"[SSE调试] node_transition 值: {node_transition}")
                if node_transition:
                    logger.info(f"[节点跳转] 检测到跳转事件，准备发送 SSE: {node_transition}")
                    # 这里 node_transition 由 iterative_research_node 写入
                    # 结构示例：
                    # {
                    #   "from": "iterative_research_node",
                    #   "to": "iterative_research_node" | "iterative_reporter_node",
                    #   "iteration": 3,
                    #   "reason": "continue" | "finish",
                    # }
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
                    logger.info(f"[SSE调试] 即将发送 node_transition 事件，payload: {event_payload}")
                    # 发送一个独立的 SSE 事件，事件名可自定义，例如 node_transition
                    sse_event = _make_event("node_transition", event_payload)
                    logger.info(f"[SSE调试] 生成的 SSE 事件内容: {sse_event[:200]}...")
                    yield sse_event

                # 其他 update 目前不需要转成事件，直接忽略
                continue

            message_chunk, message_metadata = cast(
                tuple[BaseMessage, dict[str, Any]], event_data
            )

            async for event in _process_message_chunk(
                message_chunk, message_metadata, thread_id, agent
            ):
                yield event
    except Exception as e:
        logger.exception("Error during graph execution")
        yield _make_event(
            "error",
            {
                "thread_id": thread_id,
                "error": str(e),
            },
        )



async def _astream_workflow_generator(
    messages: List[dict],
    thread_id: str,
    resources: List[Resource],
    max_plan_iterations: int,
    max_step_num: int,
    max_search_results: int,
    max_iteration: int,
    search_engine: str,
    custom_search_repository: str,
    auto_accepted_plan: bool,
    interrupt_feedback: str,
    mcp_settings: dict,
    enable_background_investigation: bool,
    report_style: ReportStyle,
    enable_deep_thinking: bool,
    system_context: str = "",  # 系统背景上下文
    force_routing_path: str = None,  # 🐛 调试模式：强制路由路径
):
    # Process initial messages
    for message in messages:
        if isinstance(message, dict) and "content" in message:
            _process_initial_messages(message, thread_id)

    # system_context 通过 State 和 Configuration 传递给各节点
    # 各节点在 Prompt Template 中按需使用，不在此处修改用户消息
    if system_context:
        enhanced_logger.logger.debug(  # 改为 DEBUG 级别，减少日志噪音
            f"🏛️ SYSTEM_CONTEXT | 系统背景已配置: {system_context} | "
            f"将通过State传递给工作流节点"
        )

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
            "custom_search_repository": custom_search_repository,
            "mcp_settings": mcp_settings,
            "report_style": report_style.value,
            "enable_deep_thinking": enable_deep_thinking,
            "system_context": system_context,  # 将系统背景传递到配置中
        },
        "recursion_limit": get_recursion_limit(),
    }

    checkpoint_saver = get_bool_env("LANGGRAPH_CHECKPOINT_SAVER", False)
    checkpoint_url = get_str_env("LANGGRAPH_CHECKPOINT_DB_URL", "")
    # Handle checkpointer if configured
    connection_kwargs = {
        "autocommit": True,
        "row_factory": "dict_row",
        "prepare_threshold": 0,
    }
    if checkpoint_saver and checkpoint_url != "":
        if checkpoint_url.startswith("postgresql://"):
            logger.info("start async postgres checkpointer.")
            async with AsyncPostgresSaver.from_conn_string(
                checkpoint_url, **connection_kwargs
            ) as checkpointer:
                await checkpointer.setup()
                graph.checkpointer = checkpointer
                graph.store = in_memory_store
                async for event in _stream_graph_events(
                    graph, workflow_input, workflow_config, thread_id
                ):
                    yield event

        if checkpoint_url.startswith("mongodb://"):
            logger.info("start async mongodb checkpointer.")
            async with AsyncMongoDBSaver.from_conn_string(
                checkpoint_url
            ) as checkpointer:
                graph.checkpointer = checkpointer
                graph.store = in_memory_store
                async for event in _stream_graph_events(
                    graph, workflow_input, workflow_config, thread_id
                ):
                    yield event
    else:
        # Use graph without MongoDB checkpointer
        async for event in _stream_graph_events(
            graph, workflow_input, workflow_config, thread_id
        ):
            yield event


def _make_event(event_type: str, data: Dict[str, Any]):
    if data.get("content") == "":
        data.pop("content")
    # Ensure JSON serialization with proper encoding
    try:
        json_data = json.dumps(data, ensure_ascii=False)

        finish_reason = data.get("finish_reason", "")
        chat_stream_message(
            data.get("thread_id", ""),
            f"event: {event_type}\ndata: {json_data}\n\n",
            finish_reason,
        )

        return f"event: {event_type}\ndata: {json_data}\n\n"
    except (TypeError, ValueError) as e:
        logger.error(f"Error serializing event data: {e}")
        # Return a safe error event
        error_data = json.dumps({"error": "Serialization failed"}, ensure_ascii=False)
        return f"event: error\ndata: {error_data}\n\n"






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
    # 获取自定义搜索仓库配置
    try:
        repositories_data = get_available_repositories()
        custom_search_repositories = [
            CustomSearchRepositoryConfig(
                id=repo["id"],
                name=repo["name"],
                description=repo["description"],
                repository=repo["repository"]
            )
            for repo in repositories_data
        ]
    except Exception as e:
        logger.warning(f"Failed to load custom search repositories: {e}")
        custom_search_repositories = []
    
    return ConfigResponse(
        rag=RAGConfigResponse(provider=SELECTED_RAG_PROVIDER),
        models=get_configured_llm_models(),
        custom_search_repositories=custom_search_repositories,
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
        "format": "openai_compatible"
    })
    
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
        
        # 直接调用 _astream_workflow_generator
        async for event in _astream_workflow_generator(
            messages=messages,
            thread_id=thread_id,
            resources=request.resources or [],
            max_plan_iterations=request.max_plan_iterations or 1,
            max_step_num=request.max_step_num or 3,
            max_search_results=request.max_search_results or 1,
            max_iteration=request.max_iteration or 5,
            search_engine=request.search_engine or "custom_search",
            custom_search_repository=request.custom_search_repository or "",
            auto_accepted_plan=request.auto_accepted_plan if request.auto_accepted_plan is not None else True,
            interrupt_feedback=request.interrupt_feedback or "",
            mcp_settings=request.mcp_settings or {},
            enable_background_investigation=request.enable_background_investigation or True,
            report_style=request.report_style or ReportStyle.ACADEMIC,
            enable_deep_thinking=request.enable_deep_thinking or False,
            system_context=get_str_env("SYSTEM_CONTEXT", ""),  # 从环境变量读取
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
