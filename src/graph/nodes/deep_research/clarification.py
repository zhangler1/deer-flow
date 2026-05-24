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

from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.utils.enhanced_logger import get_enhanced_logger


logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger("graph.nodes.clarification")

# 用于从 coordinator 回复中提取澄清要点的正则
_CLARIFICATION_TAG_RE = re.compile(r"\[NEED_CLARIFICATION\]\s*", re.IGNORECASE)

# LLM 生成选项的提示词
_GENERATE_OPTIONS_PROMPT = """你是一个问题澄清助手。根据用户的模糊问题和协调者的判断，生成 3 个最可能的研究方向选项。

用户的原始问题：{user_query}

协调者的判断：{coordinator_reasoning}

请严格按以下 JSON 格式输出（不要包含其他内容）：
{{
  "question": "一句话描述你想问用户的澄清问题",
  "options": ["选项一的描述", "选项二的描述", "选项三的描述"]
}}

要求：
- question 要简洁明了，让用户一眼明白你在问什么
- 每个选项要具体、有区分度，代表不同的研究方向
- 选项用中文描述，每个不超过 30 字
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

    # 2. 用 LLM 生成 3 个澄清选项
    try:
        prompt_text = _GENERATE_OPTIONS_PROMPT.format(
            user_query=user_query,
            coordinator_reasoning=coordinator_content,
        )
        llm = get_llm_by_type("basic")
        response = llm.invoke([{"role": "user", "content": prompt_text}])
        raw_content = response.content if hasattr(response, "content") else str(response)

        # 尝试从回复中解析 JSON
        parsed = _extract_json(raw_content)
        question = parsed.get("question", "请问您想研究哪个方面？")
        options_text = parsed.get("options", [])

        # 兜底：如果解析失败，用 coordinator 的原始内容
        if not options_text or len(options_text) < 2:
            question = "请问您想研究哪个方面？"
            options_text = [
                f"方向一：{coordinator_content[:30]}",
                f"方向二：综合分析",
                f"方向三：行业对比",
            ]

    except Exception as e:
        enhanced_logger.logger.warning(f"⚠️ LLM生成选项失败，使用兜底选项: {e}")
        question = "请问您想研究哪个方面？"
        options_text = [
            f"关于 {user_query} 的行业概况",
            f"关于 {user_query} 的发展趋势",
            f"关于 {user_query} 的竞争格局",
        ]

    # 3. 构造 4 个选项（3 AI + 1 自定义）
    options = [
        {"text": opt, "value": opt, "editable": False}
        for opt in options_text[:3]
    ]
    options.append({"text": "自定义答案", "value": "", "editable": True})

    enhanced_logger.logger.info(
        f"✅ CLARIFICATION_OPTIONS | question='{question}' | "
        f"options_count={len(options)}"
    )

    # 4. interrupt 暂停，返回选项给前端
    user_answer = interrupt({
        "question": question,
        "options": options,
        "type": "clarification",
    })

    enhanced_logger.logger.info(
        f"📥 CLARIFICATION_FEEDBACK | user_answer='{user_answer}'"
    )

    # 5. 用户反馈回来后，将答案作为新的用户消息，重回 coordinator
    # 将 research_topic 更新为用户选择的具体方向
    new_research_topic = user_answer if user_answer else user_query
    updated_messages = list(messages) + [
        HumanMessage(content=new_research_topic)
    ]

    duration = time.time() - start_time
    enhanced_logger.logger.info(
        f"✅ NODE_EXIT | clarification | 澄清完成，重回 coordinator | "
        f"new_topic='{new_research_topic}' | 耗时={duration:.2f}s"
    )

    return Command(
        update={
            "messages": updated_messages,
            "research_topic": new_research_topic,
        },
        goto="coordinator",
    )


def _extract_json(text: str) -> dict:
    """从 LLM 回复中提取 JSON 对象，支持 markdown 代码块包裹。"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试从 ```json ... ``` 中提取
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # 尝试找第一个 { ... } 块
    match = re.search(r"\{[^{}]*\"question\"[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            pass

    return {}
