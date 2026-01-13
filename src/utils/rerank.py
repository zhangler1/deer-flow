# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
重排序工具

使用阿里云 Rerank 模型对文档列表进行重排序，提高搜索结果的相关性。
支持新闻、行业等任意类型对象的重排序。
"""

import logging
import os
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class RerankConfig:
    """Rerank 配置"""

    # Rerank API URL - 从环境变量获取
    RERANK_API_URL = os.getenv("RERANK_API_URL")

    # 请求超时时间（秒）
    TIMEOUT = 30


def call_rerank_api(
    query: str,
    documents: List[str],
    api_url: Optional[str] = None,
    top_n: int = 5,
    timeout: int = 30
) -> List[Dict[str, Any]]:
    """
    调用 Qwen3 Rerank API

    Args:
        query: 搜索关键词
        documents: 待排序的文档列表
        api_url: API URL（可选，默认使用环境变量配置）
        top_n: 返回前 N 个结果
        timeout: 超时时间（秒）

    Returns:
        List[Dict[str, Any]]: Rerank 结果列表，包含 index 和 relevance_score
    """
    try:
        # 使用传入的 URL 或默认配置
        url = api_url or RerankConfig.RERANK_API_URL

        if not url:
            raise ValueError("RERANK_API_URL 未配置")

        logger.debug(f"📤 调用 Rerank API: {url}")
        logger.debug(f"📤 查询: {query}")
        logger.debug(f"📤 文档数量: {len(documents)}")

        # 构建请求头
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Content-type": "application/json",
            "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
        }

        # 构建请求体（Qwen3 Rerank API 格式）
        request_body = {
            "query": query,
            "documents": documents,
            "top_n": top_n,
            "return_documents": False,
            "model_name": "qwen3-reranker-4B"
        }

        # 发送请求
        response = requests.post(
            url,
            headers=headers,
            json=request_body,
            timeout=timeout
        )

        # 检查响应状态
        response.raise_for_status()

        # 解析响应
        result = response.json()

        # 提取 rerank 结果（Qwen3 API 格式）
        if "results" in result:
            rerank_results = result["results"]
            logger.info(f"✅ Rerank API 调用成功 | 返回 {len(rerank_results)} 条结果")
            return rerank_results
        else:
            logger.warning(f"Rerank API 响应格式异常: {result}")
            return []

    except requests.exceptions.Timeout:
        error_msg = f"Rerank API 请求超时 (>{timeout}s)"
        logger.error(f"❌ {error_msg}")
        raise

    except requests.exceptions.RequestException as e:
        error_msg = f"Rerank API 请求失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise

    except Exception as e:
        error_msg = f"调用 Rerank API 时出错: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise


def rerank_news(
    query: str,
    news_list: List[Dict[str, Any]],
    api_url: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    对新闻列表进行重排序

    Args:
        query: 搜索关键词
        news_list: 新闻列表，每条新闻应包含 'title' 字段
        api_url: Rerank API URL（可选，默认使用环境变量配置）
        top_k: 返回前 K 条新闻

    Returns:
        List[Dict[str, Any]]: 重排序后的新闻列表（前 top_k 条）
    """
    try:
        if not news_list:
            logger.warning("新闻列表为空，无需重排序")
            return []

        if len(news_list) <= 1:
            logger.info("新闻列表只有1条或更少，无需重排序")
            return news_list[:top_k]

        # 提取所有新闻标题作为文档
        documents = [news.get("title", "") for news in news_list]

        if not any(documents):
            logger.warning("所有新闻标题为空，无法重排序")
            return news_list[:top_k]

        logger.info(f"🔄 开始重排序 | 查询: '{query}' | 新闻数量: {len(news_list)}")

        # 调用 Rerank API
        rerank_results = call_rerank_api(
            query=query,
            documents=documents,
            api_url=api_url,
            top_n=top_k
        )

        if not rerank_results:
            logger.warning("Rerank 未返回结果，使用原始顺序")
            return news_list[:top_k]

        # 根据 rerank 结果重新排序新闻
        # rerank_results 已按相关性排序，直接使用其中的 index
        reranked_news = []
        for result in rerank_results:
            index = result.get("index")
            relevance_score = result.get("relevance_score", 0)

            if 0 <= index < len(news_list):
                news = news_list[index].copy()
                # 可选：添加相关性评分到新闻对象中
                news["relevance_score"] = relevance_score
                reranked_news.append(news)

                logger.debug(f"  📌 排序: index={index}, score={relevance_score:.4f}, title={news.get('title', '')[:50]}")

        logger.info(f"✅ 重排序完成 | 返回前 {len(reranked_news)} 条")

        return reranked_news

    except Exception as e:
        logger.error(f"❌ 重排序失败: {e}")
        logger.info("🔄 返回原始顺序的新闻")
        # 发生错误时返回原始顺序
        return news_list[:top_k]


def rerank_objects(
    query: str,
    objects: List[Dict[str, Any]],
    text_field: str,
    api_url: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    对任意对象列表进行重排序

    Args:
        query: 搜索关键词
        objects: 对象列表，每个对象应包含指定的文本字段
        text_field: 用于重排序的字段名（如 "title"、"IndustryName" 等）
        api_url: Rerank API URL（可选，默认使用环境变量配置）
        top_k: 返回前 K 个对象

    Returns:
        List[Dict[str, Any]]: 重排序后的对象列表（前 top_k 个）
    """
    try:
        if not objects:
            logger.warning("对象列表为空，无需重排序")
            return []

        if len(objects) <= 1:
            logger.info("对象列表只有1条或更少，无需重排序")
            return objects[:top_k]

        # 提取指定字段的文本作为文档
        documents = [obj.get(text_field, "") for obj in objects]

        if not any(documents):
            logger.warning(f"所有对象的 {text_field} 字段为空，无法重排序")
            return objects[:top_k]

        logger.info(f"🔄 开始重排序对象 | 查询: '{query}' | 对象数量: {len(objects)} | 字段: {text_field}")

        # 调用 Rerank API
        rerank_results = call_rerank_api(
            query=query,
            documents=documents,
            api_url=api_url,
            top_n=top_k
        )

        if not rerank_results:
            logger.warning("Rerank 未返回结果，使用原始顺序")
            return objects[:top_k]

        # 根据 rerank 结果重新排序对象
        reranked_objects = []
        for result in rerank_results:
            index = result.get("index")
            relevance_score = result.get("relevance_score", 0)

            if 0 <= index < len(objects):
                obj = objects[index].copy()
                # 添加相关性评分到对象中
                obj["relevance_score"] = relevance_score
                reranked_objects.append(obj)

                logger.debug(f"  📌 排序: index={index}, score={relevance_score:.4f}, {text_field}={obj.get(text_field, '')[:50]}")

        logger.info(f"✅ 对象重排序完成 | 返回前 {len(reranked_objects)} 条")

        return reranked_objects

    except Exception as e:
        logger.error(f"❌ 对象重排序失败: {e}")
        logger.info("🔄 返回原始顺序的对象")
        # 发生错误时返回原始顺序
        return objects[:top_k]


# 导出
__all__ = [
    "RerankConfig",
    "rerank_news",
    "rerank_objects",
    "call_rerank_api",
]
