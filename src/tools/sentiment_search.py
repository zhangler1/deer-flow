# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
舆情数据检索工具

通过调用企业知识库API，查询企业的舆情信息。
支持企业名称搜索，返回企业的舆情数据，包括人员变动、股东变动、董监高变动等信息。
"""

import logging
import os
import requests
import json
from typing import Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


class SentimentSearchConfig:
    """舆情数据检索配置"""

    # API 配置 - 从环境变量获取
    BASE_URL = os.getenv("EUVD_API_URL", "http://12.244.113.82/EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do")

    # 请求头配置
    HEADERS = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Content-Type": "multipart/form-data",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
        "caller": "sjyh",
        "jumpcloud-ENV": "BASE",
    }

    # Cookie（如果需要的话，可以从环境变量读取）
    COOKIES = {
        # 可以根据需要添加 cookies
    }


def _build_request_body(
    keyword: str,
    user_code: str = "147852",
    search_type: str = "0",
    vector_top_n: int = 1,
    space_code_list: list = None,
    caller: str = "P2025094",
    customized_tag_list: list = None,
) -> Dict[str, Any]:
    """构建请求体"""

    if space_code_list is None:
        space_code_list = ["SP0000082"]

    if customized_tag_list is None:
        customized_tag_list = ["sentiment"]

    req_body = {
        "REQ_HEAD": {},
        "REQ_BODY": {
            "param": {
                "keyword": keyword,
                "userCode": user_code,
                "searchType": search_type,
                "qaType": [0],
                "vectorTopN": vector_top_n,
                "spaceCodeList": space_code_list,
                "caller": caller,
                "customizedTagList": customized_tag_list
            }
        }
    }

    return req_body


def _extract_sentiment_info(sentiment: Dict[str, Any]) -> str:
    """提取单个舆情信息"""
    try:
        para_title = sentiment.get("paraTitle", "无标题")
        content = sentiment.get("content", "")
        score = sentiment.get("score", 0)
        rerank_score = sentiment.get("rerankScore")

        # 构建舆情信息
        info = f"""企业名称: {para_title}
匹配度: {score:.4f}"""

        if rerank_score is not None:
            info += f"\n重排序得分: {rerank_score:.4f}"

        if content:
            info += f"\n舆情数据:\n{content}"

        return info
    except Exception as e:
        logger.error(f"提取舆情信息失败: {e}")
        return json.dumps(sentiment, ensure_ascii=False, indent=2)


def call_sentiment_search(
    keyword: str,
    timeout: int = 30
) -> str:
    """
    调用舆情数据检索API

    Args:
        keyword: 搜索关键词（企业名称），例如 "河北双星种业股份有限公司"
        timeout: 超时时间（秒）

    Returns:
        str: API 返回的舆情数据信息
    """
    try:
        logger.info(
            f"🔰 调用舆情数据检索 | 企业名称: '{keyword}'"
        )

        # 构建请求体
        request_body = _build_request_body(keyword=keyword)

        logger.debug(f"📤 发送请求体: {json.dumps(request_body, ensure_ascii=False, indent=2)}")

        # 将请求体转换为表单数据格式
        form_data = {
            "REQ_MESSAGE": json.dumps(request_body, ensure_ascii=False)
        }

        # 发送请求
        base_url = SentimentSearchConfig.BASE_URL
        response = requests.post(
            base_url,
            headers=SentimentSearchConfig.HEADERS,
            cookies=SentimentSearchConfig.COOKIES,
            data=form_data,
            timeout=timeout
        )

        # 检查响应状态
        response.raise_for_status()

        # 打印原始响应文本以便调试
        logger.debug(f"📥 响应状态码: {response.status_code}")
        logger.debug(f"📥 响应Content-Type: {response.headers.get('content-type', 'N/A')}")
        logger.debug(f"📥 响应文本（前500字符）: {response.text[:500]}")

        # 解析响应
        try:
            result = response.json()
        except ValueError as e:
            logger.error(f"❌ JSON解析失败: {e}")
            logger.error(f"❌ 完整响应文本: {response.text}")
            raise

        logger.info(f"✅ 舆情数据检索响应成功 | 状态码: {response.status_code}")

        # 提取舆情数据内容
        sentiment_content = _extract_sentiments(result, keyword)

        return sentiment_content

    except requests.exceptions.Timeout:
        error_msg = f"舆情数据检索请求超时 (>{timeout}s)"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except requests.exceptions.RequestException as e:
        error_msg = f"舆情数据检索请求失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except Exception as e:
        error_msg = f"处理舆情数据检索响应时出错: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"


def _extract_sentiments(result: Dict[str, Any], keyword: str) -> str:
    """从API响应中提取舆情数据内容"""
    try:
        # 检查响应状态
        if "RSP_HEAD" in result:
            trans_success = result["RSP_HEAD"].get("TRAN_SUCCESS")
            if trans_success != "1":
                error_msg = result["RSP_HEAD"].get("PROCESS_STATUS_CODE", "未知错误")
                return f"API返回错误: {error_msg}"

        # 提取舆情数据列表
        if "RSP_BODY" in result:
            rsp_body = result["RSP_BODY"]
            result_data = rsp_body.get("result", {})

            # 优先返回向量检索结果
            vector_list = result_data.get("vectorGroupList", [])
            text_list = result_data.get("textGroupList", [])

            # 合并结果，优先使用向量检索结果
            all_sentiments = vector_list if vector_list else text_list

            if not all_sentiments:
                return f"未找到相关舆情数据。企业名称: {keyword}"

            # 构建舆情信息摘要
            sentiment_infos = []
            for i, sentiment in enumerate(all_sentiments, 1):
                sentiment_info = _extract_sentiment_info(sentiment)
                sentiment_infos.append(f"【舆情数据 {i}】\n{sentiment_info}")

            # 添加总览信息
            total_count = len(all_sentiments)
            summary = f"""查询成功！
企业名称: {keyword}
数据类型说明: 包括人员变动、股东变动、董监高变动、持股情况变动等舆情信息
返回数量: {total_count}

{'=' * 80}

"""

            return summary + "\n\n" + "\n\n" + "-" * 80 + "\n\n".join(sentiment_infos)

        # 如果无法提取，返回原始结果
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"提取舆情数据内容失败: {e}")
        return json.dumps(result, ensure_ascii=False, indent=2)


# ===== LangChain Tool 封装 =====

@tool
def sentiment_search(
    keyword: str
) -> str:
    """
    舆情数据检索工具

    通过企业名称搜索企业的舆情数据，包括人员变动、股东变动、董监高变动、持股情况变动等信息。

    Args:
        keyword: 搜索关键词（企业全称），例如 "河北双星种业股份有限公司"

    Returns:
        paraTitle: 企业名称
        content: 舆情数据详情（包括人员变动、股东变动、董监高变动等信息）
        score: 匹配度等详细信息。

    Examples:
        >>> # 查询河北双星种业的舆情数据
        >>> sentiment_search(keyword="河北双星种业股份有限公司")
        >>> # 查询其他企业的舆情数据
        >>> sentiment_search(keyword="某某科技有限公司")
    """
    return call_sentiment_search(keyword=keyword)


# 导出工具
__all__ = [
    "SentimentSearchConfig",
    "call_sentiment_search",
    "sentiment_search",
]
