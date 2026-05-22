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
from pydantic import BaseModel, Field, ValidationError
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger


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


def _validate_search_results(results: List[Dict[str, Any]], context: str = "") -> None:
    """验证检索结果是否符合 Pydantic 模型定义，不符合则打印日志但不抛异常"""
    for idx, item in enumerate(results):
        try:
            SearchResultItem.model_validate(item)
        except ValidationError as e:
            logger.warning(
                f"检索结果第 {idx + 1} 项数据类型不符合预期"
                f"{f' [{context}]' if context else ''}: {e}"
            )


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

        # 处理 fullCategoryName：可能是 None、字符串或列表
        raw_category = item.get("fullCategoryName") or ""
        if isinstance(raw_category, list):
            raw_category = "/".join(str(c) for c in raw_category if c)

        results.append(
            {
                "title": title,
                "content": content,
                "score": score,
                "url": item.get("url") or "",
                "source": item.get("source") or "bocomsearch",
                "category": raw_category,
                "createTime": item.get("createTime") or "",
                "docGuid": item.get("docGuid") or "",
                "repository": item.get("repository") or "",
                "attachEcmId": item.get("attachEcmId") or "",
                "fromAttachment": bool(item.get("fromAttachment") or False),
            }
        )

    # 简单排序与截断，可根据需要调整
    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    # 验证结果数据类型，仅记录日志不阻断流程
    _validate_search_results(results, context="_parse_response")
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
    token_preview = (token[:8] + "...") if token and len(token) > 8 else token
    
    # ── 调试日志1: 入参检查 ──
    logger.info(
        f"🔍 bocomsearch | 入参 | query='{query}' | token={token_preview} | "
        f"max_results={max_results} | timeout={timeout}"
    )
    
    if not token:
        logger.warning("🔑 bocomsearch | GUWP_TOKEN 为空，请求可能因鉴权失败")

    headers = {**BocomSearchConfig.HEADERS_BASE, "guwp-token": token} if token else BocomSearchConfig.HEADERS_BASE
    form_data = _build_form_payload(query)
    
    # ── 调试日志2: 请求详情（可直接复制到 Apifox/Postman 调试）──
    # headers 脱敏：隐藏 guwp-token 实际值
    safe_headers = dict(headers)
    if "guwp-token" in safe_headers:
        safe_headers["guwp-token"] = token_preview or "***"
    # REQ_MESSAGE 里面是 JSON 字符串，还原为可读的 pretty JSON
    try:
        req_message_pretty = json.dumps(
            json.loads(form_data["REQ_MESSAGE"]),
            ensure_ascii=False,
            indent=2,
        )
    except Exception:
        req_message_pretty = form_data.get("REQ_MESSAGE", "")
    debug_block = (
        f"\n─── bocomsearch REQUEST (可直接复制到 Apifox/Postman) ───\n"
        f"POST {BocomSearchConfig.API_URL}\n"
        f"Headers:\n{json.dumps(safe_headers, ensure_ascii=False, indent=2)}\n"
        f"Body (application/x-www-form-urlencoded):\n"
        f"REQ_MESSAGE=\n{req_message_pretty}\n"
        f"───────────────────────────────────────────────────────────────────────\n"
    )
    logger.info(
        f"📡 bocomsearch | 发起请求 | url={BocomSearchConfig.API_URL} | "
        f"REQ_MESSAGE长度={len(form_data.get('REQ_MESSAGE', ''))}"
        f"{debug_block}"
    )

    try:
        resp = requests.post(BocomSearchConfig.API_URL, headers=headers, data=form_data, timeout=timeout)
        
        # ── 调试日志3: 响应状态 ──
        logger.info(
            f"📡 bocomsearch | 响应 | status={resp.status_code} | "
            f"content-length={len(resp.content)} | encoding={resp.encoding}"
        )
        
        resp.raise_for_status()
        data = resp.json()
        
        # ── 调试日志4: 响应结构 ──
        rsp_head = data.get("RSP_HEAD", {})
        tran_success = rsp_head.get("TRAN_SUCCESS")
        result_count = len(data.get("RSP_BODY", {}).get("result", []))
        logger.info(
            f"📡 bocomsearch | 解析 | TRAN_SUCCESS={tran_success} | "
            f"result条数={result_count} | RSP_HEAD keys={list(rsp_head.keys())}"
        )
        
        results = _parse_response(data)
        trimmed = results[:max_results] if (max_results and max_results > 0) else results
        logger.info(f"✅ bocomsearch | 完成 | 结果={len(trimmed)}")
        _validate_search_results(trimmed, context="call_bocomsearch")
        return trimmed
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ bocomsearch | 请求失败 | type={type(e).__name__} | error={e}")
        error_result = [
            {
                "title": "搜索错误",
                "url": "",
                "content": f"搜索服务出现错误: {str(e)}",
                "source": "bocomsearch",
                "score": 0.0,
            }
        ]
        _validate_search_results(error_result, context="request_exception")
        return error_result
    except Exception as e:
        logger.error(f"❌ bocomsearch | 异常 | type={type(e).__name__} | error={e}")
        error_result = [
            {
                "title": "搜索错误",
                "url": "",
                "content": f"搜索服务出现错误: {str(e)}",
                "source": "bocomsearch",
                "score": 0.0,
            }
        ]
        _validate_search_results(error_result, context="unexpected_exception")
        return error_result


@tool
def bocomsearch(query: str) -> List[Dict[str, Any]]:
    """
    交通银行搜索工具

    直接传入查询字符串，令牌默认从环境变量 GUWP_TOKEN 读取；如需覆盖，可改为调用 `call_bocomsearch(query, guwp_token="...")`
    """
    return call_bocomsearch(query=query, max_results=10)


__all__ = [
    "BocomSearchConfig",
    "call_bocomsearch",
    "bocomsearch",
]
