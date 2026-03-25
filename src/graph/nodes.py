# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import json
import logging
import os
import time
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.types import Command, interrupt

from src.agents import create_agent
from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.graph.tool_limit_middleware import ToolCallLimitMiddleware
from src.llms.llm import get_llm_by_type
from src.prompts.planner_model import Plan
from src.prompts.template import apply_prompt_template
from src.tools import (
    get_retriever_tool,
    get_web_search_tool,
    python_repl_tool,
    crawl_tool,
    domain_fin_search,
    industry_report_search,
    news_search,
    news_detail_search,
    product_search,
    product_instance_search,
    online_search_tool,
    research_skill_prompt_search,
    business_opportunity_search,
    sentiment_search,
    financial_summary,
    report_search
)
from src.tools.search import LoggedTavilySearch
from src.utils.json_utils import repair_json_output
from src.utils.text_utils import remove_think_tags
from src.utils.enhanced_logger import get_enhanced_logger

from ..config import SELECTED_SEARCH_ENGINE, SearchEngine
from .types import State
from .classifier import classify_request


import requests
from SQL.services import SceneMapService
from SQL.database import init_database

# Langfuse 集成 - v3 模式 (@observe 装饰器会自动捕获输入输出)
try:
    from langfuse import observe
except ImportError:
    logging.warning("Langfuse not installed. Tracing disabled.")
    
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        # 支持 @observe 和 @observe(...) 两种用法
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return decorator


logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes')


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


@tool
def handoff_to_planner(
    research_topic: Annotated[str, "要移交的研究任务主题"],
    locale: Annotated[str, "用户检测到的语言区域设置（例如：en-US, zh-CN）"],
):
    """移交给规划智能体进行计划制定"""
    # 此工具不返回任何内容：我们只是用它作为LLM信号表示需要移交给规划智能体
    return


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
    # 支持调试模式：从状态中获取 force_routing_path 参数
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
    
    # 🆕 构造分类信息，输出到前端
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
    
    # 更新状态（包含分类信息消息）
    from langchain_core.messages import AIMessage
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


@observe(name="⚡ 直接回答节点", as_type="agent")
def direct_answer_node(state: State, config: RunnableConfig) -> Command[Literal["__end__"]]:
    """
    直接回答节点 - 不走检索，使用LLM的通用知识直接回答
    
    适用于通用常识性问题，如基础概念、定义等
    """
    start_time = time.time()
    enhanced_logger.logger.info("🔄 NODE_ENTRY | direct_answer | 开始直接回答处理")
    
    configurable = Configuration.from_runnable_config(config)
    query = state.get("research_topic") or (
        state["messages"][-1].content if state.get("messages") else ""
    )
    
    enhanced_logger.logger.info(f"❓ DIRECT_ANSWER_QUERY | '{query}'")
    
    try:
        # 使用 Prompt 模板（不调用检索工具）
        try:
            messages_for_llm = apply_prompt_template(
                "direct_answer",
                state,
                configurable
            )
        except Exception as e:
            logger.warning(f"应用Prompt模板失败，使用备用方案: {e}")
            # 备用方案：简单提示词
            messages_for_llm = [
                {"role": "user", "content": f"请简洁准确地回答以下问题（不超过300字）: {query}"}
            ]
        
        # 生成回答
        llm_start = time.time()
        llm = get_llm_by_type("basic")
        
        # DEBUG级别：打印LLM输入
        if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
            prompt_str = str(messages_for_llm)
            enhanced_logger.logger.debug(
                f"🤖 LLM_INPUT | direct_answer | Prompt长度: {len(prompt_str)}\n"
                f"{'='*80}\n{prompt_str}\n{'='*80}"
            )
        
        response = llm.invoke(messages_for_llm)
        answer = response.content if hasattr(response, 'content') else str(response)
        llm_duration = time.time() - llm_start
        
        # INFO级别：打印LLM最终输出
        enhanced_logger.logger.info(
            f"🤖 LLM_OUTPUT | direct_answer | 响应长度: {len(answer)} | LLM耗时: {llm_duration:.2f}s\n"
            f"{'='*80}\n{answer}\n{'='*80}"
        )
        
        # DEBUG级别：打印更详细的输出信息
        if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
            enhanced_logger.logger.debug(
                f"🤖 LLM_OUTPUT_DETAIL | direct_answer | 响应类型: {type(response)} | 完整响应: {response}"
            )
        
        duration = time.time() - start_time
        enhanced_logger.logger.info(
            f"✅ NODE_EXIT | direct_answer | 节点执行完成 | 总耗时: {duration:.2f}s"
        )
        
        # 不添加 messages，让 LangGraph 自动捕获 LLM 的流式响应（避免双重输出）
        return Command(
            update={
                "final_report": answer,
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"直接回答处理失败: {e}")
        enhanced_logger.logger.error(f"❌ DIRECT_ANSWER_ERROR | {str(e)}")
        
        # 失败时返回错误信息
        error_msg = f"抱歉，在处理您的问题时遇到了错误。请尝试重新提问。\n\n错误信息: {str(e)}"
        return Command(
            update={
                "final_report": error_msg,
                "messages": [AIMessage(content=error_msg, name="direct_answer_assistant")]
            },
            goto="__end__"
        )


async def simple_search_node(state: State, config: RunnableConfig) -> Command[Literal["__end__"]]:
    """
    简单检索节点 - 多轮工具调用搜索并回答（主流路径）
    
    适用于银行业务的常规问题，通过智能体多轮调用工具获取答案
    类似 search_agent.py 的实现，但使用 LangGraph 框架
    """
    start_time = time.time()
    enhanced_logger.logger.info("🔄 NODE_ENTRY | simple_search | 开始简单检索处理（多轮工具调用）")
    
    configurable = Configuration.from_runnable_config(config)
    query = state.get("research_topic") or (
        state["messages"][-1].content if state.get("messages") else ""
    )
    
    enhanced_logger.logger.info(f"❓ SIMPLE_SEARCH_QUERY | '{query}'")
    
    try:
        # 配置工具：使用简单检索需要的工具
        tools = [
            get_web_search_tool(
                max_search_results=configurable.max_search_results,  # 使用用户配置的检索结果数量
                engine=configurable.search_engine,
                repository_id=configurable.custom_search_repository
            ),
            crawl_tool,  # 添加网页爬取工具
            domain_fin_search,  # 添加金融领域知识搜索工具（默认场景）
        ]
        
        enhanced_logger.logger.info(
            f"🔧 TOOLS_READY | 简单检索工具配置完成 | "
            f"工具数: {len(tools)} | 包含: web_search, crawl_tool, domain_fin_search"
        )
        
        # 创建简单检索智能体（使用 create_agent）
        agent_start = time.time()
        agent = create_agent(
            agent_name="simple_search_assistant",
            agent_type="researcher",  # 使用 researcher 类型的 LLM 配置
            tools=tools,
            prompt_template="simple_search",
            configurable=configurable
        )
        agent_create_duration = time.time() - agent_start
        enhanced_logger.logger.info(f"🤖 AGENT_CREATED | 耗时: {agent_create_duration:.2f}s")
        
        # 准备智能体输入
        agent_input = {
            "messages": [
                HumanMessage(
                    content=f"请回答以下问题（不超过300字）:\n\n{query}"
                )
            ]
        }
        
        # 调用智能体（多轮工具调用）
        # 设置递归限制（控制最大工具调用次数）
        # 优先使用环境变量 AGENT_RECURSION_LIMIT，否则使用默认值 25
        default_recursion_limit = 25
        try:
            env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit))
            parsed_limit = int(env_value_str)

            if parsed_limit > 0:
                max_llm_calls = parsed_limit
                enhanced_logger.logger.info(f"📊 RECURSION_LIMIT | 从环境变量读取: {max_llm_calls}")
            else:
                logger.warning(
                    f"AGENT_RECURSION_LIMIT 值 '{env_value_str}' (解析为 {parsed_limit}) 不是正数。"
                    f"使用默认值 {default_recursion_limit}。"
                )
                max_llm_calls = default_recursion_limit
        except ValueError:
            raw_env_value = os.getenv("AGENT_RECURSION_LIMIT")
            logger.warning(
                f"无效的 AGENT_RECURSION_LIMIT 值：'{raw_env_value}'。"
                f"使用默认值 {default_recursion_limit}。"
            )
            max_llm_calls = default_recursion_limit
            
        enhanced_logger.logger.info(f"⏳ AGENT_INVOKING | 正在调用智能体... | 最大调用次数: {max_llm_calls}")
        
        agent_exec_start = time.time()
        result = await agent.invoke(
            input=agent_input,
            config={"recursion_limit": max_llm_calls}
        )
        agent_exec_duration = time.time() - agent_exec_start
        enhanced_logger.logger.info(f"✅ AGENT_INVOKED | LLM调用完成 | 耗时: {agent_exec_duration:.2f}s")
        
        # 提取最终回答
        if isinstance(result, dict) and "messages" in result:
            last_message = result["messages"][-1]
            answer = last_message.content if hasattr(last_message, 'content') else str(last_message)
        else:
            answer = str(result)
        
        # 记录工具调用统计
        tool_calls_count = 0
        if isinstance(result, dict) and "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tool_calls_count += len(msg.tool_calls)
        
        enhanced_logger.logger.info(
            f"📊 TOOL_CALLS_SUMMARY | 工具调用总次数: {tool_calls_count}"
        )
        
        duration = time.time() - start_time
        enhanced_logger.logger.info(
            f"✅ NODE_EXIT | simple_search | 节点执行完成 | 总耗时: {duration:.2f}s"
        )
        
        # 不添加 messages，让 LangGraph 自动捕获 LLM 的流式响应（避免双重输出）
        return Command(
            update={
                "final_report": answer,
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"简单检索处理失败: {e}")
        enhanced_logger.logger.error(f"❌ SIMPLE_SEARCH_ERROR | {str(e)}")
        import traceback
        enhanced_logger.logger.error(f"❌ TRACEBACK | {traceback.format_exc()}")
        
        # 失败时返回错误信息
        error_msg = f"抱歉，在处理您的问题时遇到了错误。请尝试重新提问或使用深度研究模式。\n\n错误信息: {str(e)}"
        return Command(
            update={
                "final_report": error_msg,
                "messages": [AIMessage(content=error_msg, name="simple_search_assistant")]
            },
            goto="__end__"
        )


@observe(name="🔄 迭代研究节点", as_type="agent")
def iterative_research_node(state: State, config: RunnableConfig) -> Command[Literal["__end__", "iterative_research_node"]]:
    """
    迭代深度研究节点 - 针对单个问题进行多轮自主深入研究
    
    工作流程：
    1. 组织检索词
    2. 执行检索（web_search + crawl_tool）
    3. 分析信息并回答
    4. 判断是否足够回答用户问题
    5. 如果不足，针对未解决问题继续下一轮迭代（最多5轮）
    
    注意: @observe 装饰器会自动捕获输入参数和返回值，无需手动记录
    """
    start_time = time.time()
    iteration_count = state.get("iteration_count", 0)
    enhanced_logger.logger.info(
        f"🔄 NODE_ENTRY | iterative_research | 开始迭代研究 | 第{iteration_count + 1}轮"
    )
    
    configurable = Configuration.from_runnable_config(config)
    query = state.get("research_topic") or (
        state["messages"][-1].content if state.get("messages") else ""
    )
    iteration_history = state.get("iteration_history", [])
    
    enhanced_logger.logger.info(
        f"❓ ITERATIVE_RESEARCH_QUERY | '{query}' | 历史轮次: {len(iteration_history)}"
    )
    
    # 从配置中获取最大迭代次数（优先级：环境变量 > API请求 > 默认5）
    MAX_ITERATIONS = configurable.max_iteration
    enhanced_logger.logger.info(
        f"🔢 ITERATION_CONFIG | 最大迭代次数: {MAX_ITERATIONS} | 当前轮次: {iteration_count + 1}"
    )
    
    # 确保 iteration_history 是列表类型
    if not isinstance(iteration_history, list):
        iteration_history = []
        enhanced_logger.logger.warning(
            "⚠️ ITERATION_HISTORY_TYPE_ERROR | iteration_history 不是列表类型，已重置为空列表"
        )    
    try:
        # 创建带有工具的 Agent
        tools = [
            get_web_search_tool(
                max_search_results=configurable.max_search_results,  # 使用用户配置的检索结果数量
                engine=configurable.search_engine,
                repository_id=configurable.custom_search_repository
            ),
            industry_report_search,  # 网页爬取工具
            news_search,
            crawl_tool,
            news_detail_search
        ]
        
        # 准备模板变量
        state_with_history = dict(state)
        state_with_history['iteration_history'] = "\n\n".join([
            f"### 第{i+1}轮研究\n{h.get('summary', '')}"
            for i, h in enumerate(iteration_history)
        ]) if iteration_history else None
        
        # 使用 Prompt 模板
        try:
            # messages_for_llm = apply_prompt_template(
            #     "iterative_research",
            #     state_with_history,
            #     configurable
            # )
            messages_for_llm = []
            
            # 添加用户查询（必须放在最前面）
            messages_for_llm.append(
                HumanMessage(
                    content=f"请对以下问题进行深入研究:\n\n{query}",
                    name="user_query"
                )
            )
            
            # 如果有历史记录，添加历史信息
            if state_with_history.get('iteration_history'):
                messages_for_llm.append(
                    HumanMessage(
                        content=f"## 迭代研究历史记录\n\n{state_with_history['iteration_history']}",
                        name="iteration_history"
                    )
                )
        except Exception as e:
            logger.warning(f"应用Prompt模板失败，使用备用方案: {e}")
            # 备用方案：简单提示词
            history_text = state_with_history.get('iteration_history', '')
            messages_for_llm = [
                {"role": "user", "content": f"""你是一个迭代研究助手。请针对以下问题进行深入研究：

问题：{query}

{("历史研究：" + str(history_text)) if history_text else "这是第1轮研究"}

请使用可用工具（web_search, crawl_tool）进行研究，并评估是否需要继续迭代。"""}
            ]
        
        # 创建带工具的 Agent
        llm = get_llm_by_type("basic")  # 使用基础模型

        prompt_str = str(messages_for_llm)
        # enhanced_logger.logger.info(
        #         f"🤖 LLM_INPUT | iterative_research | Prompt长度: {len(prompt_str)}\n"
        #         f"{'='*80}\n{prompt_str}\n{'='*80}"
        #     )
        
        # DEBUG级别：打印LLM输入
        if enhanced_logger.logger.isEnabledFor(logging.DEBUG):
            prompt_str = str(messages_for_llm)
            enhanced_logger.logger.debug(
                f"🤖 LLM_INPUT | iterative_research | Prompt长度: {len(prompt_str)}\n"
                f"{'='*80}\n{prompt_str}\n{'='*80}"
            )
        
        # 创建带工具的 Agent
        agent_start = time.time()
        agent = create_agent(
            agent_name="iterative_researcher",
            agent_type="researcher",
            tools=tools,
            prompt_template="iterative_research",
            configurable=configurable
        )
        agent_duration = time.time() - agent_start
        
        enhanced_logger.logger.info(
            f"🤖 AGENT_CREATED | 工具数: {len(tools)} | 耗时: {agent_duration:.2f}s"
        )
        
        # 执行 Agent
        # 捕获递归限制异常，当达到限制时自动进入报告生成阶段
        invoke_start = time.time()
        should_continue = False  # 默认不继续迭代
        
        try:
            result = agent.invoke({
                "messages": messages_for_llm
            })
            invoke_duration = time.time() - invoke_start
            
            # 提取输出
            answer = ""
            if isinstance(result, dict) and "messages" in result:
                last_message = result["messages"][-1]
                answer = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                answer = str(result)
            
            # INFO级别：打印LLM最终输出
            enhanced_logger.logger.info(
                f"🤖 LLM_OUTPUT | iterative_research | 响应长度: {len(answer)} | LLM耗时: {invoke_duration:.2f}s\n"
                f"{'='*80}\n{answer}\n{'='*80}"
            )
            
            # 判断是否需要继续迭代（简单启发式判断）
            if iteration_count + 1 < MAX_ITERATIONS:
                # 检查回答中是否有表示需要继续的信号
                continue_signals = [
                    "**是否需要继续研究**：是",
                    "**是否需要继续研究**: 是"
                ]
                answer_lower = str(answer).lower()
                should_continue = any(signal.lower() in answer_lower for signal in continue_signals)
                enhanced_logger.logger.info(f"------------------------ should_continue: {should_continue}")
                
        except RecursionError as re:
            # 达到递归限制，记录日志并强制进入报告生成阶段
            enhanced_logger.logger.warning(
                f"⚠️ RECURSION_LIMIT_REACHED | iterative_research | "
                f"第{iteration_count + 1}轮达到递归限制（工具调用次数超过25次），强制进入报告生成阶段"
            )
            logger.warning(f"迭代研究达到递归限制: {str(re)}")
            
            invoke_duration = time.time() - invoke_start
            
            # 创建一个简单的结果，说明情况
            answer = f"第{iteration_count + 1}轮研究因达到工具调用次数限制（25次）而结束。已收集的信息将用于生成最终报告。"
            enhanced_logger.logger.info(
                f"🤖 LLM_OUTPUT | iterative_research | 因递归限制终止 | LLM耗时: {invoke_duration:.2f}s\n"
                f"{'='*80}\n{answer}\n{'='*80}"
            )
            
            # 强制设置不继续迭代
            should_continue = False
        
        # 更新迭代历史
        new_iteration = {
            "round": iteration_count + 1,
            # "summary": answer[:500] + "..." if len(answer) > 500 else answer,
            "summary": answer,
            "timestamp": time.time()
        }
        # 确保 updated_history 是基于列表的更新，而不是覆盖
        updated_history = list(iteration_history) + [new_iteration]
            
        
        duration = time.time() - start_time
        
        if should_continue:
            enhanced_logger.logger.info(
                f"🔄 ITERATION_CONTINUE | 第{iteration_count + 1}轮完成，继续下一轮 | 耗时: {duration:.2f}s"
            )
            # 继续下一轮迭代
            # iteration_count + 2 表示即将进入的下一轮（例如：第1轮完成后，跳转到第2轮）
            next_iteration = iteration_count + 2
            logger.info(f"[轮次跳转] 第{iteration_count + 1}轮完成 → 即将跳转到第{next_iteration}轮")
            node_transition_data = {
                "from": "iterative_research_node",
                "to": "iterative_research_node",
                "iteration": next_iteration,
                "reason": "continue",
            }
            logger.info(f"[节点跳转] 即将返回 Command，node_transition: {node_transition_data}")
            
            # 创建一条特殊消息用于传递节点跳转信息（通过 additional_kwargs）
            transition_message = AIMessage(
                content="",  # 空内容，不显示给用户
                name="node_transition_event",
                additional_kwargs={
                    "node_transition": node_transition_data
                }
            )
            
            return Command(
                update={
                    "iteration_count": iteration_count + 1,
                    "iteration_history": updated_history,
                    "messages": [transition_message],  # 只包含跳转事件消息
                    "research_topic": query,  # 保持研究主题的一致性
                },
                goto="iterative_research_node"  # 递归调用自己
            )
        else:
            enhanced_logger.logger.info(
                f"✅ NODE_EXIT | iterative_research | 研究完成 | 总轮次: {iteration_count + 1} | 总耗时: {duration:.2f}s"
            )
            # 研究完成，进入报告生成阶段
            final_iteration = iteration_count + 2
            logger.info(f"[研究完成] 第{final_iteration - 1}轮完成 → 即将生成最终报告")
            node_transition_data = {
                "from": "iterative_research_node",
                "to": "iterative_reporter_node",
                "iteration": final_iteration,
                "reason": "finish",
            }
            logger.info(f"[节点跳转] 即将返回 Command，node_transition: {node_transition_data}")
            
            # 创建一条特殊消息用于传递节点跳转信息（通过 additional_kwargs）
            transition_message = AIMessage(
                content="",  # 空内容，不显示给用户
                name="node_transition_event",
                additional_kwargs={
                    "node_transition": node_transition_data
                }
            )
            
            return Command(
                update={
                    "iteration_count": iteration_count + 1,
                    "iteration_history": updated_history,
                    "messages": [transition_message],  # 只包含跳转事件消息
                    "research_topic": query,  # 保持研究主题的一致性
                },
                goto="iterative_reporter_node"
            )
        
    except Exception as e:
        logger.error(f"迭代研究处理失败: {e}")
        enhanced_logger.logger.error(f"❌ ITERATIVE_RESEARCH_ERROR | {str(e)}")
        
        # 失败时返回错误信息
        error_msg = f"抱歉，在迭代研究过程中遇到了错误。\n\n错误信息: {str(e)}"
        return Command(
            update={
                "final_report": error_msg,
                "messages": [AIMessage(content=error_msg, name="iterative_research_error", agent="iterative_research_node")]
            },
            goto="__end__"
        )


@observe(name="📝 迭代研究报告节点", as_type="agent")
def iterative_reporter_node(state: State, config: RunnableConfig) -> Command[Literal["__end__"]]:
    """
    迭代研究报告员节点 - 专门用于生成迭代研究的最终报告
    
    工作流程：
    1. 收集所有迭代研究的历史记录
    2. 整合所有研究内容
    3. 生成最终报告
    
    注意: @observe 装饰器会自动捕获输入参数和返回值，无需手动记录
    """
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | iterative_reporter | 开始执行迭代研究报告生成节点")
    
    configurable = Configuration.from_runnable_config(config)
    
    # 获取迭代研究历史记录
    iteration_history = state.get("iteration_history", [])
    research_topic = state.get("research_topic", "")
    
    enhanced_logger.logger.info(
        f"📊 ITERATIVE_REPORT_INIT | 开始生成迭代研究报告 | 研究主题: {research_topic} | 迭代轮次: {len(iteration_history)}"
    )
    
    try:
        # 准备输入数据
        input_ = {
            "messages": [
                HumanMessage(
                    content=f"# 迭代研究最终报告生成\n\n## 研究主题\n\n{research_topic}"
                )
            ],
            "locale": state.get("locale", "zh-CN"),  # 默认使用中文
            "iteration_history": iteration_history,
            "research_topic": research_topic
        }
        
        # 应用提示词模板
        invoke_messages = apply_prompt_template("iterative_reporter", input_, configurable)
        
        # 添加迭代历史记录
        if iteration_history:
            history_content = "\n\n".join([
                f"### 第{i+1}轮研究\n\n{h.get('summary', '')}"
                for i, h in enumerate(iteration_history)
            ])
            
            invoke_messages.append(
                HumanMessage(
                    content=f"## 迭代研究历史记录\n\n{history_content}",
                    name="iteration_history"
                )
            )
        
        # 添加报告格式指导
        invoke_messages.append(
            HumanMessage(
                content=f"重要提示：请按照以下结构组织您的报告：\n\n"
                       f"1. 研究概要 - 对整个研究过程的总结\n"
                       f"2. 详细分析 - 按研究轮次组织的详细内容\n"
                       f"3. 结论 - 最终结论和发现\n"
                       f"4. 局限性 - 研究的局限性和未来改进方向\n\n"
                       f"**请用{state.get('locale', 'zh-CN')}语言编写报告。**",
                name="system"
            )
        )
        
        logger.debug(f"Current invoke messages: {invoke_messages}")
        
        # 记录 reporter 的输入内容
        logger.info(f"Iterative reporter input: {invoke_messages}")
        enhanced_logger.logger.info(
            f"📝 ITERATIVE_REPORTER_INPUT | 输入消息数: {len(invoke_messages)} | 迭代轮次: {len(iteration_history)} | 研究主题: {research_topic}"
        )
        
        # 记录LLM调用过程
        llm_start_time = time.time()
        enhanced_logger.logger.info(
            f"🤖 LLM_INVOKE | iterative_reporter | 开始生成最终报告 | 提示消息数: {len(invoke_messages)}"
        )
        
        response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(invoke_messages)
        response_content = response.content
        
        llm_duration = time.time() - llm_start_time
        report_length = len(response_content) if response_content else 0
        enhanced_logger.logger.info(
            f"✅ LLM_COMPLETE | iterative_reporter | 报告生成完成 | 报告长度: {report_length} | LLM耗时: {llm_duration:.2f}s"
        )
        
        logger.info(f"iterative reporter response: {response_content}")
        
        duration = time.time() - start_time
        enhanced_logger.logger.info(
            f"✅ NODE_EXIT | iterative_reporter | 节点执行完成 | 总耗时: {duration:.2f}s"
        )
        
        # 返回最终报告
        # 注意：不添加 messages，让 LangGraph 自动捕获 LLM 的流式响应（避免双重输出）
        # 如果在 update 中添加消息，前端会收到两份报告：一份来自 LLM 的自动流式输出，一份来自这里的消息
        return Command(
            update={
                "final_report": response_content
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"迭代研究报告生成失败: {e}")
        enhanced_logger.logger.error(f"❌ ITERATIVE_REPORTER_ERROR | {str(e)}")
        
        # 失败时返回错误信息
        error_msg = f"抱歉，在生成迭代研究报告的过程中遇到了错误。\n\n错误信息: {str(e)}"
        # 只有在失败时才添加消息，成功时让 LangGraph 自动捕获
        return Command(
            update={
                "final_report": error_msg,
                "messages": [AIMessage(content=error_msg, name="iterative_reporter_error", agent="iterative_reporter_node")]
            },
            goto="__end__"
        )


def background_investigation_node(state: State, config: RunnableConfig):
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | background_investigation | 开始执行背景调研节点")
    
    configurable = Configuration.from_runnable_config(config)
    query = state.get("research_topic")
    
    enhanced_logger.log_search_process(query, "background_investigation")
    
    background_investigation_results = None
    if SELECTED_SEARCH_ENGINE == SearchEngine.TAVILY.value:
        enhanced_logger.logger.info(f"🔍 使用Tavily搜索引擎进行背景调研 | 查询: '{query}'")
        searched_content = LoggedTavilySearch(
            max_results=configurable.max_search_results
        ).invoke(query)
        # check if the searched_content is a tuple, then we need to unpack it
        if isinstance(searched_content, tuple):
            searched_content = searched_content[0]
        if isinstance(searched_content, list):
            enhanced_logger.logger.info(f"🔍 Tavily搜索完成 | 结果数: {len(searched_content)}")
            background_investigation_results = [
                f"## {elem['title']}\n\n{elem['content']}" for elem in searched_content
            ]
            result = {
                "background_investigation_results": "\n\n".join(
                    background_investigation_results
                )
            }
        else:
            logger.error(
                f"Tavily search returned malformed response: {searched_content}"
            )
            result = {"background_investigation_results": None}
    else:
        enhanced_logger.logger.info(f"🔍 使用online_search进行背景调研 | 查询: '{query}'")
        background_investigation_results = online_search_tool(
            max_results=configurable.max_search_results
        ).invoke(query)
        result = {
            "background_investigation_results": json.dumps(
                background_investigation_results, ensure_ascii=False
            )
        }
        
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | background_investigation | 节点执行完成 | 耗时: {duration:.2f}s")
    return result


@observe(name="📋 规划节点", as_type="agent")
def planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["human_feedback", "reporter"]]:
    """生成完整计划的规划节点"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | planner | 开始执行计划生成节点")
    
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    enhanced_logger.log_plan_generation(plan_iterations + 1, state.get("research_topic", "未知"), 0)
    
    messages = []
    try:
        messages = apply_prompt_template("planner", state, configurable)
    except Exception as e:
        enhanced_logger.logger.error(f"Failed to apply prompt template: {e}")
        # 使用默认消息
        messages = [HumanMessage(content=f"为以下主题制定计划：{state.get('research_topic', '未知主题')}")]

    if state.get("enable_background_investigation") and state.get(
        "background_investigation_results"
    ):
        messages += [
            {
                "role": "user",
                "content": (
                    "用户查询的背景调研结果：\n"
                    + state["background_investigation_results"]
                    + "\n"
                ),
            }
        ]

    if configurable.enable_deep_thinking:
        llm = get_llm_by_type("reasoning")
    elif AGENT_LLM_MAP["planner"] == "basic":
        # 不使用structured_output，避免在LLM层直接验证，而是在后处理中修复字段后再验证
        llm = get_llm_by_type("basic")
        enhanced_logger.logger.info("🔧 PLANNER_CONFIG | 使用basic LLM不带structured_output，启用字段修复机制")
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"])

    # 记录 planner 的输入内容
    logger.info(f"Planner input: {messages}")
    enhanced_logger.logger.info(f"📝 PLANNER_INPUT | 输入消息数: {len(messages)} | 背景调研: {'是' if state.get('enable_background_investigation') and state.get('background_investigation_results') else '否'}")

    # if the plan iterations is greater than the max plan iterations, return the reporter node
    if plan_iterations >= configurable.max_plan_iterations:
        enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → reporter | 原因: 超过最大计划迭代次数")
        return Command(goto="reporter")

    full_response = ""
    llm_start_time = time.time()
    if AGENT_LLM_MAP["planner"] == "basic" and not configurable.enable_deep_thinking:
        response = llm.invoke(messages)
        try:
            # 不再使用structured_output，所以直接获取content
            if hasattr(response, 'content'):
                full_response = str(response.content)
            else:
                full_response = str(response)
        except Exception:
            full_response = "Response conversion failed"
    else:
        response = llm.stream(messages)
        for chunk in response:
            try:
                if hasattr(chunk, 'content'):
                    content = getattr(chunk, 'content', '')
                    if content:
                        full_response += str(content)
            except Exception:
                pass
    
    thinking_duration = time.time() - llm_start_time
    logger.debug(f"Current state messages: {state['messages']}")
    enhanced_logger.log_llm_thinking("planner", len(str(messages)), len(full_response), thinking_duration)
    logger.info(f"Planner response: {full_response}")

    try:
        curr_plan = json.loads(repair_json_output(full_response))
        
        # 检查是否为嵌套的 {"plan": {...}} 格式
        if isinstance(curr_plan, dict) and 'plan' in curr_plan and isinstance(curr_plan['plan'], dict):
            enhanced_logger.logger.warning("⚠️ PLAN_FORMAT_ERROR | 检测到嵌套plan格式，提取内层对象")
            curr_plan = curr_plan['plan']  # 提取内层的plan对象
        
        # 立即检查并修复locale字段缺失问题
        if isinstance(curr_plan, dict) and 'locale' not in curr_plan:
            curr_plan['locale'] = state.get('locale', 'zh-CN')  # 使用状态中的locale或默认值
            enhanced_logger.logger.warning(f"⚠️ PLAN_MISSING_LOCALE | 添加缺失的locale字段: {curr_plan['locale']}")
            
        # 检查并修复title字段缺失问题
        if isinstance(curr_plan, dict) and 'title' not in curr_plan:
            curr_plan['title'] = '智能研究计划'  # 默认标题
            enhanced_logger.logger.warning(f"⚠️ PLAN_MISSING_TITLE | 添加缺失的title字段: {curr_plan['title']}")
        
        # 检查并修复steps中的step_type字段缺失问题
        if isinstance(curr_plan, dict) and 'steps' in curr_plan and isinstance(curr_plan['steps'], list):
            for i, step in enumerate(curr_plan['steps']):
                if isinstance(step, dict) and 'step_type' not in step:
                    step['step_type'] = 'research'  # 默认步骤类型
                    enhanced_logger.logger.warning(f"⚠️ STEP_MISSING_TYPE | 为步骤#{i+1}添加缺失的step_type字段: {step['step_type']}")
            
    except json.JSONDecodeError as e:
        logger.warning(f"Planner response is not a valid JSON: {str(e)}")
        enhanced_logger.logger.error(f"❌ JSON_DECODE_ERROR | JSON解析失败 | 错误: {str(e)}")
        enhanced_logger.logger.error(f"📄 INVALID_JSON_CONTENT | 无效的JSON内容 (前500字符): {full_response[:500]}")
        enhanced_logger.logger.debug(f"📄 FULL_RESPONSE | 完整响应内容: {full_response}")
        if plan_iterations > 0:
            enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → reporter | 原因: JSON解析失败，重定向到reporter")
            return Command(goto="reporter")
        else:
            enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → __end__ | 原因: JSON解析失败，终止工作流")
            return Command(goto="reporter")  # 改为reporter避免类型错误
    if isinstance(curr_plan, dict) and curr_plan.get("has_enough_context"):
        logger.info("Planner response has enough context.")
        
        # 确保locale字段存在，如果不存在则从状态中获取
        if 'locale' not in curr_plan:
            curr_plan['locale'] = state.get('locale', 'zh-CN')  # 使用状态中的locale或默认值
            enhanced_logger.logger.warning(f"⚠️ PLAN_MISSING_LOCALE | 添加缺失的locale字段: {curr_plan['locale']}")
        
        # 验证其他必需字段
        required_fields = ['has_enough_context', 'thought', 'title', 'steps']
        missing_fields = [field for field in required_fields if field not in curr_plan]
        if missing_fields:
            enhanced_logger.logger.error(f"❌ PLAN_MISSING_FIELDS | Plan缺少必需字段: {missing_fields}")
            logger.error(f"Plan missing required fields: {missing_fields}")
            if plan_iterations > 0:
                return Command(goto="reporter")
            else:
                return Command(goto="reporter")
        
        try:
            new_plan = Plan.model_validate(curr_plan)
            enhanced_logger.log_plan_generation(plan_iterations + 1, new_plan.title, len(new_plan.steps))
            
            # 检查是否有需要执行的步骤
            has_unexecuted_steps = any(step.execution_res is None for step in new_plan.steps)
            
            if has_unexecuted_steps:
                enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → human_feedback | 原因: 计划包含未执行的步骤，需要研究")
                duration = time.time() - start_time
                enhanced_logger.logger.info(f"✅ NODE_EXIT | planner | 节点执行完成 | 耗时: {duration:.2f}s")
                
                return Command(
                    update={
                        "current_plan": new_plan,
                        # 不添加 messages，让 LangGraph 自动捕获流式响应（避免双重输出）
                    },
                    goto="human_feedback",
                )
            else:
                enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → reporter | 原因: 所有步骤已执行完成")
                duration = time.time() - start_time
                enhanced_logger.logger.info(f"✅ NODE_EXIT | planner | 节点执行完成 | 耗时: {duration:.2f}s")
                
                return Command(
                    update={
                        "current_plan": new_plan,
                        # 不添加 messages，让 LangGraph 自动捕获流式响应（避免双重输出）
                    },
                    goto="reporter",
                )
        except Exception as e:
            enhanced_logger.logger.error(f"❌ PLAN_VALIDATION_ERROR | Plan验证失败: {str(e)}")
            logger.error(f"Plan validation failed: {e}")
            logger.debug(f"Failed plan data: {curr_plan}")
            if plan_iterations > 0:
                return Command(goto="reporter")
            else:
                return Command(goto="reporter")
    
    enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → human_feedback | 原因: 需要人工审核计划")
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | planner | 节点执行完成 | 耗时: {duration:.2f}s")
    
    return Command(
        update={
            "current_plan": full_response,
            # 不添加 messages，让 LangGraph 自动捕获流式响应（避免双重输出）
        },
        goto="human_feedback",
    )


def human_feedback_node(
    state,
) -> Command[Literal["planner", "research_team", "reporter", "__end__"]]:
    current_plan = state.get("current_plan", "")
    # check if the plan is auto accepted
    auto_accepted_plan = state.get("auto_accepted_plan", False)
    if not auto_accepted_plan:
        feedback = interrupt("Please Review the Plan.")

        # if the feedback is not accepted, return the planner node
        if feedback and str(feedback).upper().startswith("[EDIT_PLAN]"):
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=feedback, name="feedback"),
                    ],
                },
                goto="planner",
            )
        elif feedback and str(feedback).upper().startswith("[ACCEPTED]"):
            logger.info("Plan is accepted by user.")
        else:
            raise TypeError(f"Interrupt value of {feedback} is not supported.")

    # if the plan is accepted, run the following node
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    goto = "research_team"
    
    try:
        # 检查current_plan的类型，如果已经是Plan对象则直接使用
        if hasattr(current_plan, 'title') and hasattr(current_plan, 'steps'):
            # current_plan已经是Plan对象
            enhanced_logger.logger.info("📋 PLAN_OBJECT_DETECTED | 检测到Plan对象，直接验证")
            validated_plan = current_plan
            plan_iterations += 1
            
            # 检查是否有需要执行的步骤
            has_unexecuted_steps = any(step.execution_res is None for step in validated_plan.steps)
            if not has_unexecuted_steps:
                enhanced_logger.logger.info("✅ ALL_STEPS_COMPLETED | 所有步骤已完成，跳转到reporter")
                goto = "reporter"
            
            return Command(
                update={
                    "current_plan": validated_plan,
                    "plan_iterations": plan_iterations,
                    "locale": validated_plan.locale,
                },
                goto=goto,
            )
        
        # current_plan是字符串，需要解析
        current_plan = repair_json_output(current_plan)
        # increment the plan iterations
        plan_iterations += 1
        # parse the plan
        new_plan = json.loads(current_plan)
        
        # 检查是否为嵌套的 {"plan": {...}} 格式
        if isinstance(new_plan, dict) and 'plan' in new_plan and isinstance(new_plan['plan'], dict):
            enhanced_logger.logger.warning("⚠️ PLAN_FORMAT_ERROR | 在human_feedback中检测到嵌套plan格式，提取内层对象")
            new_plan = new_plan['plan']  # 提取内层的plan对象
        
        # 立即检查并修复locale字段缺失问题
        if isinstance(new_plan, dict) and 'locale' not in new_plan:
            new_plan['locale'] = state.get('locale', 'zh-CN')  # 使用状态中的locale或默认值
            enhanced_logger.logger.warning(f"⚠️ PLAN_MISSING_LOCALE | 在human_feedback中添加缺失的locale字段: {new_plan['locale']}")
        
        # 检查并修复title字段缺失问题
        if isinstance(new_plan, dict) and 'title' not in new_plan:
            new_plan['title'] = '智能研究计划'  # 默认标题
            enhanced_logger.logger.warning(f"⚠️ PLAN_MISSING_TITLE | 在human_feedback中添加缺失的title字段: {new_plan['title']}")
        
        # 检查并修复steps中的step_type字段缺失问题
        if isinstance(new_plan, dict) and 'steps' in new_plan and isinstance(new_plan['steps'], list):
            for i, step in enumerate(new_plan['steps']):
                if isinstance(step, dict) and 'step_type' not in step:
                    step['step_type'] = 'research'  # 默认步骤类型
                    enhanced_logger.logger.warning(f"⚠️ STEP_MISSING_TYPE | 在human_feedback中为步骤#{i+1}添加缺失的step_type字段: {step['step_type']}")
        
        # 添加格式检测和错误处理机制
        # 检查是否为工具调用格式
        if isinstance(new_plan, dict) and 'name' in new_plan and 'arguments' in new_plan:
            enhanced_logger.logger.warning(f"⚠️ PLAN_FORMAT_ERROR | 检测到工具调用格式而非Plan对象 | 工具名: {new_plan.get('name')}")
            logger.warning("Planner returned tool call format instead of Plan object")
            return Command(goto="planner")  # 重新生成计划
            
        # 检查是否为Step列表而非完整Plan
        if isinstance(new_plan, list):
            enhanced_logger.logger.warning("⚠️ PLAN_FORMAT_ERROR | 检测到Step列表而非完整Plan对象")
            logger.warning("Planner returned Step list instead of complete Plan object")
            return Command(goto="planner")  # 重新生成计划
            
        # 验证Plan对象必需字段
        required_fields = ['locale', 'has_enough_context', 'thought', 'title', 'steps']
        missing_fields = [field for field in required_fields if field not in new_plan]
        if missing_fields:
            enhanced_logger.logger.warning(f"⚠️ PLAN_FORMAT_ERROR | Plan对象缺少必需字段: {missing_fields}")
            logger.warning(f"Plan missing required fields: {missing_fields}")
            return Command(goto="planner")  # 重新生成计划
            
    except json.JSONDecodeError as e:
        logger.warning(f"Planner response is not a valid JSON in human_feedback: {str(e)}")
        enhanced_logger.logger.error(f"❌ JSON_DECODE_ERROR | human_feedback节点JSON解析失败 | 错误: {str(e)}")
        enhanced_logger.logger.error(f"📄 INVALID_JSON_CONTENT | 无效的JSON内容 (前500字符): {str(current_plan)[:500]}")
        enhanced_logger.logger.debug(f"📄 FULL_CURRENT_PLAN | 完整current_plan内容: {current_plan}")
        if plan_iterations > 1:  # the plan_iterations is increased before this check
            return Command(goto="reporter")
        else:
            return Command(goto="__end__")
    except Exception as e:
        enhanced_logger.logger.error(f"❌ PLAN_PARSE_ERROR | Plan解析失败: {str(e)}")
        logger.error(f"Error parsing plan: {e}")
        return Command(goto="planner")  # 重新生成计划

    try:
        # 尝试验证Plan对象
        validated_plan = Plan.model_validate(new_plan)
        enhanced_logger.logger.info(f"✅ PLAN_VALIDATED | Plan对象验证成功 | 标题: {validated_plan.title} | 步骤数: {len(validated_plan.steps)}")
        
        return Command(
            update={
                "current_plan": validated_plan,
                "plan_iterations": plan_iterations,
                "locale": new_plan["locale"],
            },
            goto=goto,
        )
    except Exception as e:
        enhanced_logger.logger.error(f"❌ PLAN_VALIDATION_ERROR | Plan验证失败: {str(e)}")
        logger.error(f"Plan validation failed: {e}")
        # 记录详细的验证错误信息
        logger.debug(f"Failed plan data: {new_plan}")
        return Command(goto="planner")  # 重新生成计划


@observe(name="🎯 协调节点", as_type="agent")
def coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "background_investigator", "__end__"]]:
    """与客户沟通的协调节点"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | coordinator | 开始执行协调节点")
    
    logger.info("Coordinator talking.")
    configurable = Configuration.from_runnable_config(config)
    
    # 打印状态信息
    enhanced_logger.logger.info(f"📊 COORDINATOR_STATE | research_topic: {state.get('research_topic', 'Not set')}")
    enhanced_logger.logger.info(f"📊 COORDINATOR_STATE | locale: {state.get('locale', 'Not set')}")
    enhanced_logger.logger.info(f"📊 COORDINATOR_STATE | messages数量: {len(state.get('messages', []))}")
    
    try:
        messages = apply_prompt_template("coordinator", state, configurable)
        enhanced_logger.logger.info(f"📝 COORDINATOR_PROMPT | 提示模板应用成功 | 消息数: {len(messages)}")
    except Exception as e:
        enhanced_logger.logger.error(f"Failed to apply coordinator template: {e}")
        # 使用默认消息
        messages = [HumanMessage(content=f"协调请求：{state.get('research_topic', '未知请求')}")]
    
    # 打印发送给LLM的消息
    enhanced_logger.logger.info(f"🤖 COORDINATOR_LLM_INPUT | 准备调用LLM | 输入消息数: {len(messages)}")
    for i, msg in enumerate(messages):
        msg_preview = str(msg)[:200] + "..." if len(str(msg)) > 200 else str(msg)
        enhanced_logger.logger.info(f"  消息{i+1}: {msg_preview}")
    
    llm_start_time = time.time()
    response = (
        get_llm_by_type(AGENT_LLM_MAP["coordinator"])
        .bind_tools([handoff_to_planner])
        .invoke(messages)
    )
    llm_duration = time.time() - llm_start_time
    
    # 打印LLM响应的详细信息
    enhanced_logger.logger.info(f"🤖 COORDINATOR_LLM_RESPONSE | LLM调用完成 | 耗时: {llm_duration:.2f}s")
    enhanced_logger.logger.info(f"📤 COORDINATOR_RESPONSE_TYPE | 响应类型: {type(response).__name__}")
    enhanced_logger.logger.info(f"📤 COORDINATOR_RESPONSE_CONTENT | 响应内容: {response.content if hasattr(response, 'content') else 'No content'}")
    
    # 打印响应的所有属性
    response_attrs = dir(response)
    enhanced_logger.logger.info(f"📤 COORDINATOR_RESPONSE_ATTRS | 响应属性: {[attr for attr in response_attrs if not attr.startswith('_')]}")
    
    logger.debug(f"Current state messages: {state['messages']}")

    goto = "__end__"
    locale = state.get("locale", "zh-CN")  # 默认语言区域（如果未指定）
    research_topic = state.get("research_topic", "")

    # 处理response的tool_calls属性问题
    try:
        tool_calls = getattr(response, 'tool_calls', [])
        enhanced_logger.logger.info(f"🔧 COORDINATOR_TOOL_CALLS | 工具调用数量: {len(tool_calls)}")
        
        # 打印每个tool_call的详细信息
        for i, tool_call in enumerate(tool_calls):
            enhanced_logger.logger.info(f"🔧 TOOL_CALL_{i+1} | 完整内容: {tool_call}")
            enhanced_logger.logger.info(f"  - name: {tool_call.get('name', 'N/A')}")
            enhanced_logger.logger.info(f"  - args: {tool_call.get('args', {})}")
        
        if len(tool_calls) > 0:
            goto = "planner"
            if state.get("enable_background_investigation"):
                # if the search_before_planning is True, add the web search tool to the planner agent
                goto = "background_investigator"
                enhanced_logger.logger.info(f"🔀 COORDINATOR_GOTO | 启用背景调研，跳转到: {goto}")
            else:
                enhanced_logger.logger.info(f"🔀 COORDINATOR_GOTO | 直接跳转到: {goto}")
            
            try:
                for tool_call in tool_calls:
                    if tool_call.get("name", "") != "handoff_to_planner":
                        enhanced_logger.logger.warning(f"⚠️ UNEXPECTED_TOOL | 意外的工具调用: {tool_call.get('name', '')}")
                        continue
                    if tool_call.get("args", {}).get("locale") and tool_call.get(
                        "args", {}
                    ).get("research_topic"):
                        locale = tool_call.get("args", {}).get("locale")
                        research_topic = tool_call.get("args", {}).get("research_topic")
                        enhanced_logger.logger.info(f"📝 EXTRACTED_INFO | locale: {locale}, research_topic: {research_topic}")
                        break
            except Exception as e:
                logger.error(f"Error processing tool calls: {e}")
                enhanced_logger.logger.error(f"❌ TOOL_CALL_ERROR | 处理工具调用失败: {str(e)}")
        else:
            logger.warning(
                "Coordinator response contains no tool calls. Terminating workflow execution."
            )
            enhanced_logger.logger.warning(f"⚠️ NO_TOOL_CALLS | Coordinator未返回工具调用，将终止工作流")
            logger.debug(f"Coordinator response: {response}")
            enhanced_logger.logger.info(f"📤 FULL_RESPONSE | {response}")
    except Exception as e:
        logger.error(f"Error accessing tool_calls: {e}")
        enhanced_logger.logger.error(f"❌ TOOL_CALLS_ACCESS_ERROR | 访问tool_calls属性失败: {str(e)}")
    
    # LangGraph会自动捕获LLM的响应并流式输出，无需手动添加到messages
    # 只有当需要保存上下文时才添加到messages
    messages = state.get("messages", [])
    if response.content:
        messages.append(HumanMessage(content=response.content, name="coordinator"))
        enhanced_logger.logger.info(f"📝 ADDED_MESSAGE | 添加coordinator响应到消息列表")
    
    # 打印最终的返回命令
    enhanced_logger.logger.info(f"🎯 COORDINATOR_FINAL_GOTO | 最终跳转目标: {goto}")
    enhanced_logger.logger.info(f"📊 COORDINATOR_FINAL_UPDATE | locale: {locale}, research_topic: {research_topic}")
    
    # 如果有response.content，说明coordinator选择了直接回复（追问等情况）
    if response.content:
        enhanced_logger.logger.info(f"💬 COORDINATOR_RESPONSE | 协调者直接回复 | 内容长度: {len(response.content)}")
        # response本身已经被LangGraph的流式机制捕获并输出了
    
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | coordinator | 节点执行完成 | 总耗时: {duration:.2f}s")
    
    return Command(
        update={
            "messages": messages,
            "locale": locale,
            "research_topic": research_topic,
            "resources": configurable.resources,
        },
        goto=goto,
    )


@observe(name="📝 报告节点", as_type="agent")
def reporter_node(state: State, config: RunnableConfig):
    """撰写最终报告的报告员节点"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | reporter | 开始执行报告生成节点")
    
    logger.info("Reporter write final report")
    configurable = Configuration.from_runnable_config(config)
    
    # 记录报告生成的基本信息
    observations = state.get("observations", [])
    enhanced_logger.logger.info(f"📊 REPORT_INIT | 开始生成最终报告 | 研究步骤数: {len(observations)}")
    current_plan = state.get("current_plan")
    # 处理current_plan的类型差异
    if hasattr(current_plan, 'title') and hasattr(current_plan, 'thought'):
        plan_title = current_plan.title
        plan_thought = current_plan.thought
    elif isinstance(current_plan, dict):
        plan_title = current_plan.get('title', '未知计划')
        plan_thought = current_plan.get('thought', '计划详情不可用')
    else:
        plan_title = str(current_plan) if current_plan else "未知计划"
        plan_thought = "计划详情不可用"
        
    input_ = {
        "messages": [
            HumanMessage(
                f"# 研究要求\n\n## 任务\n\n{plan_title}\n\n## 描述\n\n{plan_thought}"
            )
        ],
        "locale": state.get("locale", "zh-CN"),  # 默认使用中文
    }
    invoke_messages = apply_prompt_template("reporter", input_, configurable)
    observations = state.get("observations", [])

    # 添加关于新报告格式、引用风格和表格使用的提醒
    invoke_messages.append(
        HumanMessage(
            content=f"重要提示：请按照提示词中的格式组织您的报告。记得包含：\n\n1. 关键要点 - 最重要发现的要点列表\n2. 概述 - 主题的简要介绍\n3. 详细分析 - 按逻辑部分组织\n4. 调研说明（可选）- 用于更全面的报告\n5. 主要引用 - 在末尾列出所有参考文献\n\n对于引用，不要在正文中包含内联引用。而是将所有引用放在末尾的'主要引用'部分，使用格式：`- [来源标题](URL)`。在每个引用之间包含一个空行以提高可读性。\n\n优先使用MARKDOWN表格进行数据展示和对比。在展示对比数据、统计信息、功能或选项时使用表格。使用清晰的表头和对齐的列来构建表格。示例表格格式：\n\n| 功能 | 描述 | 优点 | 缺点 |\n|------|------|------|------|\n| 功能1 | 描述1 | 优点1 | 缺点1 |\n| 功能2 | 描述2 | 优点2 | 缺点2 |\n\n**请用{state.get('locale', 'zh-CN')}语言编写报告，并充分引用下面的研究结果。**",
            name="system"
        )
    )

    for i, observation in enumerate(observations):
        invoke_messages.append(
            HumanMessage(
                content=f"# 研究步骤 {i+1} 的结果\n\n{observation}\n\n---",
                name="observation",
            )
        )
    logger.debug(f"Current invoke messages: {invoke_messages}")
    
    # 记录 reporter 的输入内容
    logger.info(f"Reporter input: {invoke_messages}")
    enhanced_logger.logger.info(f"📝 REPORTER_INPUT | 输入消息数: {len(invoke_messages)} | 观察结果数: {len(observations)} | 计划标题: {plan_title}")
    
    # 记录LLM调用过程
    llm_start_time = time.time()
    enhanced_logger.logger.info(f"🤖 LLM_INVOKE | reporter | 开始生成最终报告 | 提示消息数: {len(invoke_messages)}")

    try:
        # 获取 LLM 实例
        reporter_llm = get_llm_by_type(AGENT_LLM_MAP["reporter"])
        enhanced_logger.logger.info(f"🔍 LLM_INFO | reporter | 模型类型: {type(reporter_llm).__name__} | 模型名称: {getattr(reporter_llm, 'model_name', 'unknown')}")

        # 记录调用前的状态
        enhanced_logger.logger.info(f"⏳ LLM_CALL_START | reporter | 准备调用LLM.invoke() | 时间: {time.strftime('%H:%M:%S')}")

        response = reporter_llm.invoke(invoke_messages)

        # 记录调用后的状态
        llm_call_end_time = time.time()
        enhanced_logger.logger.info(f"✅ LLM_CALL_END | reporter | LLM调用成功返回 | 时间: {time.strftime('%H:%M:%S')} | 耗时: {llm_call_end_time - llm_start_time:.2f}s")

        response_content = response.content

        llm_duration = time.time() - llm_start_time
        report_length = len(response_content) if response_content else 0
        enhanced_logger.logger.info(f"✅ LLM_COMPLETE | reporter | 报告生成完成 | 报告长度: {report_length} | LLM耗时: {llm_duration:.2f}s")

    except Exception as e:
        llm_duration = time.time() - llm_start_time
        enhanced_logger.logger.error(f"❌ LLM_ERROR | reporter | LLM调用失败 | 耗时: {llm_duration:.2f}s | 错误类型: {type(e).__name__} | 错误信息: {str(e)}")
        logger.exception(f"Reporter LLM调用异常: {e}")
        raise
    
    logger.info(f"reporter response: {response_content}")

    # 保存 observations 为 markdown 文件到 examples 目录
    if observations:
        try:
            # 创建 examples 目录（如果不存在）
            examples_dir = "md_output"
            os.makedirs(examples_dir, exist_ok=True)

            # 生成文件名（使用时间戳）
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{examples_dir}/research_observations_{timestamp}.md"

            # 构建 markdown 内容
            md_content = f"# 研究观察结果\n\n"
            md_content += f"## 研究主题\n\n{plan_title}\n\n"
            md_content += f"---\n\n"

            # 将每个 observation 单独成段
            for i, observation in enumerate(observations):
                md_content += f"{observation}\n\n"

            # 写入文件
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(md_content)

            enhanced_logger.logger.info(f"📄 OBSERVATIONS_SAVED | 观察结果已保存到文件: {filename} | 大小: {len(md_content)} 字节")
            logger.info(f"Observations saved to: {filename}")

        except Exception as e:
            enhanced_logger.logger.error(f"❌ SAVE_OBSERVATIONS_FAILED | 保存观察结果失败: {str(e)}")
            logger.error(f"Failed to save observations: {e}")

    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | reporter | 节点执行完成 | 总耗时: {duration:.2f}s")

    return {"final_report": response_content}


def research_team_node(state: State):
    """研究团队节点，协作完成任务"""
    logger.info("研究团队正在协作执行任务")
    pass


async def _execute_agent_step(
    state: State, agent, agent_name: str, recursion_limit: int = 10
) -> Command[Literal["research_team"]]:
    """使用指定智能体执行步骤的辅助函数"""
    step_start_time = time.time()
    enhanced_logger.logger.info(f"🔄 AGENT_STEP_ENTRY | {agent_name} | 开始执行研究步骤")
    enhanced_logger.logger.info(f"🎛️  RECURSION_LIMIT_PARAM | {agent_name} | 限制: {recursion_limit}")
    
    current_plan = state.get("current_plan")
    plan_title = current_plan.title
    observations = state.get("observations", [])
    
    enhanced_logger.logger.info(f"📝 STEP_CONTEXT | {agent_name} | 计划标题: {plan_title} | 已完成步骤: {len(observations)}")

    # Find the first unexecuted step
    current_step = None
    completed_steps = []
    # 处理current_plan.steps的访问问题
    if hasattr(current_plan, 'steps'):
        plan_steps = current_plan.steps
    elif isinstance(current_plan, dict) and 'steps' in current_plan:
        plan_steps = current_plan['steps']
    else:
        logger.warning("在当前计划中未找到步骤")
        return Command(goto="research_team")
        
    for step in plan_steps:
        if not step.execution_res:
            current_step = step
            break
        else:
            completed_steps.append(step)

    if not current_step:
        enhanced_logger.logger.warning(f"⚠️ STEP_NOT_FOUND | {agent_name} | 未找到未执行的步骤")
        logger.warning("未找到未执行的步骤")
        return Command(goto="research_team")

    enhanced_logger.logger.info(f"🎯 STEP_SELECTED | {agent_name} | 正在执行: {current_step.title}")
    logger.info(f"Executing step: {current_step.title}, agent: {agent_name}")

    # 格式化已完成步骤信息
    completed_steps_info = ""
    # if completed_steps:
    #     completed_steps_info = "# 已完成的研究步骤\n\n"
    #     for i, step in enumerate(completed_steps):
    #         completed_steps_info += f"## 已完成步骤 {i + 1}：{step.title}\n\n"
    #         completed_steps_info += f"<finding>\n{step.execution_res}\n</finding>\n\n"

    # 为智能体准备包含已完成步骤信息的输入
    agent_input = {
        "messages": [
            HumanMessage(
                content=f"# 研究主题\n\n{plan_title}\n\n{completed_steps_info}# 当前步骤\n\n## 标题\n\n{current_step.title}\n\n## 描述\n\n{current_step.description}\n\n## 语言区域\n\n{state.get('locale', 'zh-CN')}"
            )
        ]
    }

    # 🆕 添加详细的工具调用前日志
    enhanced_logger.logger.info("="*80)
    enhanced_logger.logger.info(f"🤖 AGENT_INVOKE_PREPARE | {agent_name} | 准备调用LLM")
    enhanced_logger.logger.info(f"📋 输入消息内容 (前200字): {agent_input['messages'][0].content[:200]}...")
    
    # 注意：create_react_agent返回的是编译后的图对象，不直接暴露tools属性
    # 但工具已经通过create_agent函数绑定到LLM上
    # 我们可以通过检查agent的其他属性来确认
    if hasattr(agent, 'tools'):
        tool_names = [getattr(t, 'name', 'unknown') for t in agent.tools]
        enhanced_logger.logger.info(f"🔧 Agent.tools属性存在: {tool_names} (共{len(agent.tools)}个)")
    elif hasattr(agent, 'nodes'):
        enhanced_logger.logger.info(f"🔧 Agent类型: LangGraph编译图 (这是正常的)")
        enhanced_logger.logger.info(f"🔧 工具已通过create_react_agent绑定到LLM")
    else:
        enhanced_logger.logger.warning(f"⚠️  Agent对象类型异常: {type(agent)}")
        enhanced_logger.logger.warning(f"   Agent属性: {dir(agent)[:10]}...")
    
    enhanced_logger.logger.info("="*80)

    # 为研究智能体添加引用提醒
    if agent_name == "researcher":

        pass

        agent_input["messages"].append(
            HumanMessage(
                content="重要提示：不要在正文中包含内联引用。而是跟踪所有来源，并在末尾使用链接引用格式包含参考文献部分。在每个引用之间包含一个空行以提高可读性。每个引用使用以下格式：\n- [来源标题](URL)\n\n- [另一个来源](URL)",
                name="system",
            )
        )

    # 🔥 核心：使用中间件检查工具调用次数，如果接近建议限制则插入提示消息
    # 注意：我们使用软限制（建议值）和硬限制（LangGraph recursion_limit）分离
    # 软限制：建议 LLM 停止的工具调用次数
    # 硬限制：LangGraph 的 recursion_limit，设置为一个较大的值作为安全网

    # 软限制：建议 LLM 停止的次数（从 recursion_limit 参数获取）
    soft_limit = recursion_limit  # 例如：5

    # 硬限制：LangGraph 的实际 recursion_limit，设置为一个较大的值防止报错
    # 设置为软限制的 10 倍，最少 50
    hard_limit = max(soft_limit * 10, 50)

    middleware = ToolCallLimitMiddleware(max_calls=soft_limit)

    # 检查 state 中的消息（历史消息）
    state_messages = state.get("messages", [])
    tool_call_count = middleware.count_tool_calls_in_messages(state_messages)

    enhanced_logger.logger.info(
        f"📊 TOOL_CALL_COUNT | {agent_name} | 当前工具调用: {tool_call_count} | "
        f"软限制(建议): {soft_limit} | 硬限制(LangGraph): {hard_limit}"
    )

    # 如果工具调用次数已经接近软限制（>= 80%），在输入中插入提示消息
    if tool_call_count >= int(soft_limit * 0.8):
        enhanced_logger.logger.warning(
            f"⚠️  TOOL_LIMIT_WARNING | {agent_name} | 工具调用 {tool_call_count}/{soft_limit} | "
            f"已达到建议限制的 80%，将在输入中插入停止建议"
        )

        # 创建停止建议消息
        stop_advice_msg = HumanMessage(
            content=(
                f"\n\n【系统提示 - 请完成分析并输出答案】\n\n"
                f"你已经调用了 {tool_call_count} 次工具，已经收集了足够的信息。\n\n"
                f"**请立即停止搜索，开始输出最终答案**：\n\n"
                f"✅ 现在请执行：\n"
                f"   1. 综合分析已收集的所有搜索结果\n"
                f"   2. 整理关键信息和数据\n"
                f"   3. 输出完整、结构化的最终答案\n\n"
                f"❌ 不要继续操作：\n"
                f"   - 不要再调用任何搜索工具\n"
                f"   - 不要获取更多信息\n\n"
                f"请现在就开始输出你的最终答案。"
            ),
            name="tool_limit_advisor"
        )

        # 将提示消息添加到输入中
        agent_input["messages"].append(stop_advice_msg)
        enhanced_logger.logger.info(f"✅ STOP_ADVICE_ADDED | 已在输入中添加停止建议消息")

    # 使用硬限制作为 LangGraph 的 recursion_limit
    actual_recursion_limit = hard_limit

    enhanced_logger.logger.info(
        f"🎛️  RECURSION_LIMIT | {agent_name} | LangGraph递归限制: {actual_recursion_limit} 次 | "
        f"软限制(建议): {soft_limit} 次"
    )
    logger.info(f"Agent input: {agent_input}")

    # 记录Agent执行过程
    agent_exec_start_time = time.time()
    enhanced_logger.logger.info(f"⏳ AGENT_INVOKING | {agent_name} | 正在调用LLM... | 递归限制: {actual_recursion_limit} | 开始时间: {time.strftime('%H:%M:%S')}")

    # 添加定期心跳日志的异步任务
    async def log_agent_progress():
        """在agent执行期间定期输出进度日志"""
        progress_interval = 30  # 每30秒输出一次进度
        elapsed = 0
        while True:
            await asyncio.sleep(progress_interval)
            elapsed += progress_interval
            current_duration = time.time() - agent_exec_start_time
            enhanced_logger.logger.info(
                f"💓 AGENT_HEARTBEAT | {agent_name} | Agent仍在执行中... | 已耗时: {current_duration:.1f}s | 时间: {time.strftime('%H:%M:%S')}"
            )

    try:
        # 启动心跳任务
        heartbeat_task = asyncio.create_task(log_agent_progress())

        result = await agent.ainvoke(
            input=agent_input, config={"recursion_limit": actual_recursion_limit}
        )

        # 取消心跳任务
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        agent_exec_duration = time.time() - agent_exec_start_time
        enhanced_logger.logger.info(f"✅ AGENT_INVOKED | {agent_name} | LLM调用成功完成 | 耗时: {agent_exec_duration:.2f}s | 结束时间: {time.strftime('%H:%M:%S')}")

    except Exception as e:
        # 取消心跳任务
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        agent_exec_duration = time.time() - agent_exec_start_time
        enhanced_logger.logger.error(
            f"❌ AGENT_INVOKE_ERROR | {agent_name} | LLM调用失败 | 耗时: {agent_exec_duration:.2f}s | "
            f"错误类型: {type(e).__name__} | 错误信息: {str(e)} | 时间: {time.strftime('%H:%M:%S')}"
        )
        logger.exception(f"Agent {agent_name} LLM调用异常: {e}")
        raise
    
    # 🆕 添加详细的响应分析日志
    if isinstance(result, dict):
        messages = result.get("messages", [])
        enhanced_logger.logger.info(f"📨 AGENT_RESPONSE | {agent_name} | 返回消息数: {len(messages)}")
        
        # 检查是否有工具调用
        tool_calls_found = False
        tool_call_count = 0
        for msg_idx, msg in enumerate(messages):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_calls_found = True
                tool_call_count += len(msg.tool_calls)
                enhanced_logger.logger.info(f"🔧 TOOL_CALLS_DETECTED | {agent_name} | 消息[{msg_idx}]中的工具调用数: {len(msg.tool_calls)}")
                for tc_idx, tc in enumerate(msg.tool_calls):
                    tool_name = tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown')
                    tool_args = tc.get('args', {}) if isinstance(tc, dict) else getattr(tc, 'args', {})
                    # 只打印参数的摘要，避免日志过长
                    args_summary = str(tool_args)[:100] + '...' if len(str(tool_args)) > 100 else str(tool_args)
                    enhanced_logger.logger.info(f"   ⚙️  工具调用[{tc_idx}]: {tool_name} | 参数: {args_summary}")
        
        if not tool_calls_found:
            enhanced_logger.logger.warning(f"⚠️  NO_TOOL_CALLS | {agent_name} | LLM没有调用任何工具！")
            enhanced_logger.logger.warning(f"   ❌ 这是一个问题！{agent_name}应该调用工具进行搜索。")
            enhanced_logger.logger.warning(f"   可能原因:")
            enhanced_logger.logger.warning(f"      1) Prompt指令不够强制")
            enhanced_logger.logger.warning(f"      2) LLM选择直接回答")
            enhanced_logger.logger.warning(f"      3) LLM模型不支持function calling")
            # 打印LLM的实际响应内容
            for i, msg in enumerate(messages):
                content = getattr(msg, 'content', '')
                if content:
                    content_preview = content[:300] + '...' if len(content) > 300 else content
                    enhanced_logger.logger.warning(f"   📄 LLM直接响应[{i}]: {content_preview}")
        else:
            enhanced_logger.logger.info(f"✅ TOOL_CALLS_SUCCESS | {agent_name} | 共检测到 {tool_call_count} 个工具调用")
    else:
        enhanced_logger.logger.warning(f"⚠️  UNEXPECTED_RESULT_TYPE | {agent_name} | result类型: {type(result)}")

    # Process the result
    response_content = result["messages"][-1].content
    
    # 移除思考标签（如果存在）
    if response_content and '<think>' in response_content.lower():
        original_length = len(response_content)
        response_content = remove_think_tags(response_content)
        cleaned_length = len(response_content)
        enhanced_logger.logger.info(f"🧹 CLEAN_THINK_TAGS | {agent_name} | 移除思考标签 | 原始长度: {original_length} | 清理后长度: {cleaned_length} | 减少: {original_length - cleaned_length}")
    
    response_length = len(response_content) if response_content else 0
    enhanced_logger.logger.info(f"📊 STEP_RESULT | {agent_name} | 步骤结果处理完成 | 响应长度: {response_length}")
    
    logger.debug(f"{agent_name.capitalize()} full response: {response_content}")

    # Update the step with the execution result
    current_step.execution_res = response_content
    enhanced_logger.logger.info(f"✅ STEP_COMPLETE | {agent_name} | 步骤执行完成: '{current_step.title}'")
    logger.info(f"Step '{current_step.title}' execution completed by {agent_name}")
    
    step_duration = time.time() - step_start_time
    enhanced_logger.logger.info(f"✅ AGENT_STEP_EXIT | {agent_name} | 步骤执行总耗时: {step_duration:.2f}s")

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name=agent_name,
                )
            ],
            "observations": observations + [response_content],
        },
        goto="research_team",
    )


async def _setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list,
    recursion_limit: int = 10,
) -> Command[Literal["research_team"]]:
    """设置智能体并使用适当工具执行步骤的辅助函数

    此函数处理 researcher_node 和 coder_node 的通用逻辑：
    1. 根据智能体类型配置 MCP 服务器和工具
    2. 使用适当的工具创建智能体或使用默认智能体
    3. 在当前步骤上执行智能体

    参数：
        state: 当前状态
        config: 可运行配置
        agent_type: 智能体类型（"researcher" 或 "coder"）
        default_tools: 要添加到智能体的默认工具

    返回：
        Command 对象，用于更新状态并转到 research_team
    """
    setup_start_time = time.time()
    enhanced_logger.logger.info(f"🔄 AGENT_SETUP_ENTRY | {agent_type} | 开始配置智能体")
    
    configurable = Configuration.from_runnable_config(config)
    mcp_servers = {}
    enabled_tools = {}
    
    enhanced_logger.logger.info(f"🔧 TOOL_CONFIG | {agent_type} | 默认工具数: {len(default_tools)}")

    # Extract MCP server configuration for this agent type
    if configurable.mcp_settings:
        for server_name, server_config in configurable.mcp_settings["servers"].items():
            if (
                server_config["enabled_tools"]
                and agent_type in server_config["add_to_agents"]
            ):
                mcp_servers[server_name] = {
                    k: v
                    for k, v in server_config.items()
                    if k in ("transport", "command", "args", "url", "env", "headers")
                }
                for tool_name in server_config["enabled_tools"]:
                    enabled_tools[tool_name] = server_name

    # Create and execute agent with MCP tools if available
    if mcp_servers:
        enhanced_logger.logger.info(f"🔌 MCP_ENABLED | {agent_type} | 检测到MCP服务器 | 服务器数: {len(mcp_servers)}")
        client = MultiServerMCPClient(mcp_servers)
        loaded_tools = default_tools[:]
        all_tools = await client.get_tools()
        mcp_tool_count = 0
        for tool in all_tools:
            if tool.name in enabled_tools:
                tool.description = (
                    f"Powered by '{enabled_tools[tool.name]}'.\n{tool.description}"
                )
                loaded_tools.append(tool)
                mcp_tool_count += 1
        
        enhanced_logger.logger.info(f"🔧 MCP_TOOLS_LOADED | {agent_type} | MCP工具加载完成 | 新增工具: {mcp_tool_count} | 总工具数: {len(loaded_tools)}")
        agent = create_agent(agent_type, agent_type, loaded_tools, agent_type, configurable)

        setup_duration = time.time() - setup_start_time
        enhanced_logger.logger.info(f"✅ AGENT_SETUP_COMPLETE | {agent_type} | MCP智能体配置完成 | 耗时: {setup_duration:.2f}s")

        return await _execute_agent_step(state, agent, agent_type, recursion_limit=recursion_limit)
    else:
        enhanced_logger.logger.info(f"🔧 DEFAULT_TOOLS | {agent_type} | 使用默认工具 | 工具数: {len(default_tools)}")
        # Use default tools if no MCP servers are configured
        agent = create_agent(agent_type, agent_type, default_tools, agent_type, configurable)

        setup_duration = time.time() - setup_start_time
        enhanced_logger.logger.info(f"✅ AGENT_SETUP_COMPLETE | {agent_type} | 默认智能体配置完成 | 耗时: {setup_duration:.2f}s")

        return await _execute_agent_step(state, agent, agent_type, recursion_limit=recursion_limit)


async def researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """执行研究任务的研究员节点"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | researcher | 开始执行研究节点")
    
    logger.info("Researcher node is researching.")
    configurable = Configuration.from_runnable_config(config)

    # 读取 researcher 特定的递归限制配置
    researcher_limit = getattr(configurable, 'researcher_recursion_limit', None)
    if researcher_limit is None:
        # 如果配置中没有，尝试从环境变量读取，默认值改为 5
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
            report_search,  # 研报知识库搜索（必需）
        ]
        tool_names = "report_search"

    elif report_style == "business_marketing":
        # 对公营销报告：使用完整的工具链
        tools = [
            # online_search_tool(max_results=configurable.max_search_results),  # 互联网公开信息搜索（必需）
            research_skill_prompt_search,  # 提示词召回（必需）
            business_opportunity_search,  # 商机数据
            sentiment_search,  # 舆情数据
            financial_summary,  # 财务数据
            # product_search,  # 产品类型搜索
            product_instance_search,  # 产品实例搜索
        ]
        tool_names = "online_search, research_skill_prompt_search, business_opportunity_search, sentiment_search, financial_summary, product_instance_search"

    elif report_style == "business_marketing_client":
        # 默认配置：使用基础搜索工具
        tools = [
            online_search_tool(max_results=configurable.max_search_results),
            report_search,
        ]
        tool_names = "online_search, report_search"

    elif report_style == "academic":
        # 默认配置：使用基础搜索工具
        tools = [
            online_search_tool(max_results=configurable.max_search_results),
            report_search,
        ]
        tool_names = "online_search, report_search"

    enhanced_logger.logger.info(
        f"🔧 TOOLS_READY | 研究工具配置完成 | "
        f"报告风格: {report_style} | 工具数: {len(tools)} | 包含: {tool_names}"
    )
    
    logger.info(f"Researcher tools: {tools}")
    
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
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """执行代码分析的编码员节点"""
    logger.info("编码员节点正在编写代码")
    return await _setup_and_execute_agent_step(
        state,
        config,
        "coder",
        [python_repl_tool],
    )


# 导出所有节点函数
__all__ = [
    # 路由和简单路径节点
    "router_node",
    "direct_answer_node",
    "simple_search_node",
    "iterative_research_node",  # 新增：迭代研究节点
    "iterative_reporter_node",  # 新增：迭代研究报告节点
    
    # 深度研究路径节点
    "coordinator_node",
    "background_investigation_node",
    "planner_node",
    "human_feedback_node",
    "reporter_node",
    "research_team_node",
    "researcher_node",
    "coder_node",
    
    # 辅助函数
    "handoff_to_planner",
]
