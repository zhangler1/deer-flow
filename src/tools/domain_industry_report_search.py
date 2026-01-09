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

logger = logging.getLogger(__name__)


class IndustryReportSearchConfig:
    """行业研报查询配置"""

    # API 配置 - 从环境变量获取
    BASE_URL = os.getenv("INDUSTRY_REPORT_API_URL")

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
    industry_codes: Optional[List[str]] = None,
    begin_date_str: str = "",
    end_date_str: str = "",
    page_num: int = 1,
    page_size: int = 2,
    is_random_query: bool = False
) -> str:
    """
    行业研报查询工具

    查询行业研究报告，支持按行业代码、日期范围等条件筛选。

    Args:
        industry_codes: 行业代码列表，例如 ["3702"] 代表中药行业，["6307"] 代表锂电池行业。
                       如果为空，则查询所有行业的研报。
        begin_date_str: 开始日期，格式如 "2025-01-01"。如果为空，不限制开始日期。
        end_date_str: 结束日期，格式如 "2025-12-31"。如果为空，不限制结束日期。
        page_num: 页码，从1开始。默认为1。
        page_size: 每页返回的研报数量。强制为2。
        is_random_query: 是否随机查询。默认为False。随机查询可能会返回更多样化的结果。

    Returns:
        str: 研报列表信息，包括标题、机构、作者、发布日期、行业分类等详细信息。

    Examples:
        >>> # 查询中药行业的研报
        >>> industry_report_search(industry_codes=["3702"])
        >>> # 查询2025年12月的锂电池行业研报
        >>> industry_report_search(
        ...     industry_codes=["6307"],
        ...     begin_date_str="2025-12-01",
        ...     end_date_str="2025-12-31"
        ... )
        >>> # 随机查询2篇研报
        >>> industry_report_search(is_random_query=True)
    """
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
