# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
import os
from typing import Any, Dict, List, Optional, Type

import requests
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CustomSearchInput(BaseModel):
    """Input for custom search tool."""
    query: str = Field(description="Search query string")


class CustomSearchTool(BaseTool):
    """
    自定义搜索引擎工具
    实现"边想边搜"功能的检索接口
    适配交通银行内部搜索API格式
    """
    
    name: str = "web_search"
    description: str = "搜索网络信息。输入应该是搜索查询字符串。"
    args_schema: Type[BaseModel] = CustomSearchInput
    
    # 配置参数
    api_url: str = Field(default="")
    api_key: str = Field(default="")
    max_results: int = Field(default=10)
    timeout: int = Field(default=30)
    repository: str = Field(default="okic-dynamicSearch")
    channel_id: str = Field(default="0")
    
    # 用户信息配置
    muwp_user: Dict[str, str] = Field(default_factory=dict)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 从环境变量获取配置
        self.api_url = os.getenv("CUSTOM_SEARCH_API_URL", "")
        self.api_key = os.getenv("CUSTOM_SEARCH_API_KEY", "")
        self.repository = os.getenv("CUSTOM_SEARCH_REPOSITORY", "okic-dynamicSearch")
        self.channel_id = os.getenv("CUSTOM_SEARCH_CHANNEL_ID", "0")
        
        # 设置默认用户信息（可以从环境变量获取）
        self.muwp_user = {
            "muwp_branchID": os.getenv("MUWP_BRANCH_ID", "1000027159"),
            "muwp_loginName": os.getenv("MUWP_LOGIN_NAME", "xuew_4"),
            "muwp_userCode": os.getenv("MUWP_USER_CODE", "9743616"),
            "muwp_userName": os.getenv("MUWP_USER_NAME", "薛巍"),
            "muwp_userID": os.getenv("MUWP_USER_ID", "132298")
        }
        
        if not self.api_url:
            raise ValueError("CUSTOM_SEARCH_API_URL environment variable is required")
    
    def _call_search_api(self, query: str) -> List[Dict[str, Any]]:
        """调用交通银行内部搜索 API"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "User-Agent": "DeerFlow-SearchTool/1.0.0",
            "jumpCloud-Env": "BASE"
        }
        
        # 如果需要 API 密钥
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # 构建符合交通银行API格式的请求参数
        payload = {
            "REQ_HEAD": {
                "TRANS_PROCESS": "",
                "TRAN_ID": ""
            },
            "REQ_BODY": {
                "param": {
                    "messages": [
                        {
                            "content": query,
                            "role": "user"
                        }
                    ],
                    "repository": self.repository,
                    "param": {
                        "channelId": self.channel_id
                    }
                },
                "muwpUser": self.muwp_user
            }
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 解析响应
            data = response.json()
            
            # 将API响应格式转换为标准格式
            results = self._parse_response(data)
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Custom search API request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse custom search API response: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in search API call: {e}")
            return []
    
    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        将交通银行搜索API响应转换为标准格式
        """
        results = []
        
        # 检查响应是否成功
        rsp_head = data.get("RSP_HEAD", {})
        if rsp_head.get("TRAN_SUCCESS") != "1":
            logger.warning(f"Search API returned error: {rsp_head}")
            return results
        
        # 从RSP_BODY中提取搜索结果
        rsp_body = data.get("RSP_BODY", {})
        api_results = rsp_body.get("result", [])
        
        for item in api_results:
            # 转换为 DeerFlow 标准格式
            result = {
                "title": item.get("title", "").strip(),
                "url": item.get("url") or "",  # url可能为None
                "content": item.get("content", "").strip() or item.get("absContent", "").strip(),
                "source": item.get("source", ""),
                "score": float(item.get("score", 0)) if item.get("score") else 0.0,
                "doc_id": item.get("docId", ""),
                "repository": item.get("repository", "")
            }
            
            # 添加其他可用字段
            if item.get("createTime"):
                result["create_time"] = item["createTime"]
            if item.get("updateTime"):
                result["update_time"] = item["updateTime"]
            if item.get("fullCategoryName"):
                result["category"] = item["fullCategoryName"]
            if item.get("fullOrgName"):
                result["organization"] = item["fullOrgName"]
                
            # 只有当内容不为空时才添加到结果中
            if result["title"] or result["content"]:
                results.append(result)
        
        # 按分数排序（降序）
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 限制结果数量
        return results[:self.max_results]
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Dict[str, Any]]:
        """同步执行搜索"""
        logger.info(f"Custom search query: {query}")
        
        try:
            results = self._call_search_api(query)
            logger.info(f"Custom search returned {len(results)} results")
            
            # 返回结果列表，结果为空时返回提示
            if not results:
                logger.warning("No search results found")
                return [{
                    "title": "未找到相关结果",
                    "url": "",
                    "content": f"未能找到与查询“{query}”相关的信息，请尝试使用不同的关键词。",
                    "source": "system",
                    "score": 0.0
                }]
            
            return results
        except Exception as e:
            logger.error(f"Custom search error: {e}")
            return [{
                "title": "搜索错误",
                "url": "",
                "content": f"搜索服务出现错误: {str(e)}",
                "source": "error",
                "score": 0.0
            }]
    
    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> List[Dict[str, Any]]:
        """异步执行搜索（可选实现）"""
        # 对于简单的 HTTP 请求，可以直接调用同步方法
        return self._run(query, None)


def get_custom_search_tool(
    max_results: int = 10,
    api_url: str = None,
    repository: str = None,
    channel_id: str = None,
    muwp_user: Dict[str, str] = None
) -> CustomSearchTool:
    """创建自定义搜索工具实例"""
    kwargs = {"max_results": max_results}
    
    # 如果提供了参数，则传递给工具
    if api_url:
        kwargs["api_url"] = api_url
    if repository:
        kwargs["repository"] = repository
    if channel_id:
        kwargs["channel_id"] = channel_id
    if muwp_user:
        kwargs["muwp_user"] = muwp_user
        
    return CustomSearchTool(**kwargs)