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
    searchknowledge_standard,
    searchknowledge_standard_tool,
    VectorSearchBaseTool,
    get_budget_manager,
    clear_budget_manager,
)
from src.utils.enhanced_logger import get_enhanced_logger

from src.graph.nodes.utils import _execute_agent_step

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.deep_research.researcher')

async def researcher_node(
    state, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """执行研究任务的研究员节点（采用 Middleware 架构）"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | researcher | 开始执行研究节点 (Middleware 模式)")
    
    configurable = Configuration.from_runnable_config(config)
    
    # 🔥 每个 researcher 节点开始时清零预算，确保每个节点独立计算预算
    # 使用 thread_id 作为 budget session_id（State 中无 session_id 字段）
    session_id = config.get("thread_id") or config.get("configurable", {}).get("thread_id", "default")
    
    # 从配置中获取预算参数
    max_tokens = getattr(configurable, 'search_budget_max_tokens', 10000)
    hard_token_limit = getattr(configurable, 'search_budget_hard_limit', 14000)
    token_chars_ratio = getattr(configurable, 'search_budget_token_chars_ratio', 2.5)
    
    budget_manager = get_budget_manager(
        session_id, 
        max_search_calls=getattr(configurable, 'search_budget_max_calls', 5),
        max_tokens=max_tokens,
        token_chars_ratio=token_chars_ratio,
        hard_token_limit=hard_token_limit,
    )
    budget_manager.reset()  # 清零计数器
    enhanced_logger.logger.info(
        f"🔄 BUDGET_RESET | session: {session_id} | 预算计数器已清零 | "
        f"max_tokens: {max_tokens} | hard_limit: {hard_token_limit} | "
        f"token_chars_ratio: {token_chars_ratio}"
    )

    # 读取 researcher 每步的搜索工具调用预算
    # 说明：该值主要作为 researcher 节点内搜索工具的 max_search_calls（即每步最多可调用的搜索次数）；
    # 同时兼作 LangGraph agent recursion 的软建议值，实际硬上限 = max(budget * 10, 50)。
    # 配置来源优先级：env(RESEARCHER_RECURSION_LIMIT) > configurable > yaml(SEARCH_BUDGET.researcher_per_step_budget) > 默认值 5
    # 由 Configuration 统一解析。
    researcher_search_budget = getattr(configurable, 'researcher_recursion_limit', 5)
    try:
        researcher_search_budget = int(researcher_search_budget)
    except (TypeError, ValueError):
        researcher_search_budget = 5
    enhanced_logger.logger.info(
        f"🎛️  SEARCH_BUDGET_CONFIG | researcher | 每步搜索调用预算: {researcher_search_budget}"
    )
    
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

    # 获取报告风格，默认为学术
    report_style = state.get("report_style", "academic")
    enhanced_logger.logger.info(f"📋 REPORT_STYLE | 当前报告风格: {report_style}")

    # 获取预算控制开关（优先从 configurable 读取，默认 True）
    use_budget_online = getattr(configurable, 'use_budget_controlled_online_search', True)
    use_budget_bocom = getattr(configurable, 'use_budget_controlled_bocom_search', True)
    # 兼容字符串（环境变量传入时可能是字符串）
    if isinstance(use_budget_online, str):
        use_budget_online = use_budget_online.lower() not in ('false', '0', 'no', '')
    if isinstance(use_budget_bocom, str):
        use_budget_bocom = use_budget_bocom.lower() not in ('false', '0', 'no', '')


    # 根据报告风格动态配置工具
    # 说明：预算控制现已下沉到 BudgetEnforcementMiddleware（方案 C），
    # 所以 researcher 节点下发到 ReactLoop 的是原生工具。
    # vector_search 也已改为无状态原生工具，guwp_token 由中间件注入。
    if report_style == "industry_report":
        # 行业研报：searchknowledge_standard(段落级标准知识检索) + online_search
        session_id = state.get("session_id", "default")
        logger.info(f"📚 industry_report | session_id={session_id}")
        tools = [
            research_skill_prompt_search,
        ]
        tool_name_list = ["research_skill_prompt_search"]
        # 根据开关决定是否添加在线搜索工具
        if use_budget_online:
            tools.append(online_search_tool(configurable.get_max_results("online_search")))
            tool_name_list.append("online_search")
        # 行业研报沿用 use_budget_bocom 开关控制内部知识库检索（语义复用：内网知识库开关）
        if use_budget_bocom:
            tools.append(searchknowledge_standard_tool(configurable.get_max_results("searchknowledge_standard")))
            tool_name_list.append("searchknowledge_standard")
            # 新增 vector_search（向量相似度检索），与 searchknowledge_standard 互补
            # 原生注册，guwp_token 由中间件从 state 注入
            tools.append(VectorSearchBaseTool(
                max_results=configurable.get_max_results("vector_search"),
            ))
            tool_name_list.append("vector_search")
        tool_names = ", ".join(tool_name_list)

    elif report_style == "business_marketing":
        # 对公营销报告：使用完整的工具链
        session_id = state.get("session_id", "default")
        logger.info(f"📋 business_marketing | session_id={session_id}")
        tools = []
        tool_name_list = []
        # 根据开关决定是否添加在线搜索工具
        if use_budget_online:
            tools.append(online_search_tool(configurable.get_max_results("online_search")))
            tool_name_list.append("online_search")
        # vector_search 原生注册（guwp_token 由中间件从 state 注入），替换原 bocomsearch 包装器
        if use_budget_bocom:
            tools.append(VectorSearchBaseTool(
                max_results=configurable.get_max_results("vector_search"),
            ))
            tool_name_list.append("vector_search")
        tools += [
            business_opportunity_search,
            sentiment_search,
            financial_summary,
            product_instance_search,
        ]
        tool_name_list += ["business_opportunity_search", "sentiment_search", "financial_summary", "product_instance_search"]
        tool_names = ", ".join(tool_name_list)

    elif report_style == "business_marketing_client":
        # 对公营销客户版：使用基础搜索工具
        session_id = state.get("session_id", "default")
        tools = [research_skill_prompt_search]
        tool_name_list = ["research_skill_prompt_search"]
        # 根据开关决定是否添加在线搜索工具
        if use_budget_online:
            tools.append(online_search_tool(configurable.get_max_results("online_search")))
            tool_name_list.append("online_search")
        tool_names = ", ".join(tool_name_list)

    elif report_style == "industry_research":
        # 行业研究报告：使用 research_skill_prompt_search + online_search
        tools = [research_skill_prompt_search]
        tool_name_list = ["research_skill_prompt_search"]
        # 根据开关决定是否添加在线搜索工具
        if use_budget_online:
            tools.append(online_search_tool(configurable.get_max_results("online_search")))
            tool_name_list.append("online_search")
        tool_names = ", ".join(tool_name_list)

    elif report_style == "academic":
        # 学术研究：使用基础搜索工具
        session_id = state.get("session_id", "default")
        tools = []
        tool_name_list = []
        # 根据开关决定是否添加在线搜索工具
        if use_budget_online:
            tools.append(online_search_tool(configurable.get_max_results("online_search")))
            tool_name_list.append("online_search")
        tool_names = ", ".join(tool_name_list) if tool_name_list else "(无搜索工具)"
    
    else:
        # 默认配置
        tools = [
            research_skill_prompt_search,
        ]
        tool_names = "research_skill_prompt_search"

    enhanced_logger.logger.info(
        f"🔧 TOOLS_READY | 研究工具配置完成 | "
        f"报告风格: {report_style} | 工具数: {len(tools)} | 包含: {tool_names}"
    )
    
    
    # 执行研究节点
    result = await _execute_agent_step(
        state,
        config,
        "researcher",
        tools,
        recursion_limit=researcher_search_budget,
    )
    
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | researcher | 节点执行完成 | 总耗时: {duration:.2f}s")
    
    return result


async def coder_node(
    state, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """执行代码分析的编码员节点"""
    logger.info("编码员节点正在编写代码")
    return await _execute_agent_step(
        state,
        config,
        "coder",
        [python_repl_tool],
    )
