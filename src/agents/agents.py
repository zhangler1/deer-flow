# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import cast
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from src.config.agents import AGENT_LLM_MAP
from src.llms.llm import get_llm_by_type
from src.prompts import apply_prompt_template


# Create agents using configured LLM types
def create_agent(agent_name: str, agent_type: str, tools: list, prompt_template: str):
    """Factory function to create agents with consistent configuration."""
    llm = get_llm_by_type(AGENT_LLM_MAP[agent_type])
    
    # 解包LLM包装器以获取原始LLM对象，确保与LangGraph兼容
    raw_llm = llm
    
    # 安全检测并提取原始LLM对象
    if hasattr(llm, '__class__') and hasattr(llm, 'llm'):
        # 检测EnhancedLLMWrapper类型
        class_name = llm.__class__.__name__
        if 'EnhancedLLMWrapper' in class_name:
            raw_llm = getattr(llm, 'llm', llm)
        elif 'EnhancedToolBoundLLMWrapper' in class_name:
            raw_llm = getattr(llm, 'tool_bound_llm', llm)
    
    # 确保raw_llm是BaseChatModel类型
    chat_model = cast(BaseChatModel, raw_llm)
    
    return create_react_agent(
        name=agent_name,
        model=chat_model,
        tools=tools,
        prompt=lambda state: apply_prompt_template(prompt_template, state),
    )
