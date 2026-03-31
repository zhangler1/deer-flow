# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""Researcher Agent with Middleware support for DeerFlow 1.0"""

import logging
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.language_models import BaseChatModel

from src.config.summarization_config import get_summarization_config
from src.graph.types import State
from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)


def _create_summarization_middleware() -> SummarizationMiddleware | None:
    """Create and configure the summarization middleware from config.
    
    Returns:
        SummarizationMiddleware instance if enabled, None otherwise.
    """
    config = get_summarization_config()

    if not config.enabled:
        logger.info("📊 Summarization middleware is disabled")
        return None

    # Prepare trigger parameter
    trigger = None
    if config.trigger is not None:
        if isinstance(config.trigger, list):
            trigger = [t.to_tuple() for t in config.trigger]
        else:
            trigger = config.trigger.to_tuple()

    # Prepare keep parameter
    keep = config.keep.to_tuple()

    # Prepare model parameter
    if config.model_name:
        model = config.model_name
        logger.info(f"📊 Using configured model for summarization: {config.model_name}")
    else:
        # Use basic model for summarization to save costs
        # Falls back to default model if not explicitly specified
        model = get_llm_by_type("basic")
        logger.info(f"📊 Using default basic model for summarization")

    # Prepare kwargs
    kwargs = {
        "model": model,
        "trigger": trigger,
        "keep": keep,
    }

    if config.trim_tokens_to_summarize is not None:
        kwargs["trim_tokens_to_summarize"] = config.trim_tokens_to_summarize

    if config.summary_prompt is not None:
        kwargs["summary_prompt"] = config.summary_prompt

    logger.info(f"📊 Summarization middleware initialized: trigger={trigger}, keep={keep}")
    return SummarizationMiddleware(**kwargs)


def create_researcher_agent(
    tools: list[Any],
    model: BaseChatModel | None = None,
    enable_summarization: bool = True,
) -> Any:
    """Create a researcher agent with middleware support.
    
    Args:
        tools: List of tools available to the agent
        model: Language model to use (defaults to basic model)
        enable_summarization: Whether to enable summarization middleware
        
    Returns:
        Configured agent with middlewares
    """
    # Use basic model if not provided
    if model is None:
        model = get_llm_by_type("basic")
    
    # Build middleware list
    middlewares = []
    
    # Add summarization middleware if enabled
    if enable_summarization:
        summarization_middleware = _create_summarization_middleware()
        if summarization_middleware is not None:
            middlewares.append(summarization_middleware)
            logger.info("✅ Summarization middleware added to researcher agent")
    
    # Future: Add other middlewares here
    # middlewares.append(TitleMiddleware())
    # middlewares.append(MemoryMiddleware())
    
    if not middlewares:
        logger.info("⚠️  No middlewares enabled for researcher agent")
    
    # 使用 LangChain 标准 create_agent API
    try:
        from langchain.agents import create_agent as langchain_create_agent
        
        agent = langchain_create_agent(
            model=model,
            tools=tools,
            middlewares=middlewares,
            state_schema=State,
        )
        
        logger.info(
            f"🤖 Researcher agent created with {len(tools)} tools and {len(middlewares)} middlewares"
        )
        
        return agent
    except Exception as e:
        logger.warning(f"⚠️  Failed to create agent with middlewares: {e}")
        logger.info("ℹ️  Falling back to standard agent creation without middleware support")
        
        # 备用方案：返回 None，让调用者使用传统方式
        return None
