# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
from dataclasses import dataclass, field, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig

from src.config.report_style import ReportStyle
from src.rag.retriever import Resource
from src.config.loader import get_str_env, get_int_env, get_bool_env

logger = logging.getLogger(__name__)


def get_recursion_limit(default: int = 25) -> int:
    """Get the recursion limit from environment variable or use default.

    Args:
        default: Default recursion limit if environment variable is not set or invalid

    Returns:
        int: The recursion limit to use
    """
    env_value_str = get_str_env("AGENT_RECURSION_LIMIT", str(default))
    parsed_limit = get_int_env("AGENT_RECURSION_LIMIT", default)

    if parsed_limit > 0:
        logger.info(f"Recursion limit set to: {parsed_limit}")
        return parsed_limit
    else:
        logger.warning(
            f"AGENT_RECURSION_LIMIT value '{env_value_str}' (parsed as {parsed_limit}) is not positive. "
            f"Using default value {default}."
        )
        return default


@dataclass(kw_only=True)
class Configuration:
    """The configurable fields."""

    resources: list[Resource] = field(
        default_factory=list
    )  # Resources to be used for the research
    max_plan_iterations: int = 2  # Maximum number of plan iterations
    max_step_num: int = 5  # Maximum number of steps in a plan
    max_search_results: int = 2  # Maximum number of search results
    max_iteration: int = 5  # Maximum number of iterations for iterative research node
    search_engine: str = "custom_search"  # Search engine to use
    use_budget_controlled_online_search: bool = True  # 是否使用Budget控制的在线检索
    use_budget_controlled_bocom_search: bool = True   # 是否使用Budget控制的交行搜索
    mcp_settings: dict = None  # MCP settings, including dynamic loaded tools
    report_style: str = ReportStyle.ACADEMIC.value  # Report style
    enable_deep_thinking: bool = False  # Whether to enable deep thinking
    system_context: str = ""  # 系统背景上下文，通过State传递给各节点，在Prompt Template中按需使用
    
    # 搜索预算控制配置
    search_budget_max_calls: int = 5  # 最大搜索调用次数
    search_budget_max_tokens: int = 10000  # 最大token数量（预警阈值）
    search_budget_hard_limit: int = 14000  # 硬token限制（强制停止）
    search_budget_token_chars_ratio: float = 2.5  # Token估算比例（字符数/token，纯中文场景）

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})
