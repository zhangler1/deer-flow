# SPDX-License-Identifier: MIT

"""
向量相似度检索工具（vector_search）

基于 EUVD 向量检索 API 提供的请求格式，实现内部知识库的精准向量检索。
- 通过 header `guwp-token` 进行鉴权
- 使用 `application/json` 请求体格式（区别于 bocomsearch 的 form-urlencoded）
- 请求体结构为 `{"REQ_HEAD": {...}, "REQ_BODY": {"param": {"summaryQuestion": query, ...}}}`
- 将响应解析为 DeerFlow 标准结构（title, content, score, url, source）

使用方式：
- 默认从环境变量 `GUWP_TOKEN` 读取 token
- 也可在函数调用时显式传入 `guwp_token`
- 通过中间件从 state 注入 token（LLM 不可见）

配置优先级：conf.yaml VECTOR_SEARCH 段 > 环境变量 > 硬编码默认值
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests
from langchain_core.tools import tool  # type: ignore
from pydantic import BaseModel, Field, ValidationError

from src.tools.bocom_search import SearchResultItem, _validate_search_results
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger


# ============================================================================
# 配置类
# ============================================================================


class VectorSearchConfig:
    """向量检索配置

    三级配置优先级：conf.yaml VECTOR_SEARCH 段 > 环境变量 > 硬编码默认值
    """

    API_URL: str = os.getenv(
        "VECTOR_SEARCH_API_URL",
        "",
    )

    TIMEOUT: int = int(os.getenv("VECTOR_SEARCH_TIMEOUT", "30"))

    PAGE_SIZE: int = int(os.getenv("VECTOR_SEARCH_PAGE_SIZE", "10"))

    REPOSITORY: str = os.getenv(
        "VECTOR_SEARCH_REPOSITORY",
        "aggregation-search",
    )

    SEARCH_TYPE: str = os.getenv("VECTOR_SEARCH_SEARCH_TYPE", "2")

    SPACE_CODES: List[str] = os.getenv(
        "VECTOR_SEARCH_SPACE_CODES", ""
    ).split(",") if os.getenv("VECTOR_SEARCH_SPACE_CODES") else ["SP0999999"]

    RERANK_FLAG: int = int(os.getenv("VECTOR_SEARCH_RERANK_FLAG", "1"))

    CHANNEL_ID: str = os.getenv("VECTOR_SEARCH_CHANNEL_ID", "0")

    TEXT_TOP_N: int = int(os.getenv("VECTOR_SEARCH_TEXT_TOP_N", "7"))

    VECTOR_TOP_N: int = int(os.getenv("VECTOR_SEARCH_VECTOR_TOP_N", "10"))

    QA_TYPE: List[int] = [0, 1]

    MATCH_FIELDS: List[str] = ["title", "content", "attachTitles", "attachContent"]

    KNOW_STATUS: List[str] = ["3", "4"]

    ONLINE_STATUS: List[str] = ["3", "4"]

    KP_STATUS: List[str] = ["3", "4"]

    # 默认请求头（除 guwp-token 外）
    HEADERS_BASE: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "User-Agent": "DeerFlow-VectorSearch/1.0",
    }


def _load_vector_search_yaml_section() -> Dict[str, Any]:
    """从 conf.yaml 加载 VECTOR_SEARCH 配置段"""
    try:
        from src.llms.llm import _get_config_file_path
        from src.config import load_yaml_config

        raw = load_yaml_config(_get_config_file_path()).get("VECTOR_SEARCH", {}) or {}
    except Exception as e:
        logger.warning(f"读取 VECTOR_SEARCH 配置段失败，将使用默认值: {e}")
        return {}
    return raw


def get_vector_search_config() -> Dict[str, Any]:
    """获取合并后的 vector_search 配置

    优先级：conf.yaml VECTOR_SEARCH 段 > 环境变量 > 硬编码默认值

    Returns:
        合并后的配置字典
    """
    yaml_section = _load_vector_search_yaml_section()

    def _pick(yaml_key: str, env_key: str, default: Any) -> Any:
        """优先 yaml > env > default"""
        val = yaml_section.get(yaml_key)
        if val is not None:
            return val
        env_val = os.getenv(env_key)
        if env_val is not None:
            return env_val
        return default

    return {
        "api_url": _pick("api_url", "VECTOR_SEARCH_API_URL", VectorSearchConfig.API_URL),
        "timeout": int(_pick("timeout", "VECTOR_SEARCH_TIMEOUT", VectorSearchConfig.TIMEOUT)),
        "page_size": int(_pick("page_size", "VECTOR_SEARCH_PAGE_SIZE", VectorSearchConfig.PAGE_SIZE)),
        "repository": _pick("repository", "VECTOR_SEARCH_REPOSITORY", VectorSearchConfig.REPOSITORY),
        "search_type": _pick("search_type", "VECTOR_SEARCH_SEARCH_TYPE", VectorSearchConfig.SEARCH_TYPE),
        "space_codes": _pick("space_codes", "VECTOR_SEARCH_SPACE_CODES", VectorSearchConfig.SPACE_CODES),
        "rerank_flag": int(_pick("rerank_flag", "VECTOR_SEARCH_RERANK_FLAG", VectorSearchConfig.RERANK_FLAG)),
        "channel_id": _pick("channel_id", "VECTOR_SEARCH_CHANNEL_ID", VectorSearchConfig.CHANNEL_ID),
        "text_top_n": int(_pick("text_top_n", "VECTOR_SEARCH_TEXT_TOP_N", VectorSearchConfig.TEXT_TOP_N)),
        "vector_top_n": int(_pick("vector_top_n", "VECTOR_SEARCH_VECTOR_TOP_N", VectorSearchConfig.VECTOR_TOP_N)),
        "qa_type": VectorSearchConfig.QA_TYPE,
        "match_fields": VectorSearchConfig.MATCH_FIELDS,
        "know_status": VectorSearchConfig.KNOW_STATUS,
        "online_status": VectorSearchConfig.ONLINE_STATUS,
        "kp_status": VectorSearchConfig.KP_STATUS,
    }


# ============================================================================
# 请求构建 & 响应解析
# ============================================================================


def _build_request_body(query: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """构建向量检索 JSON 请求体

    Args:
        query: 搜索查询字符串（LLM 看到的参数名为 query，请求体字段名为 summaryQuestion）
        config: 可选配置字典，未提供时使用默认配置

    Returns:
        完整的 JSON 请求体字典
    """
    if config is None:
        config = get_vector_search_config()

    return {
        "REQ_HEAD": {
            "TRANS_PROCESS": "",
            "TRAN_ID": "",
        },
        "REQ_BODY": {
            "param": {
                "summaryQuestion": query,
                "pageSize": config.get("page_size", VectorSearchConfig.PAGE_SIZE),
                "repository": config.get("repository", VectorSearchConfig.REPOSITORY),
                "param": {
                    "searchType": config.get("search_type", VectorSearchConfig.SEARCH_TYPE),
                    "spaceCodes": config.get("space_codes", VectorSearchConfig.SPACE_CODES),
                    "rerankFlag": config.get("rerank_flag", VectorSearchConfig.RERANK_FLAG),
                    "channelId": config.get("channel_id", VectorSearchConfig.CHANNEL_ID),
                    "textTopN": config.get("text_top_n", VectorSearchConfig.TEXT_TOP_N),
                    "vectorTopN": config.get("vector_top_n", VectorSearchConfig.VECTOR_TOP_N),
                    "qaType": config.get("qa_type", VectorSearchConfig.QA_TYPE),
                    "matchFields": config.get("match_fields", VectorSearchConfig.MATCH_FIELDS),
                    "knowStatus": config.get("know_status", VectorSearchConfig.KNOW_STATUS),
                    "onlineStatus": config.get("online_status", VectorSearchConfig.ONLINE_STATUS),
                    "kpStatus": config.get("kp_status", VectorSearchConfig.KP_STATUS),
                },
            },
        },
    }


def _parse_response(data: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """解析 EUVD 向量检索 API 响应为 DeerFlow 标准结构

    Args:
        data: API 响应的 JSON 字典
        query: 原始查询字符串（用于错误信息）

    Returns:
        标准化搜索结果列表
    """
    results: List[Dict[str, Any]] = []

    rsp_head = data.get("RSP_HEAD", {})
    if rsp_head.get("TRAN_SUCCESS") != "1":
        error_msg = rsp_head.get("PROCESS_STATUS_CODE", "未知错误")
        logger.warning(f"Vector search API returned error: {rsp_head}")
        return [
            {
                "title": "搜索错误",
                "url": "",
                "content": f"向量检索服务返回错误: {error_msg}",
                "source": "vector_search",
                "score": 0.0,
            }
        ]

    rsp_body = data.get("RSP_BODY", {})
    api_results = rsp_body.get("result", [])

    if not isinstance(api_results, list):
        logger.warning(f"Vector search returned unexpected result payload: {api_results}")
        api_results = []

    if not api_results:
        return [
            {
                "title": "未找到相关内容",
                "url": "",
                "content": f"未找到相关内容。关键词: {query}",
                "source": "vector_search",
                "score": 0.0,
            }
        ]

    for item in api_results:
        title = (item.get("title") or "无标题").strip() if item.get("title") else "无标题"
        content = (item.get("content") or item.get("absContent") or "").strip()
        score_raw = item.get("score")
        try:
            score = float(score_raw) if score_raw not in (None, "") else 0.0
        except (TypeError, ValueError):
            score = 0.0

        # 处理 fullCategoryName：可能是 None、字符串或列表
        raw_category = item.get("fullCategoryName") or ""
        if isinstance(raw_category, list):
            raw_category = "/".join(str(c) for c in raw_category if c)

        results.append(
            {
                # url/title/score 优先序列化，确保 SummarizationMiddleware 截断后
                # best-effort-json-parser 仍能解出关键字段供前端展示
                "url": item.get("url") or "",
                "title": title,
                "score": score,
                "source": item.get("source") or "vector_search",
                "docGuid": item.get("docGuid") or "",
                "category": raw_category,
                "createTime": item.get("createTime") or "",
                "repository": item.get("repository") or "",
                "attachEcmId": item.get("attachEcmId") or "",
                "fromAttachment": bool(item.get("fromAttachment") or False),
                "content": content,  # 长字段放最后，截断时不影响关键元数据
            }
        )

    # 按 score 降序排列
    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    # 验证结果数据类型，仅记录日志不阻断流程
    _validate_search_results(results, context="_parse_response(vector_search)")
    return results


# ============================================================================
# 后端调用
# ============================================================================


def call_vector_search(
    query: str,
    guwp_token: Optional[str] = None,
    timeout: Optional[int] = None,
    max_results: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """调用 EUVD 向量检索 API

    Args:
        query: 搜索查询字符串
        guwp_token: 鉴权令牌（由 VectorSearchBaseTool._run 传入，非 LLM 参数）
        timeout: 请求超时秒数
        max_results: 最大返回条数

    Returns:
        标准化搜索结果列表
    """
    token = guwp_token or os.getenv("GUWP_TOKEN", "").strip()
    token_preview = (token[:8] + "...") if token and len(token) > 8 else token

    config = get_vector_search_config()
    actual_timeout = timeout or config.get("timeout", VectorSearchConfig.TIMEOUT)

    # ── 调试日志1: 入参检查 ──
    logger.info(
        f"🔍 vector_search | 入参 | query='{query}' | token={token_preview} | "
        f"max_results={max_results} | timeout={actual_timeout}"
    )

    if not token:
        logger.warning("🔑 vector_search | GUWP_TOKEN 为空，请求可能因鉴权失败")

    headers = {**VectorSearchConfig.HEADERS_BASE}
    if token:
        headers["guwp-token"] = token

    body = _build_request_body(query, config)

    # ── 调试日志2: 请求详情 ──
    safe_headers = dict(headers)
    if "guwp-token" in safe_headers:
        safe_headers["guwp-token"] = token_preview or "***"
    debug_block = (
        f"\n─── vector_search REQUEST ───\n"
        f"POST {config.get('api_url', VectorSearchConfig.API_URL)}\n"
        f"Headers:\n{json.dumps(safe_headers, ensure_ascii=False, indent=2)}\n"
        f"Body (application/json):\n{json.dumps(body, ensure_ascii=False, indent=2)}\n"
        f"───────────────────────────────────────\n"
    )
    logger.info(f"📡 vector_search | 发起请求{debug_block}")

    try:
        resp = requests.post(
            config.get("api_url", VectorSearchConfig.API_URL),
            headers=headers,
            json=body,
            timeout=actual_timeout,
        )

        # ── 调试日志3: 响应状态 ──
        logger.info(
            f"📡 vector_search | 响应 | status={resp.status_code} | "
            f"content-length={len(resp.content)} | encoding={resp.encoding}"
        )

        resp.raise_for_status()
        data = resp.json()

        # ── 调试日志4: 响应结构 ──
        rsp_head = data.get("RSP_HEAD", {})
        tran_success = rsp_head.get("TRAN_SUCCESS")
        result_count = len(data.get("RSP_BODY", {}).get("result", []))
        logger.info(
            f"📡 vector_search | 解析 | TRAN_SUCCESS={tran_success} | "
            f"result条数={result_count} | RSP_HEAD keys={list(rsp_head.keys())}"
        )

        results = _parse_response(data, query)
        trimmed = results[:max_results] if (max_results and max_results > 0) else results
        logger.info(f"✅ vector_search | 完成 | 结果={len(trimmed)}")
        _validate_search_results(trimmed, context="call_vector_search")
        return trimmed
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ vector_search | 请求失败 | type={type(e).__name__} | error={e}")
        error_result = [
            {
                "title": "搜索错误",
                "url": "",
                "content": f"搜索服务出现错误: {str(e)}",
                "source": "vector_search",
                "score": 0.0,
            }
        ]
        _validate_search_results(error_result, context="request_exception")
        return error_result
    except Exception as e:
        logger.error(f"❌ vector_search | 异常 | type={type(e).__name__} | error={e}")
        error_result = [
            {
                "title": "搜索错误",
                "url": "",
                "content": f"搜索服务出现错误: {str(e)}",
                "source": "vector_search",
                "score": 0.0,
            }
        ]
        _validate_search_results(error_result, context="unexpected_exception")
        return error_result


# ============================================================================
# @tool 快捷入口（无预算控制）
# ============================================================================


@tool
def vector_search(query: str) -> List[Dict[str, Any]]:
    """基于向量相似度精准检索内部知识库，支持混合召回和重排序。

    直接传入查询字符串，令牌默认从环境变量 GUWP_TOKEN 读取；
    如需预算控制和 token 注入，请使用 VectorSearchBaseTool + BudgetControlledSearchTool。
    """
    return call_vector_search(query=query, max_results=10)


# ============================================================================
# VectorSearchBaseTool（原生工具，由中间件注入 guwp_token）
# ============================================================================


from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun


class VectorSearchBaseTool(BaseTool):
    """向量检索基础工具（无状态，原生注册）

    封装 call_vector_search 函数为 LangChain BaseTool 接口。
    guwp_token 由中间件通过 kwargs 注入（来源于 state），不进入 args_schema（LLM 不可见）。
    """

    name: str = "vector_search"
    description: str = "基于向量相似度精准检索内部知识库，支持混合召回和重排序。适用于查询银行政策、产品信息、业务流程、合规要求等内部资料，相比聚合搜索具有更高的检索精度。"
    repository: str = "vector-search"
    max_results: int = 10

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """执行向量检索"""
        guwp_token = kwargs.get("guwp_token") or os.getenv("GUWP_TOKEN", "").strip()
        token_preview = (guwp_token[:8] + "...") if guwp_token and len(guwp_token) > 8 else guwp_token
        logger.info(f"🔑 vector_search | guwp_token={token_preview} | max_results={self.max_results}")
        return call_vector_search(
            query=query,
            guwp_token=guwp_token,
            max_results=self.max_results,
        )


__all__ = [
    "VectorSearchConfig",
    "get_vector_search_config",
    "call_vector_search",
    "vector_search",
    "VectorSearchBaseTool",
]
