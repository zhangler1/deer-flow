# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
节点工具函数模块

提供节点执行所需的辅助函数，包括：
- Agent 执行步骤
- Agent 设置和配置
- 工具函数（handoff_to_planner）
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
from src.graph.tool_limit_middleware import ToolCallLimitMiddleware
from src.middlewares.tool_result_compression import ToolResultCompressionMiddleware
from src.graph.types import State
from src.utils.enhanced_logger import get_enhanced_logger
from src.utils.text_utils import remove_think_tags
from src.utils.search_budget import SearchBudgetManager

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.utils')


def _load_search_budget_config() -> dict:
    """从当前激活的 yaml (conf.yaml / conf.internal.yaml) 加载 SEARCH_BUDGET 段。

    未配置或解析失败时返回空 dict，由调用处用默认值兄底。
    使用 lazy import 避免循环依赖。
    """
    try:
        from src.llms.llm import _get_config_file_path
        from src.config import load_yaml_config
        return load_yaml_config(_get_config_file_path()).get("SEARCH_BUDGET", {}) or {}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"读取 SEARCH_BUDGET 配置失败，将使用默认值: {e}")
        return {}


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@tool
def handoff_to_planner(
    research_topic: Annotated[str, "要移交的研究任务主题"],
    locale: Annotated[str, "用户检测到的语言区域设置（例如：en-US, zh-CN）"],
):
    """移交给规划智能体进行计划制定"""
    # 此工具不返回任何内容：我们只是用它作为LLM信号表示需要移交给规划智能体
    return


async def _execute_agent_step(
    state: State, agent: Any, agent_name: str, recursion_limit: int = 10,
    cancel_event=None,
) -> Command[Literal["research_team"]]:
    """使用指定智能体执行步骤的辅助函数
    
    Args:
        state: 当前状态
        agent: 智能体实例
        agent_name: 智能体名称
        recursion_limit: 递归限制
        cancel_event: 可选的 asyncio.Event，客户端断连时被 set
        
    Returns:
        Command 对象，用于更新状态并转到 research_team
    """
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

    # ─── 取消信号检查：如果客户端已断连，标记所有剩余 step 为 cancelled ───
    if cancel_event and cancel_event.is_set():
        enhanced_logger.logger.info(
            f"⛔ STEP_CANCELLED | {agent_name} | 客户端已断连，跳过剩余步骤"
        )
        # 标记所有未完成步骤为 cancelled，使路由函数认为全部完成 → 进入 reporter
        for step in plan_steps:
            if not step.execution_res:
                step.execution_res = "[用户取消]"
        return Command(
            update={
                "observations": observations + ["[研究被用户取消]"],
                "current_step_index": len(plan_steps) - 1,
                "current_step_title": current_step.title,
                "next_step_index": -1,
                "next_step_title": "",
            },
            goto="research_team",
        )
    # ─────────────────────────────────────────────────────────────────────

    enhanced_logger.logger.info(f"🎯 STEP_SELECTED | {agent_name} | 正在执行: {current_step.title}")
    logger.info(f"Executing step: {current_step.title}, agent: {agent_name}")

    # 格式化已完成步骤信息
    completed_steps_info = ""

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
        agent_input["messages"].append(
            HumanMessage(
                content="重要提示：不要在正文中包含内联引用。而是跟踪所有来源，并在末尾使用链接引用格式包含参考文献部分。在每个引用之间包含一个空行以提高可读性。每个引用使用以下格式：\n- [来源标题](URL)\n\n- [另一个来源](URL)",
                name="system",
            )
        )

    # 🔥 核心：使用中间件检查工具调用次数和压缩工具结果
    soft_limit = recursion_limit
    hard_limit = max(soft_limit * 10, 50)

    # 初始化搜索预算管理器（用于更精细的预算控制）
    # 参数优先从 yaml 的 SEARCH_BUDGET 段读取（随 LLM_NETWORK 切换同步），
    # 缺失时回落到历史硬编码默认值，保持向后兼容。
    # 可以在state中持久化budget_manager以跨步骤跟踪
    _budget_conf = _load_search_budget_config()
    budget_manager = SearchBudgetManager(
        max_search_calls=_safe_int(_budget_conf.get("max_search_calls"), soft_limit),
        max_tokens=_safe_int(_budget_conf.get("max_tokens"), 10000),
        hard_token_limit=_safe_int(_budget_conf.get("hard_token_limit"), 14000),
        token_chars_ratio=_safe_float(_budget_conf.get("token_chars_ratio"), 2.5),
    )

    # 1. 工具调用限制中间件
    tool_limit_middleware = ToolCallLimitMiddleware(max_calls=soft_limit)
    
    # 2. 工具结果压缩中间件（只对 researcher 启用）
    tool_compression_middleware = None
    compression_llm = None
    if agent_name == "researcher":
        # 获取用于压缩的 LLM（使用 BASIC_MODEL）
        from src.llms.llm import get_llm_by_type
        try:
            compression_llm = get_llm_by_type("basic")
        except Exception as e:
            logger.warning(f"⚠️ 无法获取压缩用 LLM: {e}")
        
        tool_compression_middleware = ToolResultCompressionMiddleware(llm=compression_llm)
        enhanced_logger.logger.info(f"🗜️  COMPRESSION_ENABLED | {agent_name} | 工具结果压缩中间件已启用 | 模式: {tool_compression_middleware.config.mode}")

    # 检查 state 中的消息
    state_messages = state.get("messages", [])
    tool_call_count = tool_limit_middleware.count_tool_calls_in_messages(state_messages)

    # 使用预算管理器检查状态
    budget_status = budget_manager.get_budget_status(state_messages)
    budget_info = budget_manager.get_remaining_budget(state_messages)

    enhanced_logger.logger.info(
        f"📊 TOOL_CALL_COUNT | {agent_name} | 当前工具调用: {tool_call_count} | "
        f"软限制(建议): {soft_limit} | 硬限制(LangGraph): {hard_limit}"
    )
    enhanced_logger.logger.info(
        f"📊 BUDGET_STATUS | {agent_name} | "
        f"搜索: {budget_info['search_calls_used']}/{soft_limit} | "
        f"Tokens: {budget_info['estimated_tokens']}/{budget_manager.config.max_tokens} | "
        f"警告级别: {budget_info['warning_level']} | "
        f"可搜索: {budget_info['remaining_search_calls'] > 0}"
    )

    # 如果工具调用次数已经接近软限制（>= 80%），在输入中插入提示消息
    if tool_call_count >= int(soft_limit * 0.8):
        enhanced_logger.logger.warning(
            f"⚠️  TOOL_LIMIT_WARNING | {agent_name} | 工具调用 {tool_call_count}/{soft_limit} | "
            f"已达到建议限制的 80%，将在输入中插入停止建议"
        )

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

        agent_input["messages"].append(stop_advice_msg)
        enhanced_logger.logger.info(f"✅ STOP_ADVICE_ADDED | 已在输入中添加停止建议消息")

    actual_recursion_limit = hard_limit

    enhanced_logger.logger.info(
        f"🎛️  RECURSION_LIMIT | {agent_name} | LangGraph递归限制: {actual_recursion_limit} 次 | "
        f"软限制(建议): {soft_limit} 次"
    )
    logger.info(f"Agent input: {agent_input}")

    # 记录Agent执行过程
    agent_exec_start_time = time.time()
    # 整步超时（秒），默认 900s，可通过 AGENT_STEP_TIMEOUT 环境变量覆盖
    try:
        step_timeout = float(os.getenv("AGENT_STEP_TIMEOUT", "900"))
    except ValueError:
        step_timeout = 900.0
    enhanced_logger.logger.info(
        f"⏳ AGENT_INVOKING | {agent_name} | 正在调用LLM... | 递归限制: {actual_recursion_limit} | "
        f"超时阈值: {step_timeout:.0f}s | 开始时间: {time.strftime('%H:%M:%S')}"
    )

    # 添加定期心跳日志的异步任务
    async def log_agent_progress():
        """在agent执行期间定期输出进度日志"""
        progress_interval = 30  # 每30秒输出一次进度
        while True:
            await asyncio.sleep(progress_interval)
            current_duration = time.time() - agent_exec_start_time
            enhanced_logger.logger.info(
                f"💓 AGENT_HEARTBEAT | {agent_name} | Agent仍在执行中... | "
                f"已耗时: {current_duration:.1f}s / 超时: {step_timeout:.0f}s | 时间: {time.strftime('%H:%M:%S')}"
            )

    try:
        # 应用工具结果压缩（如果启用，使用异步版本支持 summarize 模式）
        if tool_compression_middleware is not None:
            original_msg_count = len(agent_input["messages"])
            # 使用异步版本，支持 summarize 模式
            compressed_messages = await tool_compression_middleware.process_messages_before_invoke_async(
                agent_input["messages"]
            )
            
            if compressed_messages != agent_input["messages"]:
                agent_input["messages"] = compressed_messages
                enhanced_logger.logger.info(
                    f"🔄 COMPRESSION_APPLIED | {agent_name} | "
                    f"消息列表已压缩 | 原始: {original_msg_count} 条 → 压缩后: {len(compressed_messages)} 条 | "
                    f"模式: {tool_compression_middleware.config.mode}"
                )
        
        # 启动心跳任务
        heartbeat_task = asyncio.create_task(log_agent_progress())

        # 整步超时兜底：超时后取消 agent 任务，走 skip_step 分支
        result = await asyncio.wait_for(
            agent.ainvoke(
                input=agent_input, config={"recursion_limit": actual_recursion_limit}
            ),
            timeout=step_timeout,
        )

        # 取消心跳任务
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        agent_exec_duration = time.time() - agent_exec_start_time
        enhanced_logger.logger.info(f"✅ AGENT_INVOKED | {agent_name} | LLM调用成功完成 | 耗时: {agent_exec_duration:.2f}s | 结束时间: {time.strftime('%H:%M:%S')}")

    except asyncio.TimeoutError:
        # 取消心跳任务
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        agent_exec_duration = time.time() - agent_exec_start_time
        enhanced_logger.logger.warning(
            f"⏰ AGENT_TIMEOUT | {agent_name} | 超过 {step_timeout:.0f}s 阈值，跳过当前步骤 | "
            f"已耗时: {agent_exec_duration:.2f}s | 时间: {time.strftime('%H:%M:%S')}"
        )
        logger.warning(
            f"Agent {agent_name} 执行超时({step_timeout:.0f}s)，跳过步骤 '{current_step.title}'"
        )

        # 标记当前步骤为因超时跳过
        current_step.execution_res = f"⚠️ 由于执行超时({step_timeout:.0f}s)，此步骤被跳过。"

        step_duration = time.time() - step_start_time
        enhanced_logger.logger.info(
            f"⏭️  STEP_SKIPPED | {agent_name} | 步骤因超时跳过，继续下一步 | 总耗时: {step_duration:.2f}s"
        )

        return Command(
            update={
                "messages": [
                    HumanMessage(
                        content=f"⚠️ 步骤 '{current_step.title}' 由于执行超时({step_timeout:.0f}s)被跳过",
                        name=agent_name,
                    )
                ],
                "observations": observations + [current_step.execution_res],
                "current_step_index": len(completed_steps),
                "current_step_title": current_step.title,
                "next_step_index": (
                    len(completed_steps) + 1
                    if len(completed_steps) + 1 < len(plan_steps)
                    else -1
                ),
                "next_step_title": (
                    plan_steps[len(completed_steps) + 1].title
                    if len(completed_steps) + 1 < len(plan_steps)
                    else ""
                ),
            },
            goto="research_team",
        )

    except Exception as e:
        # 取消心跳任务
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        agent_exec_duration = time.time() - agent_exec_start_time
        
        # 🔥 处理网络连接异常 - 跳过当前节点继续执行
        import httpcore
        if isinstance(e, (httpcore.RemoteProtocolError, httpcore.ConnectError, httpcore.ReadTimeout)):
            enhanced_logger.logger.warning(
                f"⚠️  AGENT_NETWORK_ERROR | {agent_name} | 网络连接异常，跳过当前节点 | 耗时: {agent_exec_duration:.2f}s | "
                f"错误类型: {type(e).__name__} | 错误信息: {str(e)} | 时间: {time.strftime('%H:%M:%S')}"
            )
            logger.warning(f"Agent {agent_name} 网络连接异常，跳过当前步骤: {e}")
            
            # 标记当前步骤为部分完成（带错误信息）
            current_step.execution_res = f"⚠️ 由于网络连接异常，此步骤被跳过。错误信息: {str(e)[:200]}"
            
            step_duration = time.time() - step_start_time
            enhanced_logger.logger.info(f"⏭️  STEP_SKIPPED | {agent_name} | 步骤已跳过，继续下一步 | 总耗时: {step_duration:.2f}s")
            
            # 返回 Command 继续执行流程
            return Command(
                update={
                    "messages": [
                        HumanMessage(
                            content=f"⚠️ 步骤 '{current_step.title}' 由于网络异常被跳过",
                            name=agent_name,
                        )
                    ],
                    "observations": observations + [current_step.execution_res],
                },
                goto="research_team",
            )
        
        # 其他异常仍然抛出
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
        tool_call_count_in_response = 0
        for msg_idx, msg in enumerate(messages):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_calls_found = True
                tool_call_count_in_response += len(msg.tool_calls)
                enhanced_logger.logger.info(f"🔧 TOOL_CALLS_DETECTED | {agent_name} | 消息[{msg_idx}]中的工具调用数: {len(msg.tool_calls)}")
                for tc_idx, tc in enumerate(msg.tool_calls):
                    tool_name = tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown')
                    tool_args = tc.get('args', {}) if isinstance(tc, dict) else getattr(tc, 'args', {})
                    args_summary = str(tool_args)[:100] + '...' if len(str(tool_args)) > 100 else str(tool_args)
                    enhanced_logger.logger.info(f"   ⚙️  工具调用[{tc_idx}]: {tool_name} | 参数: {args_summary}")
        
        if not tool_calls_found:
            enhanced_logger.logger.warning(f"⚠️  NO_TOOL_CALLS | {agent_name} | LLM没有调用任何工具！")
            for i, msg in enumerate(messages):
                content = getattr(msg, 'content', '')
                if content:
                    content_preview = content[:300] + '...' if len(content) > 300 else content
                    enhanced_logger.logger.warning(f"   📄 LLM直接响应[{i}]: {content_preview}")
        else:
            enhanced_logger.logger.info(f"✅ TOOL_CALLS_SUCCESS | {agent_name} | 共检测到 {tool_call_count_in_response} 个工具调用")
    else:
        enhanced_logger.logger.warning(f"⚠️  UNEXPECTED_RESULT_TYPE | {agent_name} | result类型: {type(result)}")

    # Process the result
    response_content = result["messages"][-1].content
    
    # 防止空 content 导致 LLM 报错 "content len should not be 0"
    if not response_content or not str(response_content).strip():
        response_content = "（步骤已完成，工具调用未产生文本响应）"
    
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
            # 当前步骤信息（刚完成的步骤）
            "current_step_index": len(completed_steps),
            "current_step_title": current_step.title,
            # 下一步信息（供 SSE 层直接使用，无需 +1 推算）
            "next_step_index": len(completed_steps) + 1 if len(completed_steps) + 1 < len(plan_steps) else -1,
            "next_step_title": (plan_steps[len(completed_steps) + 1].title
                                if len(completed_steps) + 1 < len(plan_steps)
                                else ""),
        },
        goto="research_team",
    )


async def _setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list,
    recursion_limit: int = 10,
    agent_executor: Any = None,
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
        recursion_limit: 递归限制
        agent_executor: 可选的自定义 agent 执行器（支持 middleware）

    返回：
        Command 对象，用于更新状态并转到 research_team
    """
    setup_start_time = time.time()
    enhanced_logger.logger.info(f"🔄 AGENT_SETUP_ENTRY | {agent_type} | 开始配置智能体")
    
    # 如果提供了自定义 agent_executor，直接使用（跳过 MCP 配置）
    if agent_executor is not None:
        enhanced_logger.logger.info(f"✅ CUSTOM_AGENT | {agent_type} | 使用自定义 agent executor (middleware 支持)")
        setup_duration = time.time() - setup_start_time
        enhanced_logger.logger.info(f"✅ AGENT_SETUP_COMPLETE | {agent_type} | 自定义智能体配置完成 | 耗时: {setup_duration:.2f}s")
        return await _execute_agent_step(state, agent_executor, agent_type, recursion_limit=recursion_limit, cancel_event=cancel_event)
    
    configurable = Configuration.from_runnable_config(config)
    mcp_servers = {}
    enabled_tools = {}
    
    # 提取取消信号（客户端断连时通知节点停止）
    cancel_event = config.get("configurable", {}).get("cancel_event")
    
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

        return await _execute_agent_step(state, agent, agent_type, recursion_limit=recursion_limit, cancel_event=cancel_event)
    else:
        enhanced_logger.logger.info(f"🔧 DEFAULT_TOOLS | {agent_type} | 使用默认工具 | 工具数: {len(default_tools)}")
        # Use default tools if no MCP servers are configured
        agent = create_agent(agent_type, agent_type, default_tools, agent_type, configurable)

        setup_duration = time.time() - setup_start_time
        enhanced_logger.logger.info(f"✅ AGENT_SETUP_COMPLETE | {agent_type} | 默认智能体配置完成 | 耗时: {setup_duration:.2f}s")

        return await _execute_agent_step(state, agent, agent_type, recursion_limit=recursion_limit, cancel_event=cancel_event)
