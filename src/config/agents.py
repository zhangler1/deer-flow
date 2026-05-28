# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Literal

# Define available LLM types
LLMType = Literal["coordinator", "planner", "researcher", "coder", "reporter", "vision", "basic", "compression"]

# Define agent-LLM mapping
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "coordinator",
    "planner": "planner",
    "researcher": "researcher",
    "coder": "coder",
    "reporter": "reporter",
    "podcast_script_writer": "basic",
    "ppt_composer": "basic",
    "prose_writer": "basic",
    "prompt_enhancer": "basic",
}
