# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
动态上下文注入中间件（对齐 DeerFlow 2.0 命名）

在 ReactLoop 循环开始前注入系统级动态信息（当前日期、系统角色提示等），
并标记为 protected 确保不会被上下文摘要中间件压缩化。

注入的消息对 LLM 可见但对前端隐藏（hide_from_ui=True）。
"""

import logging
from datetime import datetime
from typing import Optional

from langchain_core.messages import HumanMessage

from src.agents.middleware import AgentMiddleware

logger = logging.getLogger(__name__)


class DynamicContextMiddleware(AgentMiddleware):
    """动态上下文注入中间件
    
    功能：
    - before_agent: 注入一条系统级提示消息（日期 + 自定义 hint）
    - 消息标记为 protected，不会被 SummarizationMiddleware 压缩
    
    未来扩展：
    - 技能系统加载后，技能内容也通过此中间件注入
    - 用户记忆/偏好注入
    
    Usage:
        middleware = DynamicContextMiddleware(system_hint="你是一个金融研究助理")
    """
    
    def __init__(self, system_hint: str = ""):
        """
        Args:
            system_hint: 自定义系统提示（如角色说明），为空则只注入日期
        """
        self.system_hint = system_hint
    
    async def before_agent(self, messages: list, context: dict) -> list:
        """在循环开始前注入动态上下文"""
        reminder = self._build_reminder()
        # 插入到消息列表最前面（系统 prompt 之后、用户消息之前）
        # 寻找第一条非 system 消息的位置插入
        insert_idx = self._find_insert_position(messages)
        messages.insert(insert_idx, reminder)
        logger.debug(f"📌 DynamicContext 已注入 | 位置: {insert_idx} | 内容长度: {len(reminder.content)}")
        return messages
    
    def _build_reminder(self) -> HumanMessage:
        """构建动态上下文消息"""
        current_time = datetime.now().strftime("%Y年%m月%d日 %A")
        
        parts = ["<system-context>"]
        parts.append(f"当前时间: {current_time}")
        
        if self.system_hint:
            parts.append(f"系统角色: {self.system_hint}")
        
        parts.append("</system-context>")
        
        content = "\n".join(parts)
        
        return HumanMessage(
            content=content,
            name="system_context",
            additional_kwargs={
                "protected": True,
                "hide_from_ui": True,
            },
        )
    
    @staticmethod
    def _find_insert_position(messages: list) -> int:
        """找到合适的插入位置（第一条 system 消息之后）
        
        如果第一条消息是 system role，则插在它后面；
        否则插在最前面。
        """
        if not messages:
            return 0
        
        first = messages[0]
        # 检查是否是 system 消息
        if isinstance(first, dict):
            if first.get("role") == "system":
                return 1
        elif hasattr(first, "type") and first.type == "system":
            return 1
        
        return 0
