# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
预算控制的搜索工具包装器

在 React 框架下，大模型自主决定工具调用。本模块通过包装搜索工具，
在工具执行层实现预算控制，当预算不足时返回提示信息给模型。

状态管理：
- 使用线程安全的数据结构存储预算管理器
- 按 session_id 隔离不同用户的预算状态
- 支持内存存储（默认）和外部存储（Redis等）
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Type
from functools import wraps
from datetime import datetime, timedelta

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

from src.utils.search_budget import SearchBudgetManager
from src.tools.custom_search import CustomSearchTool

logger = logging.getLogger(__name__)


# ============================================================================
# 线程安全的预算管理器存储
# ============================================================================

class BudgetManagerStore:
    """线程安全的预算管理器存储类
    
    解决多用户并发访问时的竞态条件问题。
    使用读写锁确保线程安全。
    
    特性：
    - TTL 自动过期：默认 20 分钟无访问后自动清理
    - 容量限制：最多存储 1000 个 session，防止内存溢出
    - LRU 驱逐：达到容量上限时清理最久未访问的 session
    """
    
    def __init__(self, ttl_seconds: int = 1200, max_sessions: int = 100):
        """初始化存储
        
        Args:
            ttl_seconds: 预算管理器的存活时间（秒），默认20分钟
            max_sessions: 最大存储的 session 数量，默认 1000
        """
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()  # 可重入锁，支持嵌套锁定
        self._ttl_seconds = ttl_seconds
        self._max_sessions = max_sessions
        
    def get_or_create(
        self, 
        session_id: str, 
        max_search_calls: int = 10, 
        max_tokens: int = 12000,
        token_chars_ratio: float = 3.0,
    ) -> SearchBudgetManager:
        """获取或创建预算管理器（线程安全）
        
        Args:
            session_id: 会话ID
            max_search_calls: 最大搜索调用次数
            max_tokens: 最大token数量
            token_chars_ratio: 字符数/token比例，用于估算token消耗
            
        Returns:
            SearchBudgetManager: 预算管理器实例
        """
        with self._lock:
            now = datetime.now()
            
            # 清理过期的管理器
            self._cleanup_expired(now)
            
            # 检查是否存在且未过期
            if session_id in self._store:
                entry = self._store[session_id]
                entry['last_accessed'] = now  # 更新访问时间
                logger.debug(f"🔧 BudgetManager retrieved for session: {session_id}")
                return entry['manager']
            
            # 容量检查：如果超过最大数量，先清理最久未访问的 session（LRU驱逐）
            if len(self._store) >= self._max_sessions:
                self._cleanup_oldest()
            
            # 创建新的管理器
            manager = SearchBudgetManager(
                max_search_calls=max_search_calls,
                max_tokens=max_tokens,
                token_chars_ratio=token_chars_ratio,
            )
            self._store[session_id] = {
                'manager': manager,
                'created_at': now,
                'last_accessed': now,
                'session_id': session_id,
            }
            logger.info(
                f"🔧 BudgetManager created for session: {session_id} | "
                f"Total sessions: {len(self._store)}/{self._max_sessions}"
            )
            return manager
    
    def get(self, session_id: str) -> Optional[SearchBudgetManager]:
        """获取预算管理器（线程安全）
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[SearchBudgetManager]: 预算管理器实例，不存在返回None
        """
        with self._lock:
            if session_id in self._store:
                self._store[session_id]['last_accessed'] = datetime.now()
                return self._store[session_id]['manager']
            return None
    
    def clear(self, session_id: str) -> bool:
        """清除预算管理器（线程安全）
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功清除
        """
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]
                logger.info(f"🧹 BudgetManager cleared for session: {session_id}")
                return True
            return False
    
    def clear_all(self) -> int:
        """清除所有预算管理器
        
        Returns:
            int: 清除的管理器数量
        """
        with self._lock:
            count = len(self._store)
            self._store.clear()
            logger.info(f"🧹 All BudgetManagers cleared, total: {count}")
            return count
    
    def _cleanup_expired(self, now: datetime) -> None:
        """清理过期的预算管理器
        
        Args:
            now: 当前时间
        """
        expired_keys = []
        for session_id, entry in self._store.items():
            if now - entry['last_accessed'] > timedelta(seconds=self._ttl_seconds):
                expired_keys.append(session_id)
        
        for key in expired_keys:
            del self._store[key]
        
        if expired_keys:
            logger.info(
                f"🧹 CLEANUP_EXPIRED | Cleared {len(expired_keys)} expired sessions | "
                f"Remaining: {len(self._store)}/{self._max_sessions}"
            )
    
    def _cleanup_oldest(self, count: int = 100) -> None:
        """清理最久未访问的 session，防止内存溢出（LRU驱逐）
        
        Args:
            count: 清理的数量，默认 100
        """
        if not self._store:
            return
        
        # 按最后访问时间排序，获取最久未访问的 session
        sorted_sessions = sorted(
            self._store.items(),
            key=lambda x: x[1]['last_accessed']
        )
        
        # 清理最旧的 count 个 session
        removed_count = 0
        for session_id, _ in sorted_sessions[:count]:
            del self._store[session_id]
            removed_count += 1
        
        logger.warning(
            f"⚠️ CLEANUP_OLDEST | Capacity limit reached! "
            f"Cleared {removed_count} oldest sessions | "
            f"Remaining: {len(self._store)}/{self._max_sessions}"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息
        
        Returns:
            Dict: 统计信息
        """
        with self._lock:
            return {
                'total_sessions': len(self._store),
                'max_sessions': self._max_sessions,
                'capacity_usage': f"{len(self._store)}/{self._max_sessions} ({len(self._store)/self._max_sessions*100:.1f}%)",
                'session_ids': list(self._store.keys()),
                'ttl_seconds': self._ttl_seconds,
            }


# 全局存储实例（单例模式）
# TTL=20分钟，最多 1000 个 session，防止内存溢出
_budget_store = BudgetManagerStore(ttl_seconds=1200, max_sessions=100)


# ============================================================================
# 对外接口（保持向后兼容）
# ============================================================================

def get_budget_manager(
    session_id: str, 
    max_search_calls: int = 10, 
    max_tokens: int = 12000,
    token_chars_ratio: float = 2.5,
) -> SearchBudgetManager:
    """获取或创建预算管理器（线程安全）
    
    Args:
        session_id: 会话ID
        max_search_calls: 最大搜索调用次数
        max_tokens: 最大token数量
        token_chars_ratio: 字符数/token比例，用于估算token消耗
        
    Returns:
        SearchBudgetManager: 预算管理器实例
    """
    return _budget_store.get_or_create(session_id, max_search_calls, max_tokens, token_chars_ratio)


def clear_budget_manager(session_id: str) -> bool:
    """清除预算管理器（线程安全）
    
    Args:
        session_id: 会话ID
        
    Returns:
        bool: 是否成功清除
    """
    return _budget_store.clear(session_id)


def get_budget_store_stats() -> Dict[str, Any]:
    """获取预算存储统计信息
    
    Returns:
        Dict: 统计信息
    """
    return _budget_store.get_stats()


class BudgetControlledSearchInput(BaseModel):
    """预算控制搜索工具的输入"""
    query: str = Field(description="搜索查询字符串")


class BudgetControlledSearchTool(BaseTool):
    """预算控制的搜索工具
    
    包装原始搜索工具，在执行前检查预算。
    当预算不足时，返回提示信息给模型，而不是执行搜索。
    
    使用示例:
        # 创建原始工具
        original_tool = online_search_tool(max_results=5)
        
        # 包装为预算控制工具
        budget_tool = BudgetControlledSearchTool(
            wrapped_tool=original_tool,
            session_id="session_123",
            max_search_calls=10,
        )
    """
    
    name: str = "online_search"
    description: str = "搜索互联网公开信息。适用于查询最新新闻、公开资讯、行业动态等。当系统提示搜索预算不足时，请立即停止搜索并基于已有信息回答问题。"
    args_schema: Type[BaseModel] = BudgetControlledSearchInput
    
    # 被包装的工具
    wrapped_tool: BaseTool = Field(exclude=True)
    
    # 预算配置
    session_id: str = Field(default="default")
    max_search_calls: int = Field(default=10)
    max_tokens: int = Field(default=12000)
    
    def __init__(self, wrapped_tool: BaseTool, session_id: str = "default", 
                 max_search_calls: int = 10, max_tokens: int = 12000, **kwargs):
        """初始化预算控制工具
        
        Args:
            wrapped_tool: 被包装的原始搜索工具
            session_id: 会话ID，用于隔离不同会话的预算
            max_search_calls: 最大搜索调用次数
            max_tokens: 最大token数量
        """
        # 从被包装工具复制属性
        kwargs['name'] = wrapped_tool.name
        kwargs['description'] = wrapped_tool.description
        kwargs['wrapped_tool'] = wrapped_tool
        kwargs['session_id'] = session_id
        kwargs['max_search_calls'] = max_search_calls
        kwargs['max_tokens'] = max_tokens
        
        super().__init__(**kwargs)
        
        # 确保预算管理器存在
        get_budget_manager(session_id, max_search_calls, max_tokens)
        
        logger.info(
            f"🔧 BudgetControlledSearchTool initialized | "
            f"session: {session_id} | max_calls: {max_search_calls}"
        )
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """执行搜索（带预算控制）
        
        流程：
        1. 检查预算状态
        2. 如果预算充足，执行原始搜索工具
        3. 如果预算不足，返回提示信息
        """
        # 获取预算管理器
        budget = get_budget_manager(
            self.session_id, 
            self.max_search_calls, 
            self.max_tokens
        )
        
        # 获取当前消息上下文（从run_manager或state）
        # 注意：这里简化处理，实际可能需要从state获取完整消息
        messages = []  # 简化处理，实际应从state获取
        
        # 检查预算状态
        if not budget.can_search(messages):
            status = budget.get_budget_status(messages)
            warning_msg = budget.get_warning_message(messages)
            
            logger.warning(
                f"🛑 SEARCH_BLOCKED | session: {self.session_id} | "
                f"calls: {status.search_calls_used}/{self.max_search_calls} | "
                f"tokens: {status.estimated_tokens}/{self.max_tokens}"
            )
            
            # 返回预算不足的提示信息给模型
            return {
                "status": "budget_exhausted",
                "message": warning_msg or "搜索预算已耗尽，请基于已有信息回答问题。",
                "search_calls_used": status.search_calls_used,
                "max_search_calls": self.max_search_calls,
                "suggestion": "请立即停止搜索，综合分析已收集的信息并输出最终答案。"
            }
        
        # 预算充足，执行原始搜索
        try:
            logger.info(f"🔍 SEARCH_EXECUTING | session: {self.session_id} | query: '{query}'")
            
            # 调用被包装的工具（统一签名支持）
            result = self.wrapped_tool._run(query, run_manager=run_manager, config=config, **kwargs)
            
            # 记录搜索调用
            budget.record_search_call()
            
            # 获取更新后的预算状态
            status = budget.get_budget_status(messages)
            remaining = budget.get_remaining_budget(messages)
            
            logger.info(
                f"✅ SEARCH_COMPLETED | session: {self.session_id} | "
                f"remaining_calls: {remaining['remaining_search_calls']} | "
                f"warning_level: {remaining['warning_level']}"
            )
            
            # 如果接近预算限制，在结果中添加警告
            if remaining['warning_level'] >= 1:
                warning = budget.get_warning_message(messages)
                if isinstance(result, dict):
                    result['_budget_warning'] = warning
                    result['_remaining_calls'] = remaining['remaining_search_calls']
                elif isinstance(result, list):
                    # 在列表结果中添加警告信息
                    result.append({
                        "_budget_warning": warning,
                        "_remaining_calls": remaining['remaining_search_calls'],
                        "_type": "system_notice"
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ SEARCH_ERROR | session: {self.session_id} | error: {e}")
            raise


def create_budget_controlled_search_tool(
    wrapped_tool: BaseTool,
    session_id: str = "default",
    max_search_calls: int = 10,
    max_tokens: int = 12000,
) -> BudgetControlledSearchTool:
    """创建预算控制的搜索工具
    
    便捷函数，用于包装现有搜索工具。
    
    Args:
        wrapped_tool: 原始搜索工具
        session_id: 会话ID
        max_search_calls: 最大搜索调用次数
        max_tokens: 最大token数量
        
    Returns:
        BudgetControlledSearchTool: 预算控制工具
    """
    return BudgetControlledSearchTool(
        wrapped_tool=wrapped_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
    )


def budget_controlled_financial_summary_tool(
    session_id: str = "default",
    max_search_calls: int = 10,
    max_tokens: int = 12000,
) -> BudgetControlledSearchTool:
    """创建预算控制的财务数据汇总工具
    
    Args:
        session_id: 会话ID
        max_search_calls: 最大搜索调用次数
        max_tokens: 最大token数量
        
    Returns:
        BudgetControlledSearchTool: 预算控制的财务数据汇总工具
    """
    from src.tools.financial_summary import financial_summary
    
    original_tool = financial_summary
    
    return create_budget_controlled_search_tool(
        wrapped_tool=original_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
    )


def budget_controlled_product_instance_search_tool(
    session_id: str = "default",
    max_search_calls: int = 10,
    max_tokens: int = 12000,
) -> BudgetControlledSearchTool:
    """创建预算控制的产品实例搜索工具
    
    Args:
        session_id: 会话ID
        max_search_calls: 最大搜索调用次数
        max_tokens: 最大token数量
        
    Returns:
        BudgetControlledSearchTool: 预算控制的产品实例搜索工具
    """
    from src.tools.product_instance_search import product_instance_search
    
    original_tool = product_instance_search
    
    return create_budget_controlled_search_tool(
        wrapped_tool=original_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
    )


def budget_controlled_product_search_tool(
    session_id: str = "default",
    max_search_calls: int = 10,
    max_tokens: int = 12000,
) -> BudgetControlledSearchTool:
    """创建预算控制的产品搜索工具
    
    Args:
        session_id: 会话ID
        max_search_calls: 最大搜索调用次数
        max_tokens: 最大token数量
        
    Returns:
        BudgetControlledSearchTool: 预算控制的产品搜索工具
    """
    from src.tools.product_search import product_search
    
    original_tool = product_search
    
    return create_budget_controlled_search_tool(
        wrapped_tool=original_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
    )


# 便捷函数：创建预算控制的 online_search 工具
def budget_controlled_online_search_tool(
    max_results: int = 10,
    session_id: str = "default",
    max_search_calls: int = 10,
    max_tokens: int = 12000,
) -> BudgetControlledSearchTool:
    """创建预算控制的联网搜索工具
    
    Args:
        max_results: 最大搜索结果数
        session_id: 会话ID
        max_search_calls: 最大搜索调用次数
        max_tokens: 最大token数量
        
    Returns:
        BudgetControlledSearchTool: 预算控制的搜索工具
    """
    from src.tools.online_search import online_search_tool
    
    original_tool = online_search_tool(max_results=max_results)
    
    return create_budget_controlled_search_tool(
        wrapped_tool=original_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
    )
