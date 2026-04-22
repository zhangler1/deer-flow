# SPDX-License-Identifier: MIT

"""
交通银行搜索工具（bocomsearch）

基于 api——info/bocomsearch 提供的请求格式，实现对内网搜索接口的调用。
- 通过 header `guwp-token` 进行鉴权
- 使用 `application/x-www-form-urlencoded` 的 `REQ_MESSAGE` 表单字段
- 将响应解析为 DeerFlow 标准结构（title, content, score, url, source）

使用方式：
- 默认从环境变量 `GUWP_TOKEN` 读取 token
- 也可在函数调用时显式传入 `guwp_token`

前端会通过设置项将 token 传到后端，并在服务器侧预留从父页面传参的机制
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests
from langchain_core.tools import tool  # type: ignore

logger = logging.getLogger(__name__)


class BocomSearchConfig:
    """交通银行搜索配置"""

    API_URL: str = os.getenv(
        "BOCOM_SEARCH_API_URL",
        "http://eaip-chn-slb-7006.bocomm.com/ELLM.ELLM-OFFICE.V-1.0/querySources.do",
    )

    # 默认请求头（除 guwp-token 外）
    HEADERS_BASE: Dict[str, str] = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "User-Agent": "DeerFlow-BocomSearch/1.0",
        "content-type": "application/x-www-form-urlencoded",
    }

    # 默认参数模板（根据 api——info/bocomsearch）
    DEFAULT_REQ_PARAM: Dict[str, Any] = {
        "sourceType": "HNSS",
        # 将 summaryQuestion 设为查询字符串
        # "summaryQuestion": query,
        "repository": "aggregation-search",
        "param": {
            "rerankFlag": 1,
            "spaceCodes": ["SP0999999"],
            "textTopN": 10,
            "vectorTopN": 30,
            "attachFlag": 1,
            "qaType": [0, 1],
        },
    }


def _build_form_payload(query: str) -> Dict[str, str]:
    """构建 REQ_MESSAGE 表单字段"""
    payload = {
        "REQ_HEAD": {"TRANS_PROCESS": "", "TRAN_ID": ""},
        "REQ_BODY": {
            "param": {
                **BocomSearchConfig.DEFAULT_REQ_PARAM,
                "summaryQuestion": query,
            }
        },
    }
    return {"REQ_MESSAGE": json.dumps(payload, ensure_ascii=False)}


def _parse_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """解析 API 响应为标准结构"""
    results: List[Dict[str, Any]] = []

    rsp_head = data.get("RSP_HEAD", {})
    if rsp_head.get("TRAN_SUCCESS") != "1":
        logger.warning(f"Bocom search API returned error: {rsp_head}")
        return results

    rsp_body = data.get("RSP_BODY", {})
    api_results = rsp_body.get("result", [])

    for item in api_results:
        title = (item.get("title") or "").strip()
        content = (item.get("content") or item.get("absContent") or "").strip()
        score_raw = item.get("score")
        try:
            score = float(score_raw) if score_raw is not None else 0.0
        except Exception:
            score = 0.0

        results.append(
            {
                "title": title,
                "content": content,
                "score": score,
                "url": item.get("url") or "",
                "source": item.get("source") or "bocomsearch",
                "category": item.get("fullCategoryName", ""),
                "createTime": item.get("createTime", ""),
                "docGuid": item.get("docGuid", ""),
                "repository": item.get("repository", ""),
                "attachEcmId": item.get("attachEcmId", ""),
                "fromAttachment": bool(item.get("fromAttachment", False)),
                "category": item.get("fullCategoryName", ""),
                "createTime": item.get("createTime", ""),
            }
        )

            #         result = {
            #     # === 核心必需字段 ===
            #     "title": item.get("title", "").strip(),
            #     "content": item.get("content", "").strip() or item.get("absContent", "").strip(),
            #     "score": float(item.get("score", 0)) if item.get("score") else 0.0,
            #     "url": item.get("url") or "",  # url可能为None
            #     "source": item.get("source", ""),

            #     # === 次要可选字段 ===
            #     "category": item.get("fullCategoryName", ""),
            #     "createTime": item.get("createTime", ""),  # 创建时间
            # }

    # 简单排序与截断，可根据需要调整
    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return results


def call_bocomsearch(query: str, guwp_token: Optional[str] = None, timeout: int = 30, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    调用交通银行搜索接口

    Args:
        query: 搜索查询字符串
        guwp_token: 鉴权令牌（可选）。未提供时从环境变量 GUWP_TOKEN 读取
        timeout: 请求超时秒数

    Returns:
        标准化搜索结果列表
    """
    token = guwp_token or os.getenv("GUWP_TOKEN", "").strip()
    if not token:
        logger.warning("GUWP_TOKEN is empty; bocomsearch may fail due to missing auth header")

    headers = {**BocomSearchConfig.HEADERS_BASE, "guwp-token": token} if token else BocomSearchConfig.HEADERS_BASE
    form_data = _build_form_payload(query)

    try:
        resp = requests.post(BocomSearchConfig.API_URL, headers=headers, data=form_data, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        results = _parse_response(data)
        # 截断到 max_results（若提供）
        return results[:max_results] if (max_results and max_results > 0) else results
    except requests.exceptions.RequestException as e:
        logger.error(f"Bocom search API request failed: {e}")
        return [
            {
                "title": "搜索错误",
                "url": "",
                "content": f"搜索服务出现错误: {str(e)}",
                "source": "bocomsearch",
                "score": 0.0,
            }
        ]
    except Exception as e:
        logger.error(f"Unexpected error in bocomsearch: {e}")
        return [
            {
                "title": "搜索错误",
                "url": "",
                "content": f"搜索服务出现错误: {str(e)}",
                "source": "bocomsearch",
                "score": 0.0,
            }
        ]


@tool
def bocomsearch(query: str) -> List[Dict[str, Any]]:
    """
    交通银行搜索工具

    直接传入查询字符串，令牌默认从环境变量 GUWP_TOKEN 读取；如需覆盖，可改为调用 `call_bocomsearch(query, guwp_token="...")`
    """
    return call_bocomsearch(query=query, max_results=10)


def create_budget_controlled_bocomsearch_tool(
    session_id: str = "default",
    max_search_calls: int = 5,
    max_tokens: int = 10000,
    max_results: int = 10,
    guwp_token: Optional[str] = None,
):
    """
    创建带预算控制的交通银行搜索工具
    
    与 budget_controlled_online_search 共用预算管理器，确保总搜索量不超限
    
    Args:
        session_id: 会话ID，用于隔离不同用户的预算
        max_search_calls: 最大搜索调用次数（与 online_search 共享）
        max_tokens: 最大token预算（与 online_search 共享）
        max_results: 单次搜索返回的最大结果数
        guwp_token: GUWP认证令牌，未提供时从环境变量读取
        
    Returns:
        BudgetControlledBocomSearchTool: 带预算控制的搜索工具实例
    """
    from src.tools.budget_controlled_search import BudgetControlledSearchTool
    from langchain_core.tools import BaseTool
    from langchain_core.callbacks import CallbackManagerForToolRun
    
    # 创建 bocomsearch 基础工具类
    class BocomSearchBaseTool(BaseTool):
        """Bocom搜索基础工具，适配 BudgetControlledSearchTool"""
        name: str = "bocomsearch"
        description: str = "搜索交通银行内部知识库。适用于查询银行政策、产品信息、业务流程、合规要求等内部资料。"
        max_results: int = 10
        guwp_token: Optional[str] = None
        
        def __init__(self, max_results: int = 10, guwp_token: Optional[str] = None, **kwargs):
            super().__init__(**kwargs)
            self.max_results = max_results
            self.guwp_token = guwp_token
        
        def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
            **kwargs
        ) -> List[Dict[str, Any]]:
            """执行搜索"""
            return call_bocomsearch(
                query=query,
                guwp_token=self.guwp_token,
                max_results=self.max_results,
            )
    
    # 创建基础工具实例
    base_tool = BocomSearchBaseTool(max_results=max_results, guwp_token=guwp_token)
    
    # 创建预算控制包装器
    return BudgetControlledSearchTool(
        wrapped_tool=base_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
    )


__all__ = [
    "BocomSearchConfig",
    "call_bocomsearch",
    "bocomsearch",
    "create_budget_controlled_bocomsearch_tool",
]
