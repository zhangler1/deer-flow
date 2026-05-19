# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
工具错误处理中间件（对齐 DeerFlow 2.0 ToolErrorHandlingMiddleware）

功能：
- wrap_tool_call: 捕获工具执行异常，转换为错误 ToolMessage（不崩溃）
- after_tool: 对工具返回的错误结果做格式化增强
- 统计工具错误频率
- 连续错误时注入提示引导 LLM 换策略
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.agents.middleware import AgentMiddleware

logger = logging.getLogger(__name__)


# 工具错误的标记前缀（ReactLoop 中生成）
TOOL_ERROR_PREFIX = "工具执行错误:"


@dataclass
class ToolErrorConfig:
    """工具错误处理配置"""
    # 单个工具连续错误多少次后注入引导提示
    consecutive_error_warn: int = 3
    # 错误消息最大长度（截断过长的 traceback）
    error_max_chars: int = 500
    # 是否在错误消息中添加建议
    add_suggestions: bool = True


class ToolErrorHandlingMiddleware(AgentMiddleware):
    """工具错误处理中间件
    
    功能：
    1. wrap_tool_call: 捕获工具执行异常，转换为错误 ToolMessage
    2. after_tool: 检测工具错误，格式化错误消息，统计错误频率
    3. 连续错误时注入系统提示引导 LLM 换策略
    
    Usage:
        middleware = ToolErrorHandlingMiddleware(config=ToolErrorConfig())
    """
    
    def __init__(self, config: ToolErrorConfig = None):
        self.config = config or ToolErrorConfig()
        
        # session 级统计
        self._tool_errors: dict[str, int] = {}  # tool_name -> error_count
        self._consecutive_errors: int = 0
        self._total_errors: int = 0
    
    async def before_agent(self, messages: list, context: dict) -> list:
        """重置 loop 级状态"""
        self._consecutive_errors = 0
        return messages
    
    async def wrap_tool_call(
        self, tool_name: str, tool_args: dict, tool_call_id: str,
        call_next: Callable, context: dict
    ) -> ToolMessage:
        """捕获工具执行异常，转换为错误 ToolMessage
        
        确保工具异常不会导致 ReactLoop 崩溃，
        而是返回包含错误信息的 ToolMessage，让 LLM 可以看到并调整策略。
        """
        try:
            return await call_next(tool_name, tool_args, tool_call_id)
        except Exception as e:
            logger.warning(f"⚠️ 工具 {tool_name} 执行异常: {type(e).__name__}: {str(e)[:300]}")
            error_content = f"{TOOL_ERROR_PREFIX} {type(e).__name__}: {str(e)[:300]}"
            return ToolMessage(
                content=error_content,
                tool_call_id=tool_call_id,
                name=tool_name,
            )
    
    async def after_tool(self, messages: list, tool_results: list[Any], iteration: int, context: dict) -> list:
        """处理工具执行结果中的错误"""
        has_error = False
        
        for tool_msg in tool_results:
            if not isinstance(tool_msg, ToolMessage):
                continue
            
            content = tool_msg.content or ""
            tool_name = getattr(tool_msg, "name", "unknown")
            
            # 检测是否是错误消息
            if self._is_error_message(content):
                has_error = True
                self._total_errors += 1
                self._tool_errors[tool_name] = self._tool_errors.get(tool_name, 0) + 1
                self._consecutive_errors += 1
                
                # 格式化错误消息（截断过长内容 + 添加建议）
                tool_msg.content = self._format_error(content, tool_name)
                
                logger.info(
                    f"⚠️ ToolError | 第 {iteration+1} 轮 | "
                    f"工具: {tool_name} | 累计错误: {self._tool_errors[tool_name]} | "
                    f"连续错误: {self._consecutive_errors}"
                )
        
        if not has_error:
            self._consecutive_errors = 0
        
        # 连续错误过多时注入引导提示
        if self._consecutive_errors >= self.config.consecutive_error_warn:
            messages.append(HumanMessage(
                content=(
                    f"⚠️ 系统提示：已连续 {self._consecutive_errors} 次工具调用失败。"
                    f"请考虑：1) 换一个工具 2) 修改参数重试 3) 基于已有信息直接回答。"
                    f"不要反复使用相同的失败参数。"
                ),
                name="system",
            ))
            logger.warning(
                f"💡 ToolError 引导提示注入 | 连续失败 {self._consecutive_errors} 次"
            )
        
        return messages
    
    async def after_agent(self, messages: list, context: dict) -> list:
        """记录统计"""
        if self._total_errors > 0:
            logger.info(
                f"📊 ToolErrorHandling 统计 | "
                f"总错误: {self._total_errors} | "
                f"各工具: {dict(self._tool_errors)}"
            )
        return messages
    
    @staticmethod
    def _is_error_message(content: str) -> bool:
        """判断工具返回内容是否是错误消息"""
        error_markers = [
            TOOL_ERROR_PREFIX,
            "错误:",
            "Error:",
            "Exception:",
            "Traceback",
            "未知工具",
            "[系统] 工具",  # DanglingToolCallMiddleware 注入的
        ]
        for marker in error_markers:
            if marker in content:
                return True
        return False
    
    def _format_error(self, content: str, tool_name: str) -> str:
        """格式化错误消息"""
        # 截断过长的错误信息
        max_chars = self.config.error_max_chars
        if len(content) > max_chars:
            content = content[:max_chars] + "\n... [错误信息已截断]"
        
        # 添加建议
        if self.config.add_suggestions:
            error_count = self._tool_errors.get(tool_name, 0)
            if error_count >= 2:
                content += (
                    f"\n\n💡 提示：工具 '{tool_name}' 已失败 {error_count} 次，"
                    f"建议尝试其他方式获取信息。"
                )
        
        return content
