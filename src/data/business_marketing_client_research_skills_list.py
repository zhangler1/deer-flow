# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
对公营销报告-战客版研究技能提示词列表配置

存储所有可用的对公营销战客版报告研究技能提示词信息。
每个技能包含 name 和 filepath 两个字段。
"""

# 对公营销报告-战客版研究技能列表配置
# 用于根据用户输入智能匹配最相关的提示词
BUSINESS_MARKETING_CLIENT_RESEARCH_SKILLS_LIST = [
  {
    "name": "公司概况分析",
    "filepath": "src/prompts/business_marketing_client/research_skills/公司概况分析.md",
    "description": "全面收集和深入分析企业的基本信息,包括成立时间、注册资本、发展历程、核心业务定位、市场地位等"
  },
  {
    "name": "公司上市情况分析",
    "filepath": "src/prompts/business_marketing_client/research_skills/公司上市情况分析.md",
    "description": "分析企业上市历程、资本市场表现、再融资情况、股权结构和限售股解禁情况"
  },
  {
    "name": "公司相关荣誉奖项",
    "filepath": "src/prompts/business_marketing_client/research_skills/公司相关荣誉奖项.md",
    "description": "收集企业获得的重要荣誉和奖项,评估企业在行业中的排名和地位"
  },
  {
    "name": "股权架构分析",
    "filepath": "src/prompts/business_marketing_client/research_skills/股权架构分析.md",
    "description": "分析企业股权结构、实际控制人、关联关系、控制链条和股权变动趋势"
  },
  {
    "name": "高管信息分析",
    "filepath": "src/prompts/business_marketing_client/research_skills/高管信息分析.md",
    "description": "分析企业核心高管团队背景、薪酬结构、职能分工和公司治理结构"
  },
  {
    "name": "主营业务分析",
    "filepath": "src/prompts/business_marketing_client/research_skills/主营业务分析.md",
    "description": "分析企业主营业务板块、核心产品、商业模式、客户结构和技术优势"
  },
  {
    "name": "产业架构分析",
    "filepath": "src/prompts/business_marketing_client/research_skills/产业架构分析.md",
    "description": "分析企业产业链布局、生产基地分布、产能规划和研发体系"
  },
  {
    "name": "公司财务情况分析",
    "filepath": "src/prompts/business_marketing_client/research_skills/公司财务情况分析.md",
    "description": "从资产负债、营收盈利、现金流三个维度系统分析企业财务状况"
  },
  {
    "name": "行业内竞争者比较分析",
    "filepath": "src/prompts/business_marketing_client/research_skills/行业内竞争者比较分析.md",
    "description": "识别主要竞争对手,从财务表现、经营状况等多维度进行对比分析"
  },
  {
    "name": "公司发展战略分析",
    "filepath": "src/prompts/business_marketing_client/research_skills/公司发展战略分析.md",
    "description": "分析企业技术创新战略、产能扩张战略、市场拓展战略和可持续发展战略"
  },
  {
    "name": "公司经营风险及化解措施",
    "filepath": "src/prompts/business_marketing_client/research_skills/公司经营风险及化解措施.md",
    "description": "识别企业面临的财务风险、经营风险、战略风险和外部环境风险,分析应对措施"
  }
]
