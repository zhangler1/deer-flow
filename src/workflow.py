# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import time

from src.config.configuration import get_recursion_limit
from src.graph import build_graph
from src.utils.enhanced_logger import get_enhanced_logger, setup_enhanced_logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# 获取增强日志记录器
enhanced_logger = get_enhanced_logger('workflow')


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)
    # 也启用增强日志的调试模式
    setup_enhanced_logging(level=logging.DEBUG, enable_colors=True)


logger = logging.getLogger(__name__)

# Create the graph
graph = build_graph()


async def run_agent_workflow_async(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
):
    """Run the agent workflow asynchronously with the given user input.

    Args:
        user_input: The user's query or request
        debug: If True, enables debug level logging
        max_plan_iterations: Maximum number of plan iterations
        max_step_num: Maximum number of steps in a plan
        enable_background_investigation: If True, performs web search before planning to enhance context

    Returns:
        The final state after the workflow completes
    """
    if not user_input:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()
        
    # 初始化增强日志
    setup_enhanced_logging(level=logging.DEBUG if debug else logging.INFO, enable_colors=True)
    
    # 记录工作流开始
    workflow_start_time = time.time()
    session_id = f"session_{int(time.time())}"
    enhanced_logger.set_session_context(session_id, user_input)
    enhanced_logger.logger.info(f"🚀 WORKFLOW_START | {session_id} | 开始工作流执行 | 用户输入: '{user_input}'")
    
    logger.info(f"Starting async workflow with user input: {user_input}")
    # 记录配置信息
    enhanced_logger.logger.info(f"📝 WORKFLOW_CONFIG | 最大计划迭代: {max_plan_iterations} | 最大步骤数: {max_step_num} | 背景调研: {enable_background_investigation}")
    
    initial_state = {
        # Runtime Variables
        "messages": [{"role": "user", "content": user_input}],
        "auto_accepted_plan": True,
        "enable_background_investigation": enable_background_investigation,
    }
    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "mcp_settings": {
                "servers": {
                    "mcp-github-trending": {
                        "transport": "stdio",
                        "command": "uvx",
                        "args": ["mcp-github-trending"],
                        "enabled_tools": ["get_github_trending_repositories"],
                        "add_to_agents": ["researcher"],
                    }
                }
            },
        },
        "recursion_limit": get_recursion_limit(default=100),
    }
    last_message_cnt = 0
    nodes_executed = []
    tools_used = []
    
    try:
        async for s in graph.astream(
            input=initial_state, config=config, stream_mode="values"
        ):
            try:
                if isinstance(s, dict) and "messages" in s:
                    if len(s["messages"]) <= last_message_cnt:
                        continue
                    last_message_cnt = len(s["messages"])
                    message = s["messages"][-1]
                    
                    # 记录节点执行
                    if hasattr(message, 'name') and message.name:
                        if message.name not in nodes_executed:
                            nodes_executed.append(message.name)
                            enhanced_logger.logger.info(f"📊 NODE_EXECUTED | {message.name} | 节点已执行")
                    
                    if isinstance(message, tuple):
                        print(message)
                    else:
                        message.pretty_print()
                else:
                    # For any other output format
                    print(f"Output: {s}")
            except Exception as e:
                logger.error(f"Error processing stream output: {e}")
                print(f"Error processing output: {str(e)}")
                
        # 记录工作流完成
        workflow_duration = time.time() - workflow_start_time
        enhanced_logger.log_workflow_summary(workflow_duration, nodes_executed, tools_used)
        enhanced_logger.logger.info(f"🏁 WORKFLOW_COMPLETE | {session_id} | 工作流执行完成 | 总耗时: {workflow_duration:.2f}s")
        
    except Exception as e:
        workflow_duration = time.time() - workflow_start_time
        enhanced_logger.logger.error(f"❌ WORKFLOW_ERROR | {session_id} | 工作流执行失败: {str(e)} | 耗时: {workflow_duration:.2f}s")
        raise

    logger.info("Async workflow completed successfully")


if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid())
