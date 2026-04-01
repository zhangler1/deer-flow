# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""工具结果压缩配置模块"""

from typing import Literal
from pydantic import BaseModel, Field

TriggerType = Literal["messages", "tokens"]


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


class ToolCompressionConfig(BaseModel):
    """工具结果压缩配置"""
    enabled: bool = Field(default=False, description="是否启用")
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
        description="压缩模型配置"
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
