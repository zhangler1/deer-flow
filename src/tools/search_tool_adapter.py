# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
LangChain 搜索工具适配器
将搜索适配器封装为 LangChain BaseTool，供 Agent 调用
"""

import logging
from typing import List, Optional, Dict, Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.tools.search_adapter_base import get_search_adapter, SearchResult
from src.tools.adapters.custom_search_adapter import TBYHCustomSearchAdapter
from src.tools.search_adapter_base import register_search_adapter

# 注册交通银行适配器
register_search_adapter("tbyh_custom", TBYHCustomSearchAdapter)

logger = logging.getLogger(__name__)


class AdapterSearchInput(BaseModel):
    """适配器检索工具输入"""
    query: str = Field(description="Search query string")
    adapter_type: str = Field(default="mock", description="Adapter type to use for search")
    config: Dict[str, Any] = Field(default_factory=dict, description="Adapter configuration")


class AdapterSearchTool(BaseTool):
    """
    基于适配器架构的检索工具
    支持多种检索服务的统一接口
    """
    
    name: str = "adapter_search"
    description: str = "通用检索工具，支持多种检索服务。输入应该是搜索查询字符串和适配器类型。"
    args_schema: type[BaseModel] | None = AdapterSearchInput
    
    def _run(
        self,
        query: str,
        adapter_type: str = "mock",
        config: Optional[Dict[str, Any]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Dict[str, Any]]:
        """同步执行搜索"""
        try:
            logger.info(f"Adapter search query: {query} using {adapter_type}")
            
            # 获取适配器实例
            adapter = get_search_adapter(adapter_type, **(config or {}))
            
            # 执行检索
            results = adapter.search(query)
            
            # 转换为字典格式
            return [result.to_dict() for result in results]
            
        except Exception as e:
            logger.error(f"Adapter search error: {e}")
            return [{
                "title": "检索错误",
                "url": "",
                "content": f"检索服务出现错误: {str(e)}",
                "source": "error",
                "score": 0.0
            }]
    
    async def _arun(
        self,
        query: str,
        adapter_type: str = "mock",
        config: Optional[Dict[str, Any]] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> List[Dict[str, Any]]:
        """异步执行搜索"""
        # 对于简单的实现，可以直接调用同步方法
        return self._run(query, adapter_type, config, run_manager)


# 便捷函数
def create_adapter_search_tool(adapter_type: str = "mock", **config) -> AdapterSearchTool:
    """创建适配器检索工具实例"""
    # 可以在这里预配置适配器
    return AdapterSearchTool()


if __name__ == "__main__":
    # 简单测试
    tool = AdapterSearchTool()
    
    # 测试Mock适配器
    print("测试Mock适配器:")
    results = tool._run("测试查询", "mock")
    for result in results:
        print(f"  {result['title']}: {result['content'][:50]}...")
    
    # 如果配置了自定义搜索，测试自定义适配器
    import os
    if os.getenv("CUSTOM_SEARCH_API_URL"):
        print("\n测试自定义适配器:")
        config = {
            "api_url": os.getenv("CUSTOM_SEARCH_API_URL"),
            "api_key": os.getenv("CUSTOM_SEARCH_API_KEY", ""),
        }
        results = tool._run("F1赛车制造", "custom", config)
        for result in results:
            print(f"  {result['title']}: {result['content'][:50]}...")