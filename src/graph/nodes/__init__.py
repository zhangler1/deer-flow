# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
图节点包

按功能模块组织的节点：
- utils.py: 工具函数（handoff_to_planner, _execute_agent_step）
- background.py: 背景调研节点（background_investigation_node）
- deep_research/: 深度研究路径
    - coordinator.py: 协调节点
    - planner.py: 规划节点 + 人工反馈节点
    - researcher.py: 研究员节点 + 编码员节点
    - reporter.py: 报告员节点 + 研究团队节点
"""

# 工具函数
from src.graph.nodes.utils import (
    handoff_to_planner,
    _execute_agent_step,
)

# 背景调研节点
from src.graph.nodes.background import background_investigation_node

# 深度研究路径节点
from src.graph.nodes.deep_research import (
    coordinator_node,
    clarification_node,
    planner_node,
    human_feedback_node,
    researcher_node,
    coder_node,
    reporter_node,
    research_team_node,
)


__all__ = [
    # 背景调研
    "background_investigation_node",
    
    # 深度研究路径节点
    "coordinator_node",
    "clarification_node",
    "planner_node",
    "human_feedback_node",
    "reporter_node",
    "research_team_node",
    "researcher_node",
    "coder_node",
    
    # 辅助函数
    "handoff_to_planner",
    "_execute_agent_step",
]
