# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
工具调用限制中间件

在 LangGraph agent 执行过程中动态监控工具调用次数，
当达到限制时在消息流中插入停止提示，让 LLM 自然完成而不是被强制停止。
"""

import logging
from typing import Any, Dict, List, Callable
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from copy import deepcopy

logger = logging.getLogger(__name__)


class ToolCallLimitMiddleware:
    """工具调用限制中间件

    包装 agent 的输入，在执行过程中监控工具调用次数，
    当达到限制时自动插入停止消息。
    """

    def __init__(self, max_calls: int = 10):
        """初始化中间件

        Args:
            max_calls: 最大工具调用次数
        """
        self.max_calls = max_calls
        self.call_count = 0

    def count_tool_calls_in_messages(self, messages: List[BaseMessage]) -> int:
        """统计消息列表中的工具调用次数

        Args:
            messages: 消息列表

        Returns:
            int: 工具调用总次数
        """
        count = 0
        for msg in messages:
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                count += len(msg.tool_calls)
        return count

    def should_add_stop_message(self, messages: List[BaseMessage]) -> bool:
        """检查是否应该添加停止消息

        Args:
            messages: 当前消息列表

        Returns:
            bool: 如果应该添加返回 True
        """
        tool_call_count = self.count_tool_calls_in_messages(messages)
        self.call_count = tool_call_count

        # 如果工具调用次数达到或超过限制
        if tool_call_count >= self.max_calls:
            # 检查最后一条消息是否是 AI 消息且有工具调用
            if messages and isinstance(messages[-1], AIMessage):
                if hasattr(messages[-1], 'tool_calls') and messages[-1].tool_calls:
                    logger.warning(
                        f"⚠️  TOOL_LIMIT_REACHED | 已调用 {tool_call_count} 次 | "
                        f"限制: {self.max_calls} | 将插入停止消息"
                    )
                    return True

        return False

    def create_stop_message(self, tool_names: List[str]) -> HumanMessage:
        """创建停止消息

        Args:
            tool_names: 已调用的工具名称列表

        Returns:
            HumanMessage: 停止消息
        """
        return HumanMessage(
            content=(
                f"\n\n【系统提示 - 请完成分析】\n\n"
                f"你已经进行了 {self.call_count} 次工具调用，已经收集了足够的信息。\n\n"
                f"**建议现在停止搜索，开始输出最终答案**：\n\n"
                f"✅ 请执行以下操作：\n"
                f"   1. 综合分析已收集的所有搜索结果\n"
                f"   2. 整理关键信息和数据\n"
                f"   3. 输出完整、结构化的最终答案\n\n"
                f"❌ 不要继续操作：\n"
                f"   - 不要再调用搜索工具\n"
                f"   - 不要获取更多信息\n\n"
                f"你现在可以开始输出最终答案了。"
            ),
            name="tool_limit_advisor"
        )

    def inject_stop_message_if_needed(
        self,
        messages: List[BaseMessage]
    ) -> List[BaseMessage]:
        """如果需要，在消息列表中注入停止消息

        Args:
            messages: 原始消息列表

        Returns:
            List[BaseMessage]: 可能包含停止消息的新列表
        """
        if not self.should_add_stop_message(messages):
            return messages

        # 收集已使用的工具名称
        tool_names = []
        for msg in messages:
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown')
                    if tool_name not in tool_names:
                        tool_names.append(tool_name)

        # 创建停止消息
        stop_msg = self.create_stop_message(tool_names)

        # 返回新的消息列表（深拷贝避免修改原列表）
        new_messages = deepcopy(messages)
        new_messages.append(stop_msg)

        logger.info(f"✅ STOP_MESSAGE_INJECTED | 消息数: {len(messages)} -> {len(new_messages)}")

        return new_messages


async def invoke_with_tool_limit_advisor(
    agent: Any,
    input_data: Dict[str, Any],
    config: Dict[str, Any],
    max_tool_calls: int = 10
) -> Any:
    """执行 agent 并在达到工具调用限制时插入停止消息

    注意：这是一个简化版本。实际上我们需要在 LangGraph 的递归执行中
    动态检查和插入消息，这需要更复杂的实现。

    Args:
        agent: LangGraph agent
        input_data: 输入数据
        config: 运行配置
        max_tool_calls: 最大工具调用次数

    Returns:
        Any: agent 执行结果
    """
    middleware = ToolCallLimitMiddleware(max_calls=max_tool_calls)

    # 在输入中检查
    messages = input_data.get("messages", [])
    modified_messages = middleware.inject_stop_message_if_needed(messages)

    if modified_messages != messages:
        # 如果消息被修改了，更新输入
        logger.info("🛑 TOOL_LIMIT_PRE_INVOKE | 在输入中检测到工具调用超限，已插入停止消息")
        input_data = dict(input_data)
        input_data["messages"] = modified_messages
        # 不改变 recursion_limit，让 agent 自然完成
    else:
        logger.info(f"✅ TOOL_LIMIT_OK | 工具调用次数正常，开始执行 agent")

    # 正常执行 agent
    result = await agent.ainvoke(input_data, config)

    return result


__all__ = [
    "ToolCallLimitMiddleware",
    "invoke_with_tool_limit_advisor",
]
