# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
研报知识库搜索工具

通过调用研报知识库API，查询各类研究报告的详细信息。
支持关键词搜索，返回研报的段落内容、来源文件、发布时间等信息。
"""

import logging
import os
import requests
import json
from typing import Dict, Any, List
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


class ReportSearchConfig:
    """研报搜索配置"""

    # API 配置 - 从环境变量获取
    BASE_URL = os.getenv(
        "REPORT_API_URL",
        "http://12.244.113.82/EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do"
    )

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

    # Cookie 配置（从环境变量读取）
    COOKIES = {
        "JSESSIONID": os.getenv("JSESSIONID", ""),
    }


def _build_request_body(
    keyword: str,
    user_code: str = "9614443",
    caller: str = "P2025094",
    search_type: str = "0",
    vector_top_n: int = 5,
    text_top_n: int = 5,
    space_code_list: List[str] = None,
    file_id_list: List[str] = None,
    pub_time_start: str = None,
    pub_time_end: str = None,
) -> Dict[str, Any]:
    """
    构建请求体

    Args:
        keyword: 搜索关键词
        user_code: 用户代码
        caller: 调用者标识
        search_type: 搜索类型（0: 混合搜索）
        vector_top_n: 向量检索返回数量
        text_top_n: 文本检索返回数量
        space_code_list: 空间代码列表（知识库空间）
        file_id_list: 文件ID列表（限定在特定文件中搜索）
        pub_time_start: 发布时间开始，格式：YYYY-MM-DD HH:mm:ss
        pub_time_end: 发布时间结束，格式：YYYY-MM-DD HH:mm:ss

    Returns:
        请求体字典
    """

    if space_code_list is None:
        space_code_list = ["SP0000001"]

    # 默认时间范围：最近一年
    if pub_time_start is None:
        from datetime import datetime, timedelta
        pub_time_start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")

    if pub_time_end is None:
        from datetime import datetime
        pub_time_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    req_body = {
        "REQ_HEAD": {
            "TRAN_PROCESS": "searchKnowledgeStandard"
        },
        "REQ_BODY": {
            "param": {
                "keyword": keyword,
                "userCode": user_code,
                "caller": caller,
                "searchType": search_type,
                "vectorTopN": vector_top_n,
                "textTopN": text_top_n,
                "spaceCodeList": space_code_list,
                "pubTimeStart": pub_time_start,
                "pubTimeEnd": pub_time_end,
            }
        }
    }

    # 如果指定了文件ID列表，添加到请求中
    if file_id_list:
        req_body["REQ_BODY"]["param"]["fileIdList"] = file_id_list

    return req_body


def _extract_report_info(report: Dict[str, Any]) -> str:
    """
    提取单个研报段落的详细信息

    Args:
        report: 研报段落数据字典

    Returns:
        格式化的研报信息字符串
    """
    try:
        para_id = report.get("paraId", "")
        para_title = report.get("paraTitle", "无标题")
        content = report.get("content", "")
        score = report.get("score", 0)
        rerank_score = report.get("rerankScore")

        file_id = report.get("fileId", "")
        file_name = report.get("fileName", "未知文件")
        page = report.get("page", -1)
        sorted_num = report.get("sorted", 0)

        # 时间信息
        create_time = report.get("createTime", "")
        update_time = report.get("updateTime", "")
        pub_time = report.get("pubTime", "")
        valid_time_start = report.get("validTimeStart", "")
        valid_time_end = report.get("validTimeEnd", "")

        # 标签信息
        customized_tags = report.get("customizedTags", [])
        domain_tags = report.get("domainTags", [])

        # 构建研报信息
        info_lines = [
            f"📄 文件名: {file_name}",
            f"📌 段落标题: {para_title}",
        ]

        if score > 0:
            info_lines.append(f"🎯 匹配度: {score:.4f}")

        if rerank_score is not None:
            info_lines.append(f"🔄 重排序得分: {rerank_score:.4f}")

        if page > 0:
            info_lines.append(f"📖 页码: {page}")

        if sorted_num > 0:
            info_lines.append(f"🔢 排序号: {sorted_num}")

        if pub_time:
            info_lines.append(f"📅 发布时间: {pub_time}")

        if content:
            # # 截取content，避免过长
            # if len(content) > 500:
            #     content = content[:500] + "..."
            info_lines.append(f"\n📝 内容摘要:\n{content}")

        # 添加标签信息
        if customized_tags:
            info_lines.append(f"\n🏷️  自定义标签: {', '.join(customized_tags[:3])}")  # 只显示前3个

        if domain_tags:
            info_lines.append(f"🌐 领域标签: {', '.join(domain_tags[:2])}")  # 只显示前2个

        # 添加元数据信息（可选）
        meta_info = []
        if file_id:
            meta_info.append(f"文件ID: {file_id}")
        if para_id:
            meta_info.append(f"段落ID: {para_id}")

        if meta_info:
            info_lines.append(f"\n📋 元数据: {' | '.join(meta_info)}")

        return "\n".join(info_lines)

    except Exception as e:
        logger.error(f"提取研报信息失败: {e}")
        return json.dumps(report, ensure_ascii=False, indent=2)


def _extract_reports(result: Dict[str, Any], keyword: str) -> str:
    """
    从API响应中提取研报内容

    Args:
        result: API响应结果
        keyword: 搜索关键词

    Returns:
        格式化的研报列表信息
    """
    try:
        # 检查响应状态
        if "RSP_HEAD" in result:
            rsp_head = result["RSP_HEAD"]
            trans_success = rsp_head.get("TRAN_SUCCESS")
            if trans_success != "1":
                process_status = rsp_head.get("PROCESS_STATUS_CODE", "未知错误")
                trace_no = rsp_head.get("TRACE_NO", "")
                return f"❌ API返回错误: {process_status}\n追踪号: {trace_no}"

        # 提取研报列表
        if "RSP_BODY" in result:
            rsp_body = result["RSP_BODY"]
            result_data = rsp_body.get("result", {})

            # 获取向量检索和文本检索结果
            vector_list = result_data.get("vectorGroupList", [])
            text_list = result_data.get("textGroupList", [])
            graph_list = result_data.get("graphGroupList")
            rerank_list = result_data.get("rerankResultList")

            # 优先使用向量检索结果，其次使用文本检索结果
            all_reports = vector_list if vector_list else text_list

            if not all_reports:
                return f"😕 未找到相关研报内容\n\n关键词: {keyword}"

            # 构建研报信息摘要
            report_infos = []
            for i, report in enumerate(all_reports, 1):
                report_info = _extract_report_info(report)
                report_infos.append(f"【研报片段 {i}】\n{report_info}")

            # 构建总览信息
            total_count = len(all_reports)
            vector_count = len(vector_list)
            text_count = len(text_list)

            summary = f"""✅ 查询成功！

🔍 搜索关键词: {keyword}
📊 返回数量: {total_count} 条
  - 向量检索: {vector_count} 条
  - 文本检索: {text_count} 条
{'═' * 80}

"""

            return summary + "\n\n".join(report_infos)

        # 如果无法提取，返回原始结果
        logger.warning("⚠️  无法从响应中提取研报数据，返回原始结果")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"❌ 提取研报内容失败: {e}")
        logger.exception("详细错误信息:")
        return json.dumps(result, ensure_ascii=False, indent=2)


def call_report_search(
    keyword: str,
    user_code: str = "9614443",
    caller: str = "P2025094",
    space_code_list: List[str] = None,
    file_id_list: List[str] = None,
    pub_time_start: str = None,
    pub_time_end: str = None,
    vector_top_n: int = 5,
    text_top_n: int = 5,
    timeout: int = 30,
) -> str:
    """
    调用研报搜索API

    Args:
        keyword: 搜索关键词，例如 "2025年全球光伏市场经济"
        user_code: 用户代码
        caller: 调用者标识
        space_code_list: 知识库空间代码列表，例如 ["SP0000001"]
        file_id_list: 文件ID列表，限定搜索范围
        pub_time_start: 发布时间开始，格式：YYYY-MM-DD HH:mm:ss
        pub_time_end: 发布时间结束，格式：YYYY-MM-DD HH:mm:ss
        vector_top_n: 向量检索返回数量
        text_top_n: 文本检索返回数量
        timeout: 超时时间（秒）

    Returns:
        str: API 返回的研报列表信息
    """
    try:
        logger.info(
            f"🔰 调用研报搜索 | 关键词: '{keyword}' | 用户: {user_code}"
        )

        # 构建请求体
        request_body = _build_request_body(
            keyword=keyword,
            user_code=user_code,
            caller=caller,
            space_code_list=space_code_list,
            file_id_list=file_id_list,
            pub_time_start=pub_time_start,
            pub_time_end=pub_time_end,
            vector_top_n=vector_top_n,
            text_top_n=text_top_n,
        )

        logger.debug(f"📤 发送请求体: {json.dumps(request_body, ensure_ascii=False, indent=2)}")

        # 将请求体转换为表单数据格式
        form_data = {
            "REQ_MESSAGE": json.dumps(request_body, ensure_ascii=False)
        }

        # 发送请求
        base_url = ReportSearchConfig.BASE_URL
        response = requests.post(
            base_url,
            headers=ReportSearchConfig.HEADERS,
            cookies=ReportSearchConfig.COOKIES,
            data=form_data,
            timeout=timeout
        )

        # 检查响应状态
        response.raise_for_status()

        # 打印原始响应信息以便调试
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

        logger.info(f"✅ 研报搜索响应成功 | 状态码: {response.status_code}")

        # 提取研报内容
        report_content = _extract_reports(result, keyword)

        return report_content

    except requests.exceptions.Timeout:
        error_msg = f"研报搜索请求超时 (>{timeout}s)"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except requests.exceptions.RequestException as e:
        error_msg = f"研报搜索请求失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"

    except Exception as e:
        error_msg = f"处理研报搜索响应时出错: {str(e)}"
        logger.error(f"❌ {error_msg}")
        logger.exception("详细错误信息:")
        return f"错误: {error_msg}"


# ===== LangChain Tool 封装 =====

@tool
def report_search(
    keyword: str
) -> str:
    """
    研报知识库搜索工具

    通过关键词搜索研报知识库，返回相关研报的段落内容、来源文件、发布时间等信息。
    支持按时间范围和知识库空间筛选。

    Args:
        keyword: 搜索关键词，可以是研报主题、行业、公司等，例如：
            - "2025年全球光伏市场经济"
            - "人工智能发展趋势"
            - "新能源汽车市场分析"

    Returns:
        包含以下信息的研报列表:
        - fileName: 研报文件名称
        - paraTitle: 段落标题（包含章节层级信息）
        - content: 段落内容摘要
        - score: 匹配度得分
        - pubTime: 研报发布时间
        - customizedTags: 自定义标签
        - page: 页码信息

    Examples:
        >>> # 搜索光伏市场经济相关研报
        >>> report_search(keyword="2025年全球光伏市场经济")
        >>>
        >>> # 搜索新能源汽车市场分析
        >>> report_search(keyword="新能源汽车销量 市场份额")
    """
    return call_report_search(
        keyword=keyword,
        space_code_list=["SP0000001"]
    )


# 导出工具
__all__ = [
    "ReportSearchConfig",
    "call_report_search",
    "report_search",
]
