# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import time
from typing import List, Optional

# DuckDuckGo / Brave / Arxiv / Wikipedia 搜索工具依赖 langchain_community
# 对齐 2.0：这些工具已注释，如需使用请取消注释并安装 langchain-community
# try:
#     from langchain_community.tools import (
#         BraveSearch,
#         DuckDuckGoSearchResults,
#         WikipediaQueryRun,
#     )
#     from langchain_community.tools.arxiv import ArxivQueryRun
#     from langchain_community.utilities import (
#         ArxivAPIWrapper,
#         BraveSearchWrapper,
#         WikipediaAPIWrapper,
#     )
#     HAS_LANGCHAIN_COMMUNITY = True
# except ImportError:
#     HAS_LANGCHAIN_COMMUNITY = False
HAS_LANGCHAIN_COMMUNITY = False
BraveSearch = None  # type: ignore[misc, assignment]
DuckDuckGoSearchResults = None  # type: ignore[misc, assignment]
WikipediaQueryRun = None  # type: ignore[misc, assignment]
ArxivQueryRun = None  # type: ignore[misc, assignment]
ArxivAPIWrapper = None  # type: ignore[misc, assignment]
BraveSearchWrapper = None  # type: ignore[misc, assignment]
WikipediaAPIWrapper = None  # type: ignore[misc, assignment]
SecretStr = None  # type: ignore[misc, assignment]  # 仅 Brave 使用，已注释

from src.config import SELECTED_SEARCH_ENGINE, SearchEngine, load_yaml_config
from src.tools.decorators import create_logged_tool
from src.tools.tavily_search.tavily_search_results_with_images import (
    TavilySearchWithImages,
)
from src.tools.custom_search import get_custom_search_tool
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger

# Tavily 已迁移到 tavily-python（对齐 2.0），不再依赖 langchain_community
LoggedTavilySearch = create_logged_tool(TavilySearchWithImages)

# langchain_community 工具已注释（对齐 2.0），如需使用请取消上方导入注释并安装 langchain-community
LoggedDuckDuckGoSearch = None
LoggedBraveSearch = None
LoggedArxivSearch = None
LoggedWikipediaSearch = None


def get_search_config():
    config = load_yaml_config("conf.yaml")
    search_config = config.get("SEARCH_ENGINE", {})
    return search_config


# Get the selected search tool
def get_web_search_tool(max_search_results: int, engine: Optional[str] = None):
    start_time = time.time()
    search_config = get_search_config()
    
    # Use provided engine, or from config file, or fall back to environment variable
    selected_engine = engine or search_config.get("engine") or SELECTED_SEARCH_ENGINE
    
    logger.info(f"🔧 TOOL_INIT | web_search | 初始化搜索工具 | 引擎: {selected_engine} | 最大结果数: {max_search_results}")
    logger.info(f"Using search engine: {selected_engine}")

    if selected_engine == SearchEngine.TAVILY.value:
        if not LoggedTavilySearch:
            raise ValueError("Tavily 不可用（tavily-python 未安装或 TAVILY_API_KEY 未配置），请切换搜索引擎")
        # Only get and apply include/exclude domains for Tavily
        include_domains: Optional[List[str]] = search_config.get("include_domains", [])
        exclude_domains: Optional[List[str]] = search_config.get("exclude_domains", [])

        logger.info(
            f"🔧 TOOL_CONFIG | Tavily搜索配置 | 包含域名: {include_domains} | 排除域名: {exclude_domains}"
        )
        logger.info(
            f"Tavily search configuration loaded: include_domains={include_domains}, exclude_domains={exclude_domains}"
        )

        tool = LoggedTavilySearch(
            name="web_search",
            max_results=max_search_results,
            include_raw_content=True,
            include_images=True,
            include_image_descriptions=True,
            include_domains=include_domains or [],
            exclude_domains=exclude_domains or [],
        )
        duration = time.time() - start_time
        logger.info(f"🔧 TOOL_READY | Tavily搜索工具就绪 | 耗时: {duration:.2f}s")
        return tool
    # 以下搜索引擎依赖 langchain_community，对齐 2.0 已注释
    # 如需启用，请取消文件顶部 langchain_community 导入注释并安装 langchain-community
    elif selected_engine == SearchEngine.DUCKDUCKGO.value:
        raise ValueError("DuckDuckGo 已禁用（对齐 2.0），如需使用请取消 search.py 中 langchain_community 导入注释")
    elif selected_engine == SearchEngine.BRAVE_SEARCH.value:
        raise ValueError("Brave 已禁用（对齐 2.0），如需使用请取消 search.py 中 langchain_community 导入注释")
    elif selected_engine == SearchEngine.ARXIV.value:
        raise ValueError("Arxiv 已禁用（对齐 2.0），如需使用请取消 search.py 中 langchain_community 导入注释")
    elif selected_engine == SearchEngine.WIKIPEDIA.value:
        raise ValueError("Wikipedia 已禁用（对齐 2.0），如需使用请取消 search.py 中 langchain_community 导入注释")
    elif selected_engine == SearchEngine.CUSTOM_SEARCH.value:
        # 使用默认 repository 的自定义搜索引擎（repository 配置已废弃）
        tool = get_custom_search_tool(max_results=max_search_results)
        duration = time.time() - start_time
        logger.info(f"🔧 TOOL_READY | 默认自定义搜索工具就绪 | 耗时: {duration:.2f}s")
        return tool
    else:
        logger.error(f"❌ TOOL_ERROR | 不支持的搜索引擎: {selected_engine}")
        raise ValueError(f"Unsupported search engine: {selected_engine}")
