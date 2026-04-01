# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""工具结果压缩配置模块

支持两种压缩模式：
1. truncate: 截断模式 - 直接截断工具返回内容
2. summarize: 大模型摘要模式 - 使用 LLM 将工具返回总结成一段文字
"""

from typing import Literal
from pydantic import BaseModel, Field

TriggerType = Literal["messages", "tokens"]
CompressionMode = Literal["truncate", "summarize"]


class TriggerCondition(BaseModel):
    """触发条件"""
    type: TriggerType = Field(description="触发类型")
    value: int = Field(description="触发阈值")


class KeepStrategy(BaseModel):
    """保留策略"""
    recent_tool_messages: int = Field(
        default=3,
        description="保留最近 N 条工具消息的完整内容"
    )
    max_content_per_tool: int = Field(
        default=500,
        description="每条工具消息保留的最大字符数"
    )


class ModelConfig(BaseModel):
    """压缩模型配置"""
    name: str | None = Field(default=None, description="模型名称")
    temperature: float = Field(default=0.3, description="温度参数")


class SummarizeConfig(BaseModel):
    """大模型摘要配置"""
    # 摘要提示词模板，{content} 会被替换为工具返回内容
    prompt: str = Field(
        default=(
            "请将以下工具调用返回结果压缩成一段简洁的摘要，"
            "保留关键信息和数据，去除冗余内容。\n\n"
            "工具返回内容：\n{content}\n\n"
            "摘要："
        ),
        description="摘要提示词模板，{content} 会被替换为工具返回内容"
    )
    # 摘要最大长度（字符数）
    max_summary_length: int = Field(
        default=500,
        description="摘要最大长度（字符数）"
    )
    # 是否保留原始工具名称
    keep_tool_name: bool = Field(
        default=True,
        description="是否在摘要中保留原始工具名称"
    )


class ToolCompressionConfig(BaseModel):
    """工具结果压缩配置"""
    enabled: bool = Field(default=False, description="是否启用")
    
    # 压缩模式：truncate（截断）或 summarize（大模型摘要）
    mode: CompressionMode = Field(
        default="truncate",
        description="压缩模式：truncate（截断）或 summarize（大模型摘要）"
    )
    
    trigger: list[TriggerCondition] = Field(
        default_factory=list,
        description="触发条件列表"
    )
    keep: KeepStrategy = Field(
        default_factory=KeepStrategy,
        description="保留策略"
    )
    model: ModelConfig = Field(
        default_factory=ModelConfig,
        description="压缩模型配置（用于摘要模式）"
    )
    summarize: SummarizeConfig = Field(
        default_factory=SummarizeConfig,
        description="大模型摘要配置"
    )


# 全局配置实例
_config: ToolCompressionConfig | None = None


def get_tool_compression_config() -> ToolCompressionConfig:
    """获取工具压缩配置"""
    global _config
    if _config is None:
        _config = ToolCompressionConfig()
    return _config


def set_tool_compression_config(config: ToolCompressionConfig):
    """设置工具压缩配置"""
    global _config
    _config = config


def load_tool_compression_config_from_dict(config_dict: dict):
    """从字典加载配置"""
    config = ToolCompressionConfig(**config_dict)
    set_tool_compression_config(config)
    return config
