# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT


from langgraph.graph import MessagesState

from src.prompts.planner_model import Plan
from src.rag import Resource


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Runtime Variables
    locale: str = "en-US"
    research_topic: str = ""
    observations: list[str] = []
    resources: list[Resource] = []
    plan_iterations: int = 0
    current_plan: Plan | str = None
    final_report: str = ""
    auto_accepted_plan: bool = False
    enable_background_investigation: bool = True
    background_investigation_results: str = None
    system_context: str = ""  # 系统背景上下文，各节点在Prompt Template中按需使用（不修改用户消息）
    
    # 智能路由相关字段
    query_complexity: str = "unknown"  # 查询复杂度: simple/medium/complex
    routing_path: str = "auto"  # 路由路径: auto/simple_qa/deep_research
    enable_smart_routing: bool = True  # 是否启用智能路由
    
    # 迭代研究相关字段
    iteration_count: int = 0  # 当前迭代轮次
    iteration_history: list[dict] = []  # 迭代历史记录
