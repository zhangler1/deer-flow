# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""部门专用智能体配置和创建模块"""

import logging
from typing import Dict, List, Any, Optional

from src.agents import create_agent
from src.tools import (
    get_web_search_tool,
    python_repl_tool,
    get_retriever_tool
)

logger = logging.getLogger(__name__)


# 部门配置字典
DEPARTMENT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "tech": {
        "name": "技术部",
        "description": "技术部门专用智能体，擅长代码分析、系统架构设计和技术方案评估",
        "keywords": ["代码", "架构", "算法", "数据库", "API", "系统", "技术"],
        "tools_config": {
            "python_repl": True,
            "web_search": True,
            "max_search_results": 5
        },
        "prompt_template": """你是技术部的专业AI助手，具备以下专长：

**核心能力**:
- 💻 代码分析与优化
- 🏗️ 系统架构设计
- 🔧 技术方案评估
- 📊 算法与数据结构
- 🗄️ 数据库设计
- 🔌 API设计与集成

**工作原则**:
1. 提供技术精准的解决方案
2. 考虑可维护性和可扩展性
3. 遵循最佳实践和设计模式
4. 注重代码质量和性能优化
5. 提供清晰的技术文档

请基于以上专长，为用户提供专业的技术支持。
""",
        "context": {
            "domain": "technology",
            "expertise": ["coding", "architecture", "algorithms", "databases"]
        }
    },
    
    "marketing": {
        "name": "市场部",
        "description": "市场部门专用智能体，擅长市场分析、竞品研究和营销策略",
        "keywords": ["市场", "营销", "竞品", "用户", "推广", "品牌"],
        "tools_config": {
            "python_repl": False,
            "web_search": True,
            "max_search_results": 7
        },
        "prompt_template": """你是市场部的专业AI助手，具备以下专长：

**核心能力**:
- 📊 市场趋势分析
- 🔍 竞品研究与对比
- 🎯 营销策略制定
- 👥 用户画像与需求分析
- 📱 品牌定位与传播
- 📈 增长策略规划

**工作原则**:
1. 基于数据驱动决策
2. 关注用户需求和体验
3. 深入了解市场动态
4. 创新营销思路
5. 注重品牌价值传递

请基于以上专长，为用户提供专业的市场营销支持。
""",
        "context": {
            "domain": "marketing",
            "expertise": ["market_analysis", "branding", "user_research", "strategy"]
        }
    },
    
    "finance": {
        "name": "财务部",
        "description": "财务部门专用智能体，擅长财务分析、成本核算和数据报表",
        "keywords": ["财务", "成本", "预算", "报表", "投资", "收益"],
        "tools_config": {
            "python_repl": True,  # 用于财务计算
            "web_search": True,
            "max_search_results": 5
        },
        "prompt_template": """你是财务部的专业AI助手，具备以下专长：

**核心能力**:
- 💰 财务分析与预测
- 📊 成本核算与控制
- 📈 预算编制与管理
- 📑 财务报表生成
- 💹 投资分析与评估
- 🔢 财务数据建模

**工作原则**:
1. 确保数据准确性
2. 遵循财务规范和准则
3. 提供清晰的财务洞察
4. 支持数据驱动决策
5. 注重风险控制

请基于以上专长，为用户提供专业的财务支持。使用Python进行必要的财务计算。
""",
        "context": {
            "domain": "finance",
            "expertise": ["analysis", "budgeting", "reporting", "investment"]
        }
    },
    
    "hr": {
        "name": "人力资源部",
        "description": "人力资源部门专用智能体，擅长招聘、培训和员工管理",
        "keywords": ["招聘", "培训", "绩效", "薪酬", "员工", "人才"],
        "tools_config": {
            "python_repl": False,
            "web_search": True,
            "max_search_results": 5
        },
        "prompt_template": """你是人力资源部的专业AI助手，具备以下专长：

**核心能力**:
- 👥 招聘与人才获取
- 📚 培训与发展规划
- 📊 绩效管理
- 💼 薪酬福利设计
- 🤝 员工关系管理
- 📈 组织发展咨询

**工作原则**:
1. 以人为本，关注员工发展
2. 遵循劳动法规
3. 促进组织效能
4. 数据驱动HR决策
5. 营造良好企业文化

请基于以上专长，为用户提供专业的人力资源支持。
""",
        "context": {
            "domain": "hr",
            "expertise": ["recruitment", "training", "performance", "compensation"]
        }
    },
    
    "general": {
        "name": "通用",
        "description": "通用智能体，提供各类问题的专业解答",
        "keywords": [],
        "tools_config": {
            "python_repl": False,
            "web_search": True,
            "max_search_results": 5
        },
        "prompt_template": """你是一个通用AI助手，具备广泛的知识和能力：

**核心能力**:
- 📚 知识查询与解答
- 🔍 信息搜索与整理
- 💡 问题分析与建议
- 📝 内容创作与编辑
- 🤔 逻辑推理与判断

**工作原则**:
1. 准确理解用户需求
2. 提供可靠的信息
3. 清晰表达观点
4. 保持客观中立
5. 乐于学习改进

请基于以上能力，为用户提供优质的服务。
""",
        "context": {
            "domain": "general",
            "expertise": ["general_knowledge", "information_retrieval"]
        }
    }
}


def get_department_config(department: str) -> Dict[str, Any]:
    """
    获取部门专用配置
    
    Args:
        department: 部门标识符 (tech/marketing/finance/hr/general)
        
    Returns:
        Dict[str, Any]: 部门配置字典
    """
    config = DEPARTMENT_CONFIGS.get(department.lower(), DEPARTMENT_CONFIGS["general"])
    logger.info(f"加载部门配置: {config['name']}")
    return config


def get_department_tools(
    department: str,
    search_engine: str = "tavily",
    custom_search_repository: Optional[str] = None,
    resources: Optional[list] = None
) -> List:
    """
    根据部门配置获取工具列表
    
    Args:
        department: 部门标识符
        search_engine: 搜索引擎类型
        custom_search_repository: 自定义搜索仓库
        resources: RAG资源列表
        
    Returns:
        List: 工具列表
    """
    config = get_department_config(department)
    tools_config = config["tools_config"]
    tools = []
    
    # 添加网络搜索工具
    if tools_config.get("web_search", False):
        max_results = tools_config.get("max_search_results", 5)
        search_tool = get_web_search_tool(
            max_search_results=max_results,
            engine=search_engine,
            repository_id=custom_search_repository
        )
        tools.append(search_tool)
        logger.info(f"为{config['name']}添加网络搜索工具 (max_results={max_results})")
    
    # 添加Python REPL工具（用于计算和数据处理）
    if tools_config.get("python_repl", False):
        tools.append(python_repl_tool)
        logger.info(f"为{config['name']}添加Python REPL工具")
    
    # 添加RAG检索工具
    if resources:
        retriever_tool = get_retriever_tool(resources)
        if retriever_tool:
            tools.append(retriever_tool)
            logger.info(f"为{config['name']}添加RAG检索工具")
    
    return tools


def create_department_agent(
    department: str,
    search_engine: str = "tavily",
    custom_search_repository: Optional[str] = None,
    resources: Optional[list] = None
):
    """
    创建部门专用智能体
    
    Args:
        department: 部门标识符
        search_engine: 搜索引擎类型
        custom_search_repository: 自定义搜索仓库
        resources: RAG资源列表
        
    Returns:
        智能体实例
    """
    config = get_department_config(department)
    
    # 获取部门工具
    tools = get_department_tools(
        department=department,
        search_engine=search_engine,
        custom_search_repository=custom_search_repository,
        resources=resources
    )
    
    # 创建智能体
    agent = create_agent(
        agent_name=f"{config['name']}助手",
        agent_type="researcher",  # 使用researcher类型的LLM配置
        tools=tools,
        prompt_template=config["prompt_template"]
    )
    
    logger.info(f"创建{config['name']}专用智能体，包含{len(tools)}个工具")
    
    return agent


def get_available_departments() -> List[Dict[str, str]]:
    """
    获取所有可用的部门列表
    
    Returns:
        List[Dict[str, str]]: 部门信息列表
    """
    return [
        {
            "id": dept_id,
            "name": config["name"],
            "description": config["description"]
        }
        for dept_id, config in DEPARTMENT_CONFIGS.items()
    ]


# 导出主要接口
__all__ = [
    "DEPARTMENT_CONFIGS",
    "get_department_config",
    "get_department_tools",
    "create_department_agent",
    "get_available_departments"
]
