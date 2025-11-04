# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""智能路由分类器模块"""

import logging
from typing import Literal
from pydantic import BaseModel, Field

from src.llms.llm import get_llm_by_type
from src.utils.enhanced_logger import get_enhanced_logger

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.classifier')


class RouteDecision(BaseModel):
    """路由决策模型"""
    path: Literal["simple_qa", "deep_research", "department_specific"] = Field(
        description="路由路径: simple_qa(简单问答), deep_research(深度研究), department_specific(部门专用)"
    )
    complexity: Literal["simple", "medium", "complex"] = Field(
        description="问题复杂度: simple(简单), medium(中等), complex(复杂)"
    )
    department_match: bool = Field(
        description="是否需要部门专用处理"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="决策置信度 0-1之间"
    )
    reasoning: str = Field(
        description="决策理由，简要说明为什么选择此路径"
    )


def classify_request(
    query: str, 
    department: str = "general",
    enable_smart_routing: bool = True
) -> RouteDecision:
    """
    使用LLM对用户请求进行智能分类
    
    Args:
        query: 用户查询内容
        department: 用户所属部门
        enable_smart_routing: 是否启用智能路由
        
    Returns:
        RouteDecision: 路由决策结果
    """
    
    enhanced_logger.logger.info(
        f"🔍 CLASSIFIER_START | 查询: '{query[:50]}...' | 部门: {department}"
    )
    
    # 如果未启用智能路由，默认使用深度研究路径
    if not enable_smart_routing:
        enhanced_logger.logger.info("⚠️ 智能路由未启用，使用默认简单问答路径")
        return RouteDecision(
            path="simple_qa",
            complexity="medium",
            department_match=False,
            confidence=1.0,
            reasoning="智能路由未启用，使用默认路径"
        )
    
    # 构建分类提示词
    classification_prompt = f"""你是一个智能路由分类器。分析用户的查询请求，并决定最合适的处理路径。

**用户部门**: {department}
**用户查询**: {query}

请根据以下规则进行精确分类:

## 1. 简单问答 (simple_qa)
适用场景:
- ✅ 事实性问题，可通过单次搜索回答
- ✅ 定义、解释类问题（如"什么是..."、"解释..."）
- ✅ 简单计算或数据查询
- ✅ 简短的操作指导（如"如何..."单步操作）
- ✅ 问题长度通常较短（<30字）

示例:
- "什么是人工智能?"
- "Python如何定义函数?"
- "今天的日期是?"
- "GDP的全称是什么?"

## 2. 深度研究 (deep_research)
适用场景:
- ✅ 需要多步骤分析的复杂问题
- ✅ 需要综合多个来源信息
- ✅ 研究性、分析性、对比性问题
- ✅ 需要生成详细报告
- ✅ 趋势分析、影响评估类问题

示例:
- "分析AI在医疗行业的应用趋势和未来发展"
- "对比React、Vue、Angular三种框架的优劣"
- "研究区块链技术在金融领域的应用现状"
- "评估新能源汽车市场的发展前景"

## 3. 部门专用 (department_specific)
适用场景:
- ✅ 与特定部门高度相关的专业问题
- ✅ 需要部门特定知识库或工具
- ✅ 部门内部流程、规范相关

部门识别:
- **tech/技术部**: 代码分析、系统架构、技术方案、算法、数据库、API设计
- **marketing/市场部**: 市场调研、竞品分析、营销策略、用户研究、推广方案
- **finance/财务部**: 财务分析、成本核算、预算编制、财务报表、投资分析

示例:
- tech: "设计一个用户认证系统的数据库架构"
- marketing: "分析竞品的营销策略和市场定位"
- finance: "计算项目的投资回报率和成本效益"

## 分类规则总结
1. **优先级**: 部门专用 > 深度研究 > 简单问答
2. **部门匹配**: 如果查询包含部门关键词且department不是general，考虑department_specific
3. **复杂度判断**:
   - simple: 单一事实、定义、简单操作
   - medium: 需要一定分析但不复杂
   - complex: 多维度分析、研究性问题
4. **置信度**: 
   - 0.9-1.0: 非常明确
   - 0.7-0.9: 较为明确
   - 0.5-0.7: 一般明确
   - <0.5: 不太确定

请提供你的分类决策，包括路径、复杂度、部门匹配、置信度和理由。
"""

    try:
        # 使用LLM进行分类
        llm = get_llm_by_type("basic")
        
        # 尝试使用结构化输出
        try:
            structured_llm = llm.with_structured_output(RouteDecision)
            result = structured_llm.invoke([
                {"role": "user", "content": classification_prompt}
            ])
        except Exception as e:
            # 如果结构化输出失败，使用普通调用并手动解析
            logger.warning(f"结构化输出失败，使用备用方案: {e}")
            response = llm.invoke([
                {"role": "user", "content": classification_prompt}
            ])
            
            # 简单的启发式规则作为后备
            content = response.content if hasattr(response, 'content') else str(response)
            result = _fallback_classification(query, department, content)
        
        enhanced_logger.logger.info(
            f"✅ CLASSIFIER_RESULT | 路径: {result.path} | "
            f"复杂度: {result.complexity} | "
            f"置信度: {result.confidence:.2f} | "
            f"理由: {result.reasoning}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"分类过程出错: {e}，使用默认路径")
        # 出错时使用保守的默认策略
        return _fallback_classification(query, department, "")


def _fallback_classification(query: str, department: str, llm_response: str = "") -> RouteDecision:
    """
    备用分类方法，使用基于规则的启发式策略
    
    Args:
        query: 用户查询
        department: 用户部门
        llm_response: LLM的响应（如果有）
        
    Returns:
        RouteDecision: 路由决策
    """
    
    query_lower = query.lower()
    query_length = len(query)
    
    # 简单问答的关键词
    simple_keywords = [
        "什么是", "是什么", "定义", "解释", "how to", "what is",
        "如何", "怎么", "为什么", "why", "when", "where"
    ]
    
    # 深度研究的关键词
    research_keywords = [
        "分析", "研究", "对比", "比较", "评估", "趋势",
        "影响", "发展", "现状", "未来", "analyze", "research",
        "compare", "trend", "impact"
    ]
    
    # 部门关键词
    department_keywords = {
        "tech": ["代码", "架构", "算法", "数据库", "API", "系统", "技术", "code", "architecture"],
        "marketing": ["市场", "营销", "竞品", "用户", "推广", "marketing", "promotion"],
        "finance": ["财务", "成本", "预算", "报表", "投资", "finance", "budget", "cost"]
    }
    
    # 判断是否匹配部门关键词
    department_match = False
    if department in department_keywords:
        for keyword in department_keywords[department]:
            if keyword in query_lower:
                department_match = True
                break
    
    # 判断复杂度和路径
    if department != "general" and department_match:
        # 部门专用路径
        return RouteDecision(
            path="department_specific",
            complexity="medium",
            department_match=True,
            confidence=0.7,
            reasoning=f"查询包含{department}部门的专业关键词"
        )
    
    # 检查是否为简单问答
    is_simple = False
    for keyword in simple_keywords:
        if keyword in query_lower and query_length < 50:
            is_simple = True
            break
    
    if is_simple:
        return RouteDecision(
            path="simple_qa",
            complexity="simple",
            department_match=False,
            confidence=0.75,
            reasoning="查询包含简单问答关键词且长度较短"
        )
    
    # 检查是否为深度研究
    is_research = False
    for keyword in research_keywords:
        if keyword in query_lower:
            is_research = True
            break
    
    if is_research or query_length > 50:
        return RouteDecision(
            path="deep_research",
            complexity="complex" if query_length > 80 else "medium",
            department_match=False,
            confidence=0.7,
            reasoning="查询包含研究分析关键词或长度较长"
        )
    
    # 默认使用深度研究路径
    return RouteDecision(
        path="deep_research",
        complexity="medium",
        department_match=False,
        confidence=0.6,
        reasoning="无明确特征，使用默认深度研究路径"
    )


# 导出主要接口
__all__ = ["RouteDecision", "classify_request"]
