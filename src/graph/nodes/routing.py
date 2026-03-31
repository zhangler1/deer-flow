# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
路由节点模块

提供智能路由功能，根据用户查询选择最优处理路径。
"""

import time
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.graph.classifier import classify_request
from src.graph.types import State
from src.utils.enhanced_logger import get_enhanced_logger

# Langfuse 集成（受 LANGFUSE_ENABLED 开关控制）
import os
_langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
try:
    if _langfuse_enabled:
        from langfuse import observe
    else:
        raise ImportError("Langfuse disabled by LANGFUSE_ENABLED=false")
except ImportError:
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return decorator

enhanced_logger = get_enhanced_logger('graph.nodes.routing')


def _get_path_description(path: str) -> str:
    """获取路径描述"""
    descriptions = {
        "direct_answer": "直接回答，不走检索",
        "simple_search": "简单检索，单次查询",
        "iterative_research": "迭代研究，自主深挖",
        "deep_research": "深度研究，多轮分析",
    }
    return descriptions.get(path, "未知路径")


def _get_complexity_description(complexity: str) -> str:
    """获取复杂度描述"""
    descriptions = {
        "simple": "简单通用",
        "medium": "适中专业",
        "complex": "复杂分散",
        "expert": "专家集中"
    }
    return descriptions.get(complexity, "未知复杂度")


@observe(name="📡 路由节点", as_type="agent")
def router_node(
    state: State, config: RunnableConfig
) -> Command[Literal["direct_answer_node", "simple_search_node", "iterative_research_node", "coordinator"]]:
    """
    智能路由节点，分析用户请求并决定处理路径
    
    根据用户查询，自动选择最优处理路径：
    - direct_answer_node: 直接回答，通用知识（不走检索）
    - simple_search_node: 简单检索，主流业务（单次检索）
    - iterative_research_node: 迭代研究，单问题深挖（自主迭代）
    - coordinator: 深度研究路径（多轮检索研究）
    """
    start_time = time.time()
    enhanced_logger.logger.info("🔀 NODE_ENTRY | router | 开始智能路由分析")
    
    # 提取用户信息
    user_query = state.get("research_topic") or (
        state["messages"][-1].content if state.get("messages") else ""
    )
    # 确保 user_query 是字符串类型
    if not isinstance(user_query, str):
        user_query = str(user_query)
    enable_smart_routing = state.get("enable_smart_routing", True)
    
    enhanced_logger.logger.info(
        f"📝 ROUTER_INPUT | 查询: '{user_query[:50]}...' | "
        f"智能路由: {'启用' if enable_smart_routing else '禁用'}"
    )
    
    # 调用分类模型
    force_routing_path = state.get("force_routing_path", None)
    route_decision = classify_request(
        query=user_query,
        enable_smart_routing=enable_smart_routing,
        force_path=force_routing_path
    )
    
    # 记录路由决策
    enhanced_logger.logger.info(
        f"🎯 ROUTING_DECISION | 路径: {route_decision.path} | "
        f"复杂度: {route_decision.complexity} | "
        f"需要检索: {route_decision.needs_search} | "
        f"置信度: {route_decision.confidence:.2f} | "
        f"理由: {route_decision.reasoning}"
    )
    
    # 构造分类信息，输出到前端
    classification_message = (
        f"---\n"
        f"**🔀 智能路由分类结果**\n\n"
        f"- **路由路径**: `{route_decision.path}` ({_get_path_description(route_decision.path)})\n"
        f"- **问题复杂度**: `{route_decision.complexity}` ({_get_complexity_description(route_decision.complexity)})\n"
        f"- **是否检索**: {'✅ 是' if route_decision.needs_search else '❌ 否'}\n"
        f"- **置信度**: `{route_decision.confidence:.2%}`\n"
        f"- **分类理由**: {route_decision.reasoning}\n"
        f"\n---\n"
    )
    
    # 更新状态
    state_update = {
        "query_complexity": route_decision.complexity,
        "routing_path": route_decision.path,
        "messages": [
            AIMessage(
                content=classification_message,
                name="router"
            )
        ]
    }
    
    duration = time.time() - start_time
    enhanced_logger.logger.info(
        f"✅ NODE_EXIT | router | 路由决策完成 | 耗时: {duration:.2f}s"
    )
    
    # 根据决策路由到不同节点
    if route_decision.path == "direct_answer":
        return Command(update=state_update, goto="direct_answer_node")
    elif route_decision.path == "simple_search":
        return Command(update=state_update, goto="simple_search_node")
    elif route_decision.path == "iterative_research":
        return Command(update=state_update, goto="iterative_research_node")
    else:  # deep_research
        return Command(update=state_update, goto="coordinator")
