# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import base64
from datetime import datetime
import json
import logging
import time
import uuid
from typing import Annotated, Any, List, cast, Dict,Optional
from uuid import uuid4
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from langchain_core.messages import AIMessageChunk, BaseMessage, ToolMessage
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
from src.llms.llm import get_configured_llm_models
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
    TTSRequest,
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

logger = logging.getLogger(__name__)

# 初始化增强日志系统
setup_enhanced_logging(level=logging.INFO, enable_colors=True)
enhanced_logger = get_enhanced_logger("deer-flow.api")

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

    return StreamingResponse(
        _astream_workflow_generator(
            request.model_dump()["messages"],
            thread_id,
            request.resources or [],
            request.max_plan_iterations or 1,
            request.max_step_num or 3,
            request.max_search_results or 3,
            request.search_engine or "tavily",
            request.custom_search_repository or "",
            request.auto_accepted_plan or False,
            request.interrupt_feedback or "",
            request.mcp_settings if (mcp_enabled and request.mcp_settings) else {},
            request.enable_background_investigation or True,
            request.report_style or ReportStyle.ACADEMIC,
            request.enable_deep_thinking or False,
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
        event_stream_message["finish_reason"] = message_chunk.response_metadata.get(
            "finish_reason"
        )

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
    event_stream_message = _create_event_stream_message(
        message_chunk, message_metadata, thread_id, agent_name
    )

    if isinstance(message_chunk, ToolMessage):
        # Tool Message - Return the result of the tool call
        event_stream_message["tool_call_id"] = message_chunk.tool_call_id
        yield _make_event("tool_call_result", event_stream_message)
    elif isinstance(message_chunk, AIMessageChunk):
        # AI Message - Raw message tokens
        if hasattr(message_chunk, 'tool_calls') and message_chunk.tool_calls:
            # AI Message - Tool Call
            event_stream_message["tool_calls"] = message_chunk.tool_calls
            event_stream_message["tool_call_chunks"] = _process_tool_call_chunks(
                message_chunk.tool_call_chunks
            )
            yield _make_event("tool_calls", event_stream_message)
        elif hasattr(message_chunk, 'tool_call_chunks') and message_chunk.tool_call_chunks:
            # AI Message - Tool Call Chunks
            event_stream_message["tool_call_chunks"] = _process_tool_call_chunks(
                message_chunk.tool_call_chunks
            )
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
                if "__interrupt__" in event_data:
                    yield _create_interrupt_event(thread_id, event_data)
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
    search_engine: str,
    custom_search_repository: str,
    auto_accepted_plan: bool,
    interrupt_feedback: str,
    mcp_settings: dict,
    enable_background_investigation: bool,
    report_style: ReportStyle,
    enable_deep_thinking: bool,
):
    # Process initial messages
    for message in messages:
        if isinstance(message, dict) and "content" in message:
            _process_initial_messages(message, thread_id)

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
            "search_engine": search_engine,
            "custom_search_repository": custom_search_repository,
            "mcp_settings": mcp_settings,
            "report_style": report_style.value,
            "enable_deep_thinking": enable_deep_thinking,
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


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech using volcengine TTS API."""
    app_id = get_str_env("VOLCENGINE_TTS_APPID", "")
    if not app_id:
        raise HTTPException(status_code=400, detail="VOLCENGINE_TTS_APPID is not set")
    access_token = get_str_env("VOLCENGINE_TTS_ACCESS_TOKEN", "")
    if not access_token:
        raise HTTPException(
            status_code=400, detail="VOLCENGINE_TTS_ACCESS_TOKEN is not set"
        )

    try:
        cluster = get_str_env("VOLCENGINE_TTS_CLUSTER", "volcano_tts")
        voice_type = get_str_env("VOLCENGINE_TTS_VOICE_TYPE", "BV700_V2_streaming")

        tts_client = VolcengineTTS(
            appid=app_id,
            access_token=access_token,
            cluster=cluster,
            voice_type=voice_type,
        )
        # Call the TTS API
        result = tts_client.text_to_speech(
            text=request.text[:1024],
            encoding=request.encoding or "mp3",
            speed_ratio=request.speed_ratio or 1.0,
            volume_ratio=request.volume_ratio or 1.0,
            pitch_ratio=request.pitch_ratio or 1.0,
            text_type=request.text_type or "plain",
            with_frontend=request.with_frontend or 1,
            frontend_type=request.frontend_type or "unitTson",
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=str(result["error"]))

        # Decode the base64 audio data
        audio_data = base64.b64decode(result["audio_data"])

        # Return the audio file
        return Response(
            content=audio_data,
            media_type=f"audio/{request.encoding}",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=tts_output.{request.encoding}"
                )
            },
        )

    except Exception as e:
        logger.exception(f"Error in TTS endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


@app.post("/api/podcast/generate")
async def generate_podcast(request: GeneratePodcastRequest):
    try:
        report_content = request.content
        print(report_content)
        workflow = build_podcast_graph()
        # 创建正确的 PodcastState 输入
        from src.podcast.graph.state import PodcastState
        podcast_input: PodcastState = {
            "messages": [],  # MessagesState 需要 messages 字段
            "input": report_content,
            "output": None,
            "script": None,
            "audio_chunks": []
        }
        final_state = workflow.invoke(podcast_input)
        audio_bytes = final_state["output"]
        return Response(content=audio_bytes, media_type="audio/mp3")
    except Exception as e:
        logger.exception(f"Error occurred during podcast generation: {str(e)}")
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


@app.post("/api/prose/generate")
async def generate_prose(request: GenerateProseRequest):
    try:
        sanitized_prompt = request.prompt.replace("\r\n", "").replace("\n", "")
        logger.info(f"Generating prose for prompt: {sanitized_prompt}")
        workflow = build_prose_graph()
        # 创建正确的 ProseState 输入
        from src.prose.graph.state import ProseState
        prose_input: ProseState = {
            "messages": [],  # MessagesState 需要 messages 字段
            "content": request.prompt,
            "option": request.option,
            "command": request.command or "",
            "output": ""
        }
        events = workflow.astream(
            prose_input,
            stream_mode="messages",
            subgraphs=True,
        )
        return StreamingResponse(
            (f"data: {getattr(event[1][0], 'content', str(event[1][0]))}\n\n" async for agent, event in events if event and len(event) > 0),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.exception(f"Error occurred during prose generation: {str(e)}")
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

@app.post("/api/research/simple", response_model=SimpleResearchResponse)
async def simple_research(request: SimpleResearchRequest):
    """
    OpenAI格式的简化对话式研究接口：边搜边想，带上下文的对话式回答
    支持思考迭代和递归控制，不生成详细报告
    """
    import time
    start_time = time.time()
    
    # 生成唯一的对话 ID
    conversation_id = generate_conversation_id(model_prefix="chatcmpl")
    
    # 设置增强日志上下文
    enhanced_logger.set_session_context(
        session_id=conversation_id,
        user_query=request.messages[-1].get("content", "") if request.messages else ""
    )
    enhanced_logger.log_node_entry("simple_research", {
        "conversation_id": conversation_id,
        "messages_count": len(request.messages) if request.messages else 0,
        "max_search_results": request.max_search_results,
        "search_engine": request.search_engine,
        "enable_deep_thinking": request.enable_deep_thinking
    })
    
    try:
        # 验证messages格式
        if not request.messages or len(request.messages) == 0:
            raise HTTPException(status_code=400, detail="messages 不能为空")
        
        # 获取最后一条用户消息作为当前问题
        last_message = request.messages[-1]
        if last_message.get("role") != "user":
            raise HTTPException(status_code=400, detail="最后一条消息必须是用户消息")
        
        current_question = last_message.get("content", "")
        
        # 使用简化的流程进行对话式回答
        enhanced_logger.log_step_execution(
            step_number=1,
            step_title="对话式研究处理",
            step_type="conversational_research",
            agent_name="research_assistant"
        )
        
        answer, sources, thinking_steps = await _simple_conversational_research(
            messages=request.messages,
            conversation_id=conversation_id,
            max_search_results=request.max_search_results or 3,
            search_engine=request.search_engine or "custom_search",
            enable_deep_thinking=request.enable_deep_thinking or True,
            max_thinking_iterations=request.max_thinking_iterations or 2,
            max_recursion_limit=request.max_recursion_limit or 15
        )
        
        execution_time = time.time() - start_time
        
        # 记录工作流程摘要
        enhanced_logger.log_workflow_summary(
            total_duration=execution_time,
            nodes_executed=["simple_research", "conversational_research"],
            tools_used=["llm", "web_search"] if sources else ["llm"]
        )
        
        # 构建 ChatCompletionMessage
        assistant_message = ChatCompletionMessage(
            role="assistant",
            content=answer,
            research_metadata={
                "sources": sources,
                "thinking_steps": thinking_steps,
                "search_engine": request.search_engine or "custom_search",
                "max_search_results": request.max_search_results or 3
            }
        )
        
        # 构建 ChatCompletionChoice
        choice: ChatCompletionChoice = ChatCompletionChoice(
            index=0,
            message=assistant_message,
            finish_reason="stop",
            sources=sources,
            thinking_steps=thinking_steps
        )
        
        # 生成唯一ID和时间戳
        import time
        import uuid
        
        return SimpleResearchResponse(
            id=conversation_id,
            object="chat.completion",
            created=int(time.time()),
            model="deer-flow-research",
            choices=[choice],
            sources=sources,
            is_complete=True,
            execution_time=execution_time,
            thinking_steps=thinking_steps
        )
        
    except HTTPException:
        raise  # 重新抛出HTTP异常
    except Exception as e:
        logger.exception(f"Error in simple research endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR_DETAIL)


async def _simple_conversational_research(
    messages: List[Dict[str, str]],
    conversation_id: str,
    max_search_results: int,
    search_engine: str,
    enable_deep_thinking: bool,
    max_thinking_iterations: int,
    max_recursion_limit: int
) -> tuple[str, List[str], int]:
    """
    简化的对话式研究流程：边搜边想
    """
    from src.llms.llm import get_llm_by_type
    from src.tools import get_web_search_tool
    
    sources = []
    thinking_steps = 0
    
    # 获取搜索工具
    enhanced_logger.log_tool_call_start("search_tool_init", {
        "max_results": max_search_results,
        "engine": search_engine
    })
    search_tool = get_web_search_tool(max_search_results, search_engine, "")
    enhanced_logger.log_tool_call_end("search_tool_init", "工具初始化完成", 0.1)
    
    # 构建对话式研究助手的提示词
    system_prompt = """
你是一个智能的研究助手，善于进行对话式的研究和回答。

你的能力：
1. 当需要最新信息时，使用搜索工具获取相关资料
2. 基于搜索结果和你的知识进行综合分析
3. 提供自然、对话式的回答，就像在和用户直接交流

回答要求：
- 保持对话式的自然语调
- 不要生成正式的研究报告，而是简单直接的回答
- 如果需要更多信息，可以向用户提问
- 在回答末尾简单列出主要参考来源（如果有）
"""
    
    # 将系统提示词添加到消息列表开头
    conversation_messages = [{"role": "system", "content": system_prompt}] + messages
    
    # 获取LLM
    if enable_deep_thinking:
        enhanced_logger.log_llm_thinking("reasoning_llm", len(str(conversation_messages)), 0, 0)
        llm = get_llm_by_type("reasoning").bind_tools([search_tool])
    else:
        enhanced_logger.log_llm_thinking("basic_llm", len(str(conversation_messages)), 0, 0)
        llm = get_llm_by_type("basic").bind_tools([search_tool])
    
    # 进行多轮思考和搜索
    for iteration in range(max_thinking_iterations):
        thinking_steps += 1
        enhanced_logger.log_step_execution(
            step_number=iteration + 1,
            step_title=f"思考迭代 {iteration + 1}",
            step_type="llm_reasoning",
            agent_name="research_assistant"
        )
        enhanced_logger.logger.info(f"🔄 THINKING_ITERATION | {conversation_id}: 思考迭代 {iteration + 1}/{max_thinking_iterations}")
        
        try:
            # 调用LLM
            response = llm.invoke(
                conversation_messages,
                config={"recursion_limit": max_recursion_limit}
            )
            
            # 处理工具调用（搜索）
            tool_calls = getattr(response, 'tool_calls', None)
            if tool_calls:
                for tool_call in tool_calls:
                    if tool_call['name'] == search_tool.name:
                        search_query = tool_call['args'].get('query', messages[-1]['content'])
                        enhanced_logger.log_search_process(search_query, "web_search", 0)
                        enhanced_logger.logger.info(f"🔍 SEARCH_START | {conversation_id}: 执行搜索 - {search_query}")
                        
                        search_start_time = time.time()
                        search_results = search_tool.invoke(search_query)
                        search_duration = time.time() - search_start_time
                        
                        # 收集来源
                        results_count = 0
                        if isinstance(search_results, list):
                            results_count = len(search_results)
                            for result in search_results:
                                if isinstance(result, dict) and result.get('url'):
                                    sources.append(result['url'])
                        
                        enhanced_logger.log_search_process(search_query, "web_search", results_count)
                        enhanced_logger.log_tool_call_end("web_search", f"找到 {results_count} 条结果", search_duration)
                        
                        # 将搜索结果添加到对话中
                        search_context = f"搜索结果\uff1a{json.dumps(search_results, ensure_ascii=False, indent=2)}"
                        conversation_messages.append({
                            "role": "user", 
                            "content": f"基于以下搜索结果，请给出对话式回答：\n{search_context}"
                        })
                        
                        # 重新调用LLM生成最终回答
                        enhanced_logger.logger.info(f"💬 ANSWER_GENERATION | {conversation_id}: 基于搜索结果生成回答")
                        final_response = llm.invoke(
                            conversation_messages,
                            config={"recursion_limit": max_recursion_limit}
                        )
                        # 确保返回内容是字符串类型
                        final_content = final_response.content
                        if isinstance(final_content, list):
                            final_content = str(final_content)
                        elif not isinstance(final_content, str):
                            final_content = str(final_content)
                        
                        enhanced_logger.log_llm_thinking(
                            "research_assistant",
                            len(str(conversation_messages)),
                            len(final_content),
                            search_duration
                        )
                        
                        return final_content, sources, thinking_steps
            
            # 如果没有工具调用，直接返回回答
            # 确保返回内容是字符串类型
            response_content = response.content
            if isinstance(response_content, list):
                response_content = str(response_content)
            elif not isinstance(response_content, str):
                response_content = str(response_content)
            return response_content, sources, thinking_steps
            
        except Exception as e:
            enhanced_logger.logger.warning(f"⚠️ THINKING_ERROR | {conversation_id}: 思考迭代 {iteration + 1} 失败: {str(e)}")
            if iteration == max_thinking_iterations - 1:
                # 最后一次迭代，返回默认回答
                return f"抱歉，我在处理您的问题“{messages[-1]['content']}”时遇到了一些困难。请您再试一次或者提供更具体的信息。", [], thinking_steps
    
    # 如果所有迭代都失败，返回默认回答
    return f"对于您的问题'{messages[-1]['content']}'，我需要更多信息才能给出准确的回答。请您提供更具体的背景或者明确您最关心的方面。", [], thinking_steps


@app.post("/api/research/simple/stream")
async def simple_research_stream(request: SimpleResearchRequest):
    """
    流式版本的简化对话式研究接口：实时流式输出思考过程和回答
    支持SSE (Server-Sent Events) 实时推送每一步的检索、思考和处理过程
    """
    # 生成唯一的对话 ID
    conversation_id = generate_conversation_id(model_prefix="streamcmpl")
    
    enhanced_logger.set_session_context(
        session_id=conversation_id,
        user_query=request.messages[-1].get("content", "") if request.messages else ""
    )
    enhanced_logger.log_node_entry("simple_research_stream", {
        "conversation_id": conversation_id,
        "messages_count": len(request.messages) if request.messages else 0,
        "max_search_results": request.max_search_results,
        "search_engine": request.search_engine,
        "enable_deep_thinking": request.enable_deep_thinking
    })
    
    return StreamingResponse(
        _stream_simple_research_generator(
            request=request,
            conversation_id=conversation_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


async def _stream_simple_research_generator(
    request: SimpleResearchRequest,
    conversation_id: str
):
    """
    流式研究生成器：实时推送每一步的处理过程
    """
    import time
    import asyncio
    from src.llms.llm import get_llm_by_type
    from src.tools import get_web_search_tool
    
    start_time = time.time()
    sources = []
    thinking_steps = 0
    
    try:
        # 验证请求
        if not request.messages or len(request.messages) == 0:
            yield _make_stream_event("error", {"error": "messages 不能为空"})
            return
        
        last_message = request.messages[-1]
        if last_message.get("role") != "user":
            yield _make_stream_event("error", {"error": "最后一条消息必须是用户消息"})
            return
        
        current_question = last_message.get("content", "")
        enhanced_logger.log_search_process(current_question, "initial_question", 0)
        
        # 发送开始事件
        yield _make_stream_event("start", {
            "conversation_id": conversation_id,
            "question": current_question,
            "timestamp": int(time.time())
        })
        
        # 初始化工具和LLM
        enhanced_logger.log_tool_call_start("search_tool_init", {
            "max_results": request.max_search_results or 3,
            "engine": request.search_engine or "custom_search"
        })
        
        search_tool = get_web_search_tool(
            request.max_search_results or 3, 
            request.search_engine or "custom_search", 
            ""
        )
        
        enhanced_logger.log_tool_call_end("search_tool_init", "工具初始化完成", 0.1)
        
        # 构建对话上下文
        system_prompt = """
你是一个智能的研究助手，善于进行对话式的研究和回答。

你的能力：
1. 当需要最新信息时，使用搜索工具获取相关资料
2. 基于搜索结果和你的知识进行综合分析
3. 提供自然、对话式的回答，就像在和用户直接交流

回答要求：
- 保持对话式的自然语调
- 不要生成正式的研究报告，而是简单直接的回答
- 如果需要更多信息，可以向用户提问
- 在回答末尾简单列出主要参考来源（如果有）
"""
        
        conversation_messages = [{"role": "system", "content": system_prompt}] + request.messages
        
        # 获取LLM
        if request.enable_deep_thinking:
            enhanced_logger.log_llm_thinking("reasoning_llm", len(str(conversation_messages)), 0, 0)
            llm = get_llm_by_type("reasoning").bind_tools([search_tool])
        else:
            enhanced_logger.log_llm_thinking("basic_llm", len(str(conversation_messages)), 0, 0)
            llm = get_llm_by_type("basic").bind_tools([search_tool])
        
        # 发送思考开始事件
        yield _make_stream_event("thinking_start", {
            "iteration": 1,
            "model_type": "reasoning" if request.enable_deep_thinking else "basic"
        })
        
        # 开始思考迭代
        max_iterations = request.max_thinking_iterations or 2
        for iteration in range(max_iterations):
            thinking_steps += 1
            iteration_start = time.time()
            
            enhanced_logger.log_step_execution(
                step_number=iteration + 1,
                step_title=f"思考迭代 {iteration + 1}",
                step_type="llm_reasoning",
                agent_name="research_assistant"
            )
            
            yield _make_stream_event("thinking_iteration", {
                "iteration": iteration + 1,
                "total_iterations": max_iterations
            })
            
            try:
                # 调用LLM
                response = llm.invoke(
                    conversation_messages,
                    config={"recursion_limit": request.max_recursion_limit or 15}
                )
                
                iteration_duration = time.time() - iteration_start
                enhanced_logger.log_llm_thinking(
                    "research_assistant", 
                    len(str(conversation_messages)), 
                    len(str(response.content)), 
                    iteration_duration
                )
                
                # 检查是否有工具调用
                tool_calls = getattr(response, 'tool_calls', None)
                if tool_calls:
                    for tool_call in tool_calls:
                        if tool_call['name'] == search_tool.name:
                            search_query = tool_call['args'].get('query', current_question)
                            
                            enhanced_logger.log_search_process(search_query, "web_search", 0)
                            
                            # 发送搜索开始事件
                            yield _make_stream_event("search_start", {
                                "query": search_query,
                                "engine": request.search_engine or "custom_search"
                            })
                            
                            search_start = time.time()
                            search_results = search_tool.invoke(search_query)
                            search_duration = time.time() - search_start
                            
                            # 收集来源
                            results_count = 0
                            if isinstance(search_results, list):
                                results_count = len(search_results)
                                for result in search_results:
                                    if isinstance(result, dict) and result.get('url'):
                                        sources.append(result['url'])
                            
                            enhanced_logger.log_search_process(search_query, "web_search", results_count)
                            enhanced_logger.log_tool_call_end("web_search", f"找到 {results_count} 条结果", search_duration)
                            
                            # 发送搜索结果事件
                            yield _make_stream_event("search_results", {
                                "query": search_query,
                                "results_count": results_count,
                                "duration": search_duration,
                                "sources": sources[-results_count:] if sources else []
                            })
                            
                            # 将搜索结果添加到对话中
                            search_context = f"搜索结果：{json.dumps(search_results, ensure_ascii=False, indent=2)}"
                            conversation_messages.append({
                                "role": "user", 
                                "content": f"基于以下搜索结果，请给出对话式回答：\n{search_context}"
                            })
                            
                            # 发送生成回答开始事件
                            yield _make_stream_event("answer_generation_start", {
                                "has_search_context": True
                            })
                            
                            # 重新调用LLM生成最终回答
                            final_response = llm.invoke(
                                conversation_messages,
                                config={"recursion_limit": request.max_recursion_limit or 15}
                            )
                            
                            # 流式输出最终回答
                            final_content = str(final_response.content) if final_response.content else ""
                            yield _make_stream_event("answer_chunk", {"content": final_content})
                            
                            # 发送完成事件
                            total_duration = time.time() - start_time
                            enhanced_logger.log_workflow_summary(
                                total_duration=total_duration,
                                nodes_executed=["simple_research_stream", "llm_reasoning", "web_search"],
                                tools_used=["web_search", "llm"]
                            )
                            
                            yield _make_stream_event("complete", {
                                "conversation_id": conversation_id,
                                "answer": final_content,
                                "sources": sources,
                                "thinking_steps": thinking_steps,
                                "execution_time": total_duration,
                                "timestamp": int(time.time())
                            })
                            return
                
                # 如果没有工具调用，直接返回回答
                response_content = str(response.content) if response.content else ""
                
                yield _make_stream_event("answer_generation_start", {
                    "has_search_context": False
                })
                yield _make_stream_event("answer_chunk", {"content": response_content})
                
                total_duration = time.time() - start_time
                enhanced_logger.log_workflow_summary(
                    total_duration=total_duration,
                    nodes_executed=["simple_research_stream", "llm_reasoning"],
                    tools_used=["llm"]
                )
                
                yield _make_stream_event("complete", {
                    "conversation_id": conversation_id,
                    "answer": response_content,
                    "sources": sources,
                    "thinking_steps": thinking_steps,
                    "execution_time": total_duration,
                    "timestamp": int(time.time())
                })
                return
                
            except Exception as e:
                enhanced_logger.logger.warning(f"思考迭代 {iteration + 1} 失败: {str(e)}")
                yield _make_stream_event("thinking_error", {
                    "iteration": iteration + 1,
                    "error": str(e)
                })
                
                if iteration == max_iterations - 1:
                    # 最后一次迭代，返回默认回答
                    default_answer = f"抱歉，我在处理您的问题'{current_question}'时遇到了一些困难。请您再试一次或者提供更具体的信息。"
                    yield _make_stream_event("answer_chunk", {"content": default_answer})
                    
                    total_duration = time.time() - start_time
                    yield _make_stream_event("complete", {
                        "conversation_id": conversation_id,
                        "answer": default_answer,
                        "sources": sources,
                        "thinking_steps": thinking_steps,
                        "execution_time": total_duration,
                        "error": "部分处理失败",
                        "timestamp": int(time.time())
                    })
                    return
        
        # 如果所有迭代都没有返回结果
        default_answer = f"对于您的问题'{current_question}'，我需要更多信息才能给出准确的回答。请您提供更具体的背景或者明确您最关心的方面。"
        yield _make_stream_event("answer_chunk", {"content": default_answer})
        
        total_duration = time.time() - start_time
        yield _make_stream_event("complete", {
            "conversation_id": conversation_id,
            "answer": default_answer,
            "sources": sources,
            "thinking_steps": thinking_steps,
            "execution_time": total_duration,
            "timestamp": int(time.time())
        })
        
    except Exception as e:
        enhanced_logger.logger.exception(f"流式研究接口发生错误: {str(e)}")
        yield _make_stream_event("error", {
            "conversation_id": conversation_id,
            "error": str(e),
            "timestamp": int(time.time())
        })


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
