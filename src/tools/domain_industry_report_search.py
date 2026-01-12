# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
行业研报查询工具

通过调用行业研报API，查询行业研究报告。
支持多种查询条件：
- 行业代码（industryCodes）
- 日期范围（beginDateStr, endDateStr）
- 分页查询（pageNum, pageSize）
- 随机查询（isRandomQuery）
"""

import logging
import os
import requests
import json
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool

# 导入重排序工具
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.rerank import rerank_objects
from config.industry_list import INDUSTRY_LIST

logger = logging.getLogger(__name__)


class IndustryReportSearchConfig:
    """行业研报查询配置"""

    # API 配置 - 从环境变量获取
    BASE_URL = os.getenv("INDUSTRY_REPORT_API_URL")
    REPORT_NUM = os.getenv("INDUSTRY_REPORT_NUM")

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
    industry_codes: Optional[List[str]] = None,
    begin_date_str: str = "",
    end_date_str: str = "",
    page_num: int = 1,
    page_size: int = 2,
    is_random_query: bool = False,
    reserved_field1: str = "",
    reserved_field2: str = "",
    reserved_field3: str = "",
    reserved_field4: str = "",
    reserved_field5: str = "",
) -> Dict[str, Any]:
    """构建请求体"""

    req_body = {
        "REQ_HEAD": {
            "TRAN_PROCESS": "",
            "TRAN_ID": ""
        },
        "REQ_BODY": {
            "REQ_BODY": {
                "endDateStr": end_date_str,
                "beginDateStr": begin_date_str,
                "reservedField2": reserved_field2,
                "reservedField4": reserved_field4,
                "pageNum": page_num,
                "isRandomQuery": is_random_query,
                "reservedField1": reserved_field1,
                "pageSize": 2,
                "reservedField3": reserved_field3,
                "industryCodes": industry_codes or [],
                "reservedField5": reserved_field5
            }
        }
    }

    return req_body


def _extract_report_info(report: Dict[str, Any]) -> str:
    """提取单条研报信息"""
    try:
        title = report.get("title", "无标题")
        org_name = report.get("orgName", "未知机构")
        publish_date = report.get("publishDate", "N/A")
        industry_names = report.get("industryNameList", [])
        authors = report.get("authors", [])

        # 构建作者信息
        author_info = []
        if authors:
            for author in authors[:3]:  # 最多显示3个作者
                name = author.get("analystName", "")
                edu = author.get("edu", "")
                if edu:
                    author_info.append(f"{name}({edu})")
                else:
                    author_info.append(name)
        authors_str = "、".join(author_info) if author_info else "未知"

        # 构建行业信息
        industry_str = "、".join(industry_names) if industry_names else "未分类"

        # 研报页数
        page_count = report.get("reportPageSize", "N/A")

        # 附件信息
        attach_name = report.get("attachName", "")
        attach_url = report.get("attachUrl", "")

        info = f"""标题: {title}
机构: {org_name}
作者: {authors_str}
发布日期: {publish_date}
行业: {industry_str}
页数: {page_count}"""
        if attach_name:
            info += f"\n附件: {attach_name}"

        return info
    except Exception as e:
        logger.error(f"提取研报信息失败: {e}")
        return json.dumps(report, ensure_ascii=False, indent=2)


def call_industry_report_search(
    industry_codes: Optional[List[str]] = None,
    begin_date_str: str = "",
    end_date_str: str = "",
    page_num: int = 1,
    page_size: int = 2,
    is_random_query: bool = False,
    timeout: int = 30
) -> str:
    """
    调用行业研报查询API

    Args:
        industry_codes: 行业代码列表，例如 ["3702", "6307"]
        begin_date_str: 开始日期，格式如 "2025-01-01"
        end_date_str: 结束日期，格式如 "2025-12-31"
        page_num: 页码，从1开始
        page_size: 每页数量
        is_random_query: 是否随机查询
        timeout: 超时时间（秒）

    Returns:
        str: API 返回的研报列表信息
    """
    try:
        logger.info(
            f"🔍 调用行业研报查询 | 行业代码: {industry_codes} | "
            f"日期范围: {begin_date_str} ~ {end_date_str} | "
            f"分页: {page_num}/{page_size} | 随机查询: {is_random_query}"
        )

        # 构建请求体
        request_body = _build_request_body(
            industry_codes=industry_codes,
            begin_date_str=begin_date_str,
            end_date_str=end_date_str,
            page_num=page_num,
            page_size=page_size,
            is_random_query=is_random_query
        )

        # 将请求体转换为表单数据格式
        form_data = {
            "REQ_MESSAGE": json.dumps(request_body, ensure_ascii=False)
        }

        logger.debug(f"📤 发送请求体: {json.dumps(request_body, ensure_ascii=False, indent=2)}")

        # 发送请求
        base_url = os.getenv("INDUSTRY_REPORT_API_URL")
        response = requests.post(
            base_url,
            headers=IndustryReportSearchConfig.HEADERS,
            cookies=IndustryReportSearchConfig.COOKIES,
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

        logger.info(f"✅ 行业研报查询响应成功 | 状态码: {response.status_code}")

        # 提取研报内容
        report_content = _extract_reports(result)

        return report_content

    except requests.exceptions.Timeout:
        error_msg = f"行业研报查询请求超时 (>{timeout}s)"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except requests.exceptions.RequestException as e:
        error_msg = f"行业研报查询请求失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except Exception as e:
        error_msg = f"处理行业研报查询响应时出错: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"


def _match_industries_by_keyword(
    keyword: str,
    top_k: int = 3
) -> List[Dict[str, str]]:
    """
    根据关键词智能匹配相关行业

    Args:
        keyword: 搜索关键词
        top_k: 返回前 K 个最相关的行业

    Returns:
        List[Dict]: 包含 IndustryId 和 IndustryName 的行业列表
    """
    try:
        # 如果配置了 Rerank API，使用智能匹配
        if os.getenv("RERANK_API_URL") and os.getenv("RERANK_API_KEY"):
            logger.info(f"🔄 使用 Rerank 模型智能匹配行业 | 关键词: '{keyword}'")

            # 使用重排序工具找到最相关的行业
            matched_industries = rerank_objects(
                query=keyword,
                objects=INDUSTRY_LIST,
                text_field="IndustryName",
                top_k=top_k
            )

            if matched_industries:
                # 提取 IndustryId 和 IndustryName
                result = []
                for industry in matched_industries:
                    result.append({
                        "IndustryId": industry.get("IndustryId"),
                        "IndustryName": industry.get("IndustryName"),
                        "relevance_score": industry.get("relevance_score", 0)
                    })
                    logger.info(f"  ✓ 匹配行业: {industry.get('IndustryName')} (ID: {industry.get('IndustryId')}, 评分: {industry.get('relevance_score', 0):.4f})")

                return result

        # 降级方案：简单的关键词匹配
        logger.info(f"🔄 使用关键词匹配算法 | 关键词: '{keyword}'")
        matched_industries = []
        for industry in INDUSTRY_LIST:
            industry_name = industry.get("IndustryName", "")
            # 检查关键词是否包含在行业名称中，或行业名称包含关键词
            if keyword in industry_name or industry_name in keyword:
                matched_industries.append({
                    "IndustryId": industry.get("IndustryId"),
                    "IndustryName": industry_name,
                    "relevance_score": 1.0  # 默认评分
                })
                logger.info(f"  ✓ 匹配行业: {industry_name} (ID: {industry.get('IndustryId')})")

                if len(matched_industries) >= top_k:
                    break

        return matched_industries if matched_industries else []

    except Exception as e:
        logger.error(f"❌ 行业匹配失败: {e}")
        return []


def _extract_reports(result: Dict[str, Any]) -> str:
    """从API响应中提取研报内容"""
    try:
        # 检查响应状态
        if "RSP_HEAD" in result:
            trans_success = result["RSP_HEAD"].get("TRAN_SUCCESS")
            if trans_success != "1":
                error_msg = result["RSP_HEAD"].get("PROCESS_STATUS_CODE", "未知错误")
                return f"API返回错误: {error_msg}"

        # 提取研报列表
        if "RSP_BODY" in result:
            rsp_body = result["RSP_BODY"]
            total = rsp_body.get("total", 0)
            report_list = rsp_body.get("reportList", [])

            if not report_list:
                return f"未找到相关研报。总记录数: {total}"

            # 构建研报信息摘要
            report_infos = []
            REPORT_NUM = os.getenv("INDUSTRY_REPORT_NUM")
            report_list = report_list[:REPORT_NUM]
            for i, report in enumerate(report_list, 1):
                report_info = _extract_report_info(report)
                report_infos.append(f"【研报 {i}】\n{report_info}")

            # 添加总览信息
            summary = f"""查询成功！
总记录数: {total}
当前页: {rsp_body.get('REQ_BODY', {}).get('pageNum', 1)}
每页数量: {rsp_body.get('REQ_BODY', {}).get('pageSize', len(report_list))}
返回数量: {len(report_list)}

{'=' * 80}

"""

            return summary + "\n\n" + "\n\n" + "-" * 80 + "\n\n".join(report_infos)

        # 如果无法提取，返回原始结果
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"提取研报内容失败: {e}")
        return json.dumps(result, ensure_ascii=False, indent=2)


# ===== LangChain Tool 封装 =====

@tool
def industry_report_search(
    keyword: str = "",
    industry_codes: Optional[List[str]] = None,
    begin_date_str: str = "",
    end_date_str: str = "",
    page_num: int = 1,
    page_size: int = 2,
    is_random_query: bool = False
) -> str:
    """
    行业研报查询工具 - 支持关键词智能匹配行业

    【重要】使用指南：
    1. **必须使用 keyword 参数**：系统会智能匹配最相关的2个行业，并查询这些行业的研报。
       例如：用户问"人工智能相关研报"，使用 keyword="人工智能"

    2. **禁止直接使用 industry_codes 参数**：让系统自动根据 keyword 匹配最相关的行业。
       系统会使用 Rerank 模型进行智能匹配，确保查询到最准确的行业研报。

    3. **参数说明**：
       - keyword: 搜索关键词，使用行业名称或主题词即可
       - 其他参数为可选参数

    【使用场景】
    - 用户询问某个行业/主题的研报时，使用该工具
    - 关键词可以是行业名称（如"中药"、"锂电池"）或主题（如"人工智能"、"新能源"）
    - 系统会自动匹配最相关的2个行业，无需提供具体行业代码

    Args:
        keyword: 【必填】搜索关键词，如 "人工智能"、"新能源"、"中药"、"汽车" 等。
                 系统会使用 Rerank 模型智能匹配最相关的 2 个行业。
                 **必须使用此参数**，不要使用 industry_codes 参数。
        industry_codes: 【内部使用】行业代码列表，由系统自动匹配生成。
                       大模型不应直接提供此参数，必须使用 keyword 参数。
        begin_date_str: 开始日期，格式 "2025-01-01"。如果为空，不限制开始日期。
        end_date_str: 结束日期，格式 "2025-12-31"。如果为空，不限制结束日期。
        page_num: 页码，从1开始。默认为1。
        page_size: 每页返回的研报数量。强制为2。
        is_random_query: 是否随机查询。默认为False。

    Returns:
        str: 研报列表信息，包括标题、机构、作者、发布日期、行业分类等详细信息。

    Examples:
        >>> # 使用关键词智能匹配（推荐且唯一的方式）
        >>> industry_report_search(keyword="人工智能")
        >>> industry_report_search(keyword="新能源汽车")
        >>> industry_report_search(keyword="中药")
        >>> industry_report_search(keyword="银行")
        >>> industry_report_search(keyword="半导体")

        >>> # 带日期范围
        >>> industry_report_search(keyword="新能源", begin_date_str="2025-01-01", end_date_str="2025-12-31")

        >>> # 随机查询
        >>> industry_report_search(is_random_query=True)

    ⚠️ 重要提示：
    - 不要直接提供 industry_codes 参数
    - 不要猜测或提供具体的行业代码
    - 让系统根据 keyword 自动匹配最相关的行业
    """
    # 如果提供了关键词但没有提供行业代码，则智能匹配行业
    if keyword and not industry_codes:
        matched_industries = _match_industries_by_keyword(keyword, top_k=2)
        if matched_industries:
            # 使用匹配到的行业代码
            industry_codes = [ind["IndustryId"] for ind in matched_industries]
            logger.info(f"✅ 智能匹配到 {len(matched_industries)} 个相关行业: {[ind['IndustryName'] for ind in matched_industries]}")
        else:
            logger.warning(f"⚠️ 未能匹配到相关行业，将查询所有行业的研报")

    return call_industry_report_search(
        industry_codes=industry_codes,
        begin_date_str=begin_date_str,
        end_date_str=end_date_str,
        page_num=page_num,
        page_size=2,
        is_random_query=is_random_query
    )


# 导出工具
__all__ = [
    "IndustryReportSearchConfig",
    "call_industry_report_search",
    "industry_report_search",
]
