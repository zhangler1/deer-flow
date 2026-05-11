# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import cast
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.prompts import apply_prompt_template

logger = logging.getLogger(__name__)


# Create agents using configured LLM types
def create_agent(agent_name: str, agent_type: str, tools: list, prompt_template: str, configurable=None):
    """Factory function to create agents with consistent configuration.

    Args:
        agent_name: Name of the agent
        agent_type: Type of the agent (e.g., "researcher", "coder")
        tools: List of tools available to the agent
        prompt_template: Name of the prompt template to use
        configurable: Optional Configuration object containing report_style and other settings
    """
    # 🆕 添加工具诊断日志
    logger.info(f"🔧 TOOLS_INPUT | 接收到的工具列表:")
    for i, tool in enumerate(tools):
        tool_name = getattr(tool, 'name', 'unknown')
        logger.info(f"   [{i}] {tool_name}")
    logger.info(f"🔧 TOOLS_COUNT | 工具总数: {len(tools)}")

    if len(tools) == 0:
        logger.warning(f"⚠️  NO_TOOLS | {agent_name} | 警告：没有工具被传递给Agent！")

    llm = get_llm_by_type(AGENT_LLM_MAP[agent_type])

    # 解包LLM包装器以获取原始LLM对象，确保与LangGraph兼容
    raw_llm = llm

    # 安全检测并提取原始LLM对象
    if hasattr(llm, '__class__') and hasattr(llm, 'llm'):
        # 检测EnhancedLLMWrapper类型
        class_name = llm.__class__.__name__
        if 'EnhancedLLMWrapper' in class_name:
            raw_llm = getattr(llm, 'llm', llm)
            logger.debug(f"🔄 LLM_UNWRAP | 从EnhancedLLMWrapper中提取原始LLM")
        elif 'EnhancedToolBoundLLMWrapper' in class_name:
            raw_llm = getattr(llm, 'tool_bound_llm', llm)
            logger.debug(f"🔄 LLM_UNWRAP | 从EnhancedToolBoundLLMWrapper中提取原始LLM")

    # 确保raw_llm是BaseChatModel类型
    chat_model = cast(BaseChatModel, raw_llm)
    logger.info(f"🤖 LLM_MODEL | 使用模型: {getattr(chat_model, 'model_name', 'unknown')}")


    agent = create_react_agent(
        name=agent_name,
        model=chat_model,
        tools=tools,
        prompt=lambda state: apply_prompt_template(prompt_template, state, configurable),
    )

    logger.info(f"✅ AGENT_CREATED | {agent_name} | Agent创建成功 | 类型: {type(agent).__name__}")

    return agent
