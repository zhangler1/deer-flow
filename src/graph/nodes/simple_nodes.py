# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
简单节点模块

包含：
- direct_answer_node: 直接回答节点（不走检索）
- simple_search_node: 简单检索节点（多轮工具调用）
"""

import logging
import os
import time
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.agents import create_agent
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.template import apply_prompt_template
from src.tools import (
    crawl_tool,
    domain_fin_search,
    get_web_search_tool,
)
from src.utils.enhanced_logger import get_enhanced_logger

# Langfuse 集成
try:
    from langfuse import observe
except ImportError:
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return decorator


logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.simple_nodes')


@observe(name="⚡ 直接回答节点", as_type="agent")
def direct_answer_node(state, config: RunnableConfig) -> Command[Literal["__end__"]]:
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
        
        duration = time.time() - start_time
        enhanced_logger.logger.info(
            f"✅ NODE_EXIT | direct_answer | 节点执行完成 | 总耗时: {duration:.2f}s"
        )
        
        return Command(
            update={
                "final_report": answer,
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"直接回答处理失败: {e}")
        enhanced_logger.logger.error(f"❌ DIRECT_ANSWER_ERROR | {str(e)}")
        
        error_msg = f"抱歉，在处理您的问题时遇到了错误。请尝试重新提问。\n\n错误信息: {str(e)}"
        return Command(
            update={
                "final_report": error_msg,
                "messages": [AIMessage(content=error_msg, name="direct_answer_assistant")]
            },
            goto="__end__"
        )


async def simple_search_node(state, config: RunnableConfig) -> Command[Literal["__end__"]]:
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
                max_search_results=configurable.max_search_results,
                engine=configurable.search_engine,
                repository_id=configurable.custom_search_repository
            ),
            crawl_tool,
            domain_fin_search,
        ]
        
        enhanced_logger.logger.info(
            f"🔧 TOOLS_READY | 简单检索工具配置完成 | "
            f"工具数: {len(tools)} | 包含: web_search, crawl_tool, domain_fin_search"
        )
        
        # 创建简单检索智能体
        agent_start = time.time()
        agent = create_agent(
            agent_name="simple_search_assistant",
            agent_type="researcher",
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
        
        # 设置递归限制
        default_recursion_limit = 25
        try:
            env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit))
            parsed_limit = int(env_value_str)
            max_llm_calls = parsed_limit if parsed_limit > 0 else default_recursion_limit
        except ValueError:
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
        
        error_msg = f"抱歉，在处理您的问题时遇到了错误。请尝试重新提问或使用深度研究模式。\n\n错误信息: {str(e)}"
        return Command(
            update={
                "final_report": error_msg,
                "messages": [AIMessage(content=error_msg, name="simple_search_assistant")]
            },
            goto="__end__"
        )
