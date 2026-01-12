# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
新闻列表查询工具

通过调用新闻API，查询各类新闻资讯。
支持多种查询条件：
- 关键词搜索（title）：可以是任意主题的关键词
- 新闻分类（categoryCode）：独家、宏观、行业、大宗
- 日期范围（beginDateStr, endDateStr）
- 排序方式（sortType）：按热度或按时间
- 分页查询（pageNum, pageSize）
"""

import logging
import os
import requests
import json
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


class NewsSearchConfig:
    """新闻查询配置"""

    # API 配置 - 从环境变量获取
    BASE_URL = os.getenv("NEWS_SEARCH_API_URL")

    # 新闻类型映射
    CATEGORY_CODES = {
        "news_exclusive": "独家",
        "news_macro": "宏观",
        "news_region": "行业",
        "news_commodity": "大宗"
    }

    # 排序方式映射
    SORT_TYPES = {
        1: "热度",
        2: "时间"
    }

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
    title: str = "",
    category_code: str = "news_exclusive",
    begin_date_str: str = "",
    end_date_str: str = "",
    page_num: int = 1,
    page_size: int = 2,
    sort_type: int = 1,
    is_random_query: bool = False,
) -> Dict[str, Any]:
    """构建请求体"""

    req_body = {
        "REQ_HEAD": {
            "TRAN_PROCESS": "",
            "TRAN_ID": ""
        },
        "REQ_BODY": {
            "newsType": 5,  # 固定为5
            "sortType": sort_type,
            "title": title,
            "beginDateStr": begin_date_str,
            "isRandomQuery": is_random_query,
            "endDateStr": end_date_str,
            "pageNum": page_num,
            "categoryCode": category_code,
            "pageSize": page_size
        }
    }

    return req_body


def _extract_news_info(news: Dict[str, Any]) -> str:
    """提取单条新闻信息"""
    try:
        title = news.get("title", "无标题")
        id = news.get("id", "无")
        source = news.get("source", "未知来源")
        publish_time = news.get("publishTime", "N/A")
        category = news.get("category", "")
        authors = news.get("authors", [])
        content_abstract = news.get("contentAbstract", "")

        # 构建作者信息
        authors_str = "、".join(authors) if authors else "未知"

        # 构建新闻信息
        info = f"""新闻id: {id}
标题: {title}
来源: {source}
作者: {authors_str}
发布时间: {publish_time}
分类: {category}"""
        if content_abstract:
            info += f"\n摘要: {content_abstract[:100]}..." if len(content_abstract) > 100 else f"\n摘要: {content_abstract}"

        return info
    except Exception as e:
        logger.error(f"提取新闻信息失败: {e}")
        return json.dumps(news, ensure_ascii=False, indent=2)


def call_news_search(
    title: str = "",
    category_code: str = "news_exclusive",
    begin_date_str: str = "",
    end_date_str: str = "",
    page_num: int = 1,
    page_size: int = 5,
    sort_type: int = 1,
    is_random_query: bool = False,
    timeout: int = 30
) -> str:
    """
    调用新闻查询API

    Args:
        title: 搜索关键词，可以是任意主题，如 "人工智能"、"新能源"、"政策" 等
        category_code: 新闻分类代码，可选值: news_exclusive(独家), news_macro(宏观), news_region(行业), news_commodity(大宗)
        begin_date_str: 开始日期，格式如 "2020-11-11 00:00:00"
        end_date_str: 结束日期，格式如 "2025-11-11 00:00:00"
        page_num: 页码，从1开始
        page_size: 每页数量
        sort_type: 排序方式，1=按热度排序，2=按时间排序
        is_random_query: 是否随机查询
        timeout: 超时时间（秒）

    Returns:
        str: API 返回的新闻列表信息
    """
    try:
        category_name = NewsSearchConfig.CATEGORY_CODES.get(
            category_code, category_code
        )
        sort_name = NewsSearchConfig.SORT_TYPES.get(
            sort_type, "未知"
        )

        logger.info(
            f"🔰 调用新闻查询 | 关键词: '{title}' | "
            f"类型: {category_name} | 排序: {sort_name} | "
            f"日期范围: {begin_date_str} ~ {end_date_str} | "
            f"分页: {page_num}/{page_size}"
        )

        # 构建请求体
        request_body = _build_request_body(
            title=title,
            category_code=category_code,
            begin_date_str=begin_date_str,
            end_date_str=end_date_str,
            page_num=page_num,
            page_size=page_size,
            sort_type=sort_type,
            is_random_query=is_random_query
        )

        logger.debug(f"📤 发送请求体: {json.dumps(request_body, ensure_ascii=False, indent=2)}")

        # 将请求体转换为表单数据格式
        form_data = {
            "REQ_MESSAGE": json.dumps(request_body, ensure_ascii=False)
        }

        # 发送请求
        base_url = os.getenv("NEWS_SEARCH_API_URL")
        response = requests.post(
            base_url,
            headers=NewsSearchConfig.HEADERS,
            cookies=NewsSearchConfig.COOKIES,
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

        logger.info(f"✅ 新闻查询响应成功 | 状态码: {response.status_code}")

        # 提取新闻内容
        news_content = _extract_news(result)

        return news_content

    except requests.exceptions.Timeout:
        error_msg = f"新闻查询请求超时 (>{timeout}s)"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except requests.exceptions.RequestException as e:
        error_msg = f"新闻查询请求失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except Exception as e:
        error_msg = f"处理新闻查询响应时出错: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"


def _extract_news(result: Dict[str, Any]) -> str:
    """从API响应中提取新闻内容"""
    try:
        # 检查响应状态
        if "RSP_HEAD" in result:
            trans_success = result["RSP_HEAD"].get("TRAN_SUCCESS")
            if trans_success != "1":
                error_msg = result["RSP_HEAD"].get("PROCESS_STATUS_CODE", "未知错误")
                return f"API返回错误: {error_msg}"

        # 提取新闻列表
        if "RSP_BODY" in result:
            rsp_body = result["RSP_BODY"]
            total = rsp_body.get("total", 0)
            news_list = rsp_body.get("industryNewsList", [])

            if not news_list:
                return f"未找到相关新闻。总记录数: {total}"

            # 构建新闻信息摘要
            news_infos = []
            for i, news in enumerate(news_list, 1):
                news_info = _extract_news_info(news)
                news_infos.append(f"【新闻 {i}】\n{news_info}")

            # 添加总览信息
            title = rsp_body.get("title", "")
            category_code = rsp_body.get("categoryCode", "")
            category_name = NewsSearchConfig.CATEGORY_CODES.get(
                category_code, category_code
            )
            sort_type = rsp_body.get("sortType", 1)
            sort_name = NewsSearchConfig.SORT_TYPES.get(sort_type, "未知")

            summary = f"""查询成功！
关键词: {title}
新闻类型: {category_name}
排序方式: {sort_name}
总记录数: {total}
当前页: {rsp_body.get('pageNum', 1)}
每页数量: {rsp_body.get('pageSize', len(news_list))}
返回数量: {len(news_list)}

{'=' * 80}

"""

            return summary + "\n\n" + "\n\n" + "-" * 80 + "\n\n".join(news_infos)

        # 如果无法提取，返回原始结果
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"提取新闻内容失败: {e}")
        return json.dumps(result, ensure_ascii=False, indent=2)


# ===== LangChain Tool 封装 =====

@tool
def news_search(
    title: str = "",
    category_code: str = "news_exclusive",
    begin_date_str: str = "",
    end_date_str: str = "",
    page_num: int = 1,
    page_size: int = 5,
    sort_type: int = 1
) -> str:
    """
    新闻列表查询工具

    查询各类新闻资讯，支持按关键词、新闻类型、日期范围等条件筛选。

    Args:
        title: 搜索关键词，可以是任意主题，例如 "人工智能"、"新能源"、"政策"、"股市" 等。如果为空，则查询所有新闻。
        category_code: 新闻类型代码，可选值:
            - "news_exclusive": 独家新闻（默认）
            - "news_macro": 宏观新闻
            - "news_region": 行业新闻
            - "news_commodity": 大宗商品新闻
        begin_date_str: 开始日期，格式如 "2020-11-11 00:00:00"。如果为空，不限制开始日期。
        end_date_str: 结束日期，格式如 "2025-11-11 00:00:00"。如果为空，不限制结束日期。
        page_num: 页码，从1开始。默认为1。
        page_size: 每页返回的新闻数量。强制为2。
        sort_type: 排序方式，1=按热度排序（默认），2=按时间排序。

    Returns:
        str: 新闻列表信息，包括标题、来源、作者、发布时间、分类、摘要等详细信息。

    Examples:
        >>> # 查询人工智能相关新闻
        >>> news_search(title="人工智能", category_code="news_region", sort_type=1)
        >>> # 查询2024年的宏观新闻
        >>> news_search(
        ...     category_code="news_macro",
        ...     begin_date_str="2024-01-01 00:00:00",
        ...     end_date_str="2024-12-31 23:59:59"
        ... )
        >>> # 按时间排序查询行业新闻
        >>> news_search(category_code="news_region", sort_type=2)
        >>> # 查询新能源相关独家新闻
        >>> news_search(title="新能源", category_code="news_exclusive")
    """
    return call_news_search(
        title=title,
        category_code=category_code,
        begin_date_str=begin_date_str,
        end_date_str=end_date_str,
        page_num=page_num,
        page_size=2,
        sort_type=sort_type
    )


# 导出工具
__all__ = [
    "NewsSearchConfig",
    "call_news_search",
    "news_search",
]
