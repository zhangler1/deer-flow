# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
联网搜索工具
基于 CustomSearchTool 实现，固定使用 online-search repository
"""

import logging
from typing import Optional

from src.tools.custom_search import CustomSearchTool

logger = logging.getLogger(__name__)


def online_search_tool(max_results: int = 10) -> CustomSearchTool:
    """
    创建联网搜索工具实例
    
    该工具是 CustomSearchTool 的封装版本，固定使用 online-search repository
    用于进行互联网公开信息搜索
    
    Args:
        max_results: 最大返回结果数，默认 10
        
    Returns:
        CustomSearchTool: 配置好的联网搜索工具实例
    """
    tool = CustomSearchTool(
        repository="online-search",
        max_results=max_results
    )
    # 自定义工具名称和描述，让模型能够识别这是互联网搜索工具
    tool.name = "online_search"
    tool.description = "搜索互联网公开信息。适用于查询最新新闻、公开资讯、行业动态、学术文献等互联网内容。输入应该是搜索查询字符串。"
    return tool


# 为了保持一致性，也提供一个函数式的调用接口
def call_online_search(query: str, max_results: int = 10):
    """
    直接调用联网搜索
    
    Args:
        query: 搜索查询字符串
        max_results: 最大返回结果数
        
    Returns:
        搜索结果列表
    """
    tool = online_search_tool(max_results=max_results)
    return tool._run(query)
