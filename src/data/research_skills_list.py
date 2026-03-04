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
    "name": "企业基本信息",
    "filepath": "src/prompts/business_marketing/research_skills/企业基本信息.md",
    "description": "全面收集和深入分析企业的基本信息,包括企业概况、发展历程、市场地位、核心竞争力等"
  },
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
    "description": "企业所在地区的宏观经济分析,包括经济发展水平、产业结构、区域支持政策等"
  },
  {
    "name": "产业政策分析",
    "filepath": "src/prompts/business_marketing/research_skills/产业政策分析.md",
    "description": "国家产业政策解读及对银行营销的启示,包括政策支持措施和银行营销建议"
  },
  {
    "name": "产业及产业节点",
    "filepath": "src/prompts/business_marketing/research_skills/产业及产业节点.md",
    "description": "围绕目标企业的产业链结构分析,包括上下游关系、目标企业定位、上下游龙头企业经营状况等"
  },
  {
    "name": "股权架构分析",
    "filepath": "src/prompts/business_marketing/research_skills/股权架构分析.md",
    "description": "企业股权结构、股权架构图、股东信息、控制关系和管理层分析"
  },
  {
    "name": "财务分析",
    "filepath": "src/prompts/business_marketing/research_skills/财务分析.md",
    "description": "企业财务数据深度分析,包括资产负债、盈利能力、现金流、运营效率、成长能力分析,与竞争对手对比,以及产业链上下游龙头企业财务分析"
  }
]
