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
    """
    
    def __init__(self, ttl_seconds: int = 3600):
        """初始化存储
        
        Args:
            ttl_seconds: 预算管理器的存活时间（秒），默认1小时
        """
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()  # 可重入锁，支持嵌套锁定
        self._ttl_seconds = ttl_seconds
        
    def get_or_create(
        self, 
        session_id: str, 
        max_search_calls: int = 10, 
        max_tokens: int = 12000
    ) -> SearchBudgetManager:
        """获取或创建预算管理器（线程安全）
        
        Args:
            session_id: 会话ID
            max_search_calls: 最大搜索调用次数
            max_tokens: 最大token数量
            
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
            
            # 创建新的管理器
            manager = SearchBudgetManager(
                max_search_calls=max_search_calls,
                max_tokens=max_tokens,
            )
            self._store[session_id] = {
                'manager': manager,
                'created_at': now,
                'last_accessed': now,
                'session_id': session_id,
            }
            logger.info(f"🔧 BudgetManager created for session: {session_id}")
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
            logger.info(f"🧹 Expired BudgetManager cleared for session: {key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息
        
        Returns:
            Dict: 统计信息
        """
        with self._lock:
            return {
                'total_sessions': len(self._store),
                'session_ids': list(self._store.keys()),
                'ttl_seconds': self._ttl_seconds,
            }


# 全局存储实例（单例模式）
_budget_store = BudgetManagerStore(ttl_seconds=3600)  # 1小时TTL


# ============================================================================
# 对外接口（保持向后兼容）
# ============================================================================

def get_budget_manager(session_id: str, max_search_calls: int = 10, max_tokens: int = 12000) -> SearchBudgetManager:
    """获取或创建预算管理器（线程安全）
    
    Args:
        session_id: 会话ID
        max_search_calls: 最大搜索调用次数
        max_tokens: 最大token数量
        
    Returns:
        SearchBudgetManager: 预算管理器实例
    """
    return _budget_store.get_or_create(session_id, max_search_calls, max_tokens)


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
            
            # 调用被包装的工具
            result = self.wrapped_tool._run(query, run_manager=run_manager)
            
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
