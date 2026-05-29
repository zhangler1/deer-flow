# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
协调节点模块

包含：
- coordinator_node: 协调节点，与用户沟通并决定处理路径
"""

import json
import logging
import time
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.template import apply_prompt_template
from src.utils.enhanced_logger import get_enhanced_logger

# handoff_to_planner 从 utils 模块导入
from src.graph.nodes.utils import handoff_to_planner




logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.deep_research.coordinator')


# ---------------------------------------------------------------------------
# 辅助：让 LLM 判断是否为全新话题（需要重置已有研究状态）
# ---------------------------------------------------------------------------

_RESET_JUDGE_PROMPT = """你是一个智能助手。请判断用户的新输入与之前已完成的研究报告主题之间的关系。

## 之前的研究主题
{old_topic}

## 用户的新输入
{new_input}

## 判断规则
- 如果新输入是一个**全新的研究话题**（与之前的主题无关），返回 {"reset": true}
- 如果新输入是对已有报告的**追问、修改、深入**（基于同一主题），返回 {"reset": false}

只返回 JSON，不要解释。"""


async def _should_reset_state(state: dict) -> bool:
    """判断是否需要重置上一轮研究状态。

    条件：final_report 非空（上一轮已完成）且 LLM 判定新输入为全新话题。
    如果 LLM 调用失败，保守策略：默认重置（避免状态污染）。
    """
    final_report = state.get("final_report", "")
    if not final_report:
        return False  # 尚无已完成的报告，无需重置

    old_topic = state.get("research_topic", "")
    # 取最后一条用户消息作为新输入
    messages = state.get("messages", [])
    new_input = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            new_input = msg.get("content", "")
            break
        elif hasattr(msg, "type") and msg.type == "human":
            new_input = msg.content
            break

    if not new_input:
        return True  # 无法获取新输入，保守重置

    enhanced_logger.logger.info(
        f"🔍 RESET_JUDGE | 检测到上一轮已完成报告，启动 LLM 判断 | "
        f"old_topic='{old_topic[:50]}' | new_input='{new_input[:50]}'"
    )

    try:
        judge_llm = get_llm_by_type(AGENT_LLM_MAP["coordinator"])
        prompt = _RESET_JUDGE_PROMPT.format(
            old_topic=old_topic[:200],
            new_input=new_input[:500],
        )
        resp = await judge_llm.ainvoke([SystemMessage(content=prompt)])
        content = resp.content.strip()
        # 容忍 markdown 代码块
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        result = json.loads(content)
        should_reset = result.get("reset", True)
        enhanced_logger.logger.info(
            f"🔍 RESET_JUDGE_RESULT | LLM 判断: reset={should_reset} | 原始响应: {content[:50]}"
        )
        return bool(should_reset)
    except Exception as e:
        enhanced_logger.logger.warning(
            f"⚠️ RESET_JUDGE_FAILED | LLM判断失败，保守重置 | error={e}"
        )
        return True  # 保守策略：默认重置


async def coordinator_node(
    state, config: RunnableConfig
) -> Command[Literal["planner", "background_investigator", "clarification", "__end__"]]:
    """与客户沟通的协调节点"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | coordinator | 开始执行协调节点")
    
    # logger.info("Coordinator talking.")
    configurable = Configuration.from_runnable_config(config)

    # ------------------------------------------------------------------
    # 智能状态重置：如果上一轮已生成报告，让 LLM 判断是否为新话题
    # ------------------------------------------------------------------
    state_reset_fields = {}
    if await _should_reset_state(state):
        enhanced_logger.logger.info(
            "🔄 STATE_RESET | 判定为全新话题，重置 observations / current_plan / final_report"
        )
        state_reset_fields = {
            "observations": [],
            "current_plan": None,
            "final_report": "",
            "plan_iterations": 0,
            "current_step_index": -1,
            "current_step_title": "",
            "next_step_index": -1,
            "next_step_title": "",
            "background_investigation_results": None,
        }
    else:
        if state.get("final_report"):
            enhanced_logger.logger.info(
                "🔄 STATE_KEEP | 判定为追问/修改，保留已有研究状态"
            )
    # ------------------------------------------------------------------
    
    enhanced_logger.logger.info(f"📊 COORDINATOR_STATE | research_topic: {state.get('research_topic', 'Not set')}")
    enhanced_logger.logger.debug(f"📊 COORDINATOR_STATE | locale: {state.get('locale', 'Not set')}")
    enhanced_logger.logger.debug(f"📊 COORDINATOR_STATE | messages数量: {len(state.get('messages', []))}")
    
    try:
        messages = apply_prompt_template("coordinator", state, configurable)
        enhanced_logger.logger.debug(f"📝 COORDINATOR_PROMPT | 提示模板应用成功 | 消息数: {len(messages)}")
    except Exception as e:
        enhanced_logger.logger.error(f"Failed to apply coordinator template: {e}")
        messages = [HumanMessage(content=f"协调请求：{state.get('research_topic', '未知请求')}")]
    
    enhanced_logger.logger.debug(f"🤖 COORDINATOR_LLM_INPUT | 准备调用LLM | 输入消息数: {len(messages)}")
    for i, msg in enumerate(messages):
        msg_preview = str(msg)[:200] + "..." if len(str(msg)) > 200 else str(msg)
        enhanced_logger.logger.info(f"  消息{i+1}: {msg_preview}")
    
    llm_start_time = time.time()
    full_response = None
    async for chunk in (
        get_llm_by_type(AGENT_LLM_MAP["coordinator"])
        .bind_tools([handoff_to_planner])
        .astream(messages)
    ):
        if full_response is None:
            full_response = chunk
        else:
            full_response = full_response + chunk
    response = full_response
    llm_duration = time.time() - llm_start_time
    
    enhanced_logger.logger.info(f"🤖 COORDINATOR_LLM_RESPONSE | LLM调用完成 | 耗时: {llm_duration:.2f}s")
    enhanced_logger.logger.debug(f"📤 COORDINATOR_RESPONSE_TYPE | 响应类型: {type(response).__name__}")
    enhanced_logger.logger.info(f"📤 COORDINATOR_RESPONSE_CONTENT | 响应内容: {response.content[:100] if hasattr(response, 'content') else 'No content'}")
    
    logger.debug(f"Current state messages: {state['messages']}")

    goto = "__end__"
    locale = state.get("locale", "zh-CN")
    research_topic = state.get("research_topic", "")

    # 处理 tool_calls
    try:
        tool_calls = getattr(response, 'tool_calls', [])
        enhanced_logger.logger.debug(f"🔧 COORDINATOR_TOOL_CALLS | 工具调用数量: {len(tool_calls)}")
        
        for i, tool_call in enumerate(tool_calls):
            enhanced_logger.logger.debug(f"🔧 TOOL_CALL_{i+1} | 完整内容: {tool_call}")
            enhanced_logger.logger.debug(f"  - name: {tool_call.get('name', 'N/A')}")
            enhanced_logger.logger.debug(f"  - args: {tool_call.get('args', {})}")
        
        if len(tool_calls) > 0:
            goto = "planner"
            if state.get("enable_background_investigation"):
                goto = "background_investigator"
                enhanced_logger.logger.debug(f"🔀 COORDINATOR_GOTO | 启用背景调研，跳转到: {goto}")
            else:
                enhanced_logger.logger.debug(f"🔀 COORDINATOR_GOTO | 直接跳转到: {goto}")
            
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
                        enhanced_logger.logger.debug(f"📝 EXTRACTED_INFO | locale: {locale}, research_topic: {research_topic}")
                        break
            except Exception as e:
                logger.error(f"Error processing tool calls: {e}")
                enhanced_logger.logger.error(f"❌ TOOL_CALL_ERROR | 处理工具调用失败: {str(e)}")
        else:
            # 无工具调用：判断是否需要澄清
            if response.content and "[NEED_CLARIFICATION]" in response.content:
                # 检查澄清轮次是否已达上限（3 轮）
                clarification_rounds = state.get("clarification_rounds", 0)
                if clarification_rounds >= 3:
                    # 超过 3 轮，强制进入 planner，不再澄清
                    goto = "planner"
                    if state.get("enable_background_investigation"):
                        goto = "background_investigator"
                    enhanced_logger.logger.info(
                        f"⚠️ CLARIFICATION_LIMIT_REACHED | 澄清已达{clarification_rounds}轮上限，强制进入 {goto}"
                    )
                else:
                    goto = "clarification"
                    enhanced_logger.logger.info(f"❓ NEED_CLARIFICATION | Coordinator判定问题需要澄清，进入澄清节点 (第{clarification_rounds + 1}轮)")
            else:
                logger.warning(
                    "Coordinator response contains no tool calls. Terminating workflow execution."
                )
                enhanced_logger.logger.warning(f"⚠️ NO_TOOL_CALLS | Coordinator未返回工具调用，将终止工作流")
            enhanced_logger.logger.debug(f"📤 FULL_RESPONSE | {response}")
    except Exception as e:
        logger.error(f"Error accessing tool_calls: {e}")
        enhanced_logger.logger.error(f"❌ TOOL_CALLS_ACCESS_ERROR | 访问tool_calls属性失败: {str(e)}")
    
    # 只有当需要保存上下文时才添加到messages
    # 注意：必须复用 response.id，否则后端去重逻辑无法匹配
    # （LangGraph 流式发出的 chunk 用的是 response.id，手动创建的 AIMessage 如果用新 ID 就会绕过去重）
    messages = state.get("messages", [])
    if response.content:
        messages.append(AIMessage(content=response.content, name="coordinator", id=response.id))
        enhanced_logger.logger.info(f"📝 ADDED_MESSAGE | 添加coordinator响应到消息列表 | id={response.id}")
    
    enhanced_logger.logger.info(f"🎯 COORDINATOR_FINAL_GOTO | 最终跳转目标: {goto}")
    enhanced_logger.logger.debug(f"📊 COORDINATOR_FINAL_UPDATE | locale: {locale}, research_topic: {research_topic}")
    
    if response.content:
        enhanced_logger.logger.debug(f"💬 COORDINATOR_RESPONSE | 协调者直接回复 | 内容长度: {len(response.content)}")
    
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | coordinator | 节点执行完成 | 总耗时: {duration:.2f}s")
    
    return Command(
        update={
            **state_reset_fields,
            "messages": messages,
            "locale": locale,
            "research_topic": research_topic,
            "resources": configurable.resources,
        },
        goto=goto,
    )
