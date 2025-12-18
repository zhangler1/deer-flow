# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
from langgraph.graph import StateGraph

from src.prompt_enhancer.graph.enhancer_node import prompt_enhancer_node
from src.prompt_enhancer.graph.state import PromptEnhancerState


def build_graph():
    """Build and return the prompt enhancer workflow graph."""
    # Build state graph
    builder = StateGraph(PromptEnhancerState)

    # Add the enhancer node
    builder.add_node("enhancer", prompt_enhancer_node)

    # Set entry point
    builder.set_entry_point("enhancer")

    # Set finish point
    builder.set_finish_point("enhancer")

    # Compile the graph
    compiled_graph = builder.compile()
    
    # Add Langfuse callback for tracing (只在配置了 PUBLIC_KEY 时启用)
    try:
        if os.getenv("LANGFUSE_PUBLIC_KEY"):
            from langfuse.langchain import CallbackHandler
            return compiled_graph.with_config({"callbacks": [CallbackHandler()]})
    except ImportError:
        pass
    
    return compiled_graph
