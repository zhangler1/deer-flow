# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
节点工具函数模块

提供节点执行所需的辅助函数，包括：
- _execute_agent_step: Agent 设置 + 执行步骤（含 MCP 配置和 Agent 创建）
- handoff_to_planner: 移交给规划智能体的工具
"""

import asyncio
import logging
import os
import time
from typing import Annotated, Any, Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.types import Command

from src.agents import create_agent
from src.config.configuration import Configuration
from src.graph.cancellation import get_from_config as _get_cancel_event
from src.graph.types import State
from src.utils.enhanced_logger import get_enhanced_logger
from src.utils.text_utils import remove_think_tags

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.utils')


@tool
def handoff_to_planner(
    research_topic: Annotated[str, "要移交的研究任务主题"],
    locale: Annotated[str, "用户检测到的语言区域设置（例如：en-US, zh-CN）"],
):
    """移交给规划智能体进行计划制定"""
    return


# ─── 内部辅助函数 ───────────────────────────────────────────────────────────


def _get_plan_steps(current_plan):
    """从计划对象中提取步骤列表"""
    if hasattr(current_plan, 'steps'):
        return current_plan.steps
    if isinstance(current_plan, dict) and 'steps' in current_plan:
        return current_plan['steps']
    return None


async def _load_mcp_tools(agent_type: str, default_tools: list, configurable) -> list:
    """加载 MCP 工具并与默认工具合并，无 MCP 配置时直接返回默认工具"""
    if not configurable.mcp_settings:
        return default_tools

    mcp_servers = {}
    enabled_tools = {}
    for server_name, server_config in configurable.mcp_settings["servers"].items():
        if server_config["enabled_tools"] and agent_type in server_config["add_to_agents"]:
            mcp_servers[server_name] = {
                k: v for k, v in server_config.items()
                if k in ("transport", "command", "args", "url", "env", "headers")
            }
            for tool_name in server_config["enabled_tools"]:
                enabled_tools[tool_name] = server_name

    if not mcp_servers:
        return default_tools

    client = MultiServerMCPClient(mcp_servers)
    loaded_tools = default_tools[:]
    for t in await client.get_tools():
        if t.name in enabled_tools:
            t.description = f"Powered by '{enabled_tools[t.name]}'.\n{t.description}"
            loaded_tools.append(t)

    enhanced_logger.logger.info(
        f"🔌 MCP_TOOLS | {agent_type} | 加载完成 | 总工具数: {len(loaded_tools)}"
    )
    return loaded_tools


def _build_cancel_command(agent_name, current_step, plan_steps, observations):
    """构建用户取消时的 Command，标记所有未完成步骤"""
    for step in plan_steps:
        if not step.execution_res:
            step.execution_res = "[用户取消]"
    return Command(
        update={
            "messages": [HumanMessage(content=f"⛔ 步骤 '{current_step.title}' 被用户取消", name=agent_name)],
            "observations": observations + ["[研究被用户取消]"],
            "current_step_index": len(plan_steps) - 1,
            "current_step_title": current_step.title,
            "next_step_index": -1,
            "next_step_title": "",
        },
        goto="research_team",
    )


def _build_skip_command(agent_name, current_step, completed_steps, plan_steps, observations, reason):
    """构建步骤跳过时的 Command"""
    next_idx = len(completed_steps) + 1
    has_next = next_idx < len(plan_steps)
    return Command(
        update={
            "messages": [HumanMessage(content=f"⚠️ 步骤 '{current_step.title}' {reason}", name=agent_name)],
            "observations": observations + [current_step.execution_res],
            "current_step_index": len(completed_steps),
            "current_step_title": current_step.title,
            "next_step_index": next_idx if has_next else -1,
            "next_step_title": plan_steps[next_idx].title if has_next else "",
        },
        goto="research_team",
    )


async def _silently_cancel(t):
    """静默取消一个 asyncio.Task"""
    if t is None or t.done():
        return
    t.cancel()
    try:
        await t
    except (asyncio.CancelledError, Exception):
        pass


# ─── 核心执行函数 ───────────────────────────────────────────────────────────


async def _execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list,
    recursion_limit: int = 10,
) -> Command[Literal["research_team"]]:
    """设置智能体并执行当前研究步骤

    包含 Agent 创建（含 MCP 配置）和步骤执行逻辑：
    1. 从 config 提取取消信号
    2. 加载 MCP 工具并创建 Agent
    3. 执行 Agent（支持超时、取消、心跳监控）
    4. 处理结果并返回 Command

    Args:
        state: 当前状态
        config: RunnableConfig
        agent_type: 智能体类型（"researcher" / "coder"）
        default_tools: 默认工具列表
        recursion_limit: 每步搜索工具调用预算

    Returns:
        Command 对象，用于更新状态并转到 research_team
    """
    step_start_time = time.time()
    enhanced_logger.logger.info(f"🔄 AGENT_STEP | {agent_type} | 开始执行 | 搜索预算: {recursion_limit}")

    # ─── 1. 提取取消信号 ───
    cancel_event = _get_cancel_event(config)

    # ─── 2. 解析计划和当前步骤 ───
    current_plan = state.get("current_plan")
    plan_title = current_plan.title
    observations = state.get("observations", [])

    plan_steps = _get_plan_steps(current_plan)
    if plan_steps is None:
        logger.warning("在当前计划中未找到步骤")
        return Command(goto="research_team")

    current_step = None
    completed_steps = []
    for step in plan_steps:
        if not step.execution_res:
            current_step = step
            break
        else:
            completed_steps.append(step)

    if not current_step:
        logger.warning("未找到未执行的步骤")
        return Command(goto="research_team")

    # ─── 3. 取消信号检查 ───
    if cancel_event and cancel_event.is_set():
        enhanced_logger.logger.info(f"⛔ CANCELLED | {agent_type} | 客户端已断连")
        return _build_cancel_command(agent_type, current_step, plan_steps, observations)

    enhanced_logger.logger.info(f"🎯 STEP | {agent_type} | 执行: {current_step.title}")

    # ─── 4. 创建 Agent（含 MCP 工具加载）───
    configurable = Configuration.from_runnable_config(config)
    tools = await _load_mcp_tools(agent_type, default_tools, configurable)
    agent = create_agent(agent_type, agent_type, tools, agent_type, configurable)

    # ─── 5. 准备输入消息 ───
    agent_input = {
        "messages": [
            HumanMessage(
                content=(
                    f"# 研究主题\n\n{plan_title}\n\n"
                    f"# 当前步骤\n\n## 标题\n\n{current_step.title}\n\n"
                    f"## 描述\n\n{current_step.description}\n\n"
                    f"## 语言区域\n\n{state.get('locale', 'zh-CN')}"
                )
            )
        ]
    }
    if agent_type == "researcher":
        agent_input["messages"].append(
            HumanMessage(
                content=(
                    "重要提示：不要在正文中包含内联引用。而是跟踪所有来源，"
                    "并在末尾使用链接引用格式包含参考文献部分。在每个引用之间包含一个空行以提高可读性。"
                    "每个引用使用以下格式：\n- [来源标题](URL)\n\n- [另一个来源](URL)"
                ),
                name="system",
            )
        )

    # ─── 6. 执行 Agent（超时 + 取消 + 心跳）───
    try:
        step_timeout = float(os.getenv("AGENT_STEP_TIMEOUT", "900"))
    except ValueError:
        step_timeout = 900.0

    agent_exec_start = time.time()
    enhanced_logger.logger.info(f"⏳ INVOKING | {agent_type} | 超时: {step_timeout:.0f}s")

    async def _heartbeat():
        while True:
            await asyncio.sleep(30)
            enhanced_logger.logger.info(
                f"💓 HEARTBEAT | {agent_type} | 已耗时: {time.time() - agent_exec_start:.1f}s / {step_timeout:.0f}s"
            )

    heartbeat_task = None
    try:
        heartbeat_task = asyncio.create_task(_heartbeat())
        agent_task = asyncio.create_task(agent.ainvoke(input=agent_input, config={}))

        wait_set = {agent_task}
        cancel_wait_task = None
        if cancel_event is not None:
            cancel_wait_task = asyncio.create_task(cancel_event.wait())
            wait_set.add(cancel_wait_task)

        done, _ = await asyncio.wait(wait_set, timeout=step_timeout, return_when=asyncio.FIRST_COMPLETED)

        # 分支 1：用户取消
        if cancel_wait_task is not None and cancel_wait_task in done:
            await _silently_cancel(agent_task)
            enhanced_logger.logger.info(f"⛔ CANCELLED_MID | {agent_type} | 耗时: {time.time() - agent_exec_start:.2f}s")
            return _build_cancel_command(agent_type, current_step, plan_steps, observations)

        # 分支 2：超时
        if agent_task not in done:
            await _silently_cancel(agent_task)
            await _silently_cancel(cancel_wait_task)
            raise asyncio.TimeoutError()

        # 分支 3：正常完成
        await _silently_cancel(cancel_wait_task)
        result = agent_task.result()
        enhanced_logger.logger.info(f"✅ INVOKED | {agent_type} | 耗时: {time.time() - agent_exec_start:.2f}s")

    except asyncio.TimeoutError:
        enhanced_logger.logger.warning(f"⏰ TIMEOUT | {agent_type} | 超过 {step_timeout:.0f}s")
        current_step.execution_res = f"⚠️ 由于执行超时({step_timeout:.0f}s)，此步骤被跳过。"
        return _build_skip_command(
            agent_type, current_step, completed_steps, plan_steps, observations,
            f"由于执行超时({step_timeout:.0f}s)被跳过",
        )

    except Exception as e:
        # 网络异常 - 跳过当前步骤继续执行
        import httpcore
        if isinstance(e, (httpcore.RemoteProtocolError, httpcore.ConnectError, httpcore.ReadTimeout)):
            enhanced_logger.logger.warning(f"⚠️ NETWORK_ERROR | {agent_type} | {type(e).__name__}: {e}")
            current_step.execution_res = f"⚠️ 由于网络连接异常，此步骤被跳过。错误信息: {str(e)[:200]}"
            return _build_skip_command(
                agent_type, current_step, completed_steps, plan_steps, observations,
                "由于网络异常被跳过",
            )
        enhanced_logger.logger.error(f"❌ ERROR | {agent_type} | {type(e).__name__}: {e}")
        raise

    finally:
        if heartbeat_task is not None and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except BaseException:
                pass

    # ─── 7. 处理结果 ───
    response_content = result["messages"][-1].content
    if not response_content or not str(response_content).strip():
        response_content = "（步骤已完成，工具调用未产生文本响应）"
    if response_content and '<think>' in response_content.lower():
        response_content = remove_think_tags(response_content)

    current_step.execution_res = response_content
    next_idx = len(completed_steps) + 1
    has_next = next_idx < len(plan_steps)

    step_duration = time.time() - step_start_time
    enhanced_logger.logger.info(f"✅ STEP_DONE | {agent_type} | '{current_step.title}' | 耗时: {step_duration:.2f}s")

    return Command(
        update={
            "messages": [HumanMessage(content=response_content, name=agent_type)],
            "observations": observations + [response_content],
            "current_step_index": len(completed_steps),
            "current_step_title": current_step.title,
            "next_step_index": next_idx if has_next else -1,
            "next_step_title": plan_steps[next_idx].title if has_next else "",
        },
        goto="research_team",
    )
