# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
研究技能提示词列表配置

存储所有可用的对公营销报告研究技能提示词信息。
每个技能包含 name 和 filepath 两个字段。
"""

# 研究技能列表配置
# 用于根据用户输入智能匹配最相关的提示词
#
# 注意：当本 Skill 在项目中使用时，路径应为项目根目录相对路径
# 当本 Skill 独立使用时，需要修改为相对于 Skill 目录的路径

# Skill 内部使用时的路径配置
SKILL_ROOT = "skills/public/Corporate-marketing-report-generation"

RESEARCH_SKILLS_LIST = [
  {
    "name": "企业基本信息",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/企业基本信息.md",
    "description": "全面收集和深入分析企业的基本信息,包括企业概况、发展历程、市场地位、核心竞争力等"
  },
  {
    "name": "商机分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/商机分析.md",
    "description": "企业商机数据分析和产品匹配,包括股权质押、专利、中标、分红、资质审批等商机信息,以及银行产品推荐"
  },
  {
    "name": "舆情分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/舆情分析.md",
    "description": "基于舆情数据分析企业声誉风险和潜在影响"
  },
  {
    "name": "区域经济环境分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/区域经济环境分析.md",
    "description": "企业所在地区的宏观经济环境分析,包括经济发展水平、产业结构特征、产业集群分布、发展机遇等"
  },
  {
    "name": "区域支持政策分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/区域支持政策分析.md",
    "description": "企业所在地区的产业支持政策分析,包括产业支持政策、政策红利分析、财税人才土地金融支持等"
  },
  {
    "name": "产业政策分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/产业政策分析.md",
    "description": "国家产业政策解读及对银行营销的启示,包括政策支持措施和银行营销建议"
  },
  {
    "name": "产业链上游分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/产业链上游分析.md",
    "description": "围绕目标企业的产业链上游分析,包括上游原材料供应商、供应风险分析、上游龙头企业经营状况等"
  },
  {
    "name": "产业链中游分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/产业链中游分析.md",
    "description": "围绕目标企业的产业链中游分析,包括中游制造加工环节、竞争格局、中游龙头企业经营状况等"
  },
  {
    "name": "产业链下游分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/产业链下游分析.md",
    "description": "围绕目标企业的产业链下游分析,包括下游应用领域、市场需求、销售渠道、下游龙头企业经营状况等"
  },
  {
    "name": "股权结构分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/股权结构分析.md",
    "description": "企业股权结构分析,包括股权架构图、股东信息、控股股东背景、实际控制人、股权变动等"
  },
  {
    "name": "高管团队分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/高管团队分析.md",
    "description": "企业高管团队分析,包括核心高管介绍、高管背景、团队稳定性、高管持股情况等"
  },
  {
    "name": "财务数据分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/财务数据分析.md",
    "description": "企业财务数据深度分析,包括资产负债、盈利能力、现金流、运营效率、成长能力分析,与竞争对手全面对比"
  },
  {
    "name": "产业链财务分析",
    "filepath": f"{SKILL_ROOT}/prompts/research_skills/产业链财务分析.md",
    "description": "产业链上下游龙头企业财务分析,包括上下游财务状况、产业链地位评估、定价权分析等"
  }
]
