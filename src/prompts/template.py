# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import dataclasses
import os
from datetime import datetime
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from langgraph.prebuilt.chat_agent_executor import AgentState

from src.config.configuration import Configuration

# Get the base prompts directory
PROMPTS_DIR = os.path.dirname(__file__)

# Initialize Jinja2 environment for default prompts
env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _get_prompt_env(report_style: Optional[str] = None) -> Environment:
    """
    Get the appropriate Jinja2 environment based on report style.

    Args:
        report_style: The report style (e.g., 'business_marketing', 'academic', etc.)

    Returns:
        Jinja2 Environment configured for the appropriate directory
    """
    if report_style == "business_marketing":
        style_dir = os.path.join(PROMPTS_DIR, "business_marketing")
        if os.path.exists(style_dir):
            return Environment(
                loader=FileSystemLoader(style_dir),
                autoescape=select_autoescape(),
                trim_blocks=True,
                lstrip_blocks=True,
            )

    # Default to base prompts directory
    return env


def get_prompt_template(prompt_name: str) -> str:
    """
    Load and return a prompt template using Jinja2.

    Args:
        prompt_name: Name of the prompt template file (without .md extension)

    Returns:
        The template string with proper variable substitution syntax
    """
    try:
        template = env.get_template(f"{prompt_name}.md")
        return template.render()
    except Exception as e:
        raise ValueError(f"Error loading template {prompt_name}: {e}")


def apply_prompt_template(
    prompt_name: str, state: AgentState, configurable: Configuration = None
) -> list:
    """
    Apply template variables to a prompt template and return formatted messages.

    Args:
        prompt_name: Name of the prompt template to use
        state: Current agent state containing variables to substitute
        configurable: Configuration object that may contain report_style

    Returns:
        List of messages with the system prompt as the first message
    """
    # Convert state to dict for template rendering
    state_vars = {
        "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
        **state,
    }

    # Add configurable variables
    report_style = None
    if configurable:
        state_vars.update(dataclasses.asdict(configurable))
        report_style = getattr(configurable, 'report_style', None)

    # Get the appropriate environment based on report style
    prompt_env = _get_prompt_env(report_style)

    try:
        template = prompt_env.get_template(f"{prompt_name}.md")
        system_prompt = template.render(**state_vars)
        return [{"role": "system", "content": system_prompt}] + state["messages"]
    except Exception as e:
        raise ValueError(f"Error applying template {prompt_name}: {e}")
