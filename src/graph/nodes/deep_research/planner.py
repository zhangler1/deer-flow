# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
规划节点模块

包含：
- planner_node: 规划节点，生成研究计划
- human_feedback_node: 人工反馈节点，处理用户对计划的审核
"""

import json
import logging
import time
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt

from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.planner_model import Plan
from src.prompts.template import apply_prompt_template
from src.utils.enhanced_logger import get_enhanced_logger
from src.utils.json_utils import repair_json_output

from src.config import SELECTED_SEARCH_ENGINE, SearchEngine




logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.deep_research.planner')


async def planner_node(
    state, config: RunnableConfig
) -> Command[Literal["human_feedback", "reporter"]]:
    """生成完整计划的规划节点"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | planner | 开始执行计划生成节点")
    
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    enhanced_logger.log_plan_generation(plan_iterations + 1, state.get("research_topic", "未知"), 0)
    
    # ===== 详细输入日志 =====
    _existing_plan = state.get("current_plan")
    _existing_plan_info = "None"
    if _existing_plan:
        if isinstance(_existing_plan, str):
            _existing_plan_info = f"字符串(前100字={_existing_plan[:100]})"
        elif isinstance(_existing_plan, dict):
            _existing_plan_info = f"字典(title='{_existing_plan.get('title', 'N/A')}', steps={len(_existing_plan.get('steps', []))})"
        elif hasattr(_existing_plan, 'title') and hasattr(_existing_plan, 'steps'):
            _existing_plan_info = f"Plan对象(title='{_existing_plan.title}', steps={len(_existing_plan.steps)})"
    _state_messages = state.get("messages", [])
    _last_user_msg = ""
    for _m in reversed(_state_messages):
        _content = _m.get("content", "") if isinstance(_m, dict) else getattr(_m, "content", "")
        _role = _m.get("role", "") if isinstance(_m, dict) else getattr(_m, "type", "")
        if _role in ("user", "human"):
            _last_user_msg = str(_content)[:200]
            break
    enhanced_logger.logger.info(
        f"📥 PLANNER_STATE_INPUT | "
        f"research_topic='{state.get('research_topic', '')[:100]}' | "
        f"plan_iterations={plan_iterations} | "
        f"current_plan={_existing_plan_info} | "
        f"messages_count={len(_state_messages)} | "
        f"last_user_msg='{_last_user_msg}'"
    )
    
    messages = []
    try:
        messages = apply_prompt_template("planner", state, configurable)
    except Exception as e:
        enhanced_logger.logger.error(f"Failed to apply prompt template: {e}")
        messages = [HumanMessage(content=f"为以下主题制定计划：{state.get('research_topic', '未知主题')}")]

    if state.get("enable_background_investigation") and state.get(
        "background_investigation_results"
    ):
        # 当用户上传了文档时，背景调研仅作为补充参考，文档内容优先
        _has_doc = bool(state.get("document_summary"))
        _bg_prefix = (
            "以下是背景调研的补充信息（注意：用户已上传文档，请以文档内容为主，背景调研仅作参考）：\n"
            if _has_doc
            else "用户查询的背景调研结果：\n"
        )
        messages += [
            {
                "role": "user",
                "content": (
                    _bg_prefix
                    + state["background_investigation_results"]
                    + "\n"
                ),
            }
        ]

    if configurable.enable_deep_thinking:
        llm = get_llm_by_type("researcher")
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"])

    logger.debug(f"Planner input: {messages}")
    enhanced_logger.logger.info(f"📝 PLANNER_INPUT | 输入消息数: {len(messages)} | 背景调研: {'是' if state.get('enable_background_investigation') and state.get('background_investigation_results') else '否'}")

    # 超过最大计划迭代次数，直接进入 reporter
    if plan_iterations >= configurable.max_plan_iterations:
        enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → reporter | 原因: 超过最大计划迭代次数")
        return Command(goto="reporter")

    full_response = ""
    llm_start_time = time.time()
    if not configurable.enable_deep_thinking:
        response = await llm.ainvoke(messages)
        try:
            if hasattr(response, 'content'):
                full_response = str(response.content)
            else:
                full_response = str(response)
        except Exception:
            full_response = "Response conversion failed"
    else:
        async for chunk in llm.astream(messages):
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
    # ===== LLM 输出日志 =====
    _response_preview = full_response[:500] if len(full_response) > 500 else full_response
    enhanced_logger.logger.debug(
        f"📤 PLANNER_LLM_OUTPUT | "
        f"响应长度={len(full_response)} | "
        f"耗时={thinking_duration:.2f}s | "
        f"内容预览: {_response_preview}"
    )

    try:
        curr_plan = json.loads(repair_json_output(full_response))
        
        # 检查是否为嵌套的 {"plan": {...}} 格式
        if isinstance(curr_plan, dict) and 'plan' in curr_plan and isinstance(curr_plan['plan'], dict):
            enhanced_logger.logger.warning("⚠️ PLAN_FORMAT_ERROR | 检测到嵌套plan格式，提取内层对象")
            curr_plan = curr_plan['plan']
        
        # 修复缺失的 locale 字段
        if isinstance(curr_plan, dict) and 'locale' not in curr_plan:
            curr_plan['locale'] = state.get('locale', 'zh-CN')
            enhanced_logger.logger.warning(f"⚠️ PLAN_MISSING_LOCALE | 添加缺失的locale字段: {curr_plan['locale']}")
            
        # 修复缺失的 title 字段
        if isinstance(curr_plan, dict) and 'title' not in curr_plan:
            curr_plan['title'] = '智能研究计划'
            enhanced_logger.logger.warning(f"⚠️ PLAN_MISSING_TITLE | 添加缺失的title字段: {curr_plan['title']}")
        
        # 修复 steps 中缺失的 step_type 字段
        if isinstance(curr_plan, dict) and 'steps' in curr_plan and isinstance(curr_plan['steps'], list):
            for i, step in enumerate(curr_plan['steps']):
                if isinstance(step, dict) and 'step_type' not in step:
                    step['step_type'] = 'research'
                    enhanced_logger.logger.warning(f"⚠️ STEP_MISSING_TYPE | 为步骤#{i+1}添加缺失的step_type字段")
            
    except json.JSONDecodeError as e:
        logger.warning(f"Planner response is not a valid JSON: {str(e)}")
        enhanced_logger.logger.error(f"❌ JSON_DECODE_ERROR | JSON解析失败 | 错误: {str(e)}")
        enhanced_logger.logger.error(f"📄 INVALID_JSON_CONTENT | 无效的JSON内容 (前500字符): {full_response[:500]}")
        enhanced_logger.logger.debug(f"📄 FULL_RESPONSE | 完整响应内容: {full_response}")
        enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → reporter | 原因: JSON解析失败")
        return Command(goto="reporter")
    
    if isinstance(curr_plan, dict) and curr_plan.get("has_enough_context"):
        logger.info("Planner response has enough context.")
        
        if 'locale' not in curr_plan:
            curr_plan['locale'] = state.get('locale', 'zh-CN')
            enhanced_logger.logger.warning(f"⚠️ PLAN_MISSING_LOCALE | 添加缺失的locale字段: {curr_plan['locale']}")
        
        # 验证必需字段
        required_fields = ['has_enough_context', 'thought', 'title', 'steps']
        missing_fields = [field for field in required_fields if field not in curr_plan]
        if missing_fields:
            enhanced_logger.logger.error(f"❌ PLAN_MISSING_FIELDS | Plan缺少必需字段: {missing_fields}")
            logger.error(f"Plan missing required fields: {missing_fields}")
            return Command(goto="reporter")
        
        try:
            new_plan = Plan.model_validate(curr_plan)
            enhanced_logger.log_plan_generation(plan_iterations + 1, new_plan.title, len(new_plan.steps))
            
            has_unexecuted_steps = any(step.execution_res is None for step in new_plan.steps)
            
            if has_unexecuted_steps:
                enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → human_feedback | 原因: 计划包含未执行的步骤")
                duration = time.time() - start_time
                enhanced_logger.logger.info(f"✅ NODE_EXIT | planner | 节点执行完成 | 耗时: {duration:.2f}s")
                
                return Command(
                    update={
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
                        "current_plan": new_plan,
                    },
                    goto="reporter",
                )
        except Exception as e:
            enhanced_logger.logger.error(f"❌ PLAN_VALIDATION_ERROR | Plan验证失败: {str(e)}")
            logger.error(f"Plan validation failed: {e}")
            logger.debug(f"Failed plan data: {curr_plan}")
            return Command(goto="reporter")
    
    enhanced_logger.logger.info(f"🔀 NODE_TRANSITION | planner → human_feedback | 原因: 需要人工审核计划")
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | planner | 节点执行完成 | 耗时: {duration:.2f}s")
    
    return Command(
        update={
            "current_plan": full_response,
        },
        goto="human_feedback",
    )


def _serialize_current_plan(current_plan) -> str:
    """将 current_plan 序列化为可读字符串，供 LLM 消费"""
    if current_plan is None:
        return ""
    # Plan 对象
    if hasattr(current_plan, 'model_dump'):
        import json
        return json.dumps(current_plan.model_dump(), ensure_ascii=False, indent=2)
    # 字符串（可能是 JSON）
    if isinstance(current_plan, str):
        return current_plan
    # dict
    if isinstance(current_plan, dict):
        import json
        return json.dumps(current_plan, ensure_ascii=False, indent=2)
    return str(current_plan)


def human_feedback_node(
    state,
) -> Command[Literal["planner", "research_team", "reporter", "__end__"]]:
    """人工反馈节点 - 处理用户对研究计划的审核与修改"""
    current_plan = state.get("current_plan", "")
    # 检查是否自动接受计划
    auto_accepted_plan = state.get("auto_accepted_plan", False)
    if not auto_accepted_plan:
        feedback = interrupt("Please Review the Plan.")

        if feedback and str(feedback).upper().startswith("[EDIT_PLAN]"):
            # 提取用户的实际修改意见（去掉协议前缀）
            user_feedback = str(feedback)
            # 尝试提取 [edit_plan] 之后的用户输入
            import re
            match = re.match(r'\[edit_plan\]\s*(.*)', user_feedback, re.IGNORECASE | re.DOTALL)
            edit_instruction = match.group(1).strip() if match else user_feedback

            # 将当前计划和用户修改意见一起注入 messages，确保 planner 能感知
            plan_content = _serialize_current_plan(current_plan)
            feedback_content = (
                "用户要求修改研究计划，请根据以下修改意见调整计划。\n\n"
                f"【当前研究计划】\n{plan_content}\n\n"
                f"【用户修改意见】\n{edit_instruction}"
            )
            enhanced_logger.logger.info(f"📝 EDIT_PLAN_FEEDBACK | 用户修改意见: {edit_instruction[:100]}")

            return Command(
                update={
                    "messages": [
                        HumanMessage(content=feedback_content, name="feedback"),
                    ],
                },
                goto="planner",
            )
        elif feedback and str(feedback).upper().startswith("[ACCEPTED]"):
            logger.info("Plan is accepted by user.")
        else:
            raise TypeError(f"Interrupt value of {feedback} is not supported.")

    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    goto = "research_team"
    
    try:
        # 检查 current_plan 的类型
        if not isinstance(current_plan, (str, dict)) and hasattr(current_plan, 'title') and hasattr(current_plan, 'steps'):
            # current_plan 已经是 Plan 对象
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
        
        # current_plan 是字符串，需要解析
        current_plan = repair_json_output(current_plan)
        plan_iterations += 1
        new_plan = json.loads(current_plan)
        
        # 检查是否为嵌套的 {"plan": {...}} 格式
        if isinstance(new_plan, dict) and 'plan' in new_plan and isinstance(new_plan['plan'], dict):
            enhanced_logger.logger.warning("⚠️ PLAN_FORMAT_ERROR | 在human_feedback中检测到嵌套plan格式，提取内层对象")
            new_plan = new_plan['plan']
        
        # 修复缺失的 locale 字段
        if isinstance(new_plan, dict) and 'locale' not in new_plan:
            new_plan['locale'] = state.get('locale', 'zh-CN')
            enhanced_logger.logger.warning(f"⚠️ PLAN_MISSING_LOCALE | 在human_feedback中添加缺失的locale字段: {new_plan['locale']}")
        
        # 修复缺失的 title 字段
        if isinstance(new_plan, dict) and 'title' not in new_plan:
            new_plan['title'] = '智能研究计划'
            enhanced_logger.logger.warning(f"⚠️ PLAN_MISSING_TITLE | 在human_feedback中添加缺失的title字段")
        
        # 修复 steps 中缺失的 step_type 字段
        if isinstance(new_plan, dict) and 'steps' in new_plan and isinstance(new_plan['steps'], list):
            for i, step in enumerate(new_plan['steps']):
                if isinstance(step, dict) and 'step_type' not in step:
                    step['step_type'] = 'research'
                    enhanced_logger.logger.warning(f"⚠️ STEP_MISSING_TYPE | 在human_feedback中为步骤#{i+1}添加缺失的step_type字段")
        
        # 检查是否为工具调用格式
        if isinstance(new_plan, dict) and 'name' in new_plan and 'arguments' in new_plan:
            enhanced_logger.logger.warning(f"⚠️ PLAN_FORMAT_ERROR | 检测到工具调用格式而非Plan对象")
            logger.warning("Planner returned tool call format instead of Plan object")
            return Command(goto="planner")
            
        # 检查是否为 Step 列表而非完整 Plan
        if isinstance(new_plan, list):
            enhanced_logger.logger.warning("⚠️ PLAN_FORMAT_ERROR | 检测到Step列表而非完整Plan对象")
            logger.warning("Planner returned Step list instead of complete Plan object")
            return Command(goto="planner")
            
        # 验证必需字段
        required_fields = ['locale', 'has_enough_context', 'thought', 'title', 'steps']
        missing_fields = [field for field in required_fields if field not in new_plan]
        if missing_fields:
            enhanced_logger.logger.warning(f"⚠️ PLAN_FORMAT_ERROR | Plan对象缺少必需字段: {missing_fields}")
            logger.warning(f"Plan missing required fields: {missing_fields}")
            return Command(goto="planner")
            
    except json.JSONDecodeError as e:
        logger.warning(f"Planner response is not a valid JSON in human_feedback: {str(e)}")
        enhanced_logger.logger.error(f"❌ JSON_DECODE_ERROR | human_feedback节点JSON解析失败 | 错误: {str(e)}")
        enhanced_logger.logger.error(f"📄 INVALID_JSON_CONTENT | 无效的JSON内容 (前500字符): {str(current_plan)[:500]}")
        enhanced_logger.logger.debug(f"📄 FULL_CURRENT_PLAN | 完整current_plan内容: {current_plan}")
        if plan_iterations > 1:
            return Command(goto="reporter")
        else:
            return Command(goto="__end__")
    except Exception as e:
        enhanced_logger.logger.error(f"❌ PLAN_PARSE_ERROR | Plan解析失败: {str(e)}")
        logger.error(f"Error parsing plan: {e}")
        return Command(goto="planner")

    try:
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
        logger.debug(f"Failed plan data: {new_plan}")
        return Command(goto="planner")
