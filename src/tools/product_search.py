# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
基础产品搜索工具

通过调用产品知识库API，查询银行基础产品信息。
支持关键词搜索，返回产品的详细介绍和适用客户信息。
"""

import logging
import os
import requests
import json
from typing import Dict, Any
from langchain_core.tools import tool
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger


class ProductSearchConfig:
    """产品搜索配置"""

    # API 配置 - 从环境变量获取
    BASE_URL = os.getenv("EUVD_API_URL", "http://12.244.113.82/EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do")

    # 请求头配置
    HEADERS = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        # 不要手动设置 Content-Type，让 requests 库自动设置 multipart/form-data 的 boundary
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
    vector_top_n: int = 10,
    space_code_list: list = None,
    caller: str = "P2025094",
    customized_tag_list: list = None,
) -> Dict[str, Any]:
    """构建请求体"""

    if space_code_list is None:
        space_code_list = ["SP0000082"]

    if customized_tag_list is None:
        customized_tag_list = ["s1"]

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


def _extract_product_info(product: Dict[str, Any]) -> str:
    """提取单个产品信息"""
    try:
        para_title = product.get("paraTitle", "无标题")
        content = product.get("content", "")
        score = product.get("score", 0)
        rerank_score = product.get("rerankScore")

        # 构建产品信息
        info = f"""产品名称: {para_title}
匹配度: {score:.4f}"""

        if rerank_score is not None:
            info += f"\n重排序得分: {rerank_score:.4f}"

        if content:
            # 截取content，避免过长
            if len(content) > 300:
                content = content[:300] + "..."
            info += f"\n产品详情:\n{content}"

        return info
    except Exception as e:
        logger.error(f"提取产品信息失败: {e}")
        return json.dumps(product, ensure_ascii=False, indent=2)


def call_product_search(
    keyword: str,
    timeout: int = 30
) -> str:
    """
    调用产品搜索API

    Args:
        keyword: 搜索关键词，例如 "科技企业 信用贷款 四川"
        timeout: 超时时间（秒）

    Returns:
        str: API 返回的产品列表信息
    """
    try:
        logger.info(
            f"🔰 调用产品搜索 | 关键词: '{keyword}'"
        )

        # 构建请求体
        request_body = _build_request_body(keyword=keyword)

        logger.debug(f"📤 发送请求体: {json.dumps(request_body, ensure_ascii=False, indent=2)}")

        # 将请求体转换为表单数据格式
        form_data = {
            "REQ_MESSAGE": json.dumps(request_body, ensure_ascii=False)
        }

        # 发送请求
        base_url = ProductSearchConfig.BASE_URL
        response = requests.post(
            base_url,
            headers=ProductSearchConfig.HEADERS,
            cookies=ProductSearchConfig.COOKIES,
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

        logger.info(f"✅ 产品搜索响应成功 | 状态码: {response.status_code}")

        # 提取产品内容
        product_content = _extract_products(result, keyword)

        return product_content

    except requests.exceptions.Timeout:
        error_msg = f"产品搜索请求超时 (>{timeout}s)"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except requests.exceptions.RequestException as e:
        error_msg = f"产品搜索请求失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except Exception as e:
        error_msg = f"处理产品搜索响应时出错: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"


def _extract_products(result: Dict[str, Any], keyword: str) -> str:
    """从API响应中提取产品内容"""
    try:
        # 检查响应状态
        if "RSP_HEAD" in result:
            trans_success = result["RSP_HEAD"].get("TRAN_SUCCESS")
            if trans_success != "1":
                error_msg = result["RSP_HEAD"].get("PROCESS_STATUS_CODE", "未知错误")
                return f"API返回错误: {error_msg}"

        # 提取产品列表
        if "RSP_BODY" in result:
            rsp_body = result["RSP_BODY"]
            result_data = rsp_body.get("result", {})

            # 优先返回向量检索结果
            vector_list = result_data.get("vectorGroupList", [])
            text_list = result_data.get("textGroupList", [])

            # 合并结果，优先使用向量检索结果
            all_products = vector_list if vector_list else text_list

            if not all_products:
                return f"未找到相关产品。关键词: {keyword}"

            # 构建产品信息摘要
            product_infos = []
            for i, product in enumerate(all_products, 1):
                product_info = _extract_product_info(product)
                product_infos.append(f"【产品 {i}】\n{product_info}")

            # 添加总览信息
            total_count = len(all_products)
            summary = f"""查询成功！
关键词: {keyword}
产品格式说明: paraTitle表示"产品组-基础产品-可售产品"的层级关系
返回数量: {total_count}

{'=' * 80}

"""

            return summary + "\n\n" + "\n\n" + "-" * 80 + "\n\n".join(product_infos)

        # 如果无法提取，返回原始结果
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"提取产品内容失败: {e}")
        return json.dumps(result, ensure_ascii=False, indent=2)


# ===== LangChain Tool 封装 =====

@tool
def product_search(
    keyword: str
) -> str:
    """
    基础产品搜索工具

    通过关键词搜索银行的基础产品信息，包括产品介绍和适用客户说明。

    Args:
        keyword: 搜索关键词，可以是产品名称、客户类型、地区等组合，例如 "科技企业 信用贷款 四川"

    Returns:
        paraTitle: 产品列表信息，包括产品名称（产品组-基础产品-可售产品的层级结构）
        content: 产品介绍、适合客户
        score: 匹配度等详细信息。

    Examples:
        >>> # 搜索科技企业相关的信用贷款产品
        >>> product_search(keyword="科技企业 信用贷款")
        >>> # 搜索四川地区的农业贷款产品
        >>> product_search(keyword="农业 四川 贷款")
        >>> # 搜索普惠金融相关产品
        >>> product_search(keyword="普惠e贷 小微企业")
    """
    return call_product_search(keyword=keyword)


# 导出工具
__all__ = [
    "ProductSearchConfig",
    "call_product_search",
    "product_search",
]
