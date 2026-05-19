# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
from typing import cast
from langchain_core.language_models import BaseChatModel

from src.agents.react_loop import ReactLoop
from src.agents.middlewares.loop_detection import LoopDetectionMiddleware, LoopDetectionConfig
from src.agents.middlewares.context_compression import ContextCompressionMiddleware, ContextCompressionConfig
from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.prompts import apply_prompt_template

logger = logging.getLogger(__name__)

# 默认参数（可通过环境变量覆盖）
DEFAULT_MAX_ITERATIONS = int(os.getenv("REACT_MAX_ITERATIONS", "8"))
DEFAULT_WARN_AT = int(os.getenv("REACT_WARN_AT", "5"))
DEFAULT_LOOP_DETECT_THRESHOLD = int(os.getenv("REACT_LOOP_DETECT_THRESHOLD", "3"))

# 上下文压缩配置
DEFAULT_MAX_CONTEXT_TOKENS = int(os.getenv("REACT_MAX_CONTEXT_TOKENS", "80000"))
DEFAULT_TOOL_RESULT_MAX_CHARS = int(os.getenv("REACT_TOOL_RESULT_MAX_CHARS", "3000"))
DEFAULT_COMPRESSION_MODE = os.getenv("REACT_COMPRESSION_MODE", "summarize")


# Create agents using configured LLM types
def create_agent(agent_name: str, agent_type: str, tools: list, prompt_template: str, configurable=None):
    """Factory function to create agents with consistent configuration.

    使用 ReactLoop 替代 langgraph.prebuilt.create_react_agent，
    提供可控的 ReAct 循环（循环检测、软提示停止、硬上限保护）。

    Args:
        agent_name: Name of the agent
        agent_type: Type of the agent (e.g., "researcher", "coder")
        tools: List of tools available to the agent
        prompt_template: Name of the prompt template to use
        configurable: Optional Configuration object containing report_style and other settings
    """
    # 工具诊断日志
    logger.info(f"🔧 TOOLS_INPUT | 接收到的工具列表:")
    for i, tool in enumerate(tools):
        tool_name = getattr(tool, 'name', 'unknown')
        logger.info(f"   [{i}] {tool_name}")

    if len(tools) == 0:
        logger.warning(f"⚠️  NO_TOOLS | {agent_name} | 警告：没有工具被传递给Agent！")

    llm = get_llm_by_type(AGENT_LLM_MAP[agent_type])

    # 解包LLM包装器以获取原始LLM对象
    raw_llm = llm

    # 安全检测并提取原始LLM对象
    if hasattr(llm, '__class__') and hasattr(llm, 'llm'):
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

    # === 装配中间件链 ===
    middlewares = []
    
    # 1. 上下文压缩中间件（仅对 researcher 类型启用）
    if agent_type in ("researcher", "iterative_researcher"):
        compression_llm = None
        if DEFAULT_COMPRESSION_MODE == "summarize":
            try:
                compression_llm = get_llm_by_type("basic")
            except Exception as e:
                logger.warning(f"⚠️ 无法获取压缩用 LLM，回退到 truncate 模式: {e}")
        
        compression_config = ContextCompressionConfig(
            enabled=True,
            max_context_tokens=DEFAULT_MAX_CONTEXT_TOKENS,
            tool_result_max_chars=DEFAULT_TOOL_RESULT_MAX_CHARS,
            compression_mode=DEFAULT_COMPRESSION_MODE if compression_llm else "truncate",
        )
        middlewares.append(ContextCompressionMiddleware(llm=compression_llm, config=compression_config))
    
    # 2. 循环检测中间件（所有 agent 都启用）
    loop_config = LoopDetectionConfig(
        hash_threshold=DEFAULT_LOOP_DETECT_THRESHOLD,
        warn_at=DEFAULT_WARN_AT,
    )
    middlewares.append(LoopDetectionMiddleware(config=loop_config))

    # === 创建 ReactLoop ===
    agent = ReactLoop(
        model=chat_model,
        tools=tools,
        prompt=lambda state: apply_prompt_template(prompt_template, state, configurable),
        max_iterations=DEFAULT_MAX_ITERATIONS,
        middlewares=middlewares,
    )

    logger.info(
        f"🔁 REACT_LOOP | {agent_name} | "
        f"max_iterations={DEFAULT_MAX_ITERATIONS} | "
        f"warn_at={DEFAULT_WARN_AT} | "
        f"middlewares={[m.name for m in middlewares]}"
    )

    return agent
