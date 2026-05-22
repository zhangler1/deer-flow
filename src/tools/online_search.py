# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
联网搜索工具
基于 CustomSearchTool 实现，固定使用 online-search repository

环境变量（可选）：
- ONLINE_SEARCH_MAX_RESULTS 最大返回条数（默认 2）

返回条数优先级：调用显式传入 max_results > 环境变量 ONLINE_SEARCH_MAX_RESULTS > 硬编码默认 2
"""

import logging
import os
from typing import Optional

from src.tools.custom_search import CustomSearchTool
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger

_DEFAULT_MAX_RESULTS_FALLBACK = 2


def _default_max_results() -> int:
    """最大返回条数：env ONLINE_SEARCH_MAX_RESULTS > 硬编码默认 2"""
    try:
        return int(os.getenv("ONLINE_SEARCH_MAX_RESULTS", str(_DEFAULT_MAX_RESULTS_FALLBACK)))
    except (TypeError, ValueError):
        return _DEFAULT_MAX_RESULTS_FALLBACK


def online_search_tool(max_results: Optional[int] = None) -> CustomSearchTool:
    """
    创建联网搜索工具实例

    该工具是 CustomSearchTool 的封装版本，固定使用 online-search repository
    用于进行互联网公开信息搜索

    Args:
        max_results: 最大返回结果数。
            优先级：调用显式传入 > env ONLINE_SEARCH_MAX_RESULTS > 默认 2

    Returns:
        CustomSearchTool: 配置好的联网搜索工具实例
    """
    effective = max_results if (max_results and max_results > 0) else _default_max_results()
    tool = CustomSearchTool(
        repository="online_search",
        max_results=effective
    )
    # 自定义工具名称和描述，让模型能够识别这是互联网搜索工具
    tool.name = "online_search"
    tool.description = "搜索互联网公开信息。适用于查询最新新闻、公开资讯、行业动态、学术文献等互联网内容。输入应该是搜索查询字符串。"
    return tool


# 为了保持一致性，也提供一个函数式的调用接口
def call_online_search(query: str, max_results: Optional[int] = None):
    """
    直接调用联网搜索

    Args:
        query: 搜索查询字符串
        max_results: 最大返回结果数。
            优先级：调用显式传入 > env ONLINE_SEARCH_MAX_RESULTS > 默认 2

    Returns:
        搜索结果列表
    """
    tool = online_search_tool(max_results=max_results)
    return tool._run(query)
