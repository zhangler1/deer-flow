# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
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

from src.config import SELECTED_SEARCH_ENGINE, SearchEngine, load_yaml_config
from src.tools.decorators import create_logged_tool
from src.tools.tavily_search.tavily_search_results_with_images import (
    TavilySearchWithImages,
)
from src.tools.custom_search import get_custom_search_tool, create_custom_search_with_repository

logger = logging.getLogger(__name__)

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
def get_web_search_tool(max_search_results: int, engine: Optional[str] = None, repository_id: Optional[str] = None):
    search_config = get_search_config()
    
    # Use provided engine, or from config file, or fall back to environment variable
    selected_engine = engine or search_config.get("engine") or SELECTED_SEARCH_ENGINE
    
    logger.info(f"Using search engine: {selected_engine}")

    if selected_engine == SearchEngine.TAVILY.value:
        # Only get and apply include/exclude domains for Tavily
        include_domains: Optional[List[str]] = search_config.get("include_domains", [])
        exclude_domains: Optional[List[str]] = search_config.get("exclude_domains", [])

        logger.info(
            f"Tavily search configuration loaded: include_domains={include_domains}, exclude_domains={exclude_domains}"
        )

        return LoggedTavilySearch(
            name="web_search",
            max_results=max_search_results,
            include_raw_content=True,
            include_images=True,
            include_image_descriptions=True,
            include_domains=include_domains or [],
            exclude_domains=exclude_domains or [],
        )
    elif selected_engine == SearchEngine.DUCKDUCKGO.value:
        return LoggedDuckDuckGoSearch(
            name="web_search",
            num_results=max_search_results,
        )
    elif selected_engine == SearchEngine.BRAVE_SEARCH.value:
        return LoggedBraveSearch(
            name="web_search",
            search_wrapper=BraveSearchWrapper(
                api_key=os.getenv("BRAVE_SEARCH_API_KEY", ""),
                search_kwargs={"count": max_search_results},
            ),
        )
    elif selected_engine == SearchEngine.ARXIV.value:
        return LoggedArxivSearch(
            name="web_search",
            api_wrapper=ArxivAPIWrapper(
                top_k_results=max_search_results,
                load_max_docs=max_search_results,
                load_all_available_meta=True,
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
            ),
        )
    elif selected_engine == SearchEngine.CUSTOM_SEARCH.value:
        # 使用自定义搜索引擎
        if repository_id:
            return create_custom_search_with_repository(repository_id=repository_id, max_results=max_search_results)
        else:
            return get_custom_search_tool(max_results=max_search_results)
    else:
        raise ValueError(f"Unsupported search engine: {selected_engine}")
