# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
图节点包（重构版）

按功能模块组织的节点：
- utils.py: 工具函数（handoff_to_planner, _execute_agent_step, _setup_and_execute_agent_step）
- routing.py: 路由节点（router_node）
- simple_nodes.py: 简单节点（direct_answer_node, simple_search_node）
- iterative_research.py: 迭代研究节点（iterative_research_node, iterative_reporter_node）
- background.py: 背景调研节点（background_investigation_node）
- deep_research/: 深度研究路径
    - coordinator.py: 协调节点
    - planner.py: 规划节点 + 人工反馈节点
    - researcher.py: 研究员节点 + 编码员节点
    - reporter.py: 报告员节点 + 研究团队节点

此模块提供与原始 nodes.py 完全兼容的导出接口，
外部代码无需修改即可直接使用。
"""

# 工具函数
from src.graph.nodes.utils import (
    handoff_to_planner,
    _execute_agent_step,
    _setup_and_execute_agent_step,
)

# 路由节点
from src.graph.nodes.routing import router_node

# 简单路径节点
from src.graph.nodes.simple_nodes import (
    direct_answer_node,
    simple_search_node,
)

# 迭代研究节点
from src.graph.nodes.iterative_research import (
    iterative_research_node,
    iterative_reporter_node,
)

# 背景调研节点
from src.graph.nodes.background import background_investigation_node

# 深度研究路径节点
from src.graph.nodes.deep_research import (
    coordinator_node,
    planner_node,
    human_feedback_node,
    researcher_node,
    coder_node,
    reporter_node,
    research_team_node,
)


__all__ = [
    # 路由和简单路径节点
    "router_node",
    "direct_answer_node",
    "simple_search_node",
    "iterative_research_node",
    "iterative_reporter_node",
    
    # 背景调研
    "background_investigation_node",
    
    # 深度研究路径节点
    "coordinator_node",
    "background_investigation_node",
    "planner_node",
    "human_feedback_node",
    "reporter_node",
    "research_team_node",
    "researcher_node",
    "coder_node",
    
    # 辅助函数
    "handoff_to_planner",
    "_execute_agent_step",
    "_setup_and_execute_agent_step",
]
