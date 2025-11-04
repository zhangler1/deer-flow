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
    path: Literal["direct_answer", "simple_search", "deep_research", "domain_knowledge"] = Field(
        description="路由路径: direct_answer(直接回答), simple_search(简单检索), deep_research(深度研究), domain_knowledge(领域知识)"
    )
    complexity: Literal["simple", "medium", "complex", "expert"] = Field(
        description="问题复杂度: simple(简单通用), medium(适中专业), complex(复杂分散), expert(专家集中)"
    )
    needs_search: bool = Field(
        description="是否需要外部检索"
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
    
    # 如果未启用智能路由，默认使用简单检索路径
    if not enable_smart_routing:
        enhanced_logger.logger.info("⚠️ 智能路由未启用，使用默认简单检索路径")
        return RouteDecision(
            path="simple_search",
            complexity="medium",
            needs_search=True,
            confidence=1.0,
            reasoning="智能路由未启用，使用默认主流路径"
        )
    
    # 构建分类提示词
    classification_prompt = f"""你是一个银行业务智能路由分类器。分析用户的查询请求，并决定最合适的处理路径。

**用户查询**: {query}

请根据以下规则进行精确分类:

## 1. 直接回答 (direct_answer)
适用场景:
- ✅ 通用常识性问题，不需要外部检索
- ✅ 基础概念、定义类问题（如"什么是汽车"、"什么是互联网"）
- ✅ 简单数学计算、日期时间查询
- ✅ 非银行业务相关的通用知识
- ✅ LLM训练数据中包含的基础知识

示例:
- "什么是汽车?"
- "地球有多大?"
- "1+1等于几?"
- "Python是什么编程语言?"

## 2. 简单检索 (simple_search) - **主流路径，默认选择**
适用场景:
- ✅ 银行业务相关的常规问题
- ✅ 金融产品介绍、业务流程查询
- ✅ 专业度适中，主流业务知识
- ✅ 单次检索即可获得答案
- ✅ 信息相对集中，不需要多源对比

示例:
- "信用卡如何申请?"
- "个人贷款需要什么条件?"
- "网上银行如何开通?"
- "手机银行转账限额是多少?"

## 3. 深度研究 (deep_research)
适用场景:
- ✅ 需要多维度分析的复杂问题
- ✅ 需要综合多个来源的信息
- ✅ 趋势分析、对比研究类问题
- ✅ 知识比较分散，需要多次检索
- ✅ 研究性、分析性问题

示例:
- "分析金融科技对传统银行的影响趋势"
- "对比国内外数字货币政策的异同"
- "研究普惠金融在农村地区的发展现状"
- "评估开放银行API的安全风险"

## 4. 领域知识 (domain_knowledge)
适用场景:
- ✅ 高度专业化的银行内部知识
- ✅ 特定产品规则、内部流程
- ✅ 专业术语、监管要求
- ✅ 知识高度集中但专业性强
- ✅ 需要特定领域知识库

示例:
- "交通银行沃德财富卡的积分规则"
- "理财产品风险评级R3是什么标准?"
- "SWIFT报文MT103的字段说明"
- "反洗钱可疑交易监测规则"

## 分类规则总结
1. **优先级**: 直接回答 < 简单检索(主流) < 深度研究 < 领域知识
2. **默认原则**: 有疑问时选择"simple_search"（简单检索）
3. **复杂度判断**:
   - simple: 通用常识，不需检索
   - medium: 主流业务，单次检索
   - complex: 分析研究，多次检索
   - expert: 专业知识，领域检索
4. **检索判断**:
   - direct_answer: needs_search = false
   - simple_search: needs_search = true
   - deep_research: needs_search = true
   - domain_knowledge: needs_search = true
5. **置信度**: 
   - 0.9-1.0: 非常明确
   - 0.7-0.9: 较为明确
   - 0.5-0.7: 一般明确（默认simple_search）
   - <0.5: 不确定（默认simple_search）

请提供你的分类决策，包括路径、复杂度、是否需要检索、置信度和理由。
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


def _fallback_classification(query: str, department: str = "general", llm_response: str = "") -> RouteDecision:
    """
    备用分类方法，使用基于规则的启发式策略
    
    Args:
        query: 用户查询
        department: 用户部门（不再使用）
        llm_response: LLM的响应（如果有）
        
    Returns:
        RouteDecision: 路由决策
    """
    
    query_lower = query.lower()
    query_length = len(query)
    
    # 直接回答的关键词（通用常识）
    direct_keywords = [
        "什么是汽车", "什么是互联网", "什么是python",
        "地球有多大", "1+1", "汽车是什么",
        "what is car", "what is internet"
    ]
    
    # 简单检索的关键词（银行业务主流）
    simple_search_keywords = [
        "信用卡", "贷款", "网上银行", "手机银行",
        "转账", "存款", "取款", "理财",
        "如何申请", "如何开通", "需要什么条件",
        "产品介绍", "业务流程", "操作步骤"
    ]
    
    # 深度研究的关键词
    research_keywords = [
        "分析", "研究", "对比", "比较", "评估", "趋势",
        "影响", "发展", "现状", "未来", 
        "analyze", "research", "compare", "trend", "impact"
    ]
    
    # 领域知识关键词（银行专业）
    domain_keywords = [
        "积分规则", "风险评级", "swift报文", "mt103",
        "反洗钱", "监测规则", "内部流程", "监管要求",
        "产品规则", "专业术语", "技术标准"
    ]
    
    # 检查直接回答（通用常识）
    for keyword in direct_keywords:
        if keyword in query_lower:
            return RouteDecision(
                path="direct_answer",
                complexity="simple",
                needs_search=False,
                confidence=0.8,
                reasoning=f"查询包含通用常识关键词，不需要外部检索"
            )
    
    # 非银行业务相关的通用知识（如汽车、地理等）
    non_banking_keywords = ["汽车", "地球", "历史", "科学", "数学", "物理"]
    is_non_banking = any(kw in query_lower for kw in non_banking_keywords)
    is_banking_related = any(kw in query_lower for kw in simple_search_keywords + domain_keywords)
    
    if is_non_banking and not is_banking_related and query_length < 30:
        return RouteDecision(
            path="direct_answer",
            complexity="simple",
            needs_search=False,
            confidence=0.75,
            reasoning="非银行业务相关的通用知识，使用直接回答"
        )
    
    # 检查领域知识（高度专业）
    for keyword in domain_keywords:
        if keyword in query_lower:
            return RouteDecision(
                path="domain_knowledge",
                complexity="expert",
                needs_search=True,
                confidence=0.8,
                reasoning=f"查询包含专业领域关键词，需要专业知识库"
            )
    
    # 检查深度研究
    for keyword in research_keywords:
        if keyword in query_lower:
            return RouteDecision(
                path="deep_research",
                complexity="complex",
                needs_search=True,
                confidence=0.75,
                reasoning="查询包含研究分析关键词，需要深度研究"
            )
    
    # 检查简单检索（主流路径）
    for keyword in simple_search_keywords:
        if keyword in query_lower:
            return RouteDecision(
                path="simple_search",
                complexity="medium",
                needs_search=True,
                confidence=0.8,
                reasoning="查询包含业务关键词，使用简单检索"
            )
    
    # 根据问题长度判断
    if query_length > 80:
        # 长问题，可能是深度研究
        return RouteDecision(
            path="deep_research",
            complexity="complex",
            needs_search=True,
            confidence=0.65,
            reasoning="问题长度较长，可能需要深度研究"
        )
    
    # 默认：简单检索（主流路径）
    return RouteDecision(
        path="simple_search",
        complexity="medium",
        needs_search=True,
        confidence=0.6,
        reasoning="无明确特征，使用默认主流路径（简单检索）"
    )


# 导出主要接口
__all__ = ["RouteDecision", "classify_request"]
