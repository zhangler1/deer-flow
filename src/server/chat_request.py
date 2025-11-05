# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import List, Optional, Union, Dict, Any

from pydantic import BaseModel, Field

from src.config.report_style import ReportStyle
from src.rag.retriever import Resource


class ContentItem(BaseModel):
    type: str = Field(..., description="The type of content (text, image, etc.)")
    text: Optional[str] = Field(None, description="The text content if type is 'text'")
    image_url: Optional[str] = Field(
        None, description="The image URL if type is 'image'"
    )


class ChatMessage(BaseModel):
    role: str = Field(
        ..., description="The role of the message sender (user or assistant)"
    )
    content: Union[str, List[ContentItem]] = Field(
        ...,
        description="The content of the message, either a string or a list of content items",
    )


class ChatRequest(BaseModel):
    messages: Optional[List[ChatMessage]] = Field(
        [], description="History of messages between the user and the assistant"
    )
    resources: Optional[List[Resource]] = Field(
        [], description="Resources to be used for the research"
    )
    debug: Optional[bool] = Field(False, description="Whether to enable debug logging")
    thread_id: Optional[str] = Field(
        "__default__", description="A specific conversation identifier"
    )
    max_plan_iterations: Optional[int] = Field(
        1, description="The maximum number of plan iterations"
    )
    max_step_num: Optional[int] = Field(
        3, description="The maximum number of steps in a plan"
    )
    max_search_results: Optional[int] = Field(
        3, description="The maximum number of search results"
    )
    search_engine: Optional[str] = Field(
        "custom_search", description="The search engine to use (tavily, duckduckgo, brave_search, arxiv, wikipedia, custom_search)"
    )
    custom_search_repository: Optional[str] = Field(
        None, description="The repository ID for custom search engine"
    )
    auto_accepted_plan: Optional[bool] = Field(
        False, description="Whether to automatically accept the plan"
    )
    interrupt_feedback: Optional[str] = Field(
        None, description="Interrupt feedback from the user on the plan"
    )
    mcp_settings: Optional[dict] = Field(
        None, description="MCP settings for the chat request"
    )
    enable_background_investigation: Optional[bool] = Field(
        True, description="Whether to get background investigation before plan"
    )
    report_style: Optional[ReportStyle] = Field(
        ReportStyle.ACADEMIC, description="The style of the report"
    )
    enable_deep_thinking: Optional[bool] = Field(
        False, description="Whether to enable deep thinking"
    )


class TTSRequest(BaseModel):
    text: str = Field(..., description="The text to convert to speech")
    voice_type: Optional[str] = Field(
        "BV700_V2_streaming", description="The voice type to use"
    )
    encoding: Optional[str] = Field("mp3", description="The audio encoding format")
    speed_ratio: Optional[float] = Field(1.0, description="Speech speed ratio")
    volume_ratio: Optional[float] = Field(1.0, description="Speech volume ratio")
    pitch_ratio: Optional[float] = Field(1.0, description="Speech pitch ratio")
    text_type: Optional[str] = Field("plain", description="Text type (plain or ssml)")
    with_frontend: Optional[int] = Field(
        1, description="Whether to use frontend processing"
    )
    frontend_type: Optional[str] = Field("unitTson", description="Frontend type")


class GeneratePodcastRequest(BaseModel):
    content: str = Field(..., description="The content of the podcast")


class GeneratePPTRequest(BaseModel):
    content: str = Field(..., description="The content of the ppt")


class GenerateProseRequest(BaseModel):
    prompt: str = Field(..., description="The content of the prose")
    option: str = Field(..., description="The option of the prose writer")
    command: Optional[str] = Field(
        "", description="The user custom command of the prose writer"
    )


class EnhancePromptRequest(BaseModel):
    prompt: str = Field(..., description="The original prompt to enhance")
    context: Optional[str] = Field(
        "", description="Additional context about the intended use"
    )
    report_style: Optional[str] = Field(
        "academic", description="The style of the report"
    )


class SimpleResearchRequest(BaseModel):
    """简化研究请求模型 - 使用完整的 LangGraph 工作流（支持智能路由）"""
    messages: List[Dict[str, str]] = Field(..., description="对话消息列表，OpenAI格式")
    
    # === 与 /api/chat/stream 完全一致的参数配置 ===
    resources: Optional[List[Resource]] = Field([], description="资源列表")
    debug: Optional[bool] = Field(False, description="是否启用调试日志")
    thread_id: Optional[str] = Field("__default__", description="会话标识符")
    max_plan_iterations: Optional[int] = Field(1, description="最大计划迭代次数")
    max_step_num: Optional[int] = Field(3, description="计划中的最大步骤数")
    max_search_results: Optional[int] = Field(3, description="最大搜索结果数")
    search_engine: Optional[str] = Field("custom_search", description="搜索引擎 (tavily, duckduckgo, brave_search, arxiv, wikipedia, custom_search)")
    custom_search_repository: Optional[str] = Field(None, description="自定义搜索仓库ID")
    auto_accepted_plan: Optional[bool] = Field(True, description="是否自动接受计划")
    interrupt_feedback: Optional[str] = Field(None, description="用户对计划的中断反馈")
    mcp_settings: Optional[dict] = Field(None, description="MCP设置")
    enable_background_investigation: Optional[bool] = Field(True, description="是否启用背景调研")
    report_style: Optional[ReportStyle] = Field(ReportStyle.ACADEMIC, description="报告风格")
    enable_deep_thinking: Optional[bool] = Field(False, description="是否启用深度思考")


class ChatCompletionMessage(BaseModel):
    role: str = Field(..., description="消息角色，如 'assistant'")
    content: str = Field(..., description="消息内容")
    # 扩展字段，包含研究相关的元数据
    research_metadata: Dict[str, Any] = Field(default_factory=dict, description="研究相关元数据")

class ChatCompletionChoice(BaseModel):
    index: int = Field(..., description="选择项索引")
    message: ChatCompletionMessage = Field(..., description="消息内容")
    finish_reason: str = Field(..., description="结束原因，如 'stop', 'length', 'tool_calls' 等")
    # 研究特有的字段
    sources: List[str] = Field(default_factory=list, description="参考来源")
    thinking_steps: Optional[int] = Field(0, description="实际思考步骤数")

class SimpleResearchResponse(BaseModel):
    id: str = Field(..., description="对话的唯一标识符")
    object: str = Field("chat.completion", description="对象类型，固定为 'chat.completion'")
    created: int = Field(..., description="创建时间的 Unix 时间戳（秒）")
    model: str = Field(..., description="生成响应的模型名称")
    choices: List[ChatCompletionChoice] = Field(..., description="模型生成的选择项列表")

    sources: List[str] = Field(default_factory=list, description="参考来源")
    is_complete: bool = Field(True, description="是否完成回答")
    execution_time: float = Field(..., description="执行时间(秒)")
    thinking_steps: Optional[int] = Field(0, description="实际思考步骤数")
    # 新增plan相关字段
    research_plan: Optional[Dict[str, Any]] = Field(None, description="研究计划详情")
    plan_generated: Optional[bool] = Field(False, description="是否生成了计划")
