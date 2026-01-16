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
    "name": "财务分析",
    "filepath": "src/prompts/business_marketing/research_skills/财务分析.md",
    "description": "企业财务数据深度分析,包括资产负债表、利润表、现金流量表分析,以及行业对比评估"
  },
  {
    "name": "商机分析",
    "filepath": "src/prompts/business_marketing/research_skills/商机分析.md",
    "description": "基于商机数据分析企业营销价值,识别业务合作机会"
  },
  {
    "name": "舆情分析",
    "filepath": "src/prompts/business_marketing/research_skills/舆情分析.md",
    "description": "基于舆情数据分析企业声誉风险和潜在影响"
  },
  {
    "name": "区域产业政策分析",
    "filepath": "src/prompts/business_marketing/research_skills/区域产业政策分析.md",
    "description": "区域宏观经济分析和产业政策解读"
  },
  {
    "name": "股权架构分析",
    "filepath": "src/prompts/business_marketing/research_skills/股权架构分析.md",
    "description": "企业股权结构、股东信息和管理层分析"
  },
  {
    "name": "产业链分析",
    "filepath": "src/prompts/business_marketing/research_skills/产业链分析.md",
    "description": "企业主营业务和产业链上下游分析"
  },
]
