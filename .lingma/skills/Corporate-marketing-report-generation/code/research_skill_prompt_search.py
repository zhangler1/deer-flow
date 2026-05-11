# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
研究技能提示词查询工具

通过调用 Rerank API,智能匹配最相关的研究技能提示词。
支持根据用户输入自动选择最合适的提示词文件。

本文件是对公营销报告 Skill 的核心组件，负责智能召回研究技能提示词。
"""

import logging
import os
from typing import Optional
from langchain_core.tools import tool

# 导入重排序工具（如果在项目中使用）
try:
    import sys
    # 尝试从项目根目录导入
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
    from utils.rerank import rerank_objects
    RERANK_AVAILABLE = True
except ImportError:
    # 如果无法导入，将在运行时使用降级方案
    RERANK_AVAILABLE = False
    rerank_objects = None

# 导入研究技能列表
from .research_skills_list import RESEARCH_SKILLS_LIST

logger = logging.getLogger(__name__)


def _read_prompt_file(filepath: str) -> str:
    """
    读取提示词文件内容

    Args:
        filepath: 提示词文件路径

    Returns:
        str: 文件内容
    """
    try:
        # 构建完整路径 - 从项目根目录开始
        # 获取工具文件所在目录的父目录的父目录(即项目根目录)
        tool_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(tool_dir))
        full_path = os.path.join(project_root, filepath)

        logger.debug(f"📂 提示词文件完整路径: {full_path}")

        if not os.path.exists(full_path):
            logger.error(f"❌ 提示词文件不存在: {full_path}")
            return f"错误: 提示词文件不存在 - {filepath}"

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return content

    except Exception as e:
        logger.error(f"❌ 读取提示词文件失败: {e}")
        return f"错误: 读取提示词文件失败 - {str(e)}"


def _get_skills_list(report_style: str = "business_marketing") -> list:
    """
    根据报告风格获取相应的研究技能列表

    Args:
        report_style: 报告风格，本 Skill 仅支持 business_marketing

    Returns:
        list: 研究技能列表
    """
    # 本 Skill 专注于对公营销报告（普客版）
    if report_style != "business_marketing":
        logger.warning(f"⚠️ 本 Skill 仅支持 business_marketing 风格，请求的样式为: {report_style}")

    return RESEARCH_SKILLS_LIST


def _match_skill_by_query(
    query: str,
    top_k: int = 1,
    report_style: str = "business_marketing"
) -> Optional[dict]:
    """
    根据查询智能匹配最相关的研究技能提示词

    Args:
        query: 搜索关键词或用户需求描述
        top_k: 返回前 K 个最相关的技能
        report_style: 报告风格，用于选择相应的技能列表

    Returns:
        Optional[dict]: 匹配到的技能信息字典,包含 name, filepath, description 等
    """
    # 根据报告风格选择技能列表
    skills_list = _get_skills_list(report_style)

    try:
        # 如果配置了 Rerank API,使用智能匹配
        if os.getenv("RERANK_API_URL"):
            logger.info(f"🔄 使用 Rerank 模型智能匹配研究技能 | 查询: '{query}' | 风格: {report_style}")

            # 使用重排序工具找到最相关的技能
            # 组合 name 和 description 字段进行匹配
            enhanced_skills = []
            for skill in skills_list:
                enhanced_skill = skill.copy()
                # 将 name 和 description 组合作为匹配文本
                enhanced_skill["match_text"] = f"{skill['name']} - {skill.get('description', '')}"
                enhanced_skills.append(enhanced_skill)

            matched_skills = rerank_objects(
                query=query,
                objects=enhanced_skills,
                text_field="match_text",
                top_k=top_k
            )

            if matched_skills:
                # 返回最相关的技能
                best_match = matched_skills[0]
                # 移除临时字段
                best_match.pop("match_text", None)
                best_match.pop("relevance_score", None)

                logger.info(f"  ✓ 匹配技能: {best_match.get('name')} (评分: {matched_skills[0].get('relevance_score', 0):.4f})")
                return best_match

        # 降级方案:简单的关键词匹配
        logger.info(f"🔄 使用关键词匹配算法 | 查询: '{query}' | 风格: {report_style}")

        best_match = None
        best_score = 0

        for skill in skills_list:
            name = skill.get("name", "")
            description = skill.get("description", "")

            # 计算匹配分数
            score = 0
            query_lower = query.lower()

            # 精确匹配技能名称
            if query_lower == name.lower():
                score = 100
            # 技能名称包含查询词
            elif query_lower in name.lower():
                score = 80
            # 查询词包含技能名称
            elif name.lower() in query_lower:
                score = 70
            # 描述中包含查询词
            elif query_lower in description.lower():
                score = 60
            # 部分匹配
            elif any(word in name.lower() for word in query_lower.split()):
                score = 40

            if score > best_score:
                best_score = score
                best_match = skill

        if best_match:
            return best_match

        # 如果没有匹配到,返回第一个作为默认
        if skills_list:
            logger.warning(f"⚠️ 未能匹配到相关技能,使用默认技能: {skills_list[0].get('name')}")
            return skills_list[0]

        return None

    except Exception as e:
        logger.error(f"❌ 技能匹配失败: {e}")
        # 发生错误时返回第一个技能
        if skills_list:
            return RESEARCH_SKILLS_LIST[0]
        return None


# ===== LangChain Tool 封装 =====

@tool
def research_skill_prompt_search(
    query: str,
    report_style: str = "business_marketing"
) -> str:
    """
    研究技能提示词查询工具 - 根据用户需求智能匹配最相关的提示词

    使用指南:
    1. 当用户需要特定类型的研究分析时(如财务分析、商机分析等),使用此工具
    2. 工具会自动匹配最合适的提示词文件并返回内容
    3. 支持自然语言查询,如"财务分析"、"分析企业商机"等

    使用场景:
    - 用户询问需要分析企业财务数据时
    - 用户需要了解企业商机或舆情时
    - 用户要求进行行业分析或政策分析时
    - 任何需要使用特定研究技能的场景

    Args:
        query: 【必填】用户的需求描述或关键词,系统会智能匹配最相关的提示词。
               例如: "财务分析"、"商机分析"、"舆情分析"等
        report_style: 【可选】报告风格,本 Skill 仅支持 "business_marketing"（对公营销报告-普客版）。
                      如果未指定,默认使用 business_marketing。

    Returns:
        str: 匹配到的提示词文件的完整内容,可以直接用作系统提示词

    Examples:
        >>> # 财务分析
        >>> research_skill_prompt_search(query="财务分析")
        >>> research_skill_prompt_search(query="分析企业的财务状况")

        >>> # 商机分析
        >>> research_skill_prompt_search(query="商机分析")
        >>> research_skill_prompt_search(query="有哪些合作机会")

        >>> # 舆情分析
        >>> research_skill_prompt_search(query="舆情分析")
        >>> research_skill_prompt_search(query="企业声誉怎么样")

        >>> # 区域经济环境分析
        >>> research_skill_prompt_search(query="区域经济环境分析")

    注意事项:
    - 如果没有精确匹配,系统会选择最相关的提示词
    - 返回的提示词内容可以直接用于设置系统提示词
    - 提示词内容包含详细的研究方法和工具使用指南
    - 本 Skill 专注于对公营销报告（普客版）
    """
    try:
        logger.info(f"🔍 研究技能提示词查询 | 查询: '{query}' | 风格: {report_style}")

        # 匹配最相关的技能
        matched_skill = _match_skill_by_query(query, top_k=1, report_style=report_style)

        if not matched_skill:
            error_msg = f"未找到相关的研究技能提示词"
            logger.warning(f"⚠️  {error_msg}")
            return f"错误: {error_msg}"

        # 读取提示词文件内容
        skill_name = matched_skill.get("name", "未知技能")
        filepath = matched_skill.get("filepath", "")

        prompt_content = _read_prompt_file(filepath)

        if prompt_content.startswith("错误:"):
            return prompt_content

        # 添加技能信息作为注释
        result = f"""# {skill_name} 提示词
# 技能描述: {matched_skill.get('description', '无')}

{prompt_content}
"""

        logger.info(f"✅ 成功获取 {skill_name} 提示词 | 内容长度: {len(prompt_content)} 字符")

        return result

    except Exception as e:
        error_msg = f"研究技能提示词查询失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"


# 导出工具
__all__ = [
    "research_skill_prompt_search",
    "_match_skill_by_query",
    "_read_prompt_file",
]
