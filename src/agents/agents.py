# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
from typing import cast
from langchain_core.language_models import BaseChatModel

from src.agents.react_loop import ReactLoop
from src.agents.middlewares.loop_detection_middleware import LoopDetectionMiddleware, LoopDetectionConfig
from src.agents.middlewares.summarization_middleware import SummarizationMiddleware, SummarizationConfig
from src.agents.middlewares.dynamic_context_middleware import DynamicContextMiddleware
from src.agents.middlewares.dangling_tool_call_middleware import DanglingToolCallMiddleware
from src.agents.middlewares.llm_error_handling_middleware import LLMErrorHandlingMiddleware, LLMRetryConfig
from src.agents.middlewares.tool_error_handling_middleware import ToolErrorHandlingMiddleware
from src.agents.middlewares.token_usage_middleware import TokenUsageMiddleware
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

# LLM 重试配置（已移入 LLMErrorHandlingMiddleware 内部默认值）
DEFAULT_LLM_MAX_RETRIES = int(os.getenv("REACT_LLM_MAX_RETRIES", "3"))
DEFAULT_LLM_BASE_DELAY = float(os.getenv("REACT_LLM_BASE_DELAY", "1.0"))

# 动态上下文配置
DEFAULT_SYSTEM_HINT = os.getenv("REACT_SYSTEM_HINT", "")


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
    
    # 0. 动态上下文注入（最先执行，注入系统提示，标记为 protected）
    middlewares.append(DynamicContextMiddleware(system_hint=DEFAULT_SYSTEM_HINT))
    
    # 1. 悬空工具调用修复（P0，防止消息链断裂导致 LLM 报错）
    middlewares.append(DanglingToolCallMiddleware())
    
    # 2. LLM 错误处理（P0，重试+熔断，生产必备）
    middlewares.append(LLMErrorHandlingMiddleware(config=LLMRetryConfig(
        max_retries=DEFAULT_LLM_MAX_RETRIES,
        base_delay=DEFAULT_LLM_BASE_DELAY,
    )))
    
    # 3. 上下文压缩中间件（仅对 researcher 类型启用）
    if agent_type in ("researcher", "iterative_researcher"):
        compression_llm = None
        if DEFAULT_COMPRESSION_MODE == "summarize":
            try:
                compression_llm = get_llm_by_type("basic")
            except Exception as e:
                logger.warning(f"⚠️ 无法获取压缩用 LLM，回退到 truncate 模式: {e}")
        
        compression_config = SummarizationConfig(
            enabled=True,
            max_context_tokens=DEFAULT_MAX_CONTEXT_TOKENS,
            tool_result_max_chars=DEFAULT_TOOL_RESULT_MAX_CHARS,
            compression_mode=DEFAULT_COMPRESSION_MODE if compression_llm else "truncate",
        )
        middlewares.append(SummarizationMiddleware(llm=compression_llm, config=compression_config))
    
    # 4. 工具错误处理（P1，增强工具错误的容错）
    middlewares.append(ToolErrorHandlingMiddleware())
    
    # 5. 循环检测中间件（所有 agent 都启用）
    loop_config = LoopDetectionConfig(
        hash_threshold=DEFAULT_LOOP_DETECT_THRESHOLD,
        warn_at=DEFAULT_WARN_AT,
    )
    middlewares.append(LoopDetectionMiddleware(config=loop_config))
    
    # 6. Token 用量统计（P2，成本监控）
    middlewares.append(TokenUsageMiddleware())

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
