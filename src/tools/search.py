# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import time
from typing import List, Optional

from langchain_community.tools import (
    BraveSearch,
    DuckDuckGoSearchResults,
    WikipediaQueryRun,
)
from langchain_community.tools.arxiv import ArxivQueryRun
from langchain_community.utilities import (
    ArxivAPIWrapper,
    BraveSearchWrapper,
    WikipediaAPIWrapper,
)
from pydantic import SecretStr

from src.config import SELECTED_SEARCH_ENGINE, SearchEngine, load_yaml_config
from src.tools.decorators import create_logged_tool
from src.tools.tavily_search.tavily_search_results_with_images import (
    TavilySearchWithImages,
)
from src.tools.custom_search import get_custom_search_tool, create_custom_search_with_repository
from src.utils.enhanced_logger import get_enhanced_logger

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('tools.search')

# Create logged versions of the search tools
LoggedTavilySearch = create_logged_tool(TavilySearchWithImages)
LoggedDuckDuckGoSearch = create_logged_tool(DuckDuckGoSearchResults)
LoggedBraveSearch = create_logged_tool(BraveSearch)
LoggedArxivSearch = create_logged_tool(ArxivQueryRun)
LoggedWikipediaSearch = create_logged_tool(WikipediaQueryRun)


def get_search_config():
    config = load_yaml_config("conf.yaml")
    search_config = config.get("SEARCH_ENGINE", {})
    return search_config


# Get the selected search tool
def get_web_search_tool(max_search_results: int, engine: Optional[str] = None, repository: Optional[str] = None):
    start_time = time.time()
    search_config = get_search_config()
    
    # Use provided engine, or from config file, or fall back to environment variable
    selected_engine = engine or search_config.get("engine") or SELECTED_SEARCH_ENGINE
    
    enhanced_logger.logger.info(f"🔧 TOOL_INIT | web_search | 初始化搜索工具 | 引擎: {selected_engine} | 最大结果数: {max_search_results}")
    logger.info(f"Using search engine: {selected_engine}")

    if selected_engine == SearchEngine.TAVILY.value:
        # Only get and apply include/exclude domains for Tavily
        include_domains: Optional[List[str]] = search_config.get("include_domains", [])
        exclude_domains: Optional[List[str]] = search_config.get("exclude_domains", [])

        enhanced_logger.logger.info(
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
        enhanced_logger.logger.info(f"🔧 TOOL_READY | Tavily搜索工具就绪 | 耗时: {duration:.2f}s")
        return tool
    elif selected_engine == SearchEngine.DUCKDUCKGO.value:
        tool = LoggedDuckDuckGoSearch(
            name="web_search",
            num_results=max_search_results,
        )
        duration = time.time() - start_time
        enhanced_logger.logger.info(f"🔧 TOOL_READY | DuckDuckGo搜索工具就绪 | 耗时: {duration:.2f}s")
        return tool
    elif selected_engine == SearchEngine.BRAVE_SEARCH.value:
        tool = LoggedBraveSearch(
            name="web_search",
            search_wrapper=BraveSearchWrapper(
                api_key=SecretStr(os.getenv("BRAVE_SEARCH_API_KEY", "")),
                search_kwargs={"count": max_search_results},
            ),
        )
        duration = time.time() - start_time
        enhanced_logger.logger.info(f"🔧 TOOL_READY | Brave搜索工具就绪 | 耗时: {duration:.2f}s")
        return tool
    elif selected_engine == SearchEngine.ARXIV.value:
        return LoggedArxivSearch(
            name="web_search",
            api_wrapper=ArxivAPIWrapper(
                top_k_results=max_search_results,
                load_max_docs=max_search_results,
                load_all_available_meta=True,
                arxiv_search=None,
                arxiv_exceptions=None,
            ),
        )
    elif selected_engine == SearchEngine.WIKIPEDIA.value:
        wiki_lang = search_config.get("wikipedia_lang", "en")
        wiki_doc_content_chars_max = search_config.get(
            "wikipedia_doc_content_chars_max", 4000
        )
        return LoggedWikipediaSearch(
            name="web_search",
            api_wrapper=WikipediaAPIWrapper(
                lang=wiki_lang,
                top_k_results=max_search_results,
                load_all_available_meta=True,
                doc_content_chars_max=wiki_doc_content_chars_max,
                wiki_client=None,
            ),
        )
    elif selected_engine == SearchEngine.CUSTOM_SEARCH.value:
        # 使用自定义搜索引擎
        if repository:
            tool = create_custom_search_with_repository(repository=repository, max_results=max_search_results)
            enhanced_logger.logger.info(f"🔧 TOOL_READY | 自定义搜索工具就绪 | 仓库: {repository}")
        else:
            tool = get_custom_search_tool(max_results=max_search_results)
            enhanced_logger.logger.info(f"🔧 TOOL_READY | 默认自定义搜索工具就绪")
        duration = time.time() - start_time
        enhanced_logger.logger.info(f"🔧 TOOL_READY | 自定义搜索工具配置完成 | 耗时: {duration:.2f}s")
        return tool
    else:
        enhanced_logger.logger.error(f"❌ TOOL_ERROR | 不支持的搜索引擎: {selected_engine}")
        raise ValueError(f"Unsupported search engine: {selected_engine}")
