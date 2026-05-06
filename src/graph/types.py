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
    force_routing_path: str = None  # 🐛 调试模式：强制路由路径（可选）
    
    # 迭代研究相关字段
    iteration_count: int = 0  # 当前迭代轮次
    iteration_history: list[dict] = []  # 迭代历史记录
    node_transition: dict = None  # 节点跳转信息（用于前端事件流，不进入messages）

    # 报告风格相关字段
    report_style: str = "industry_report"  # 报告风格: industry_report(行业研报) / business_marketing(对公营销)
    
    # GUWP Token 相关字段（用于交通银行内网搜索鉴权）
    guwp_token: str = None  # GUWP认证令牌，通过 state 传递确保线程安全（避免多用户并发时环境变量覆盖）

    # 当前研究步骤追踪（由 _execute_agent_step 更新，供其他节点和前端读取）
    current_step_index: int = -1  # 当前 plan step 索引（从0开始，-1 表示未开始）
    current_step_title: str = ""  # 当前 plan step 标题
    next_step_index: int = -1  # 下一步 plan step 索引（-1 表示无下一步）
    next_step_title: str = ""  # 下一步 plan step 标题
