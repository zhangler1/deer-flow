# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
交通银行内部搜索API适配器
将现有的CustomSearchTool包装为SearchAdapter接口
"""

import logging
from typing import List, Optional, Dict, Any

from src.tools.search_adapter_base import SearchAdapter, SearchResult
from src.tools.custom_search import CustomSearchTool

logger = logging.getLogger(__name__)


class TBYHCustomSearchAdapter(SearchAdapter):
    """交通银行内部搜索API适配器"""
    
    def __init__(self, api_url: str, api_key: str = "", **kwargs):
        super().__init__("TBYHCustom", api_url=api_url, api_key=api_key, **kwargs)
        self.api_url = api_url
        self.api_key = api_key
        self.max_results = kwargs.get("max_results", 10)
        
        # 创建CustomSearchTool实例
        self.search_tool = CustomSearchTool(
            api_url=api_url,
            api_key=api_key,
            max_results=self.max_results
        )
        
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """
        执行交通银行内部搜索
        
        Args:
            query: 检索查询词
            **kwargs: 其他参数（如repository_id等）
            
        Returns:
            List[SearchResult]: 检索结果列表
        """
        try:
            logger.info(f"TBYH custom search query: {query}")
            
            # 调用现有的搜索工具
            results = self.search_tool._run(query, **kwargs)
            
            # 转换为标准格式
            search_results = self._convert_to_search_results(results)
            
            self._log_search_result(query, search_results)
            return search_results
            
        except Exception as e:
            logger.error(f"TBYH custom search error: {e}")
            return []
    
    def _convert_to_search_results(self, results: List[Dict[str, Any]]) -> List[SearchResult]:
        """将工具返回结果转换为标准SearchResult格式"""
        search_results = []
        
        # 如果返回的是错误信息字符串
        if isinstance(results, str):
            logger.warning(f"Search returned string result: {results}")
            return search_results
            
        # 如果返回的是字典列表
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    search_result = SearchResult(
                        title=item.get("title", "").strip(),
                        content=item.get("content", "").strip(),
                        url=item.get("url", ""),
                        source=item.get("source", ""),
                        score=float(item.get("score", 0)),
                        doc_id=item.get("doc_id", item.get("docId", "")),
                        repository=item.get("repository", ""),
                        create_time=item.get("create_time"),
                        update_time=item.get("update_time"),
                        category=item.get("category"),
                        organization=item.get("organization")
                    )
                    # 只有当标题或内容非空时才添加
                    if search_result.title or search_result.content:
                        search_results.append(search_result)
        
        return search_results
