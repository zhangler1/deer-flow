# SPDX-License-Identifier: MIT

"""
EUVD 段落级标准知识检索工具（searchknowledge_standard）

基于 middlewares/search/api——info/searchknowledgeStandard 提供的请求格式，
实现对 EUVD 段落级知识检索接口的调用。

特点：
- 与 bocomsearch 同样使用 application/x-www-form-urlencoded + REQ_MESSAGE
- 接口直接通过 caller / userCode 鉴权（默认值硬编码，可被环境变量覆盖）
- 响应格式：RSP_BODY.result.vectorGroupList[*]
- 输出：DeerFlow 标准结构（title / content / score / url / source / category /
  createTime / docGuid / repository / attachEcmId / fromAttachment / pubTime）

环境变量（均可选，未设置时回退到硬编码默认值）：
- SEARCHKNOWLEDGE_API_URL    接口地址
- SEARCHKNOWLEDGE_CALLER     调用方编码（caller）
- SEARCHKNOWLEDGE_USER_CODE  用户编码（userCode）
- SEARCHKNOWLEDGE_SPACE_CODES 空间编码列表，逗号分隔，例如 "SP0999999,SP0000036"
- SEARCHKNOWLEDGE_VECTOR_TOPN 向量召回TopN（默认 3）
- SEARCHKNOWLEDGE_TEXT_TOPN  文本召回TopN（默认 0）
- SEARCHKNOWLEDGE_THRESHOLD  匹配分阈值（默认 0.1）
- SEARCHKNOWLEDGE_MAX_RESULTS 最大返回条数（默认 2，作用于本地截断）

返回条数优先级：调用显式传入 max_results > 环境变量 SEARCHKNOWLEDGE_MAX_RESULTS > 硬编码默认 2
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests
from langchain_core.tools import tool  # type: ignore

from src.tools.bocom_search import SearchResultItem, _validate_search_results

logger = logging.getLogger(__name__)


class SearchKnowledgeStandardConfig:
    """EUVD 段落级标准知识检索配置（默认值硬编码 + 环境变量可覆盖）"""

    # 真实接口地址
    API_URL: str = os.getenv(
        "SEARCHKNOWLEDGE_API_URL",
        "http://euvd-chn-slb-7002.bocomm.com/EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do",
    )

    HEADERS_BASE: Dict[str, str] = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "DeerFlow-SearchKnowledgeStandard/1.0",
    }

    # 默认 caller / userCode（参考 request.sh）
    DEFAULT_CALLER: str = os.getenv("SEARCHKNOWLEDGE_CALLER", "P2024146")
    DEFAULT_USER_CODE: str = os.getenv("SEARCHKNOWLEDGE_USER_CODE", "9855835")

    # spaceCodeList：逗号分隔，默认 SP0999999
    @classmethod
    def default_space_codes(cls) -> List[str]:
        raw = os.getenv("SEARCHKNOWLEDGE_SPACE_CODES", "SP0999999")
        return [c.strip() for c in raw.split(",") if c.strip()]

    # 召回参数
    @classmethod
    def default_vector_topn(cls) -> int:
        try:
            return int(os.getenv("SEARCHKNOWLEDGE_VECTOR_TOPN", "3"))
        except (TypeError, ValueError):
            return 3

    @classmethod
    def default_text_topn(cls) -> int:
        try:
            return int(os.getenv("SEARCHKNOWLEDGE_TEXT_TOPN", "0"))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def default_threshold(cls) -> float:
        try:
            return float(os.getenv("SEARCHKNOWLEDGE_THRESHOLD", "0.1"))
        except (TypeError, ValueError):
            return 0.1

    @classmethod
    def default_max_results(cls) -> int:
        """最大返回条数：env SEARCHKNOWLEDGE_MAX_RESULTS > 硬编码默认 2"""
        try:
            return int(os.getenv("SEARCHKNOWLEDGE_MAX_RESULTS", "2"))
        except (TypeError, ValueError):
            return 2


def _build_form_payload(
    query: str,
    vector_topn: Optional[int] = None,
    text_topn: Optional[int] = None,
    threshold: Optional[float] = None,
) -> Dict[str, str]:
    """构建 REQ_MESSAGE 表单字段（参照 request.sh 模板）"""
    payload = {
        "REQ_HEAD": {},
        "REQ_BODY": {
            "param": {
                "keyword": query,
                "caller": SearchKnowledgeStandardConfig.DEFAULT_CALLER,
                "userCode": SearchKnowledgeStandardConfig.DEFAULT_USER_CODE,
                "searchType": "2",
                "qaType": [1],
                "domainTagList": [],
                "spaceCodeList": SearchKnowledgeStandardConfig.default_space_codes(),
                "customizedTagList": [],
                "vectorTopN": vector_topn if vector_topn is not None
                else SearchKnowledgeStandardConfig.default_vector_topn(),
                "textTopN": text_topn if text_topn is not None
                else SearchKnowledgeStandardConfig.default_text_topn(),
                "model": 0,
                "attachFlag": 1,
                "threshold": threshold if threshold is not None
                else SearchKnowledgeStandardConfig.default_threshold(),
                "publishedFlag": 0,
                "latestFlag": None,
                "delFlag": 0,
            }
        },
    }
    return {"REQ_MESSAGE": json.dumps(payload, ensure_ascii=False)}


def _normalize_category(tags: Any) -> str:
    """将 customizedTags 归一为字符串：列表则用 / 连接，过滤掉无意义码值"""
    if not tags:
        return ""
    if isinstance(tags, str):
        return tags
    if isinstance(tags, list):
        return "/".join(str(t) for t in tags if t)
    return str(tags)


def _parse_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """解析 EUVD 响应为 DeerFlow 标准结构

    丢弃对 LLM 无语义价值的字段：
      rerankScore / taskId / mainTaskId / updateTime / validTimeStart /
      validTimeEnd / sourceOrgId / knType / qaType / page / sorted /
      domainTags / sceneCodes / textGroupList / graphGroupList /
      rerankResultList / rerankResultStatus / groupPagination

    保留的有语义字段：
      title (paraTitle) / content / score / source (fileName) /
      docGuid (fileId) / category (customizedTags) / createTime /
      pubTime (附加) / fromAttachment
    """
    results: List[Dict[str, Any]] = []

    rsp_head = data.get("RSP_HEAD", {}) or {}
    if rsp_head.get("TRAN_SUCCESS") != "1":
        logger.warning(f"searchknowledge_standard | 接口返回失败 RSP_HEAD={rsp_head}")
        return results

    rsp_body = data.get("RSP_BODY", {}) or {}
    result_block = rsp_body.get("result", {}) or {}
    vector_list = result_block.get("vectorGroupList", []) or []

    for item in vector_list:
        if not isinstance(item, dict):
            continue
        para_title = (item.get("paraTitle") or "").strip()
        file_name = (item.get("fileName") or "").strip()
        content = (item.get("content") or "").strip()

        score_raw = item.get("score")
        try:
            score = float(score_raw) if score_raw is not None else 0.0
        except (TypeError, ValueError):
            score = 0.0

        # title 优先 paraTitle（段落小标题更贴合语义），缺失则用 fileName
        title = para_title or file_name

        results.append(
            {
                "title": title,
                "content": content,
                "score": score,
                "url": "",  # 接口不返回 URL
                "source": file_name or "searchknowledge_standard",
                "category": _normalize_category(item.get("customizedTags")),
                "createTime": item.get("createTime") or "",
                "docGuid": item.get("fileId") or "",
                "repository": "searchknowledge_standard",
                "attachEcmId": "",
                "fromAttachment": bool(item.get("fromAttachment") or False),
                # —— 附加语义字段：发布时间，对时效性查询有帮助 ——
                "pubTime": item.get("pubTime") or "",
            }
        )

    # 按 score 排序
    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    _validate_search_results(results, context="searchknowledge_standard._parse_response")
    return results


def call_searchknowledge_standard(
    query: str,
    timeout: int = 30,
    max_results: Optional[int] = None,
    vector_topn: Optional[int] = None,
    text_topn: Optional[int] = None,
    threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """调用 EUVD 段落级标准知识检索接口

    Args:
        query: 检索关键词
        timeout: 请求超时秒数
        max_results: 截断的最大返回条数
        vector_topn / text_topn / threshold: 召回参数，未传则使用环境变量/默认值

    Returns:
        DeerFlow 标准结构的检索结果列表
    """
    logger.info(
        f"🔍 searchknowledge_standard | 搜索 | 查询='{query}'"
    )

    start_time = time.time()

    headers = dict(SearchKnowledgeStandardConfig.HEADERS_BASE)
    form_data = _build_form_payload(
        query, vector_topn=vector_topn, text_topn=text_topn, threshold=threshold,
    )

    # 调试用 pretty body
    try:
        req_message_pretty = json.dumps(
            json.loads(form_data["REQ_MESSAGE"]), ensure_ascii=False, indent=2,
        )
    except Exception:
        req_message_pretty = form_data.get("REQ_MESSAGE", "")
    debug_block = (
        f"\n─── searchknowledge_standard REQUEST ───\n"
        f"POST {SearchKnowledgeStandardConfig.API_URL}\n"
        f"Headers:\n{json.dumps(headers, ensure_ascii=False, indent=2)}\n"
        f"Body (application/x-www-form-urlencoded):\n"
        f"REQ_MESSAGE=\n{req_message_pretty}\n"
        f"────────────────────────────────────────\n"
    )
    logger.debug(
        f"📡 searchknowledge_standard | 发起请求 | url={SearchKnowledgeStandardConfig.API_URL}"
        f"{debug_block}"
    )

    try:
        resp = requests.post(
            SearchKnowledgeStandardConfig.API_URL,
            headers=headers,
            data=form_data,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        rsp_head = data.get("RSP_HEAD", {}) or {}
        tran_success = rsp_head.get("TRAN_SUCCESS")
        vector_count = len(
            (data.get("RSP_BODY", {}) or {}).get("result", {}).get("vectorGroupList", []) or []
        )


        results = _parse_response(data)
        # 优先级：调用显式传入 > env SEARCHKNOWLEDGE_MAX_RESULTS > 默认 2
        effective_max = (
            max_results
            if (max_results and max_results > 0)
            else SearchKnowledgeStandardConfig.default_max_results()
        )
        trimmed = results[:effective_max]
        duration = time.time() - start_time
        # 对齐 online_search 的日志格式：成功时仅输出一条 HTTP响应汇总日志
        logger.info(
            f"📡 searchknowledge_standard | HTTP响应 | status={resp.status_code} | "
            f"content-length={len(resp.content)} | encoding={resp.encoding} | "
            f"result条数={len(trimmed)} | "
            f"耗时={duration:.1f}s"
        )
        return trimmed

    except requests.exceptions.RequestException as e:
        duration = time.time() - start_time
        logger.error(
            f"❌ searchknowledge_standard | 请求失败 | type={type(e).__name__} | 耗时={duration:.2f}s | error={e}"
        )
        return [
            {
                "title": "搜索错误",
                "content": f"标准知识检索服务出现错误: {str(e)}",
                "score": 0.0,
                "url": "",
                "source": "searchknowledge_standard",
                "category": "",
                "createTime": "",
                "docGuid": "",
                "repository": "searchknowledge_standard",
                "attachEcmId": "",
                "fromAttachment": False,
                "pubTime": "",
            }
        ]
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"❌ searchknowledge_standard | 异常 | type={type(e).__name__} | 耗时={duration:.2f}s | error={e}"
        )
        return [
            {
                "title": "搜索错误",
                "content": f"标准知识检索服务出现错误: {str(e)}",
                "score": 0.0,
                "url": "",
                "source": "searchknowledge_standard",
                "category": "",
                "createTime": "",
                "docGuid": "",
                "repository": "searchknowledge_standard",
                "attachEcmId": "",
                "fromAttachment": False,
                "pubTime": "",
            }
        ]


@tool
def searchknowledge_standard(query: str) -> List[Dict[str, Any]]:
    """段落级标准知识检索工具（EUVD）

    适用于查询行业政策、研报段落级语义片段等结构化知识库内容。
    输入应为完整的检索关键词，返回带相关度评分的段落列表。
    返回条数由 env SEARCHKNOWLEDGE_MAX_RESULTS 控制，默认 2。
    """
    return call_searchknowledge_standard(query=query)


__all__ = [
    "SearchKnowledgeStandardConfig",
    "call_searchknowledge_standard",
    "searchknowledge_standard",
]
