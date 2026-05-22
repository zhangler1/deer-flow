# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""Tavily Search Tool with Images — aligned with deer-flow-2.0 architecture.

Uses BaseTool directly instead of inheriting from langchain_community's TavilySearchResults.
No dependency on langchain_community or langchain_tavily.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Union

from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import Field

from src.tools.tavily_search.tavily_search_api_wrapper import (
    EnhancedTavilySearchAPIWrapper,
)
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger


class TavilySearchWithImages(BaseTool):
    """Tool that queries the Tavily Search API and gets back json with images.

    对齐 deer-flow-2.0 架构：直接继承 BaseTool，
    不再依赖 langchain_community.tools.tavily_search.tool.TavilySearchResults。

    Setup:
        Install ``tavily-python`` and set environment variable ``TAVILY_API_KEY``.

        .. code-block:: bash

            pip install -U tavily-python
            export TAVILY_API_KEY="your-api-key"

    Instantiate:

        .. code-block:: python

            from src.tools.tavily_search import TavilySearchWithImages

            tool = TavilySearchWithImages(
                max_results=5,
                include_answer=True,
                include_raw_content=True,
                include_images=True,
                include_image_descriptions=True,
            )
    """

    name: str = "tavily_search_results_json"
    description: str = (
        "A search engine optimized for comprehensive, accurate, "
        "and trusted results. Useful for when you need to answer questions "
        "about current events."
    )

    # Tool parameters (matching the original TavilySearchResults interface)
    max_results: int = 5
    search_depth: str = "advanced"
    include_domains: List[str] = Field(default_factory=list)
    exclude_domains: List[str] = Field(default_factory=list)
    include_answer: bool = False
    include_raw_content: bool = True
    include_images: bool = True
    include_image_descriptions: bool = False

    api_wrapper: EnhancedTavilySearchAPIWrapper = Field(
        default_factory=EnhancedTavilySearchAPIWrapper
    )

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Tuple[Union[List[Dict[str, str]], str], Dict]:
        """Use the tool."""
        try:
            raw_results = self.api_wrapper.raw_results(
                query,
                self.max_results,
                self.search_depth,
                self.include_domains,
                self.exclude_domains,
                self.include_answer,
                self.include_raw_content,
                self.include_images,
                self.include_image_descriptions,
            )
        except Exception as e:
            logger.error("Tavily search returned error: {}".format(e))
            return repr(e), {}
        cleaned_results = self.api_wrapper.clean_results_with_images(raw_results)
        logger.debug(
            "sync: %s", json.dumps(cleaned_results, indent=2, ensure_ascii=False)
        )
        return cleaned_results, raw_results

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Tuple[Union[List[Dict[str, str]], str], Dict]:
        """Use the tool asynchronously."""
        try:
            raw_results = await self.api_wrapper.raw_results_async(
                query,
                self.max_results,
                self.search_depth,
                self.include_domains,
                self.exclude_domains,
                self.include_answer,
                self.include_raw_content,
                self.include_images,
                self.include_image_descriptions,
            )
        except Exception as e:
            logger.error("Tavily search returned error: {}".format(e))
            return repr(e), {}
        cleaned_results = self.api_wrapper.clean_results_with_images(raw_results)
        logger.debug(
            "async: %s", json.dumps(cleaned_results, indent=2, ensure_ascii=False)
        )
        return cleaned_results, raw_results
