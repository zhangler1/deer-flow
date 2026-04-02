# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
协调节点模块

包含：
- coordinator_node: 协调节点，与用户沟通并决定处理路径
"""

import logging
import time
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.template import apply_prompt_template
from src.utils.enhanced_logger import get_enhanced_logger

# handoff_to_planner 从 utils 模块导入
from src.graph.nodes.utils import handoff_to_planner

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


logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.deep_research.coordinator')


def coordinator_node(
    state, config: RunnableConfig
) -> Command[Literal["planner", "background_investigator", "__end__"]]:
    """与客户沟通的协调节点"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | coordinator | 开始执行协调节点")
    
    logger.info("Coordinator talking.")
    configurable = Configuration.from_runnable_config(config)
    
    enhanced_logger.logger.info(f"📊 COORDINATOR_STATE | research_topic: {state.get('research_topic', 'Not set')}")
    enhanced_logger.logger.info(f"📊 COORDINATOR_STATE | locale: {state.get('locale', 'Not set')}")
    enhanced_logger.logger.info(f"📊 COORDINATOR_STATE | messages数量: {len(state.get('messages', []))}")
    
    try:
        messages = apply_prompt_template("coordinator", state, configurable)
        enhanced_logger.logger.info(f"📝 COORDINATOR_PROMPT | 提示模板应用成功 | 消息数: {len(messages)}")
    except Exception as e:
        enhanced_logger.logger.error(f"Failed to apply coordinator template: {e}")
        messages = [HumanMessage(content=f"协调请求：{state.get('research_topic', '未知请求')}")]
    
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
    
    enhanced_logger.logger.info(f"🤖 COORDINATOR_LLM_RESPONSE | LLM调用完成 | 耗时: {llm_duration:.2f}s")
    enhanced_logger.logger.info(f"📤 COORDINATOR_RESPONSE_TYPE | 响应类型: {type(response).__name__}")
    enhanced_logger.logger.info(f"📤 COORDINATOR_RESPONSE_CONTENT | 响应内容: {response.content if hasattr(response, 'content') else 'No content'}")
    
    logger.debug(f"Current state messages: {state['messages']}")

    goto = "__end__"
    locale = state.get("locale", "zh-CN")
    research_topic = state.get("research_topic", "")

    # 处理 tool_calls
    try:
        tool_calls = getattr(response, 'tool_calls', [])
        enhanced_logger.logger.info(f"🔧 COORDINATOR_TOOL_CALLS | 工具调用数量: {len(tool_calls)}")
        
        for i, tool_call in enumerate(tool_calls):
            enhanced_logger.logger.info(f"🔧 TOOL_CALL_{i+1} | 完整内容: {tool_call}")
            enhanced_logger.logger.info(f"  - name: {tool_call.get('name', 'N/A')}")
            enhanced_logger.logger.info(f"  - args: {tool_call.get('args', {})}")
        
        if len(tool_calls) > 0:
            goto = "planner"
            if state.get("enable_background_investigation"):
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
    
    # 只有当需要保存上下文时才添加到messages
    messages = state.get("messages", [])
    if response.content:
        messages.append(HumanMessage(content=response.content, name="coordinator"))
        enhanced_logger.logger.info(f"📝 ADDED_MESSAGE | 添加coordinator响应到消息列表")
    
    enhanced_logger.logger.info(f"🎯 COORDINATOR_FINAL_GOTO | 最终跳转目标: {goto}")
    enhanced_logger.logger.info(f"📊 COORDINATOR_FINAL_UPDATE | locale: {locale}, research_topic: {research_topic}")
    
    if response.content:
        enhanced_logger.logger.info(f"💬 COORDINATOR_RESPONSE | 协调者直接回复 | 内容长度: {len(response.content)}")
    
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
