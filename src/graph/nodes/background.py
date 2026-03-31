# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
背景调研节点模块

包含：
- background_investigation_node: 背景调研节点（在规划前进行初步搜索）
"""

import json
import logging
import time

from langchain_core.runnables import RunnableConfig

from src.config.configuration import Configuration
from src.tools import online_search_tool
from src.tools.search import LoggedTavilySearch
from src.utils.enhanced_logger import get_enhanced_logger

from src.config import SELECTED_SEARCH_ENGINE, SearchEngine

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.background')


def background_investigation_node(state, config: RunnableConfig):
    """背景调研节点 - 在规划前进行初步搜索，为规划提供上下文"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | background_investigation | 开始执行背景调研节点")
    
    configurable = Configuration.from_runnable_config(config)
    query = state.get("research_topic")
    
    enhanced_logger.log_search_process(query, "background_investigation")
    
    background_investigation_results = None
    if SELECTED_SEARCH_ENGINE == SearchEngine.TAVILY.value:
        enhanced_logger.logger.info(f"🔍 使用Tavily搜索引擎进行背景调研 | 查询: '{query}'")
        searched_content = LoggedTavilySearch(
            max_results=configurable.max_search_results
        ).invoke(query)
        # check if the searched_content is a tuple, then we need to unpack it
        if isinstance(searched_content, tuple):
            searched_content = searched_content[0]
        if isinstance(searched_content, list):
            enhanced_logger.logger.info(f"🔍 Tavily搜索完成 | 结果数: {len(searched_content)}")
            background_investigation_results = [
                f"## {elem['title']}\n\n{elem['content']}" for elem in searched_content
            ]
            result = {
                "background_investigation_results": "\n\n".join(
                    background_investigation_results
                )
            }
        else:
            logger.error(
                f"Tavily search returned malformed response: {searched_content}"
            )
            result = {"background_investigation_results": None}
    else:
        enhanced_logger.logger.info(f"🔍 使用online_search进行背景调研 | 查询: '{query}'")
        background_investigation_results = online_search_tool(
            max_results=configurable.max_search_results
        ).invoke(query)
        result = {
            "background_investigation_results": json.dumps(
                background_investigation_results, ensure_ascii=False
            )
        }
        
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | background_investigation | 节点执行完成 | 耗时: {duration:.2f}s")
    return result
