# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
问题澄清节点模块

包含：
- clarification_node: 当用户问题不清晰时，生成澄清选项并中断等待用户选择
"""

import json
import logging
import re
import time
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt

from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.utils.enhanced_logger import get_enhanced_logger


logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger("graph.nodes.clarification")

# 用于从 coordinator 回复中提取澄清要点的正则
_CLARIFICATION_TAG_RE = re.compile(r"\[NEED_CLARIFICATION\]\s*", re.IGNORECASE)

# LLM 生成选项的提示词
_GENERATE_OPTIONS_PROMPT = """你是一个问题澄清助手。根据用户的模糊问题和协调者的判断，生成 1~3 个澄清问题，每个问题带 3 个选项。

用户的原始问题：{user_query}

协调者的判断：{coordinator_reasoning}

请严格按以下 JSON 格式输出（不要包含其他内容）：
{{
  "questions": [
    {{
      "question": "第一个澄清问题",
      "options": ["选项A", "选项B", "选项C"]
    }}
  ]
}}

要求：
- 问题数量规则：
  - 如果用户只是缺少一个维度的信息（如只缺地域范围），生成 1 个问题
  - 如果缺少多个维度（如既缺地域又缺时间范围），生成 2~3 个问题
  - 最多 3 个问题
- 每个 question 要简洁明了，让用户一眼明白你在问什么
- 每个选项要具体、有区分度，中文描述，每个不超过 30 字
- 问题之间不要有依赖关系，各自独立，因为可能有下一轮澄清
"""


def clarification_node(
    state, config: RunnableConfig
) -> Command[Literal["coordinator"]]:
    """
    问题澄清节点：生成选项并中断等待用户选择。

    流程：
    1. 从 state 的最新消息中提取 coordinator 的澄清判断
    2. 调用 LLM 生成 3 个结构化选项
    3. 通过 interrupt() 暂停图执行，将选项传给前端
    4. 用户反馈后，将答案追加到消息中，重新进入 coordinator
    """
    start_time = time.time()
    enhanced_logger.logger.info("🔄 NODE_ENTRY | clarification | 开始问题澄清")

    # 1. 提取 coordinator 的澄清理由
    messages = state.get("messages", [])
    coordinator_content = ""
    for msg in reversed(messages):
        content = getattr(msg, "content", "") if hasattr(msg, "content") else str(msg)
        if "[NEED_CLARIFICATION]" in content:
            # 去掉标记本身，保留解释部分
            coordinator_content = _CLARIFICATION_TAG_RE.sub("", content).strip()
            break

    user_query = state.get("research_topic", "")
    if not user_query and messages:
        # 回退：取第一条用户消息
        for msg in messages:
            if getattr(msg, "type", None) == "human" or (
                isinstance(msg, dict) and msg.get("role") == "user"
            ):
                user_query = getattr(msg, "content", "") if hasattr(msg, "content") else msg.get("content", "")
                break

    enhanced_logger.logger.info(
        f"📝 CLARIFICATION_INPUT | user_query='{user_query}' | "
        f"coordinator_reasoning='{coordinator_content[:100]}'"
    )

    # 2. 用 LLM 生成多个澄清问题（每个 3 选项 + 1 自定义）
    try:
        prompt_text = _GENERATE_OPTIONS_PROMPT.format(
            user_query=user_query,
            coordinator_reasoning=coordinator_content,
        )
        llm = get_llm_by_type(AGENT_LLM_MAP["coordinator"])
        response = llm.invoke([{"role": "user", "content": prompt_text}])
        raw_content = response.content if hasattr(response, "content") else str(response)
    
        # 尝试从回复中解析 JSON
        parsed = _extract_json(raw_content)
        questions_raw = parsed.get("questions", [])
    
        # 兼容旧格式（单问题）
        if not questions_raw and parsed.get("question"):
            questions_raw = [{"question": parsed["question"], "options": parsed.get("options", [])}]
    
        # 校验 + 兑底
        if not questions_raw or len(questions_raw) == 0:
            questions_raw = [{
                "question": "请问您想研究哪个方面？",
                "options": [
                    f"方向一：{coordinator_content[:30]}",
                    "方向二：综合分析",
                    "方向三：行业对比",
                ]
            }]
    
    except Exception as e:
        enhanced_logger.logger.warning(f"⚠️ LLM生成选项失败，使用兑底选项: {e}")
        questions_raw = [{
            "question": "请问您想研究哪个方面？",
            "options": [
                f"关于 {user_query} 的行业概况",
                f"关于 {user_query} 的发展趋势",
                f"关于 {user_query} 的竞争格局",
            ]
        }]
    
    # 3. 构造多问题结构（每个问题 3 AI + "以上都是" + 自定义）
    questions = []
    for q in questions_raw[:3]:  # 最多 3 个问题
        q_text = q.get("question", "请选择")
        opts_text = q.get("options", [])
        if len(opts_text) < 2:
            opts_text = ["选项A", "选项B", "选项C"]
        options = [
            {"text": opt, "value": opt, "editable": False}
            for opt in opts_text[:3]
        ]
        # "以上都是" 选项：将所有 AI 选项拼接为答案
        all_values = ";".join(opts_text[:3])
        options.append({"text": "以上都是", "value": all_values, "editable": False})
        options.append({"text": "自定义答案", "value": "", "editable": True})
        questions.append({"question": q_text, "options": options})
    
    enhanced_logger.logger.info(
        f"✅ CLARIFICATION_OPTIONS | questions_count={len(questions)} | "
        f"first_question='{questions[0]['question']}'"
    )
    
    # 4. interrupt 暂停，返回多问题给前端
    user_answer = interrupt({
        "questions": questions,
        "type": "clarification",
    })

    enhanced_logger.logger.info(
        f"📥 CLARIFICATION_FEEDBACK | user_answer='{user_answer}'"
    )

    # 5. 用户反馈回来后，将所有答案拼接为新的研究主题
    # user_answer 可能是字符串（单答案兼容）或 JSON 字符串（多答案）
    if isinstance(user_answer, str):
        try:
            answers = json.loads(user_answer)
            if isinstance(answers, list):
                # 多答案：拼接为完整的研究方向描述
                new_research_topic = "；".join(answers)
            else:
                new_research_topic = user_answer
        except (json.JSONDecodeError, TypeError):
            new_research_topic = user_answer
    else:
        new_research_topic = str(user_answer) if user_answer else user_query

    updated_messages = list(messages) + [
        HumanMessage(content=new_research_topic)
    ]

    duration = time.time() - start_time
    enhanced_logger.logger.info(
        f"✅ NODE_EXIT | clarification | 澄清完成，重回 coordinator | "
        f"new_topic='{new_research_topic}' | 耗时={duration:.2f}s"
    )

    # 递增澄清轮次
    current_rounds = state.get("clarification_rounds", 0)

    return Command(
        update={
            "messages": updated_messages,
            "research_topic": new_research_topic,
            "clarification_rounds": current_rounds + 1,
        },
        goto="coordinator",
    )


def _extract_json(text: str) -> dict:
    """从 LLM 回复中提取 JSON 对象，支持 markdown 代码块包裹和嵌套结构。"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试从 ```json ... ``` 中提取（支持嵌套 {})
    match = re.search(r"```(?:json)?\s*(\{.+\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # 尝试找第一个完整的 JSON 对象（支持嵌套）
    # 找到第一个 { 后通过括号匹配找到对应的 }
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except (json.JSONDecodeError, TypeError):
                        break

    return {}
