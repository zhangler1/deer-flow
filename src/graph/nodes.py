# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

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
from src.llms.llm import get_llm_by_type
from src.prompts.planner_model import Plan
from src.prompts.template import apply_prompt_template
from src.tools import (
    get_retriever_tool,
    get_web_search_tool,
    python_repl_tool,
)
from src.tools.search import LoggedTavilySearch
from src.utils.json_utils import repair_json_output
from src.utils.enhanced_logger import get_enhanced_logger

from ..config import SELECTED_SEARCH_ENGINE, SearchEngine
from .types import State

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes')


@tool
def handoff_to_planner(
    research_topic: Annotated[str, "The topic of the research task to be handed off."],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """Handoff to planner agent to do plan."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it needs to hand off to planner agent
    return


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
        enhanced_logger.logger.info(f"🔍 使用{configurable.search_engine}搜索引擎进行背景调研 | 查询: '{query}'")
        background_investigation_results = get_web_search_tool(
            configurable.max_search_results, 
            configurable.search_engine,
            configurable.custom_search_repository
        ).invoke(query)
        result = {
            "background_investigation_results": json.dumps(
                background_investigation_results, ensure_ascii=False
            )
        }
        
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | background_investigation | 节点执行完成 | 耗时: {duration:.2f}s")
    return result


def planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["human_feedback", "reporter"]]:
    """Planner node that generate the full plan."""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | planner | 开始执行计划生成节点")
    
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    enhanced_logger.log_plan_generation(plan_iterations + 1, state.get("research_topic", "未知"), 0)
    
    messages = []
    try:
        messages = apply_prompt_template("planner", dict(state), configurable)
    except Exception as e:
        enhanced_logger.logger.error(f"Failed to apply prompt template: {e}")
        # 使用默认消息
        messages = [HumanMessage(content=f"Plan for: {state.get('research_topic', 'Unknown topic')}")]

    if state.get("enable_background_investigation") and state.get(
        "background_investigation_results"
    ):
        messages += [
            {
                "role": "user",
                "content": (
                    "background investigation results of user query:\n"
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
            
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
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
                        "messages": [AIMessage(content=full_response, name="planner")],
                        "current_plan": new_plan,
                    },
                    goto="human_feedback",
                )
            else:
                enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → reporter | 原因: 所有步骤已执行完成")
                duration = time.time() - start_time
                enhanced_logger.logger.info(f"✅ NODE_EXIT | planner | 节点执行完成 | 耗时: {duration:.2f}s")
                
                return Command(
                    update={
                        "messages": [AIMessage(content=full_response, name="planner")],
                        "current_plan": new_plan,
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
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": full_response,
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
            
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
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


def coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "background_investigator", "__end__"]]:
    """Coordinator node that communicate with customers."""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | coordinator | 开始执行协调节点")
    
    logger.info("Coordinator talking.")
    configurable = Configuration.from_runnable_config(config)
    
    # 打印状态信息
    enhanced_logger.logger.info(f"📊 COORDINATOR_STATE | research_topic: {state.get('research_topic', 'Not set')}")
    enhanced_logger.logger.info(f"📊 COORDINATOR_STATE | locale: {state.get('locale', 'Not set')}")
    enhanced_logger.logger.info(f"📊 COORDINATOR_STATE | messages数量: {len(state.get('messages', []))}")
    
    try:
        messages = apply_prompt_template("coordinator", dict(state))
        enhanced_logger.logger.info(f"📝 COORDINATOR_PROMPT | 提示模板应用成功 | 消息数: {len(messages)}")
    except Exception as e:
        enhanced_logger.logger.error(f"Failed to apply coordinator template: {e}")
        # 使用默认消息
        messages = [HumanMessage(content=f"Coordinate request: {state.get('research_topic', 'Unknown request')}")]
    
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
    locale = state.get("locale", "en-US")  # Default locale if not specified
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


def reporter_node(state: State, config: RunnableConfig):
    """Reporter node that write a final report."""
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
        plan_title = current_plan.get('title', 'Unknown Plan')
        plan_thought = current_plan.get('thought', 'Plan details not available')
    else:
        plan_title = str(current_plan) if current_plan else "Unknown Plan"
        plan_thought = "Plan details not available"
        
    input_ = {
        "messages": [
            HumanMessage(
                f"# Research Requirements\n\n## Task\n\n{plan_title}\n\n## Description\n\n{plan_thought}"
            )
        ],
        "locale": state.get("locale", "zh-CN"),  # 默认使用中文
    }
    invoke_messages = apply_prompt_template("reporter", input_, configurable)
    observations = state.get("observations", [])

    # Add a reminder about the new report format, citation style, and table usage
    invoke_messages.append(
        HumanMessage(
            content=f"IMPORTANT: Structure your report according to the format in the prompt. Remember to include:\n\n1. Key Points - A bulleted list of the most important findings\n2. Overview - A brief introduction to the topic\n3. Detailed Analysis - Organized into logical sections\n4. Survey Note (optional) - For more comprehensive reports\n5. Key Citations - List all references at the end\n\nFor citations, DO NOT include inline citations in the text. Instead, place all citations in the 'Key Citations' section at the end using the format: `- [Source Title](URL)`. Include an empty line between each citation for better readability.\n\nPRIORITIZE USING MARKDOWN TABLES for data presentation and comparison. Use tables whenever presenting comparative data, statistics, features, or options. Structure tables with clear headers and aligned columns. Example table format:\n\n| Feature | Description | Pros | Cons |\n|---------|-------------|------|------|\n| Feature 1 | Description 1 | Pros 1 | Cons 1 |\n| Feature 2 | Description 2 | Pros 2 | Cons 2 |\n\n**请用{state.get('locale', 'zh-CN')}语言编写报告，并充分引用下面的研究结果。**",
            name="system",
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
    
    response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(invoke_messages)
    response_content = response.content
    
    llm_duration = time.time() - llm_start_time
    report_length = len(response_content) if response_content else 0
    enhanced_logger.logger.info(f"✅ LLM_COMPLETE | reporter | 报告生成完成 | 报告长度: {report_length} | LLM耗时: {llm_duration:.2f}s")
    
    logger.info(f"reporter response: {response_content}")
    
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | reporter | 节点执行完成 | 总耗时: {duration:.2f}s")

    return {"final_report": response_content}


def research_team_node(state: State):
    """Research team node that collaborates on tasks."""
    logger.info("Research team is collaborating on tasks.")
    pass


async def _execute_agent_step(
    state: State, agent, agent_name: str
) -> Command[Literal["research_team"]]:
    """Helper function to execute a step using the specified agent."""
    step_start_time = time.time()
    enhanced_logger.logger.info(f"🔄 AGENT_STEP_ENTRY | {agent_name} | 开始执行研究步骤")
    
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
        logger.warning("No steps found in current_plan")
        return Command(goto="research_team")
        
    for step in plan_steps:
        if not step.execution_res:
            current_step = step
            break
        else:
            completed_steps.append(step)

    if not current_step:
        enhanced_logger.logger.warning(f"⚠️ STEP_NOT_FOUND | {agent_name} | 未找到未执行的步骤")
        logger.warning("No unexecuted step found")
        return Command(goto="research_team")

    enhanced_logger.logger.info(f"🎯 STEP_SELECTED | {agent_name} | 正在执行: {current_step.title}")
    logger.info(f"Executing step: {current_step.title}, agent: {agent_name}")

    # Format completed steps information
    completed_steps_info = ""
    if completed_steps:
        completed_steps_info = "# Completed Research Steps\n\n"
        for i, step in enumerate(completed_steps):
            completed_steps_info += f"## Completed Step {i + 1}: {step.title}\n\n"
            completed_steps_info += f"<finding>\n{step.execution_res}\n</finding>\n\n"

    # Prepare the input for the agent with completed steps info
    agent_input = {
        "messages": [
            HumanMessage(
                content=f"# Research Topic\n\n{plan_title}\n\n{completed_steps_info}# Current Step\n\n## Title\n\n{current_step.title}\n\n## Description\n\n{current_step.description}\n\n## Locale\n\n{state.get('locale', 'en-US')}"
            )
        ]
    }

    # Add citation reminder for researcher agent
    if agent_name == "researcher":
        if state.get("resources"):
            resources_info = "**The user mentioned the following resource files:**\n\n"
            for resource in state.get("resources"):
                resources_info += f"- {resource.title} ({resource.description})\n"

            agent_input["messages"].append(
                HumanMessage(
                    content=resources_info
                    + "\n\n"
                    + "You MUST use the **local_search_tool** to retrieve the information from the resource files.",
                )
            )

        agent_input["messages"].append(
            HumanMessage(
                content="IMPORTANT: DO NOT include inline citations in the text. Instead, track all sources and include a References section at the end using link reference format. Include an empty line between each citation for better readability. Use this format for each reference:\n- [Source Title](URL)\n\n- [Another Source](URL)",
                name="system",
            )
        )

    # Invoke the agent
    default_recursion_limit = 25
    try:
        env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit))
        parsed_limit = int(env_value_str)

        if parsed_limit > 0:
            recursion_limit = parsed_limit
            logger.info(f"Recursion limit set to: {recursion_limit}")
        else:
            logger.warning(
                f"AGENT_RECURSION_LIMIT value '{env_value_str}' (parsed as {parsed_limit}) is not positive. "
                f"Using default value {default_recursion_limit}."
            )
            recursion_limit = default_recursion_limit
    except ValueError:
        raw_env_value = os.getenv("AGENT_RECURSION_LIMIT")
        logger.warning(
            f"Invalid AGENT_RECURSION_LIMIT value: '{raw_env_value}'. "
            f"Using default value {default_recursion_limit}."
        )
        recursion_limit = default_recursion_limit

    logger.info(f"Agent input: {agent_input}")
    
    # 记录Agent执行过程
    agent_exec_start_time = time.time()
    enhanced_logger.logger.info(f"🤖 AGENT_INVOKE | {agent_name} | 开始智能体执行 | 递归限制: {recursion_limit}")
    
    result = await agent.ainvoke(
        input=agent_input, config={"recursion_limit": recursion_limit}
    )
    
    agent_exec_duration = time.time() - agent_exec_start_time
    enhanced_logger.logger.info(f"✅ AGENT_COMPLETE | {agent_name} | 智能体执行完成 | 耗时: {agent_exec_duration:.2f}s")

    # Process the result
    response_content = result["messages"][-1].content
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
) -> Command[Literal["research_team"]]:
    """Helper function to set up an agent with appropriate tools and execute a step.

    This function handles the common logic for both researcher_node and coder_node:
    1. Configures MCP servers and tools based on agent type
    2. Creates an agent with the appropriate tools or uses the default agent
    3. Executes the agent on the current step

    Args:
        state: The current state
        config: The runnable config
        agent_type: The type of agent ("researcher" or "coder")
        default_tools: The default tools to add to the agent

    Returns:
        Command to update state and go to research_team
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
        agent = create_agent(agent_type, agent_type, loaded_tools, agent_type)
        
        setup_duration = time.time() - setup_start_time
        enhanced_logger.logger.info(f"✅ AGENT_SETUP_COMPLETE | {agent_type} | MCP智能体配置完成 | 耗时: {setup_duration:.2f}s")
        
        return await _execute_agent_step(state, agent, agent_type)
    else:
        enhanced_logger.logger.info(f"🔧 DEFAULT_TOOLS | {agent_type} | 使用默认工具 | 工具数: {len(default_tools)}")
        # Use default tools if no MCP servers are configured
        agent = create_agent(agent_type, agent_type, default_tools, agent_type)
        
        setup_duration = time.time() - setup_start_time
        enhanced_logger.logger.info(f"✅ AGENT_SETUP_COMPLETE | {agent_type} | 默认智能体配置完成 | 耗时: {setup_duration:.2f}s")
        
        return await _execute_agent_step(state, agent, agent_type)


async def researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Researcher node that do research"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | researcher | 开始执行研究节点")
    
    logger.info("Researcher node is researching.")
    configurable = Configuration.from_runnable_config(config)
    
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
    
    # 配置工具
    tools = [get_web_search_tool(configurable.max_search_results, configurable.search_engine, configurable.custom_search_repository)]
    retriever_tool = get_retriever_tool(state.get("resources", []))
    if retriever_tool:
        tools.insert(0, retriever_tool)
        enhanced_logger.logger.info(f"🔧 TOOLS_READY | 研究工具配置完成 | 工具数: {len(tools)} | 包含本地检索: 是")
    else:
        enhanced_logger.logger.info(f"🔧 TOOLS_READY | 研究工具配置完成 | 工具数: {len(tools)} | 包含本地检索: 否")
    
    logger.info(f"Researcher tools: {tools}")
    
    result = await _setup_and_execute_agent_step(
        state,
        config,
        "researcher",
        tools,
    )
    
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | researcher | 节点执行完成 | 总耗时: {duration:.2f}s")
    
    return result


async def coder_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Coder node that do code analysis."""
    logger.info("Coder node is coding.")
    return await _setup_and_execute_agent_step(
        state,
        config,
        "coder",
        [python_repl_tool],
    )

