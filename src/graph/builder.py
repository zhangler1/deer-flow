# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
import time
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.prompts.planner_model import StepType
from src.utils.enhanced_logger import get_enhanced_logger

from .nodes import (
    background_investigation_node,
    # 暂时注释掉 coder_node 的导入
    # coder_node,
    coordinator_node,
    human_feedback_node,
    planner_node,
    reporter_node,
    research_team_node,
    researcher_node,
    # 新增的智能路由节点（3种路径）
    router_node,
    direct_answer_node,
    simple_search_node,
    iterative_research_node,  # 新增：迭代研究节点
    iterative_reporter_node,  # 新增：迭代研究报告节点
)
from .types import State

enhanced_logger = get_enhanced_logger('graph.builder')


def continue_to_running_research_team(state: State):
    """决定从research_team节点跳转到哪个下一个节点"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔀 TRANSITION_LOGIC | research_team | 开始评估下一步跳转")
    
    current_plan = state.get("current_plan")
    
    # 处理current_plan可能是字符串或对象的情况
    if not current_plan:
        enhanced_logger.logger.info(f"🔀 TRANSITION_DECISION | research_team → planner | 原因: 无当前计划")
        return "planner"
        
    # 检查是否有steps属性
    if hasattr(current_plan, 'steps'):
        plan_steps = current_plan.steps
    elif isinstance(current_plan, dict) and 'steps' in current_plan:
        plan_steps = current_plan['steps']
    else:
        enhanced_logger.logger.info(f"🔀 TRANSITION_DECISION | research_team → planner | 原因: 计划格式错误或无步骤")
        return "planner"

    if not plan_steps:
        enhanced_logger.logger.info(f"🔀 TRANSITION_DECISION | research_team → planner | 原因: 无计划步骤")
        return "planner"

    # 检查所有步骤是否完成
    try:
        completed_steps = []
        incomplete_steps = []
        for step in plan_steps:
            step_res = getattr(step, 'execution_res', None)
            step_title = getattr(step, 'title', '未知步骤')
            if step_res:
                completed_steps.append(step_title)
            else:
                incomplete_steps.append(step_title)
        
        all_completed = len(incomplete_steps) == 0
        enhanced_logger.logger.info(f"📊 STEPS_STATUS | 总步骤数: {len(plan_steps)} | 已完成: {len(completed_steps)} | 未完成: {len(incomplete_steps)}")
        
        if completed_steps:
            enhanced_logger.logger.info(f"✅ COMPLETED_STEPS | {', '.join(completed_steps)}")
        if incomplete_steps:
            enhanced_logger.logger.info(f"⏳ INCOMPLETE_STEPS | {', '.join(incomplete_steps)}")
        
        if all_completed:
            enhanced_logger.logger.info(f"🔀 TRANSITION_DECISION | research_team → reporter | 原因: 所有步骤已完成，生成最终报告")
            duration = time.time() - start_time
            enhanced_logger.logger.info(f"⏱️ TRANSITION_TIME | research_team 跳转逻辑 | 耗时: {duration:.2f}s")
            return "reporter"
    except (AttributeError, TypeError) as e:
        enhanced_logger.logger.warning(f"无法检查步骤完成状态: {e}，默认返回planner")
        return "planner"

    # Find first incomplete step
    incomplete_step = None
    try:
        for step in plan_steps:
            if not getattr(step, 'execution_res', None):
                incomplete_step = step
                break
    except (AttributeError, TypeError):
        enhanced_logger.logger.warning("无法遍历计划步骤，返回planner")
        return "planner"

    if not incomplete_step:
        enhanced_logger.logger.info(f"🔀 TRANSITION_DECISION | research_team → planner | 原因: 未找到未完成步骤")
        return "planner"

    next_node = "planner"  # 默认值
    try:
        step_type = getattr(incomplete_step, 'step_type', None)
        step_title = getattr(incomplete_step, 'title', '未知步骤')
        
        if step_type == StepType.RESEARCH:
            next_node = "researcher"
            enhanced_logger.logger.info(f"🔀 TRANSITION_DECISION | research_team → researcher | 原因: 下一步是研究类型 | 步骤: '{step_title}'")
        # 暂时注释掉 coder 节点的路由
        # elif step_type == StepType.PROCESSING:
        #     next_node = "coder"
        #     enhanced_logger.logger.info(f"🔀 TRANSITION_DECISION | research_team → coder | 原因: 下一步是处理类型 | 步骤: '{step_title}'")
        elif step_type == StepType.PROCESSING:
            # 暂时跳过处理类型，直接回到 planner
            next_node = "planner"
            enhanced_logger.logger.info(f"🔀 TRANSITION_DECISION | research_team → planner | 原因: 处理类型暂时跳过（coder已注释） | 步骤: '{step_title}'")
        else:
            enhanced_logger.logger.info(f"🔀 TRANSITION_DECISION | research_team → planner | 原因: 未知步骤类型 | 类型: {step_type}")
    except (AttributeError, TypeError):
        enhanced_logger.logger.warning("无法获取步骤类型，默认返回planner")
    
    duration = time.time() - start_time
    enhanced_logger.logger.info(f"⏱️ TRANSITION_TIME | research_team 跳转逻辑 | 耗时: {duration:.2f}s")
    return next_node


def _build_base_graph():
    """Build and return the base state graph with all nodes and edges."""
    builder = StateGraph(State)
    
    # 起始节点改为router，实现智能路由
    builder.add_edge(START, "router")
    
    # 添加智能路由节点（入口节点）
    builder.add_node("router", router_node)
    
    # 添加3种路径的节点
    # 1. 直接回答节点（通用知识，不走检索）
    builder.add_node("direct_answer_node", direct_answer_node)
    
    # 2. 简单检索节点（主流路径，单次检索）
    builder.add_node("simple_search_node", simple_search_node)
    
    # 3. 迭代研究节点（单问题深挖，自主迭代）
    builder.add_node("iterative_research_node", iterative_research_node)
    builder.add_node("iterative_reporter_node", iterative_reporter_node)
    
    # 4. 深度研究路径（原有的复杂流程，通过coordinator进入）
    # coordinator 是深度研究的入口
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("background_investigator", background_investigation_node)
    builder.add_node("planner", planner_node)
    builder.add_node("reporter", reporter_node)
    builder.add_node("research_team", research_team_node)
    builder.add_node("researcher", researcher_node)
    # 暂时注释掉 coder 节点
    # builder.add_node("coder", coder_node)
    builder.add_node("human_feedback", human_feedback_node)
    
    # 深度研究路径的边（保持不变）
    builder.add_edge("background_investigator", "planner")
    builder.add_conditional_edges(
        "research_team",
        continue_to_running_research_team,
        # 添加 "reporter" 到条件边，当所有步骤完成时跳转
        ["planner", "researcher", "reporter"],
    )
    builder.add_edge("reporter", END)
    
    # 简单路径节点直接结束
    builder.add_edge("direct_answer_node", END)
    builder.add_edge("simple_search_node", END)
    # 迭代研究节点的跳转由节点内部控制，should_continue为false时才进入报告节点
    builder.add_edge("iterative_reporter_node", END)  # 迭代研究报告节点结束
    
    return builder


def build_graph_with_memory():
    """Build and return the agent workflow graph with memory."""
    # use persistent memory to save conversation history
    # TODO: be compatible with SQLite / PostgreSQL
    memory = MemorySaver()

    # build state graph
    builder = _build_base_graph()
    compiled_graph = builder.compile(checkpointer=memory)
    
    
    return compiled_graph


def build_graph():
    """Build and return the agent workflow graph without memory."""
    # build state graph
    builder = _build_base_graph()
    compiled_graph = builder.compile()
    
    
    return compiled_graph


graph = build_graph()
