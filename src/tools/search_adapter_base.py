# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
检索接口适配器模块
提供统一的检索接口抽象，支持多种检索服务的插件化接入
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from src.utils.enhanced_logger import console_print
import json

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """标准化的检索结果"""
    title: str
    content: str
    url: str = ""
    source: str = ""
    score: float = 0.0
    doc_id: str = ""
    repository: str = ""
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    category: Optional[str] = None
    organization: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchResult':
        """从字典创建 SearchResult 实例"""
        # 过滤掉 SearchResult 中不存在的字段
        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)


class SearchAdapter(ABC):
    """检索接口适配器抽象基类"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.config = kwargs
        
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """
        执行检索操作
        
        Args:
            query: 检索查询词
            **kwargs: 其他检索参数
            
        Returns:
            List[SearchResult]: 检索结果列表
        """
        pass
    
    def _log_search_result(self, query: str, results: List[SearchResult]):
        """记录检索结果摘要"""
        console_print(
            f"\033[32m[{self.name}检索摘要] 查询: '{query}'\033[0m \033[35m| 返回结果数: {len(results)} 条\033[0m",
            level=logging.INFO
        )
        if results:
            console_print(
                f"\033[32m[结果详情] 共{len(results)}条结果:\033[0m",
                level=logging.DEBUG
            )
            for i, result in enumerate(results[:5]):  # 只显示前5条
                title = result.title if result.title else '无标题'
                content = result.content
                # 截取内容前40字
                content_preview = content[:40] if content else '无内容'
                score = result.score
                console_print(
                    f"\033[32m  {i+1}. 标题: {title}\033[0m",
                    level=logging.DEBUG
                )
                console_print(
                    f"\033[35m     内容: {content_preview}...\033[0m",
                    level=logging.DEBUG
                )
                console_print(
                    f"\033[35m     [评分: {score}]\033[0m",
                    level=logging.DEBUG
                )


class MockSearchAdapter(SearchAdapter):
    """Mock检索适配器 - 用于测试和调试"""
    
    def __init__(self, **kwargs):
        super().__init__("Mock", **kwargs)
        
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Mock检索实现"""
        logger.info(f"Mock search query: {query}")
        
        # 模拟一些检索结果
        mock_results = [
            SearchResult(
                title="Mock检索结果1",
                content=f"这是Mock检索的结果内容，查询词: {query}。这是用于测试的模拟数据。",
                url="http://example.com/mock1",
                source="mock_source",
                score=0.95,
                doc_id="mock_001"
            ),
            SearchResult(
                title="Mock检索结果2",
                content=f"另一个Mock检索结果，包含查询词: {query}。可用于验证检索接口。",
                url="http://example.com/mock2",
                source="mock_source",
                score=0.85,
                doc_id="mock_002"
            )
        ]
        
        self._log_search_result(query, mock_results)
        return mock_results


class CustomSearchAdapter(SearchAdapter):
    """自定义检索适配器"""
    
    def __init__(self, api_url: str, api_key: str = "", **kwargs):
        super().__init__("Custom", api_url=api_url, api_key=api_key, **kwargs)
        self.api_url = api_url
        self.api_key = api_key
        
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """自定义检索实现"""
        import requests
        
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        # 构建请求参数
        payload = {
            "query": query,
            **kwargs  # 允许传递额外参数
        }
        
        try:
            logger.info(f"Custom search query: {query}")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            # 解析响应
            data = response.json()
            results = self._parse_response(data)
            
            self._log_search_result(query, results)
            return results
            
        except Exception as e:
            logger.error(f"Custom search error: {e}")
            return []
    
    def _parse_response(self, data: Dict[str, Any]) -> List[SearchResult]:
        """解析检索响应"""
        results = []
        
        # 根据不同API格式解析结果
        # 这里可以根据实际API格式进行调整
        if isinstance(data, list):
            # 如果直接返回结果列表
            for item in data:
                # 确保 item 是字典类型
                if isinstance(item, dict):
                    result = self._convert_item_to_result(item)
                    if result:
                        results.append(result)
        elif isinstance(data, dict):
            # 如果返回包含结果的字典
            result_list = data.get("results", data.get("items", data.get("data", [])))
            if isinstance(result_list, list):
                for item in result_list:
                    # 确保 item 是字典类型
                    if isinstance(item, dict):
                        result = self._convert_item_to_result(item)
                        if result:
                            results.append(result)
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def _convert_item_to_result(self, item: Dict[str, Any]) -> Optional[SearchResult]:
        """将单个结果项转换为 SearchResult"""
        # 确保 item 是字典类型
        if not isinstance(item, dict):
            return None
            
        # 尝试从不同字段获取所需信息
        title = (
            item.get("title") or 
            item.get("subject") or 
            item.get("name") or 
            "无标题"
        )
        
        content = (
            item.get("content") or 
            item.get("abstract") or 
            item.get("summary") or 
            item.get("description") or 
            ""
        )
        
        # 如果标题和内容都为空，跳过这个结果
        if not title and not content:
            return None
            
        return SearchResult(
            title=title,
            content=content,
            url=item.get("url", ""),
            source=item.get("source", ""),
            score=float(item.get("score", 0)),
            doc_id=item.get("doc_id", item.get("id", "")),
            repository=item.get("repository", ""),
            create_time=item.get("create_time"),
            update_time=item.get("update_time"),
            category=item.get("category"),
            organization=item.get("organization")
        )


# 检索适配器注册表
_SEARCH_ADAPTERS = {
    "mock": MockSearchAdapter,
    "custom": CustomSearchAdapter,
}


def register_search_adapter(name: str, adapter_class: type):
    """注册新的检索适配器"""
    if not issubclass(adapter_class, SearchAdapter):
        raise ValueError("Adapter class must inherit from SearchAdapter")
    _SEARCH_ADAPTERS[name] = adapter_class


def get_search_adapter(adapter_type: str, **config) -> SearchAdapter:
    """获取检索适配器实例"""
    adapter_class = _SEARCH_ADAPTERS.get(adapter_type)
    if not adapter_class:
        raise ValueError(f"Unknown search adapter type: {adapter_type}")
    return adapter_class(**config)


def list_available_adapters() -> List[str]:
    """列出所有可用的检索适配器"""
    return list(_SEARCH_ADAPTERS.keys())


# 便捷函数用于快速测试
def test_search_adapter(adapter_type: str, query: str, **config) -> List[Dict[str, Any]]:
    """
    测试检索适配器
    
    Args:
        adapter_type: 适配器类型
        query: 查询词
        **config: 适配器配置
        
    Returns:
        List[Dict]: 检索结果列表
    """
    try:
        adapter = get_search_adapter(adapter_type, **config)
        results = adapter.search(query)
        return [result.to_dict() for result in results]
    except Exception as e:
        logger.error(f"Test search adapter error: {e}")
        return []


if __name__ == "__main__":
    # 简单的命令行测试工具
    import argparse
    
    parser = argparse.ArgumentParser(description="检索适配器测试工具")
    parser.add_argument("adapter_type", help="适配器类型")
    parser.add_argument("query", help="查询词")
    parser.add_argument("--config", help="配置参数 (JSON格式)", default="{}")
    
    args = parser.parse_args()
    
    try:
        config = json.loads(args.config)
        results = test_search_adapter(args.adapter_type, args.query, **config)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}")
