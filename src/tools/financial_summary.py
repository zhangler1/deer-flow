# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
财务数据汇总工具

通过调用联网搜索获取公司财务信息，然后使用 REPORTER_MODEL 生成财务数据汇总报告。
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage



# 复用 online_search 的 call_online_search，避免重复构造 CustomSearchTool
from src.tools.online_search import call_online_search
# 导入 LLM 工具
from src.llms.llm import get_llm_by_type
from src.config.agents import LLMType

logger = logging.getLogger(__name__)


def _filter_search_results_by_date(
    search_results: List[Dict[str, Any]],
    months_threshold: int = 8
) -> List[Dict[str, Any]]:
    """
    根据 createTime 过滤搜索结果，去除早于指定月数的数据

    Args:
        search_results: 搜索结果列表
        months_threshold: 月数阈值，默认 8 个月

    Returns:
        过滤后的搜索结果列表
    """
    if not search_results:
        return search_results

    # 计算阈值日期
    threshold_date = datetime.now() - timedelta(days=months_threshold * 30)

    filtered_results = []
    removed_count = 0

    for result in search_results:
        create_time_str = result.get("createTime", "")

        # 如果没有 createTime，保留该结果
        if not create_time_str:
            filtered_results.append(result)
            continue

        try:
            # 解析 createTime（格式如 "2025年8月15日"）
            # 处理中文日期格式
            create_time_str = create_time_str.replace("年", "-").replace("月", "-").replace("日", "")
            create_time = parse_date(create_time_str)

            # 检查是否在阈值范围内
            if create_time >= threshold_date:
                filtered_results.append(result)
            else:
                removed_count += 1
                logger.debug(
                    f"过滤掉过时数据: {result.get('title', '无标题')} "
                    f"(createTime: {create_time_str})"
                )
        except Exception as e:
            # 如果日期解析失败，保留该结果
            logger.debug(f"无法解析 createTime '{create_time_str}': {e}，保留该结果")
            filtered_results.append(result)

    if removed_count > 0:
        logger.info(
            f"📅 日期过滤完成 | 保留 {len(filtered_results)} 条结果，"
            f"去除 {removed_count} 条超过 {months_threshold} 个月的数据"
        )

    return filtered_results


def _extract_company_name(query: str) -> str:
    """
    从查询字符串中提取公司名称

    公司名称是 query 中第一个空格前的字符串

    Args:
        query: 查询字符串

    Returns:
        str: 提取的公司名称
    """
    # 分割字符串并获取第一个空格前的部分
    parts = query.split(None, 1)  # split(None, 1) 自动处理任意空白字符
    if parts:
        return parts[0]
    return query


def _online_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    联网搜索函数：在 query 上拼接年份做查询增强，然后委托给 online_search

    Args:
        query: 搜索查询字符串
        max_results: 最大返回结果数，默认 10

    Returns:
        搜索结果列表
    """
    # 根据当前月份决定使用哪一年
    # 4月及之前使用上一年，5月及之后使用当前年
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year

    if current_month <= 4:
        # 1-4月：使用上一年
        search_year = current_year - 1
    else:
        # 5-12月：使用当前年
        search_year = current_year

    enhanced_query = f"{query} {search_year}"

    logger.info(
        f"📅 增强查询: '{query}' -> '{enhanced_query}' "
        f"(当前月份: {current_month}月, 使用年份: {search_year})"
    )

    # 直接复用 online_search 工具，避免重复构造 CustomSearchTool
    return call_online_search(enhanced_query, max_results=max_results)


def call_financial_summary(
    query: str,
    max_results: int = 10,
    timeout: int = 120
) -> str:
    """
    调用财务数据汇总API

    首先调用联网搜索获取财务相关信息，然后使用 REPORTER_MODEL 生成汇总报告。

    Args:
        query: 查询字符串，格式为 "公司名称 [其他描述]"
        max_results: 联网搜索最大返回结果数，默认 10
        timeout: LLM 调用超时时间（秒），默认 120

    Returns:
        str: 财务数据汇总报告
    """
    try:
        # 提取公司名称
        company_name = _extract_company_name(query)

        logger.info(
            f"📊 开始财务数据汇总 | "
            f"公司: {company_name} | "
            f"完整查询: '{query}'"
        )

        # 步骤1: 调用联网搜索获取财务信息（使用内部实现的 _online_search）
        logger.info(f"🔍 步骤 1/3: 调用联网搜索获取 {company_name} 的财务信息")
        search_results = _online_search(query=query, max_results=max_results)

        # 检查搜索是否成功
        if not search_results:
            return f"未找到 {company_name} 的相关财务信息。"

        # 步骤2: 过滤掉超过6个月的旧数据
        logger.info(f"📅 步骤 2/3: 过滤早于6个月前的数据")
        search_results = _filter_search_results_by_date(search_results, months_threshold=8)

        # 格式化搜索结果
        if isinstance(search_results, list):
            search_context = "\n\n".join([
                f"标题: {result.get('title', '无标题')}\n"
                f"内容: {result.get('content', '无内容')}\n"
                f"来源: {result.get('source', '未知')}"
                for result in search_results
            ])
        elif isinstance(search_results, str):
            search_context = search_results
        else:
            search_context = str(search_results)

        # 步骤3: 使用 REPORTER_MODEL 生成财务数据汇总
        logger.info(f"🤖 步骤 3/3: 使用 REPORTER_MODEL 生成 {company_name} 财务数据汇总")

        # 获取 REPORTER_MODEL
        reporter_llm = get_llm_by_type(LLMType.REPORTER_LLM)

        # 构建提示词
        prompt = f"""请根据提供的结果，返回{company_name}的财务数据汇总。

以下是从联网搜索获取的相关信息：

{search_context}

请基于以上信息，生成一份结构清晰、内容准确的2023年以来的财务数据汇总报告。报告应包含：
1. 公司基本信息
2. 主要财务指标（如营业收入、净利润、资产总额、资产负债率、流动比率、速动比率、毛利率、净利率等）
3. 重要财务数据和趋势

如果某些财务数据在搜索结果中缺失，请明确说明。"""

        # 调用 REPORTER_MODEL
        message = HumanMessage(content=prompt)
        response = reporter_llm.invoke([message], timeout=timeout)

        # 提取响应内容
        summary = response.content if hasattr(response, 'content') else str(response)

        logger.info(f"✅ 财务数据汇总完成 | 公司: {company_name}")

        return summary

    except Exception as e:
        error_msg = f"生成财务数据汇总时出错: {str(e)}"
        logger.error(f"❌ {error_msg}")
        import traceback
        logger.debug(traceback.format_exc())
        return f"错误: {error_msg}"


# ===== LangChain Tool 封装 =====

@tool
def financial_summary(
    query: str
) -> str:
    """
    财务数据汇总工具

    该工具首先调用联网搜索获取指定公司的财务信息，然后使用 REPORTER_MODEL 生成结构化的财务数据汇总报告。

    Args:
        query: 查询字符串，格式为 "公司名称 [其他描述]"。
               例如："腾讯 财务数据"、"阿里巴巴 2024年财报"、"贵州茅台 财务状况"
               公司名称是第一个空格前的字符串。

    Returns:
        str: 结构化的财务数据汇总报告，包含公司基本信息、主要财务指标、财务状况分析等内容。

    Examples:
        >>> # 查询腾讯的财务数据
        >>> financial_summary("腾讯 财务数据")
        >>> # 查询阿里巴巴的财报信息
        >>> financial_summary("阿里巴巴 2024年财报")
        >>> # 查询贵州茅台的财务状况
        >>> financial_summary("贵州茅台 财务状况")
    """
    return call_financial_summary(query=query)


# 导出工具
__all__ = [
    "call_financial_summary",
    "financial_summary",
    "_online_search",
]
