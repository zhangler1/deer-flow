# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""Tavily Search API Wrapper — uses tavily-python directly (aligned with deer-flow-2.0).

No dependency on langchain_community or langchain_tavily.
"""

import json
import logging
import os
from typing import Dict, List, Optional

import aiohttp
import requests
from pydantic import SecretStr

from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger

TAVILY_API_URL = "https://api.tavily.com"


class EnhancedTavilySearchAPIWrapper:
    """Enhanced Tavily Search API wrapper using tavily-python directly.

    对齐 deer-flow-2.0 架构：不再继承 langchain_tavily / langchain_community 的基类，
    而是通过 HTTP 请求直接调用 Tavily REST API，保持相同的公共接口。
    """

    def __init__(self, tavily_api_key: Optional[str] = None):
        api_key = tavily_api_key or os.getenv("TAVILY_API_KEY", "")
        self.tavily_api_key = SecretStr(api_key)

    def raw_results(
        self,
        query: str,
        max_results: Optional[int] = 5,
        search_depth: Optional[str] = "advanced",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_answer: Optional[bool] = False,
        include_raw_content: Optional[bool] = False,
        include_images: Optional[bool] = False,
        include_image_descriptions: Optional[bool] = False,
    ) -> Dict:
        """Get raw results from the Tavily Search API synchronously."""
        params = {
            "api_key": self.tavily_api_key.get_secret_value(),
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_domains": include_domains or [],
            "exclude_domains": exclude_domains or [],
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
            "include_image_descriptions": include_image_descriptions,
        }
        response = requests.post(
            f"{TAVILY_API_URL}/search",
            json=params,
        )
        response.raise_for_status()
        return response.json()

    async def raw_results_async(
        self,
        query: str,
        max_results: Optional[int] = 5,
        search_depth: Optional[str] = "advanced",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_answer: Optional[bool] = False,
        include_raw_content: Optional[bool] = False,
        include_images: Optional[bool] = False,
        include_image_descriptions: Optional[bool] = False,
    ) -> Dict:
        """Get results from the Tavily Search API asynchronously."""

        async def fetch() -> str:
            params = {
                "api_key": self.tavily_api_key.get_secret_value(),
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_domains": include_domains or [],
                "exclude_domains": exclude_domains or [],
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
                "include_images": include_images,
                "include_image_descriptions": include_image_descriptions,
            }
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.post(f"{TAVILY_API_URL}/search", json=params) as res:
                    if res.status == 200:
                        data = await res.text()
                        return data
                    else:
                        raise Exception(f"Error {res.status}: {res.reason}")

        results_json_str = await fetch()
        return json.loads(results_json_str)

    def clean_results_with_images(
        self, raw_results: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """Clean results from Tavily Search API."""
        results = raw_results.get("results", [])
        clean_results = []
        for result in results:
            clean_result = {
                "type": "page",
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0),
            }
            if raw_content := result.get("raw_content"):
                clean_result["raw_content"] = raw_content
            clean_results.append(clean_result)
        images = raw_results.get("images", [])
        for image in images:
            clean_result = {
                "type": "image",
                "image_url": image.get("url", ""),
                "image_description": image.get("description", ""),
            }
            clean_results.append(clean_result)
        return clean_results
