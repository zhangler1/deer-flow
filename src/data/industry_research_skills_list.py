# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
行业研究类技能提示词列表配置

存储行业研报和行业研究报告的研究技能提示词信息。
每个技能包含 name、filepath 和 description 三个字段。
"""

# 行业研报研究技能列表配置（industry_report）
# 用于根据用户输入智能匹配最相关的提示词
INDUSTRY_REPORT_SKILLS_LIST = [
  {
    "name": "宏观和行业政策分析",
    "filepath": "src/prompts/industry_report/research_skills/宏观和行业政策分析.md",
    "description": "分析宏观经济环境、国家及地方相关政策法规对行业的影响,包括财政政策、货币政策、产业政策等"
  },
  {
    "name": "行业运行情况分析",
    "filepath": "src/prompts/industry_report/research_skills/行业运行情况分析.md",
    "description": "分析行业整体运行态势,包括市场规模、增长速度、供需关系、价格走势、进出口情况等"
  },
  {
    "name": "产业链运行情况分析",
    "filepath": "src/prompts/industry_report/research_skills/产业链运行情况分析.md",
    "description": "分析产业链上下游运行状况,包括原材料供应、生产制造、销售渠道、终端市场等各环节"
  },
  {
    "name": "行业经营情况分析",
    "filepath": "src/prompts/industry_report/research_skills/行业经营情况分析.md",
    "description": "分析行业整体经营状况,包括盈利能力、成本控制、资产负债、现金流等财务指标"
  },
  {
    "name": "重大事件分析",
    "filepath": "src/prompts/industry_report/research_skills/重大事件分析.md",
    "description": "分析影响行业发展的重大事件,如并购重组、技术突破、安全事故、政策变化等"
  },
  {
    "name": "行业区域分析",
    "filepath": "src/prompts/industry_report/research_skills/行业区域分析.md",
    "description": "分析行业在不同区域的分布特征、发展水平、竞争优势及区域差异"
  },
  {
    "name": "行业发展预测",
    "filepath": "src/prompts/industry_report/research_skills/行业发展预测.md",
    "description": "基于当前数据和趋势,预测行业未来发展方向、市场空间、机遇与挑战"
  }
]

# 行业研究报告研究技能列表配置（industry_research）
# 聚焦技术路线、产业链拆解与客户拓展的6步流程
INDUSTRY_RESEARCH_SKILLS_LIST = [
  {
    "name": "优势与技术路线介绍",
    "filepath": "src/prompts/industry_research/research_skills/优势与技术路线介绍.md",
    "description": "分析目标行业的技术原理与产业优势、商业化核心指标与条件、主流技术路线及其进展"
  },
  {
    "name": "产业发展情况",
    "filepath": "src/prompts/industry_research/research_skills/产业发展情况.md",
    "description": "分析全球产业发展现状（各国战略与政策、投资热度）、中国产业发展重点（战略政策、产业投资格局）"
  },
  {
    "name": "产业链全环节拆解",
    "filepath": "src/prompts/industry_research/research_skills/产业链全环节拆解.md",
    "description": "分析上游材料领域、上游设备领域、中游系统建设领域、下游商业运用场景、产业链重点企业分布"
  },
  {
    "name": "风险挑战分析",
    "filepath": "src/prompts/industry_research/research_skills/风险挑战分析.md",
    "description": "分析行业技术风险、市场风险、经营风险，提出风险管控建议"
  },
  {
    "name": "行业案例介绍",
    "filepath": "src/prompts/industry_research/research_skills/行业案例介绍.md",
    "description": "分析行业典型案例的整体优势，对典型案例进行分类分析"
  },
  {
    "name": "客户拓展思路",
    "filepath": "src/prompts/industry_research/research_skills/客户拓展思路.md",
    "description": "制定客户选择标准、产品适配方案、组织推动与渠道建设、业务创新方向、风险管控措施"
  }
]
