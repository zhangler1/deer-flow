# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""智能路由分类器模块"""

import json
import re
import logging
from typing import Literal
from pydantic import BaseModel, Field, ValidationError

from src.llms.llm import get_llm_by_type
from src.utils.enhanced_logger import get_enhanced_logger
from src.prompts.template import get_prompt_template, apply_prompt_template

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
    
    # 构建分类提示词 - 使用模板系统
    try:
        # 使用模板系统加载和渲染提示词
        messages = apply_prompt_template(
            "classifier/classifier",
            {"query": query}
        )
        
        # 使用LLM进行分类
        llm = get_llm_by_type("basic")
        
        # 直接调用LLM，不使用with_structured_output
        response = llm.invoke(messages)
        
        # 提取响应内容
        content = response.content if hasattr(response, 'content') else str(response)
        
        # 确保 content 是字符串类型
        if not isinstance(content, str):
            content = str(content)
        
        # 手动解析JSON
        result = _parse_llm_response_to_route_decision(content, query, department)
        
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


def _parse_llm_response_to_route_decision(
    content: str, 
    query: str, 
    department: str
) -> RouteDecision:
    """
    解析LLM返回的JSON字符串为RouteDecision对象
    
    Args:
        content: LLM返回的内容（可能包含JSON）
        query: 原始查询
        department: 部门信息
        
    Returns:
        RouteDecision: 解析后的路由决策
    """
    try:
        # 尝试直接解析JSON
        # 首先尝试找到JSON代码块
        json_match = re.search(r'```json\s*({.*?})\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试找到纯JSON对象
            json_match = re.search(r'{[^{}]*"path"[^{}]*}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # 如果都找不到，尝试整个内容
                json_str = content.strip()
        
        # 解析JSON
        data = json.loads(json_str)
        
        # 验证必需字段
        required_fields = ["path", "complexity", "needs_search", "confidence", "reasoning"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            enhanced_logger.logger.warning(
                f"⚠️ JSON解析缺少字段: {missing_fields}，使用默认值填充"
            )
            # 使用默认值填充缺失字段
            defaults = {
                "path": "simple_search",
                "complexity": "medium",
                "needs_search": True,
                "confidence": 0.6,
                "reasoning": "JSON解析不完整，使用默认值"
            }
            for field in missing_fields:
                data[field] = defaults.get(field)
        
        # 验证枚举值
        valid_paths = ["direct_answer", "simple_search", "deep_research", "domain_knowledge"]
        if data["path"] not in valid_paths:
            enhanced_logger.logger.warning(
                f"⚠️ 无效的path值: {data['path']}，使用默认值 simple_search"
            )
            data["path"] = "simple_search"
        
        valid_complexity = ["simple", "medium", "complex", "expert"]
        if data["complexity"] not in valid_complexity:
            enhanced_logger.logger.warning(
                f"⚠️ 无效的complexity值: {data['complexity']}，使用默认值 medium"
            )
            data["complexity"] = "medium"
        
        # 确保confidence在0-1之间
        if not isinstance(data["confidence"], (int, float)) or not (0 <= data["confidence"] <= 1):
            enhanced_logger.logger.warning(
                f"⚠️ 无效的confidence值: {data['confidence']}，使用默认值 0.6"
            )
            data["confidence"] = 0.6
        
        # 创建RouteDecision对象
        try:
            result = RouteDecision(**data)
            enhanced_logger.logger.info("✅ JSON解析成功，创建RouteDecision对象")
            return result
        except ValidationError as e:
            enhanced_logger.logger.error(f"❌ Pydantic验证失败: {e}，使用备用方案")
            return _fallback_classification(query, department, content)
            
    except json.JSONDecodeError as e:
        enhanced_logger.logger.warning(
            f"⚠️ JSON解析失败: {e}，使用基于规则的备用方案"
        )
        return _fallback_classification(query, department, content)
    except Exception as e:
        enhanced_logger.logger.error(
            f"❌ 解析过程出错: {e}，使用备用方案"
        )
        return _fallback_classification(query, department, content)


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
