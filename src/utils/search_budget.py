# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
搜索预算管理器

提供搜索次数和token消耗的预算管理，防止研究过程中因搜索过多导致上下文溢出。
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
from langchain_core.messages import BaseMessage, AIMessage

logger = logging.getLogger(__name__)


@dataclass
class BudgetConfig:
    """预算配置"""
    max_search_calls: int = 10  # 最大搜索调用次数
    max_tokens: int = 12000     # 最大token数量（预警阈值）
    hard_token_limit: int = 16000  # 硬token限制（强制停止）
    token_chars_ratio: float = 2.5  # 字符数/token比例（估算，纯中文场景）


@dataclass
class BudgetStatus:
    """预算状态"""
    search_calls_used: int = 0
    estimated_tokens: int = 0
    can_search: bool = True
    remaining_search_calls: int = 0
    remaining_tokens: int = 0
    warning_level: int = 0  # 0:正常, 1:警告, 2:严格限制, 3:已超限


class SearchBudgetManager:
    """搜索预算管理器
    
    跟踪搜索次数和token消耗，提供预算检查和预警功能。
    
    使用示例:
        budget_manager = SearchBudgetManager(max_search_calls=10, max_tokens=12000)
        
        # 检查是否可以搜索
        if budget_manager.can_search(messages):
            result = await search_tool.ainvoke(query)
            budget_manager.record_search_call()
        
        # 获取剩余预算
        status = budget_manager.get_budget_status(messages)
        print(f"剩余搜索次数: {status.remaining_search_calls}")
    """

    def __init__(
        self,
        max_search_calls: int = 10,
        max_tokens: int = 12000,
        hard_token_limit: int = 16000,
        token_chars_ratio: float = 2.5,
    ):
        """初始化预算管理器
        
        Args:
            max_search_calls: 最大搜索调用次数（软限制）
            max_tokens: 最大token数量预警阈值
            hard_token_limit: 硬token限制，超过后强制停止
            token_chars_ratio: 字符数/token比例，用于估算token消耗
        """
        self.config = BudgetConfig(
            max_search_calls=max_search_calls,
            max_tokens=max_tokens,
            hard_token_limit=hard_token_limit,
            token_chars_ratio=token_chars_ratio,
        )
        self._search_calls_used = 0
        logger.info(
            f"🔧 SearchBudgetManager initialized | "
            f"max_calls: {max_search_calls}, max_tokens: {max_tokens}, "
            f"hard_limit: {hard_token_limit}, token_chars_ratio: {token_chars_ratio}"
        )

    def estimate_tokens(self, messages: list[BaseMessage]) -> int:
        """估算消息列表的token数量
        
        使用字符数/token_chars_ratio的粗略估算方法。
        默认比例为2.5，适合纯中文场景（中英混合建议3.0，纯英文建议4.0）。
        
        Args:
            messages: 消息列表
            
        Returns:
            int: 估算的token数量
        """
        total_chars = sum(
            len(str(msg.content)) 
            for msg in messages 
            if hasattr(msg, 'content') and msg.content
        )
        return int(total_chars / self.config.token_chars_ratio)

    def count_tool_calls(self, messages: list[BaseMessage]) -> int:
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

    def can_search(self, messages: list[BaseMessage]) -> bool:
        """检查是否还可以进行搜索
        
        检查条件：
        1. 搜索调用次数未超过软限制
        2. token数量未超过硬限制
        
        Args:
            messages: 当前消息列表
            
        Returns:
            bool: 如果可以搜索返回True
        """
        status = self.get_budget_status(messages)
        
        # 🔥 添加预算检查日志
        if not status.can_search:
            logger.warning(
                f"🛑 BUDGET_LIMIT_REACHED | 预算已耗尽 | "
                f"搜索次数: {status.search_calls_used}/{self.config.max_search_calls} | "
                f"Tokens: {status.estimated_tokens}/{self.config.hard_token_limit} | "
                f"警告级别: {status.warning_level}"
            )
        elif status.warning_level > 0:
            logger.debug(
                f"💡 BUDGET_WARNING | 预算使用警告 | "
                f"搜索次数: {status.search_calls_used}/{self.config.max_search_calls} | "
                f"Tokens: {status.estimated_tokens}/{self.config.max_tokens} | "
                f"警告级别: {status.warning_level} | "
                f"剩余搜索: {status.remaining_search_calls}次"
            )
        
        return status.can_search

    def get_remaining_budget(self, messages: list[BaseMessage]) -> dict:
        """获取剩余预算信息
        
        Args:
            messages: 当前消息列表
            
        Returns:
            dict: 包含剩余搜索次数和token数的字典
        """
        status = self.get_budget_status(messages)
        return {
            "remaining_search_calls": status.remaining_search_calls,
            "remaining_tokens": status.remaining_tokens,
            "search_calls_used": status.search_calls_used,
            "estimated_tokens": status.estimated_tokens,
            "warning_level": status.warning_level,
        }

    def get_budget_status(self, messages: list[BaseMessage]) -> BudgetStatus:
        """获取完整的预算状态
        
        Args:
            messages: 当前消息列表
            
        Returns:
            BudgetStatus: 预算状态对象
        """
        # 从消息中统计实际的工具调用次数
        actual_tool_calls = self.count_tool_calls(messages)
        # 使用实际统计和记录值的较大者
        self._search_calls_used = max(self._search_calls_used, actual_tool_calls)
        
        estimated_tokens = self.estimate_tokens(messages)
        
        # 计算剩余预算
        remaining_calls = max(0, self.config.max_search_calls - self._search_calls_used)
        remaining_tokens = max(0, self.config.max_tokens - estimated_tokens)
        
        # 确定警告级别
        warning_level = 0
        if self._search_calls_used >= self.config.max_search_calls * 1.2 or \
           estimated_tokens >= self.config.hard_token_limit:
            warning_level = 3  # 已超限，强制停止
        elif self._search_calls_used >= self.config.max_search_calls or \
             estimated_tokens >= self.config.max_tokens:
            warning_level = 2  # 严格限制
        elif self._search_calls_used >= self.config.max_search_calls * 0.8 or \
             estimated_tokens >= self.config.max_tokens * 0.8:
            warning_level = 1  # 警告
        
        # 是否可以搜索
        can_search = (
            self._search_calls_used < self.config.max_search_calls and
            estimated_tokens < self.config.hard_token_limit
        )
        
        return BudgetStatus(
            search_calls_used=self._search_calls_used,
            estimated_tokens=estimated_tokens,
            can_search=can_search,
            remaining_search_calls=remaining_calls,
            remaining_tokens=remaining_tokens,
            warning_level=warning_level,
        )

    def record_search_call(self) -> None:
        """记录一次搜索调用"""
        self._search_calls_used += 1

    def get_warning_message(self, messages: list[BaseMessage]) -> Optional[str]:
        """根据当前状态获取警告消息
        
        Args:
            messages: 当前消息列表
            
        Returns:
            Optional[str]: 警告消息，如果没有警告返回None
        """
        status = self.get_budget_status(messages)
        
        if status.warning_level == 3:
            return (
                f"🛑 搜索预算已耗尽！\n"
                f"已使用 {status.search_calls_used}/{self.config.max_search_calls} 次搜索，\n"
                f"约 {status.estimated_tokens} tokens。\n"
                f"请立即停止搜索，输出最终答案。"
            )
        elif status.warning_level == 2:
            return (
                f"⚠️ 搜索预算即将耗尽！\n"
                f"已使用 {status.search_calls_used}/{self.config.max_search_calls} 次搜索，\n"
                f"约 {status.estimated_tokens} tokens。\n"
                f"建议立即总结并输出答案。"
            )
        elif status.warning_level == 1:
            return (
                f"💡 搜索预算已使用80%以上。\n"
                f"已使用 {status.search_calls_used}/{self.config.max_search_calls} 次搜索，\n"
                f"请考虑尽快完成搜索并输出答案。"
            )
        return None

    def reset(self) -> None:
        """重置预算计数器"""
        old_count = self._search_calls_used
        self._search_calls_used = 0
        logger.info(
            f"🔄 BUDGET_RESET | 预算计数器已清零 | "
            f"之前使用: {old_count}次 | "
            f"限制: {self.config.max_search_calls}次 | "
            f"Tokens限制: {self.config.max_tokens}"
        )


# 便捷函数：创建默认配置的预算管理器
def create_budget_manager(
    max_search_calls: int = 10,
    max_tokens: int = 12000,
) -> SearchBudgetManager:
    """创建搜索预算管理器
    
    Args:
        max_search_calls: 最大搜索调用次数
        max_tokens: 最大token数量
        
    Returns:
        SearchBudgetManager: 预算管理器实例
    """
    return SearchBudgetManager(
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
    )
