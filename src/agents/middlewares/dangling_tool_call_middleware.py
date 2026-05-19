# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
悬空工具调用修复中间件（对齐 DeerFlow 2.0 DanglingToolCallMiddleware）

问题场景：
- Agent 在某轮返回了包含 tool_calls 的 AIMessage，但因异常/中断/网络问题，
  对应的 ToolMessage 从未生成。
- 后续 LLM 调用时，发现消息链中有 tool_call 但无 ToolMessage，直接报错。

解决方案：
- 在 before_model 时扫描消息历史，找到所有"悬空"的 tool_call
- 为缺失的 ToolMessage 注入合成的错误消息，让 LLM 能继续工作
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from src.agents.middleware import AgentMiddleware

logger = logging.getLogger(__name__)


class DanglingToolCallMiddleware(AgentMiddleware):
    """悬空工具调用修复中间件
    
    在每轮 LLM 调用前（before_model），扫描消息列表：
    - 找到所有 AIMessage 中的 tool_call_id
    - 找到所有 ToolMessage 的 tool_call_id
    - 对缺失 ToolMessage 的 tool_call，注入合成的错误消息
    
    这样 LLM 不会因为消息链断裂而报错，还能看到错误信息做出补偿决策。
    
    Usage:
        middleware = DanglingToolCallMiddleware()
    """
    
    def __init__(self):
        self._patches_count = 0
    
    async def before_agent(self, messages: list, context: dict) -> list:
        """重置统计"""
        self._patches_count = 0
        return messages
    
    async def before_model(self, messages: list, iteration: int, context: dict) -> list:
        """扫描并修复悬空的 tool_calls"""
        patched = self._build_patched_messages(messages)
        if patched is not messages:
            self._patches_count += 1
            logger.warning(
                f"🔧 DanglingToolCall 修复 | 第 {iteration+1} 轮 | "
                f"注入合成 ToolMessage | 累计修复 {self._patches_count} 次"
            )
        return patched
    
    def _build_patched_messages(self, messages: list) -> list:
        """构建修复后的消息列表
        
        逻辑：
        1. 收集所有已存在的 ToolMessage 的 tool_call_id
        2. 遍历消息，对每个包含 tool_calls 的 AIMessage，
           检查是否所有 tool_call 都有对应的 ToolMessage
        3. 对缺失的 tool_call，在 AIMessage 之后立即插入合成的错误 ToolMessage
        """
        # 收集已有的 ToolMessage IDs
        existing_tool_msg_ids = set()
        for msg in messages:
            if isinstance(msg, ToolMessage):
                existing_tool_msg_ids.add(msg.tool_call_id)
            elif isinstance(msg, dict) and msg.get("type") == "tool":
                existing_tool_msg_ids.add(msg.get("tool_call_id", ""))
        
        # 检查是否有悬空的 tool_call
        has_dangling = False
        for msg in messages:
            tool_calls = self._extract_tool_calls(msg)
            if tool_calls:
                for tc in tool_calls:
                    tc_id = tc.get("id", "")
                    if tc_id and tc_id not in existing_tool_msg_ids:
                        has_dangling = True
                        break
            if has_dangling:
                break
        
        if not has_dangling:
            return messages  # 返回原始引用，表示没有修改
        
        # 构建修复后的消息列表
        patched = []
        for msg in messages:
            patched.append(msg)
            
            tool_calls = self._extract_tool_calls(msg)
            if not tool_calls:
                continue
            
            # 对每个缺失 ToolMessage 的 tool_call 注入合成消息
            for tc in tool_calls:
                tc_id = tc.get("id", "")
                if tc_id and tc_id not in existing_tool_msg_ids:
                    tool_name = tc.get("name", "unknown_tool")
                    synthetic = ToolMessage(
                        content=self._synthetic_error_content(tool_name),
                        tool_call_id=tc_id,
                        name=tool_name,
                    )
                    patched.append(synthetic)
                    # 标记为已处理，避免重复注入
                    existing_tool_msg_ids.add(tc_id)
                    logger.debug(f"  ↳ 注入合成 ToolMessage | tool_call_id={tc_id} | tool={tool_name}")
        
        return patched
    
    @staticmethod
    def _extract_tool_calls(msg) -> list:
        """从消息中提取 tool_calls 列表"""
        if isinstance(msg, AIMessage):
            return msg.tool_calls or []
        if isinstance(msg, dict):
            return msg.get("tool_calls", []) or []
        return []
    
    @staticmethod
    def _synthetic_error_content(tool_name: str) -> str:
        """生成合成的错误内容"""
        return (
            f"[系统] 工具 '{tool_name}' 的调用被中断或未能完成。"
            f"这可能是由于网络超时、资源不可用或前一轮执行异常导致。"
            f"请根据已有信息继续工作，或尝试使用其他方式获取所需数据。"
        )
