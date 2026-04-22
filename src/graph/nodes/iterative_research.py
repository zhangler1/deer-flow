# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
迭代研究节点模块

包含：
- iterative_research_node: 迭代深度研究节点（多轮自主研究）
- iterative_reporter_node: 迭代研究报告生成节点
"""

import logging
import time
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.agents import create_agent
from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.template import apply_prompt_template
from src.tools import (
    online_search_tool,
    crawl_tool,
    industry_report_search,
    news_search,
    news_detail_search,
)
from src.utils.enhanced_logger import get_enhanced_logger




logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.iterative_research')


def iterative_research_node(state, config: RunnableConfig) -> Command[Literal["__end__", "iterative_research_node"]]:
    """
    迭代深度研究节点 - 针对单个问题进行多轮自主深入研究
    
    工作流程：
    1. 组织检索词
    2. 执行检索（web_search + crawl_tool）
    3. 分析信息并回答
    4. 判断是否足够回答用户问题
    5. 如果不足，针对未解决问题继续下一轮迭代（最多5轮）
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
    
    # 从配置中获取最大迭代次数
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
            online_search_tool(
                max_results=configurable.max_search_results
            ),
            industry_report_search,
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
        
        # 构建消息列表
        messages_for_llm = []
        messages_for_llm.append(
            HumanMessage(
                content=f"请对以下问题进行深入研究:\n\n{query}",
                name="user_query"
            )
        )
        
        if state_with_history.get('iteration_history'):
            messages_for_llm.append(
                HumanMessage(
                    content=f"## 迭代研究历史记录\n\n{state_with_history['iteration_history']}",
                    name="iteration_history"
                )
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
        invoke_start = time.time()
        should_continue = False
        
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
            
            enhanced_logger.logger.info(
                f"🤖 LLM_OUTPUT | iterative_research | 响应长度: {len(answer)} | LLM耗时: {invoke_duration:.2f}s\n"
                f"{'='*80}\n{answer}\n{'='*80}"
            )
            
            # 判断是否需要继续迭代
            if iteration_count + 1 < MAX_ITERATIONS:
                continue_signals = [
                    "**是否需要继续研究**：是",
                    "**是否需要继续研究**: 是"
                ]
                answer_lower = str(answer).lower()
                should_continue = any(signal.lower() in answer_lower for signal in continue_signals)
                enhanced_logger.logger.info(f"------------------------ should_continue: {should_continue}")
                
        except RecursionError as re:
            enhanced_logger.logger.warning(
                f"⚠️ RECURSION_LIMIT_REACHED | iterative_research | "
                f"第{iteration_count + 1}轮达到递归限制，强制进入报告生成阶段"
            )
            logger.warning(f"迭代研究达到递归限制: {str(re)}")
            
            invoke_duration = time.time() - invoke_start
            answer = f"第{iteration_count + 1}轮研究因达到工具调用次数限制而结束。已收集的信息将用于生成最终报告。"
            should_continue = False
        
        # 更新迭代历史
        new_iteration = {
            "round": iteration_count + 1,
            "summary": answer,
            "timestamp": time.time()
        }
        updated_history = list(iteration_history) + [new_iteration]
        
        duration = time.time() - start_time
        
        if should_continue:
            enhanced_logger.logger.info(
                f"🔄 ITERATION_CONTINUE | 第{iteration_count + 1}轮完成，继续下一轮 | 耗时: {duration:.2f}s"
            )
            next_iteration = iteration_count + 2
            logger.info(f"[轮次跳转] 第{iteration_count + 1}轮完成 → 即将跳转到第{next_iteration}轮")
            
            node_transition_data = {
                "from": "iterative_research_node",
                "to": "iterative_research_node",
                "iteration": next_iteration,
                "reason": "continue",
            }
            
            transition_message = AIMessage(
                content="",
                name="node_transition_event",
                additional_kwargs={"node_transition": node_transition_data}
            )
            
            return Command(
                update={
                    "iteration_count": iteration_count + 1,
                    "iteration_history": updated_history,
                    "messages": [transition_message],
                    "research_topic": query,
                },
                goto="iterative_research_node"
            )
        else:
            enhanced_logger.logger.info(
                f"✅ NODE_EXIT | iterative_research | 研究完成 | 总轮次: {iteration_count + 1} | 总耗时: {duration:.2f}s"
            )
            
            node_transition_data = {
                "from": "iterative_research_node",
                "to": "iterative_reporter_node",
                "iteration": iteration_count + 2,
                "reason": "finish",
            }
            
            transition_message = AIMessage(
                content="",
                name="node_transition_event",
                additional_kwargs={"node_transition": node_transition_data}
            )
            
            return Command(
                update={
                    "iteration_count": iteration_count + 1,
                    "iteration_history": updated_history,
                    "messages": [transition_message],
                    "research_topic": query,
                },
                goto="iterative_reporter_node"
            )
        
    except Exception as e:
        logger.error(f"迭代研究处理失败: {e}")
        enhanced_logger.logger.error(f"❌ ITERATIVE_RESEARCH_ERROR | {str(e)}")
        
        error_msg = f"抱歉，在迭代研究过程中遇到了错误。\n\n错误信息: {str(e)}"
        return Command(
            update={
                "final_report": error_msg,
                "messages": [AIMessage(content=error_msg, name="iterative_research_error")]
            },
            goto="__end__"
        )


def iterative_reporter_node(state, config: RunnableConfig) -> Command[Literal["__end__"]]:
    """
    迭代研究报告员节点 - 专门用于生成迭代研究的最终报告
    
    工作流程：
    1. 收集所有迭代研究的历史记录
    2. 整合所有研究内容
    3. 生成最终报告
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
            "locale": state.get("locale", "zh-CN"),
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
        logger.info(f"Iterative reporter input: {invoke_messages}")
        enhanced_logger.logger.info(
            f"📝 ITERATIVE_REPORTER_INPUT | 输入消息数: {len(invoke_messages)} | 迭代轮次: {len(iteration_history)} | 研究主题: {research_topic}"
        )
        
        # 调用 LLM 生成报告
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
        
        return Command(
            update={
                "final_report": response_content
            },
            goto="__end__"
        )
        
    except Exception as e:
        logger.error(f"迭代研究报告生成失败: {e}")
        enhanced_logger.logger.error(f"❌ ITERATIVE_REPORTER_ERROR | {str(e)}")
        
        error_msg = f"抱歉，在生成迭代研究报告的过程中遇到了错误。\n\n错误信息: {str(e)}"
        return Command(
            update={
                "final_report": error_msg,
                "messages": [AIMessage(content=error_msg, name="iterative_reporter_error")]
            },
            goto="__end__"
        )
