# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
研究技能提示词列表配置

存储所有可用的对公营销报告研究技能提示词信息。
每个技能包含 name 和 filepath 两个字段。
"""

# 研究技能列表配置
# 用于根据用户输入智能匹配最相关的提示词
RESEARCH_SKILLS_LIST = [
  {
    "name": "商机分析",
    "filepath": "src/prompts/business_marketing/research_skills/商机分析.md",
    "description": "企业商机数据分析和产品匹配,包括股权质押、专利、中标、分红、资质审批等商机信息,以及银行产品推荐"
  },
  {
    "name": "舆情分析",
    "filepath": "src/prompts/business_marketing/research_skills/舆情分析.md",
    "description": "基于舆情数据分析企业声誉风险和潜在影响"
  },
  {
    "name": "区域宏观分析",
    "filepath": "src/prompts/business_marketing/research_skills/区域宏观分析.md",
    "description": "行业整体现状分析,包括市场规模、竞争格局、发展趋势和面临的挑战"
  },
  {
    "name": "区域产业政策分析",
    "filepath": "src/prompts/business_marketing/research_skills/区域产业政策分析.md",
    "description": "区域宏观经济分析、产业政策解读和产业链分析(综合模块)"
  },
  {
    "name": "产业及产业节点",
    "filepath": "src/prompts/business_marketing/research_skills/产业及产业节点.md",
    "description": "行业产业链结构分析,包括上下游关系、关键产业节点、核心企业和价值分布"
  },
  {
    "name": "财务分析",
    "filepath": "src/prompts/business_marketing/research_skills/财务分析.md",
    "description": "企业财务数据深度分析,包括资产负债表、利润表、现金流量表分析,以及行业对比评估"
  }
]
