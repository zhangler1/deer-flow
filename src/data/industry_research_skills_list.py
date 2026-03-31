# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
行业研报研究技能提示词列表配置

存储所有可用的行业研报研究技能提示词信息。
每个技能包含 name 和 filepath 两个字段。
"""

# 行业研报研究技能列表配置
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
