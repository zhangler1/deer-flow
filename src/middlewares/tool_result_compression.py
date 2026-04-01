# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
工具结果压缩中间件

专门针对工具调用返回结果进行压缩，减少上下文长度，同时保留关键信息。
- 只压缩 ToolMessage，不影响用户输入和 AI 分析
- 支持基于消息数量或 token 数量的触发条件
- 保留最近 N 条工具消息的完整内容，旧消息进行截断或摘要
"""

import logging
from typing import List, Any, Dict
from copy import deepcopy
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.language_models import BaseChatModel

from src.config.tool_compression_config import (
    get_tool_compression_config,
    ToolCompressionConfig,
    TriggerCondition
)

logger = logging.getLogger(__name__)


class ToolResultCompressionMiddleware:
    """工具结果压缩中间件
    
    在 agent 执行过程中监控消息历史，当达到触发条件时，
    自动压缩旧的工具调用结果，保留最近的完整内容。
    """

    def __init__(self, config: ToolCompressionConfig | None = None, llm: BaseChatModel | None = None):
        """初始化中间件
        
        Args:
            config: 压缩配置，如果为 None 则从全局配置加载
            llm: 用于生成摘要的语言模型（可选）
        """
        self.config = config or get_tool_compression_config()
        self.llm = llm
        self.logger = logging.getLogger(__name__)

    def estimate_token_count(self, messages: List[BaseMessage]) -> int:
        """估算消息列表的 token 数量
        
        使用简单的字符数估算：约 4 个字符 = 1 token
        这是一个粗略估算，实际 token 数可能有所不同。
        
        Args:
            messages: 消息列表
            
        Returns:
            int: 估算的 token 数量
        """
        total_chars = 0
        for msg in messages:
            if hasattr(msg, 'content') and msg.content:
                total_chars += len(str(msg.content))
        
        # 粗略估算：4 个字符约等于 1 个 token
        return total_chars // 4

    def should_compress(self, messages: List[BaseMessage]) -> bool:
        """检查是否应该进行压缩
        
        根据配置的触发条件（消息数量或 token 数量）判断。
        任一条件满足即触发压缩（OR 逻辑）。
        
        Args:
            messages: 当前消息列表
            
        Returns:
            bool: 如果应该压缩返回 True
        """
        if not self.config.enabled:
            return False
        
        if not self.config.trigger:
            return False
        
        # 检查所有触发条件（OR 逻辑）
        for condition in self.config.trigger:
            if condition.type == "messages":
                if len(messages) >= condition.value:
                    self.logger.info(
                        f"🔔 COMPRESSION_TRIGGER | 消息数量达到阈值 | "
                        f"当前: {len(messages)} | 阈值: {condition.value}"
                    )
                    return True
            
            elif condition.type == "tokens":
                token_count = self.estimate_token_count(messages)
                if token_count >= condition.value:
                    self.logger.info(
                        f"🔔 COMPRESSION_TRIGGER | Token 数量达到阈值 | "
                        f"当前: {token_count} | 阈值: {condition.value}"
                    )
                    return True
        
        return False

    def extract_tool_messages(self, messages: List[BaseMessage]) -> List[tuple[int, ToolMessage]]:
        """提取所有工具消息及其索引
        
        Args:
            messages: 消息列表
            
        Returns:
            List[tuple[int, ToolMessage]]: (索引, 工具消息) 的列表
        """
        tool_messages = []
        for idx, msg in enumerate(messages):
            if isinstance(msg, ToolMessage):
                tool_messages.append((idx, msg))
        return tool_messages

    def compress_tool_message(self, tool_msg: ToolMessage, max_length: int) -> ToolMessage:
        """压缩单个工具消息
        
        将工具消息内容截断到指定长度，并添加截断提示。
        
        Args:
            tool_msg: 原始工具消息
            max_length: 最大保留长度
            
        Returns:
            ToolMessage: 压缩后的工具消息
        """
        content = str(tool_msg.content)
        
        if len(content) <= max_length:
            return tool_msg
        
        # 截断内容并添加提示
        compressed_content = content[:max_length] + f"\n\n... [已截断，原始长度: {len(content)} 字符] ..."
        
        # 创建新的压缩消息
        compressed_msg = ToolMessage(
            content=compressed_content,
            tool_call_id=tool_msg.tool_call_id if hasattr(tool_msg, 'tool_call_id') else None,
            name=tool_msg.name if hasattr(tool_msg, 'name') else None,
        )
        
        return compressed_msg

    def compress_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """压缩消息列表中的工具消息
        
        保留最近 N 条工具消息的完整内容，旧的工具消息进行截断。
        不修改其他类型的消息（HumanMessage、AIMessage 等）。
        
        Args:
            messages: 原始消息列表
            
        Returns:
            List[BaseMessage]: 压缩后的消息列表
        """
        if not self.should_compress(messages):
            return messages
        
        # 提取所有工具消息
        tool_messages = self.extract_tool_messages(messages)
        
        if not tool_messages:
            self.logger.debug("📭 COMPRESSION_SKIP | 没有工具消息需要压缩")
            return messages
        
        # 计算需要压缩的工具消息
        recent_keep_count = self.config.keep.recent_tool_messages
        max_content_length = self.config.keep.max_content_per_tool
        
        # 确定哪些工具消息需要压缩
        total_tool_count = len(tool_messages)
        compress_count = max(0, total_tool_count - recent_keep_count)
        
        if compress_count == 0:
            self.logger.info(
                f"📭 COMPRESSION_SKIP | 工具消息数量未超过保留阈值 | "
                f"当前: {total_tool_count} | 保留: {recent_keep_count}"
            )
            return messages
        
        # 创建新的消息列表（深拷贝避免修改原列表）
        new_messages = deepcopy(messages)
        
        # 压缩旧的工具消息
        compressed_indices = []
        for i in range(compress_count):
            idx, tool_msg = tool_messages[i]
            original_length = len(str(tool_msg.content))
            
            # 压缩消息
            compressed_msg = self.compress_tool_message(tool_msg, max_content_length)
            new_messages[idx] = compressed_msg
            
            compressed_length = len(str(compressed_msg.content))
            compressed_indices.append(idx)
            
            self.logger.debug(
                f"  🗜️  工具消息 #{i+1}/{compress_count} | "
                f"索引: {idx} | "
                f"原始: {original_length} 字符 → 压缩后: {compressed_length} 字符"
            )
        
        self.logger.info(
            f"✅ COMPRESSION_COMPLETE | "
            f"压缩了 {compress_count}/{total_tool_count} 条工具消息 | "
            f"保留最近 {recent_keep_count} 条完整内容"
        )
        
        return new_messages

    def process_messages_before_invoke(
        self,
        messages: List[BaseMessage]
    ) -> List[BaseMessage]:
        """在 agent 调用前处理消息
        
        这是中间件的主要入口点，在 agent.ainvoke 前调用。
        
        Args:
            messages: 原始消息列表
            
        Returns:
            List[BaseMessage]: 处理后的消息列表
        """
        if not self.config.enabled:
            self.logger.debug("⏸️  COMPRESSION_DISABLED | 工具结果压缩未启用")
            return messages
        
        self.logger.debug(
            f"📊 COMPRESSION_CHECK | "
            f"消息数: {len(messages)} | "
            f"估算 tokens: {self.estimate_token_count(messages)}"
        )
        
        return self.compress_messages(messages)


async def invoke_with_tool_compression(
    agent: Any,
    input_data: Dict[str, Any],
    config: Dict[str, Any],
    compression_config: ToolCompressionConfig | None = None,
    llm: BaseChatModel | None = None
) -> Any:
    """使用工具结果压缩中间件执行 agent
    
    这是一个便捷函数，自动应用压缩中间件。
    
    Args:
        agent: LangGraph agent
        input_data: 输入数据
        config: 运行配置
        compression_config: 压缩配置（可选）
        llm: 用于摘要的语言模型（可选）
        
    Returns:
        Any: agent 执行结果
    """
    middleware = ToolResultCompressionMiddleware(
        config=compression_config,
        llm=llm
    )
    
    # 处理输入消息
    messages = input_data.get("messages", [])
    processed_messages = middleware.process_messages_before_invoke(messages)
    
    # 如果消息被修改，更新输入数据
    if processed_messages != messages:
        logger.info("🔄 COMPRESSION_APPLIED | 消息已压缩，更新输入数据")
        input_data = dict(input_data)
        input_data["messages"] = processed_messages
    
    # 执行 agent
    result = await agent.ainvoke(input_data, config)
    
    return result


__all__ = [
    "ToolResultCompressionMiddleware",
    "invoke_with_tool_compression",
]
