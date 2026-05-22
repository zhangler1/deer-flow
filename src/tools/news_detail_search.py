# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
新闻详情查询工具

通过调用新闻详情API，根据新闻ID查询完整的新闻内容。
通常与 news_search 工具配合使用：
1. 先使用 news_search 获取新闻列表
2. 再使用本工具根据新闻ID查询完整内容
"""

import logging
import os
import requests
import json
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger


class NewsDetailSearchConfig:
    """新闻详情查询配置"""

    # API 配置 - 从环境变量获取
    BASE_URL = os.getenv("NEWS_DETAIL_API_URL")

    # 请求头配置
    HEADERS = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
    }

    # Cookie（如果需要的话，可以从环境变量读取）
    COOKIES = {
        # 可以根据需要添加 cookies
    }


def _build_request_body(
    news_id: str,
    news_type: int = 5
) -> Dict[str, Any]:
    """构建请求体"""

    req_body = {
        "REQ_HEAD": {
            "TRAN_PROCESS": "",
            "TRAN_ID": ""
        },
        "REQ_BODY": {
            "newsType": news_type,
            "newsId": news_id
        }
    }

    return req_body


def _extract_news_detail(news_detail: Dict[str, Any]) -> str:
    """提取新闻详情信息"""
    try:
        title = news_detail.get("title", "无标题")
        source = news_detail.get("source", "未知来源")
        publish_time = news_detail.get("publishTime", "N/A")
        category = news_detail.get("category", "")
        authors = news_detail.get("authors", [])
        content_abstract = news_detail.get("contentAbstract", "")
        content = news_detail.get("content", "")

        # 构建作者信息
        authors_str = "、".join(authors) if authors else "未知"

        # 构建新闻详情
        detail = f"""标题: {title}
来源: {source}
作者: {authors_str}
发布时间: {publish_time}
分类: {category}
"""
        if content_abstract:
            detail += f"\n摘要: {content_abstract}"

        if content:
            # 清理HTML标签
            import re
            clean_content = re.sub(r'<[^>]+>', '', content)
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            detail += f"\n\n正文内容:\n{clean_content}"

        return detail
    except Exception as e:
        logger.error(f"提取新闻详情失败: {e}")
        return json.dumps(news_detail, ensure_ascii=False, indent=2)


def call_news_detail_search(
    news_id: str,
    timeout: int = 30
) -> str:
    """
    调用新闻详情查询API

    Args:
        news_id: 新闻ID，通常从 news_search 工具返回的新闻列表中获取
        timeout: 超时时间（秒）

    Returns:
        str: API 返回的新闻详情，包括标题、来源、作者、发布时间、正文等完整信息
    """
    try:
        logger.info(
            f"📰 调用新闻详情查询 | newsId: {news_id}"
        )

        # 构建请求体
        request_body = _build_request_body(
            news_id=news_id
        )

        logger.debug(f"📤 发送请求体: {json.dumps(request_body, ensure_ascii=False, indent=2)}")

        # 将请求体转换为表单数据格式
        form_data = {
            "REQ_MESSAGE": json.dumps(request_body, ensure_ascii=False)
        }

        # 发送请求
        base_url = os.getenv("NEWS_DETAIL_API_URL")
        response = requests.post(
            base_url,
            headers=NewsDetailSearchConfig.HEADERS,
            cookies=NewsDetailSearchConfig.COOKIES,
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

        logger.info(f"✅ 新闻详情查询响应成功 | 状态码: {response.status_code}")

        # 提取新闻详情
        news_detail = _extract_detail(result)

        return news_detail

    except requests.exceptions.Timeout:
        error_msg = f"新闻详情查询请求超时 (>{timeout}s)"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except requests.exceptions.RequestException as e:
        error_msg = f"新闻详情查询请求失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except Exception as e:
        error_msg = f"处理新闻详情查询响应时出错: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"


def _extract_detail(result: Dict[str, Any]) -> str:
    """从API响应中提取新闻详情"""
    try:
        # 检查响应状态
        if "RSP_HEAD" in result:
            trans_success = result["RSP_HEAD"].get("TRAN_SUCCESS")
            if trans_success != "1":
                error_msg = result["RSP_HEAD"].get("PROCESS_STATUS_CODE", "未知错误")
                return f"API返回错误: {error_msg}"

        # 提取新闻详情
        if "RSP_BODY" in result:
            rsp_body = result["RSP_BODY"]
            news_detail = rsp_body.get("industryNewsVO", {})

            if not news_detail:
                return f"未找到新闻详情。新闻ID: {rsp_body.get('newsId', 'N/A')}"

            # 提取并格式化新闻详情
            detail_info = _extract_news_detail(news_detail)

            # 添加总览信息
            news_id = rsp_body.get("newsId", "N/A")

            summary = f"""新闻详情查询成功！
新闻ID: {news_id}

{'=' * 80}

{detail_info}

{'=' * 80}
"""

            return summary

        # 如果无法提取，返回原始结果
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"提取新闻详情失败: {e}")
        return json.dumps(result, ensure_ascii=False, indent=2)


# ===== LangChain Tool 封装 =====

@tool
def news_detail_search(
    news_id: str
) -> str:
    """
    新闻详情查询工具

    根据新闻ID查询完整的新闻内容，包括标题、来源、作者、发布时间、正文等详细信息。

    Args:
        news_id: 新闻ID，通常从 news_search 工具返回的新闻列表中获取。

    Returns:
        str: 新闻详情，包括标题、来源、作者、发布时间、摘要、正文等完整内容。

    Examples:
        >>> # 查询特定新闻的详情
        >>> news_detail_search(news_id="23a44269182eaec0c29085975f90f15e")

    Notes:
        - 通常与 news_search 工具配合使用
        - 先使用 news_search 获取新闻列表和新闻ID
        - 再使用本工具根据感兴趣的新闻ID查询完整内容
        - 返回的内容包含完整的新闻正文
    """
    return call_news_detail_search(news_id=news_id)


# 导出工具
__all__ = [
    "NewsDetailSearchConfig",
    "call_news_detail_search",
    "news_detail_search",
]
