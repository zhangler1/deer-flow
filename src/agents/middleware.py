# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
Agent 中间件基类

对齐 DeerFlow 2.0 的 AgentMiddleware 设计，为 ReactLoop 提供钩子机制。
中间件通过继承 AgentMiddleware 并重写钩子方法来扩展 ReactLoop 的行为。

执行顺序:
    before_agent(所有中间件, 仅一次)
        for iteration:
            before_model(所有中间件)
            -> wrap_model_call(洋葱链) -> LLM调用
            -> after_model(所有中间件)
            -> wrap_tool_call(洋葱链) -> 工具执行
            -> after_tool(所有中间件)
    after_agent(所有中间件, 仅一次)
"""

import logging
from typing import Any, Callable

from langchain_core.messages import AIMessage, ToolMessage
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger


class AgentMiddleware:
    """Agent 中间件基类（对齐 DeerFlow 2.0 命名）
    
    所有钩子方法都有默认的 no-op 实现，子类只需重写需要的钩子。
    所有钩子均为异步方法，支持在内部执行异步操作（如 LLM 调用）。
    
    Usage:
        class MyMiddleware(AgentMiddleware):
            async def before_model(self, messages, iteration, context):
                # 修改消息列表
                return messages
    """
    
    @property
    def name(self) -> str:
        """中间件名称（用于日志）"""
        return self.__class__.__name__
    
    async def before_agent(self, messages: list, context: dict) -> list:
        """Agent 执行前（仅一次）
        
        适用场景:
        - 初始化中间件内部状态
        - 对初始消息做预处理
        
        Args:
            messages: 初始消息列表
            context: 共享上下文字典，可在此存入中间件需要的状态
            
        Returns:
            处理后的消息列表
        """
        return messages
    
    async def before_model(self, messages: list, iteration: int, context: dict) -> list:
        """每轮 LLM 调用前执行
        
        适用场景:
        - 上下文压缩（检查 token 数，超限则压缩）
        - 注入动态提示
        - 审计/过滤消息
        
        Args:
            messages: 当前消息列表
            iteration: 当前迭代轮次（从 0 开始）
            context: 共享上下文字典
            
        Returns:
            处理后的消息列表（将传递给 LLM）
        """
        return messages
    
    async def after_model(self, response: AIMessage, messages: list, iteration: int, context: dict) -> bool:
        """每轮 LLM 响应后执行
        
        适用场景:
        - 循环检测（检查重复 tool_calls）
        - 内容审查
        - 自定义停止条件
        
        Args:
            response: LLM 返回的 AIMessage
            messages: 包含 response 在内的完整消息列表
            iteration: 当前迭代轮次
            context: 共享上下文字典
            
        Returns:
            True = 强制停止循环, False = 继续
        """
        return False
    
    async def after_tool(self, messages: list, tool_results: list[Any], iteration: int, context: dict) -> list:
        """每轮工具执行后执行
        
        适用场景:
        - 即时压缩工具返回结果（避免 token 爆炸）
        - 过滤或转换工具结果
        - 记录工具调用统计
        
        Args:
            messages: 包含工具结果在内的完整消息列表
            tool_results: 本轮新增的 ToolMessage 列表
            iteration: 当前迭代轮次
            context: 共享上下文字典
            
        Returns:
            处理后的消息列表
        """
        return messages
    
    async def wrap_model_call(
        self, messages: list, call_next: Callable, context: dict
    ) -> AIMessage:
        """包装 LLM 调用（洋葱模型）
        
        通过装饰器模式包装实际的 LLM 调用，可在调用前后执行任意逻辑，
        也可以完全替换调用行为（如重试、熔断）。
        
        多个中间件的 wrap_model_call 形成洋葱链：
            mw1.wrap -> mw2.wrap -> ... -> 实际 LLM 调用
        
        适用场景:
        - 重试 + 熔断（LLMErrorHandlingMiddleware）
        - 调用耗时统计
        - 请求/响应日志
        
        Args:
            messages: 传递给 LLM 的消息列表
            call_next: 下一层调用（下一个中间件的 wrap 或实际 LLM 调用）
            context: 共享上下文字典
            
        Returns:
            LLM 返回的 AIMessage
        """
        return await call_next(messages)
    
    async def wrap_tool_call(
        self, tool_name: str, tool_args: dict, tool_call_id: str,
        call_next: Callable, context: dict
    ) -> ToolMessage:
        """包装工具调用（洋葱模型）
        
        通过装饰器模式包装实际的工具调用，可在调用前后执行任意逻辑，
        也可以捕获异常并转换为错误 ToolMessage。
        
        多个中间件的 wrap_tool_call 形成洋葱链：
            mw1.wrap -> mw2.wrap -> ... -> 实际工具调用
        
        适用场景:
        - 工具异常捕获与错误转换（ToolErrorHandlingMiddleware）
        - 工具调用超时控制
        - 工具调用日志
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            tool_call_id: 工具调用 ID
            call_next: 下一层调用（下一个中间件的 wrap 或实际工具调用）
            context: 共享上下文字典
            
        Returns:
            工具返回的 ToolMessage
        """
        return await call_next(tool_name, tool_args, tool_call_id)
    
    async def after_agent(self, messages: list, context: dict) -> list:
        """Agent 执行后（仅一次）
        
        适用场景:
        - 最终清理
        - 统计汇总
        - 后处理（如移除系统注入的消息）
        
        Args:
            messages: 最终消息列表
            context: 共享上下文字典
            
        Returns:
            处理后的消息列表
        """
        return messages
