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


# 加载 yaml 的 SEARCH_BUDGET 段时，yaml 字段名与 Configuration 字段名完全一致（带 search_budget_ / researcher_ 前缀），
# 不再做映射。仅保留白名单避免误激活同名字段。
_SEARCH_BUDGET_ALLOWED_FIELDS = {
    "search_budget_max_calls",
    "search_budget_max_tokens",
    "search_budget_hard_limit",
    "search_budget_token_chars_ratio",
    "researcher_recursion_limit",
}

# SEARCH_MAX_RESULTS 段中允许的工具名
_SEARCH_MAX_RESULTS_ALLOWED_TOOLS = {
    "online_search",
    "bocomsearch",
    "searchknowledge_standard",
    "vector_search",
}


def _load_search_budget_yaml() -> dict:
    """从当前激活的 yaml (conf.yaml / conf.internal.yaml) 加载 SEARCH_BUDGET 段。

    yaml 字段名已与 Configuration 字段名对齐，无需映射。缺失或解析失败时返回空 dict。
    使用 lazy import 避免循环依赖。
    """
    try:
        from src.llms.llm import _get_config_file_path
        from src.config import load_yaml_config
        raw = load_yaml_config(_get_config_file_path()).get("SEARCH_BUDGET", {}) or {}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"读取 SEARCH_BUDGET 配置失败，将使用默认值: {e}")
        return {}
    result: dict = {}
    for key, val in raw.items():
        if val is None:
            continue
        if key in _SEARCH_BUDGET_ALLOWED_FIELDS:
            result[key] = val
        else:
            logger.warning(
                f"SEARCH_BUDGET 中的未知字段 '{key}' 已忽略（请使用带前缀的 Configuration 字段名）"
            )
    return result


def _load_search_max_results_yaml() -> dict:
    """从当前激活的 yaml 加载 SEARCH_MAX_RESULTS 段，支持全局默认 + 按工具精细化配置。

    YAML 格式:
        SEARCH_MAX_RESULTS:
          default: 10
          online_search: 10
          bocomsearch: 10
          searchknowledge_standard: 5

    返回映射到 Configuration 字段名的 dict:
        {
            "max_search_results": 10,                           # default → 全局
            "max_search_results_online_search": 10,             # 按工具
            "max_search_results_bocomsearch": 10,
            "max_search_results_searchknowledge_standard": 5,
        }
    """
    try:
        from src.llms.llm import _get_config_file_path
        from src.config import load_yaml_config
        raw = load_yaml_config(_get_config_file_path()).get("SEARCH_MAX_RESULTS", {}) or {}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"读取 SEARCH_MAX_RESULTS 配置失败，将使用默认值: {e}")
        return {}
    result: dict = {}
    for key, val in raw.items():
        if val is None:
            continue
        if key == "default":
            result["max_search_results"] = val
        elif key in _SEARCH_MAX_RESULTS_ALLOWED_TOOLS:
            result[f"max_search_results_{key}"] = val
        else:
            logger.warning(
                f"SEARCH_MAX_RESULTS 中的未知工具 '{key}' 已忽略"
                f"（支持的工具: {', '.join(sorted(_SEARCH_MAX_RESULTS_ALLOWED_TOOLS))}）"
            )
    return result


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
    max_search_results: int = 10  # 全局默认搜索返回条数
    max_search_results_online_search: int = 0  # 互联网搜索返回条数，0=使用全局默认
    max_search_results_bocomsearch: int = 0  # 交行知识库返回条数，0=使用全局默认
    max_search_results_searchknowledge_standard: int = 0  # EUVD检索返回条数，0=使用全局默认
    max_search_results_vector_search: int = 0  # 向量检索返回条数，0=使用全局默认
    max_iteration: int = 5  # Maximum number of iterations for iterative research node
    search_engine: str = "custom_search"  # Search engine to use
    use_budget_controlled_online_search: bool = True  # 是否使用Budget控制的在线检索
    use_budget_controlled_bocom_search: bool = True   # 是否使用Budget控制的交行搜索
    mcp_settings: dict = None  # MCP settings, including dynamic loaded tools
    report_style: str = ReportStyle.ACADEMIC.value  # Report style
    enable_deep_thinking: bool = False  # Whether to enable deep thinking
    reporter_model: str = ""  # Selected reporter model key from REPORTER_MODEL_OPTIONS
    system_context: str = ""  # 系统背景上下文，通过State传递给各节点，在Prompt Template中按需使用
    
    # 搜索预算控制配置
    search_budget_max_calls: int = 5  # 最大搜索调用次数
    search_budget_max_tokens: int = 10000  # 最大token数量（预警阈值）
    search_budget_hard_limit: int = 14000  # 硬token限制（强制停止）
    search_budget_token_chars_ratio: float = 2.5  # Token估算比例（字符数/token，纯中文场景）

    # researcher 节点每步的搜索工具调用预算（也作为 LangGraph recursion 的软建议值）
    researcher_recursion_limit: int = 5

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig.

        配置优先级：env > configurable > yaml(SEARCH_BUDGET + SEARCH_MAX_RESULTS) > dataclass 默认值
        """
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        yaml_values = _load_search_budget_yaml()
        yaml_values.update(_load_search_max_results_yaml())

        values: dict[str, Any] = {}
        for f in fields(cls):
            if not f.init:
                continue
            env_val = os.environ.get(f.name.upper())
            cfg_val = configurable.get(f.name)
            yaml_val = yaml_values.get(f.name)
            if env_val is not None and env_val != "":
                values[f.name] = env_val
            elif cfg_val is not None:
                values[f.name] = cfg_val
            elif yaml_val is not None:
                values[f.name] = yaml_val

        return cls(**{k: v for k, v in values.items() if v not in (None, "")})

    def get_max_results(self, tool_name: str) -> int:
        """获取指定搜索工具的最大返回条数。

        优先级：按工具配置 > 全局默认（max_search_results）
        tool_name 支持: online_search, bocomsearch, searchknowledge_standard, vector_search

        Args:
            tool_name: 工具名称

        Returns:
            该工具应使用的最大返回条数
        """
        per_tool_attr = f"max_search_results_{tool_name}"
        per_tool_val = getattr(self, per_tool_attr, 0)
        if per_tool_val and per_tool_val > 0:
            return per_tool_val
        return self.max_search_results
