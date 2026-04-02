# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
研究员与编码员节点模块

包含：
- researcher_node: 研究员节点（执行研究任务，支持 Middleware 架构）
- coder_node: 编码员节点（执行代码分析任务）
"""

import logging
import os
import time
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.config.configuration import Configuration
from src.tools import (
    python_repl_tool,
    online_search_tool,
    research_skill_prompt_search,
    business_opportunity_search,
    sentiment_search,
    financial_summary,
    product_instance_search,
    report_search,
    budget_controlled_online_search_tool,
    get_budget_manager,
    clear_budget_manager,
)
from src.utils.enhanced_logger import get_enhanced_logger

from src.graph.nodes.utils import _setup_and_execute_agent_step

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.deep_research.researcher')


async def researcher_node(
    state, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """执行研究任务的研究员节点（采用 Middleware 架构）"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | researcher | 开始执行研究节点 (Middleware 模式)")
    
    logger.info("Researcher node is researching (with middleware support).")
    configurable = Configuration.from_runnable_config(config)
    
    # 🔥 每个 researcher 节点开始时清零预算，确保每个节点独立计算预算
    session_id = state.get("session_id", "default")
    
    # 从配置中获取预算参数
    max_tokens = getattr(configurable, 'search_budget_max_tokens', 10000)
    hard_token_limit = getattr(configurable, 'search_budget_hard_limit', 14000)
    token_chars_ratio = getattr(configurable, 'search_budget_token_chars_ratio', 2.5)
    
    budget_manager = get_budget_manager(
        session_id, 
        max_search_calls=10,  # 默认值，后续会根据配置覆盖
        max_tokens=max_tokens,
        token_chars_ratio=token_chars_ratio,
    )
    budget_manager.reset()  # 清零计数器
    enhanced_logger.logger.info(
        f"🔄 BUDGET_RESET | session: {session_id} | 预算计数器已清零 | "
        f"max_tokens: {max_tokens} | hard_limit: {hard_token_limit} | "
        f"token_chars_ratio: {token_chars_ratio}"
    )

    # 读取 researcher 特定的递归限制配置
    researcher_limit = getattr(configurable, 'researcher_recursion_limit', None)
    if researcher_limit is None:
        researcher_limit = int(os.environ.get('RESEARCHER_RECURSION_LIMIT', '5'))
    enhanced_logger.logger.info(f"🎛️  RECURSION_LIMIT_CONFIG | researcher | 配置值: {researcher_limit}")
    
    # 获取当前要执行的步骤信息用于日志
    current_plan = state.get("current_plan")
    current_step_title = "未知步骤"
    if current_plan:
        if hasattr(current_plan, 'steps'):
            plan_steps = current_plan.steps
        elif isinstance(current_plan, dict) and 'steps' in current_plan:
            plan_steps = current_plan['steps']
        else:
            plan_steps = []
            
        for step in plan_steps:
            if not step.execution_res:
                current_step_title = step.title
                break
    
    enhanced_logger.logger.info(f"🔍 RESEARCH_INIT | 开始研究步骤: {current_step_title}")

    # 获取报告风格，默认为行业研报
    report_style = state.get("report_style", "industry_report")
    enhanced_logger.logger.info(f"📋 REPORT_STYLE | 当前报告风格: {report_style}")

    # 根据报告风格动态配置工具
    if report_style == "industry_report":
        # 行业研报：使用研报知识库搜索
        tools = [
            research_skill_prompt_search,
            report_search,
        ]
        tool_names = "report_search"

    elif report_style == "business_marketing":
        # 对公营销报告：使用完整的工具链
        # 使用预算控制的搜索工具，防止搜索过多导致token溢出
        session_id = state.get("session_id", "default")
        tools = [
            budget_controlled_online_search_tool(
                max_results=configurable.max_search_results,
                session_id=session_id,
                max_search_calls=researcher_limit,
                max_tokens=max_tokens,
            ),
            research_skill_prompt_search,
            business_opportunity_search,
            sentiment_search,
            financial_summary,
            product_instance_search,
        ]
        tool_names = "budget_controlled_online_search, research_skill_prompt_search, business_opportunity_search, sentiment_search, financial_summary, product_instance_search"

    elif report_style == "business_marketing_client":
        # 对公营销客户版：使用基础搜索工具
        # 使用预算控制的搜索工具
        session_id = state.get("session_id", "default")
        tools = [
            research_skill_prompt_search,
            budget_controlled_online_search_tool(
                max_results=configurable.max_search_results,
                session_id=session_id,
                max_search_calls=researcher_limit,
                max_tokens=max_tokens,
            ),
        ]
        tool_names = "research_skill_prompt_search, budget_controlled_online_search"

    elif report_style == "academic":
        # 学术研究：使用基础搜索工具
        # 使用预算控制的搜索工具
        session_id = state.get("session_id", "default")
        tools = [
            budget_controlled_online_search_tool(
                max_results=configurable.max_search_results,
                session_id=session_id,
                max_search_calls=researcher_limit,
                max_tokens=max_tokens,
            ),
        ]
        tool_names = "budget_controlled_online_search"
    
    else:
        # 默认配置
        tools = [
            research_skill_prompt_search,
            report_search,
        ]
        tool_names = "research_skill_prompt_search, report_search"

    enhanced_logger.logger.info(
        f"🔧 TOOLS_READY | 研究工具配置完成 | "
        f"报告风格: {report_style} | 工具数: {len(tools)} | 包含: {tool_names}"
    )
    
    logger.info(f"Researcher tools: {tools}")
    
    # 尝试使用带 Middleware 的 Agent
    from src.middlewares.researcher_agent import create_researcher_agent
    
    agent = create_researcher_agent(
        tools=tools,
        model=None,
        enable_summarization=True,
    )
    
    if agent is not None:
        enhanced_logger.logger.info("✅ MIDDLEWARE_AGENT | Researcher agent 已启用 middleware 支持")
        
        result = await _setup_and_execute_agent_step(
            state,
            config,
            "researcher",
            tools,
            recursion_limit=researcher_limit,
            agent_executor=agent,
        )
    else:
        enhanced_logger.logger.info("⚠️  FALLBACK_MODE | 使用传统 agent 模式（无 middleware 支持）")
        
        result = await _setup_and_execute_agent_step(
            state,
            config,
            "researcher",
            tools,
            recursion_limit=researcher_limit,
        )
    
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | researcher | 节点执行完成 | 总耗时: {duration:.2f}s")
    
    return result


async def coder_node(
    state, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """执行代码分析的编码员节点"""
    logger.info("编码员节点正在编写代码")
    return await _setup_and_execute_agent_step(
        state,
        config,
        "coder",
        [python_repl_tool],
    )
