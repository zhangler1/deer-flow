# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
import os
from typing import Any, Dict, List, Optional, Type, Union

import requests
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ValidationError

from src.utils.enhanced_logger import console_print, get_enhanced_logger




logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('tools.custom_search')


class MuwpUser(BaseModel):
    """MUWP 用户信息模型"""
    muwp_branchID: str = Field(default="", description="分行ID")
    muwp_loginName: str = Field(default="", description="登录名")
    muwp_userCode: str = Field(default="", description="用户编码")
    muwp_userName: str = Field(default="", description="用户姓名")
    muwp_userID: str = Field(default="", description="用户ID")


class SearchResultItem(BaseModel):
    """检索结果单项的数据模型，用于验证接口返回值"""
    title: str = Field(default="", description="结果标题")
    content: str = Field(default="", description="结果内容")
    score: float = Field(default=0.0, description="匹配分数")
    url: str = Field(default="", description="结果链接")
    source: str = Field(default="", description="来源")
    category: str = Field(default="", description="分类")
    createTime: str = Field(default="", description="创建时间")
    docGuid: str = Field(default="", description="文档GUID")
    repository: str = Field(default="", description="仓库")
    attachEcmId: str = Field(default="", description="附件ECM ID")
    fromAttachment: bool = Field(default=False, description="是否来自附件")


class CustomSearchInput(BaseModel):
    """Input for custom search tool."""
    query: str = Field(description="Search query string")
    repository: Optional[str] = Field(default=None, description="Repository to use for search (e.g. online_search, aggregation-search)")


class CustomSearchTool(BaseTool):
    """
    自定义搜索引擎工具
    实现"边想边搜"功能的检索接口
    适配交通银行内部搜索API格式
    """
    
    name: str = "intranet_search"
    description: str = "搜索网络信息。输入应该是搜索查询字符串。"
    
    # 配置参数
    api_url: str = Field(default="")
    api_key: str = Field(default="")
    max_results: int = Field(default=10)
    timeout: int = Field(default=30)
    repository: str = Field(default="aggregation-search")  # API请求中的repository参数
    channel_id: str = Field(default="0")  # API请求中的channelId参数
    
    # 用户信息配置
    muwp_user: MuwpUser = Field(default_factory=MuwpUser)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 设置args_schema
        self.args_schema = CustomSearchInput
        
        # 从环境变量获取 API 地址和密钥
        self.api_url = os.getenv("ONLINE_SEARCH_API_URL", "")
        self.api_key = os.getenv("ONLINE_SEARCH_API_KEY", "")
        
        # repository / channel_id 完全由构造参数决定，不再从环境变量覆盖
        # 调用方通过 CustomSearchTool(repository="xxx") 显式传入
        
        # 如果外部未传入 muwp_user，则从环境变量设置默认值
        if not self.muwp_user or not any(self.muwp_user.model_dump().values()):
            self.muwp_user = MuwpUser(
                muwp_branchID=os.getenv("MUWP_BRANCH_ID", ""),
                muwp_loginName=os.getenv("MUWP_LOGIN_NAME", ""),
                muwp_userCode=os.getenv("MUWP_USER_CODE", ""),
                muwp_userName=os.getenv("MUWP_USER_NAME", ""),
                muwp_userID=os.getenv("MUWP_USER_ID", "")
            )
        
        if not self.api_url:
            raise ValueError("ONLINE_SEARCH_API_URL environment variable is required")
    
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
                "muwpUser": self.muwp_user.model_dump()
            }
        }
        
        # ── 调试日志: 请求 payload ──
        logger.info(
            f"📡 {self.name} | 发起请求 | url={self.api_url} | "
            f"repository={self.repository} | channelId={self.channel_id} | query='{query}'"
        )
        logger.debug(
            f"📡 {self.name} | 完整payload: {json.dumps(payload, ensure_ascii=False)[:500]}"
        )
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            # ── 调试日志: 响应状态 ──
            logger.info(
                f"📡 {self.name} | 响应 | status={response.status_code} | "
                f"content-length={len(response.content)} | encoding={response.encoding}"
            )
            
            response.raise_for_status()
            
            # 解析响应
            data = response.json()
            
            # ── 调试日志: 响应结构 ──
            rsp_head = data.get("RSP_HEAD", {})
            tran_success = rsp_head.get("TRAN_SUCCESS")
            result_count = len(data.get("RSP_BODY", {}).get("result", []))
            logger.info(
                f"📡 {self.name} | 解析 | TRAN_SUCCESS={tran_success} | "
                f"result条数={result_count}"
            )
            
            # 将API响应格式转换为标准格式
            results = self._parse_response(data)
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ {self.name} | 请求失败 | url={self.api_url} | error={e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"❌ {self.name} | JSON解析失败 | error={e}")
            return []
        except Exception as e:
            logger.error(f"❌ {self.name} | 未知错误 | error={e}")
            return []
    
    def _validate_search_results(self, results: List[Dict[str, Any]], context: str = "") -> None:
        """验证检索结果是否符合 Pydantic 模型定义，不符合则打印日志但不抛异常"""
        for idx, item in enumerate(results):
            try:
                SearchResultItem.model_validate(item)
            except ValidationError as e:
                logger.warning(
                    f"检索结果第 {idx + 1} 项数据类型不符合预期"
                    f"{f' [{context}]' if context else ''}: {e}"
                )

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
            # 处理 fullCategoryName：可能是 None、字符串或列表
            raw_category = item.get("fullCategoryName") or ""
            if isinstance(raw_category, list):
                raw_category = "/".join(str(c) for c in raw_category if c)

            # 转换为 DeerFlow 统一的结构化格式
            result = {
                # === 核心必需字段 ===
                "title": (item.get("title") or "").strip(),
                "content": (item.get("content") or "").strip() or (item.get("absContent") or "").strip(),
                "score": float(item.get("score") or 0) if item.get("score") else 0.0,
                "url": item.get("url") or "",  # url可能为None
                "source": item.get("source") or "",

                # === 次要可选字段 ===
                "category": raw_category,
                "createTime": item.get("createTime") or "",  # 创建时间
                "docGuid": item.get("docGuid") or "",
                "repository": item.get("repository") or "",
                "attachEcmId": item.get("attachEcmId") or "",
                "fromAttachment": bool(item.get("fromAttachment") or False),
            }

            # 只有当内容不为空时才添加到结果中
            if result["title"] or result["content"]:
                results.append(result)

        # 按分数排序（降序）
        results.sort(key=lambda x: x.get("score", 0), reverse=True)

        # 限制结果数量
        trimmed_results = results[:self.max_results]
        # 验证结果数据类型，仅记录日志不阻断流程
        self._validate_search_results(trimmed_results, context="_parse_response")
        return trimmed_results

    
    def _run(
        self,
        query: str,
        repository: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """同步执行搜索"""
        import time
        start_time = time.time()
        
        # 如果 LLM 调用时显式传入 repository 参数，临时覆盖实例配置
        original_repository = self.repository
        original_channel_id = self.channel_id
        if repository:
            self.repository = repository
            self.channel_id = kwargs.get("channel_id", self.channel_id)
        
        # 记录检索开始
        logger.info(f"🔍 {self.name} | 搜索 | 仓库={self.repository} | 查询='{query}'")
        
        try:
            results = self._call_search_api(query)
            duration = time.time() - start_time
            
            logger.info(f"✅ {self.name} | 搜索完成 | 结果={len(results)} | 耗时={duration:.1f}s")
            
            # 恢复原始配置
            if repository:
                self.repository = original_repository
                self.channel_id = original_channel_id
            
            # 返回结果列表，结果为空时返回提示
            if not results:
                logger.warning("No search results found")
                no_result = [{
                    "title": "未找到相关结果",
                    "url": "",
                    "content": f'未能找到与查询"{query}"相关的信息，请尝试使用不同的关键词。',
                    "source": "system",
                    "score": 0.0
                }]
                self._validate_search_results(no_result, context="empty_result")
                return no_result
            
            self._validate_search_results(results, context="_run")
            return results
        except Exception as e:
            duration = time.time() - start_time
            
            # 恢复原始配置
            if repository:
                self.repository = original_repository
                self.channel_id = original_channel_id
            
            enhanced_logger.logger.error(
                f"❌ SEARCH_ERROR | {self.name} | 搜索失败 | "
                f"耗时: {duration:.2f}s | 错误: {str(e)}"
            )
            logger.error(f"Custom search error: {e}")
            console_print(
                f"\033[31m[❌ 搜索错误] 搜索服务出现错误: {str(e)}\033[0m",
                level=logging.ERROR
            )
            
            error_result = [{
                "title": "搜索错误",
                "url": "",
                "content": f"搜索服务出现错误: {str(e)}",
                "source": "error",
                "score": 0.0
            }]
            self._validate_search_results(error_result, context="error_result")
            return error_result
    
    
    async def _arun(
        self,
        query: str,
        repository: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> List[Dict[str, Any]]:
        """异步执行搜索（可选实现）"""
        # 对于简单的 HTTP 请求，可以直接调用同步方法
        return self._run(query, repository, None)


def get_custom_search_tool(
    max_results: int = 10,
    repository: Optional[str] = None,
    api_url: Optional[str] = None,
    muwp_user: Optional[MuwpUser] = None
) -> CustomSearchTool:
    """创建自定义搜索工具实例"""
    kwargs: Dict[str, Any] = {"max_results": max_results}
    
    # 如果提供了参数，则传递给工具
    if api_url:
        kwargs["api_url"] = api_url
    if repository:
        kwargs["repository"] = repository
    if muwp_user:
        kwargs["muwp_user"] = muwp_user
        
    return CustomSearchTool(**kwargs)


def create_custom_search_with_repository(repository: str, max_results: int = 10) -> CustomSearchTool:
    """根据 repository 创建自定义搜索工具"""
    return CustomSearchTool(repository=repository, max_results=max_results)