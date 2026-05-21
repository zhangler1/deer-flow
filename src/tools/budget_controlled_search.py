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
from typing import Annotated, Any, Dict, List, Optional, Type
from functools import wraps
from datetime import datetime, timedelta

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

from src.utils.search_budget import SearchBudgetManager

# 尝试导入 LangGraph 的 InjectedState；导入失败时用占位，
# 保证非 LangGraph 环境下原有行为不被破坏。
try:
    from langgraph.prebuilt import InjectedState  # type: ignore
    _INJECTED_STATE_AVAILABLE = True
except Exception:  # noqa: BLE001
    InjectedState = None  # type: ignore
    _INJECTED_STATE_AVAILABLE = False

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
        hard_token_limit: int = 16000,
    ) -> SearchBudgetManager:
        """获取或创建预算管理器（线程安全）
        
        Args:
            session_id: 会话ID
            max_search_calls: 最大搜索调用次数
            max_tokens: 最大token数量（软警告阈值）
            token_chars_ratio: 字符数/token比例，用于估算token消耗
            hard_token_limit: 硬token限制（超过此值强制拦截搜索）
            
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
                hard_token_limit=hard_token_limit,
                token_chars_ratio=token_chars_ratio,
            )
            self._store[session_id] = {
                'manager': manager,
                'created_at': now,
                'last_accessed': now,
                'session_id': session_id,
            }

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
            logger.debug(
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
    hard_token_limit: int = 16000,
) -> SearchBudgetManager:
    """获取或创建预算管理器（线程安全）
    
    Args:
        session_id: 会话ID
        max_search_calls: 最大搜索调用次数
        max_tokens: 最大token数量（软警告阈值）
        token_chars_ratio: 字符数/token比例，用于估算token消耗
        hard_token_limit: 硬token限制（超过此值强制拦截搜索）
        
    Returns:
        SearchBudgetManager: 预算管理器实例
    """
    return _budget_store.get_or_create(
        session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
        token_chars_ratio=token_chars_ratio,
        hard_token_limit=hard_token_limit,
    )


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


if _INJECTED_STATE_AVAILABLE:
    class BudgetControlledSearchInput(BaseModel):
        """预算控制搜索工具的输入

        state 字段由 LangGraph ToolNode 自动注入，不暴露给 LLM。
        作用：拿到真实的 state["messages"]，以便计算 token 消耗并触发 token 硬限。
        """
        query: str = Field(description="搜索查询字符串")
        state: Annotated[Optional[dict], InjectedState] = Field(
            default=None,
            description="(内部) LangGraph 自动注入的 agent state",
        )
else:
    class BudgetControlledSearchInput(BaseModel):
        """预算控制搜索工具的输入（无 LangGraph 环境回退版）"""
        query: str = Field(description="搜索查询字符串")


class BocomSearchBaseTool(BaseTool):
    """交行搜索基础工具，适配 BudgetControlledSearchTool 包装
    
    封装 call_bocomsearch 函数为 LangChain BaseTool 接口，
    使其可被 BudgetControlledSearchTool 包装并纳入预算控制。
    """
    name: str = "bocomsearch"
    description: str = "搜索交通银行内部知识库。适用于查询银行政策、产品信息、业务流程、合规要求等内部资料。"
    repository: str = "bocom-search"
    max_results: int = 10
    guwp_token: Optional[str] = None
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """执行交行搜索"""
        from src.tools.bocom_search import call_bocomsearch
        token_preview = (self.guwp_token[:8] + "...") if self.guwp_token and len(self.guwp_token) > 8 else self.guwp_token
        logger.info(f"🔑 bocomsearch | guwp_token={token_preview} | max_results={self.max_results}")
        return call_bocomsearch(
            query=query,
            guwp_token=self.guwp_token,
            max_results=self.max_results,
        )


class BudgetControlledSearchTool(BaseTool):
    """预算控制的搜索工具包装器
    
    在 React 框架下，大模型自主决定工具调用。本工具通过包装原始搜索工具，
    在执行层实现预算控制：当预算充足时正常执行搜索，当预算不足时返回提示信息。
    
    核心机制：
    - 包装任意 BaseTool（online_search / bocomsearch / report_search 等）
    - 从 wrapped_tool 自动继承 name / description，对外透明
    - 按 session_id 隔离不同用户的预算状态
    - 搜索前检查预算，搜索后扣减预算
    
    使用示例:
        # 方式1：通过便捷函数创建
        tool = budget_controlled_online_search_tool(max_results=5, session_id="s1")
        
        # 方式2：手动包装
        original_tool = online_search_tool(max_results=5)
        tool = BudgetControlledSearchTool(
            wrapped_tool=original_tool,
            session_id="s1",
            max_search_calls=3,
        )
    """
    
    # 默认值仅作 Pydantic 占位，__init__ 中会被 wrapped_tool 的属性覆盖
    name: str = "budget_controlled_search"
    description: str = "预算控制的搜索工具"
    args_schema: Type[BaseModel] = BudgetControlledSearchInput
    
    # 被包装的工具
    wrapped_tool: BaseTool = Field(exclude=True)
    
    # 预算配置
    session_id: str = Field(default="default")
    max_search_calls: int = Field(default=10)
    max_tokens: int = Field(default=12000)
    hard_token_limit: int = Field(default=16000)
    
    def __init__(self, wrapped_tool: BaseTool, session_id: str = "default", 
                 max_search_calls: int = 10, max_tokens: int = 12000,
                 hard_token_limit: int = 16000, **kwargs):
        """初始化预算控制工具
        
        Args:
            wrapped_tool: 被包装的原始搜索工具（online_search / bocomsearch 等）
            session_id: 会话ID，用于隔离不同会话的预算
            max_search_calls: 最大搜索调用次数
            max_tokens: 最大token数量（软警告阈值）
            hard_token_limit: 硬token限制（超过此值强制拦截搜索）
        """
        # 从被包装工具继承 name / description，对外保持透明
        kwargs['name'] = wrapped_tool.name
        kwargs['description'] = wrapped_tool.description
        kwargs['wrapped_tool'] = wrapped_tool
        kwargs['session_id'] = session_id
        kwargs['max_search_calls'] = max_search_calls
        kwargs['max_tokens'] = max_tokens
        kwargs['hard_token_limit'] = hard_token_limit
        
        super().__init__(**kwargs)
        
        # 确保预算管理器存在（将 hard_token_limit 一并透传）
        get_budget_manager(
            session_id,
            max_search_calls=max_search_calls,
            max_tokens=max_tokens,
            hard_token_limit=hard_token_limit,
        )
        
        logger.info(
            f"🔧 BudgetControlledSearchTool 初始化 | "
            f"工具={wrapped_tool.name} | session={session_id} | max_calls={max_search_calls}"
        )
    
    @property
    def repository(self) -> str:
        """获取被包装工具的仓库标识（用于日志）"""
        return getattr(self.wrapped_tool, 'repository', 'N/A')
    
    def _run(
        self,
        query: str,
        state: Optional[dict] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """执行搜索（带预算控制）
        
        流程：
        1. 检查预算状态（包含 token 硬限）→ 不足则拦截
        2. 预算充足 → 执行原始搜索工具
        3. 扣减预算 → 在结果中附加预算警告（如接近上限）

        参数说明：
            state: 由 LangGraph ToolNode 通过 InjectedState 自动注入的 agent state，
                LLM 不可见。用于提取当前消息历史以计算 token 消耗，
                触发 hard_token_limit 拦截。非 LangGraph 环境时为 None，
                自动回退为空消息列表（行为同修复前一致）。
        """
        budget = get_budget_manager(
            self.session_id,
            max_search_calls=self.max_search_calls,
            max_tokens=self.max_tokens,
            hard_token_limit=self.hard_token_limit,
        )

        # 🔧 从 InjectedState 提取真实消息，驱动 token 硬限检查
        # 回退策略：无 state（直调 / 旧环境 / InjectedState 未生效）时仍然可用，
        # 仅 token 硬限检查退化（与原行为一致）。
        messages: list = []
        if state:
            raw_msgs = state.get("messages") if isinstance(state, dict) else getattr(state, "messages", None)
            if raw_msgs:
                messages = list(raw_msgs)

        # ── 1. 预算检查（同时检查次数与 token） ──
        if not budget.can_search(messages):
            return self._build_budget_exhausted_response(budget, messages)

        # ── 2. 执行搜索 ──
        # 注意：state 不透传给 wrapped_tool（其大多数不认识该参数）
        try:
            # 外层不再重复输出“🔍 搜索”日志，由内层 wrapped_tool 统一报告搜索入口；
            # session 信息随后随“💰 预算扣减”一起输出，避免重复。
            result = self.wrapped_tool._run(query, run_manager=run_manager, config=config, **kwargs)

            # ── 3. 扣减预算 ──
            budget.record_search_call()
            status = budget.get_budget_status(messages)
            remaining = budget.get_remaining_budget(messages)

            # 外层：报预算扣减结果；同时输出 token 估算，便于观测 token 硬限工作情况。
            logger.info(
                f"💰 {self.name} | 预算扣减 | "
                f"session={self.session_id} | "
                f"剩余={remaining['remaining_search_calls']}/{self.max_search_calls} | "
                f"tokens~{status.estimated_tokens}/{budget.config.hard_token_limit}"
            )

            # 接近预算上限时，在结果中附加警告
            if remaining['warning_level'] >= 1:
                self._attach_budget_warning(result, budget, messages, remaining)

            return result

        except Exception as e:
            logger.error(f"❌ {self.name} | 搜索异常 | session={self.session_id} | error={e}")
            raise
    
    
    def _build_budget_exhausted_response(self, budget: SearchBudgetManager, messages: list) -> dict:
        """构建预算耗尽的响应

        关键设计：通过 ToolMessage content 明确告知 LLM 预算已耗尽，避免后续重复调用。
        响应中包含强停止指令（FINAL_NOTICE）和结构化字段（budget_exhausted=True），
        供下游中间件（如 LoopDetectionMiddleware）识别后强制路由到总结阶段。
        """
        status = budget.get_budget_status(messages)
        warning_msg = budget.get_warning_message(messages)

        logger.warning(
            f"🛑 {self.name} | 预算耗尽 | session={self.session_id} | "
            f"已用={status.search_calls_used}/{self.max_search_calls} | "
            f"tokens={status.estimated_tokens}/{self.max_tokens}"
        )

        # 强停止信号：LLM 看到此消息后必须停止搜索
        final_notice = (
            f"⛔ FINAL_NOTICE | 搜索预算已耗尽，禁止再次调用任何搜索工具。\n"
            f"已用搜索次数: {status.search_calls_used}/{self.max_search_calls}\n"
            f"已用 tokens: {status.estimated_tokens}/{self.max_tokens}\n"
            f"任何后续搜索工具调用都将被系统拒绝并返回相同消息。\n"
            f"请立即基于已收集的信息综合分析并输出最终答案，不要再尝试搜索。"
        )

        return {
            "status": "budget_exhausted",
            "budget_exhausted": True,  # 结构化标记，便于中间件识别
            "message": final_notice,
            "warning": warning_msg or "搜索预算已耗尽",
            "search_calls_used": status.search_calls_used,
            "max_search_calls": self.max_search_calls,
            "estimated_tokens": status.estimated_tokens,
            "max_tokens": self.max_tokens,
            "suggestion": (
                "严禁再次调用任何搜索工具。请立即综合分析已收集的信息，"
                "按用户要求的格式输出最终报告。如信息不足，请如实说明缺口而非继续搜索。"
            ),
        }
    
    
    def _attach_budget_warning(self, result: Any, budget: SearchBudgetManager, 
                                 messages: list, remaining: dict) -> None:
        """在搜索结果中附加预算警告（原地修改）"""
        warning = budget.get_warning_message(messages)
        warning_info = {
            "_budget_warning": warning,
            "_remaining_calls": remaining['remaining_search_calls'],
            "_type": "system_notice"
        }
        if isinstance(result, dict):
            result['_budget_warning'] = warning
            result['_remaining_calls'] = remaining['remaining_search_calls']
        elif isinstance(result, list):
            result.append(warning_info)


def create_budget_controlled_search_tool(
    wrapped_tool: BaseTool,
    session_id: str = "default",
    max_search_calls: int = 10,
    max_tokens: int = 12000,
    hard_token_limit: int = 16000,
) -> BudgetControlledSearchTool:
    """创建预算控制的搜索工具
    
    便捷函数，用于包装现有搜索工具。
    
    Args:
        wrapped_tool: 原始搜索工具
        session_id: 会话ID
        max_search_calls: 最大搜索调用次数
        max_tokens: 最大token数量（软警告阈值）
        hard_token_limit: 硬token限制（超过此值强制拦截搜索）
        
    Returns:
        BudgetControlledSearchTool: 预算控制工具
    """
    return BudgetControlledSearchTool(
        wrapped_tool=wrapped_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
        hard_token_limit=hard_token_limit,
    )


def budget_controlled_financial_summary_tool(
    session_id: str = "default",
    max_search_calls: int = 10,
    max_tokens: int = 12000,
    hard_token_limit: int = 16000,
) -> BudgetControlledSearchTool:
    """创建预算控制的财务数据汇总工具"""
    from src.tools.financial_summary import financial_summary
    
    original_tool = financial_summary
    
    return create_budget_controlled_search_tool(
        wrapped_tool=original_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
        hard_token_limit=hard_token_limit,
    )


def budget_controlled_product_instance_search_tool(
    session_id: str = "default",
    max_search_calls: int = 10,
    max_tokens: int = 12000,
    hard_token_limit: int = 16000,
) -> BudgetControlledSearchTool:
    """创建预算控制的产品实例搜索工具"""
    from src.tools.product_instance_search import product_instance_search
    
    original_tool = product_instance_search
    
    return create_budget_controlled_search_tool(
        wrapped_tool=original_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
        hard_token_limit=hard_token_limit,
    )


def budget_controlled_product_search_tool(
    session_id: str = "default",
    max_search_calls: int = 10,
    max_tokens: int = 12000,
    hard_token_limit: int = 16000,
) -> BudgetControlledSearchTool:
    """创建预算控制的产品搜索工具"""
    from src.tools.product_search import product_search
    
    original_tool = product_search
    
    return create_budget_controlled_search_tool(
        wrapped_tool=original_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
        hard_token_limit=hard_token_limit,
    )


# 便捷函数：创建预算控制的 online_search 工具
def budget_controlled_online_search_tool(
    max_results: Optional[int] = None,
    session_id: str = "default",
    max_search_calls: int = 10,
    max_tokens: int = 12000,
    hard_token_limit: int = 16000,
) -> BudgetControlledSearchTool:
    """创建预算控制的联网搜索工具

    max_results 优先级：显式传入 > env ONLINE_SEARCH_MAX_RESULTS > 默认 2
    将负责返回条数的处理委托给 online_search_tool 内部的默认值解析。
    """
    from src.tools.online_search import online_search_tool

    # max_results=None 时 online_search_tool 会读 env / 默认
    original_tool = online_search_tool(max_results=max_results)
    
    return create_budget_controlled_search_tool(
        wrapped_tool=original_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
        hard_token_limit=hard_token_limit,
    )


def budget_controlled_bocomsearch_tool(
    session_id: str = "default",
    max_search_calls: int = 5,
    max_tokens: int = 10000,
    max_results: int = 10,
    guwp_token: Optional[str] = None,
    hard_token_limit: int = 16000,
) -> BudgetControlledSearchTool:
    """创建预算控制的交行搜索工具
    
    与 budget_controlled_online_search 共用预算管理器，确保总搜索量不超限
    """
    base_tool = BocomSearchBaseTool(max_results=max_results, guwp_token=guwp_token)
    
    return create_budget_controlled_search_tool(
        wrapped_tool=base_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
        hard_token_limit=hard_token_limit,
    )


# 向后兼容别名
create_budget_controlled_bocomsearch_tool = budget_controlled_bocomsearch_tool


# ============================================================================
# searchknowledge_standard（EUVD 段落级标准知识检索）适配
# ============================================================================


def _resolve_searchknowledge_max_results() -> int:
    """解析 searchknowledge 最大返回条数的默认值

    优先级：env SEARCHKNOWLEDGE_MAX_RESULTS > 硬编码默认 2
    避免模块导入时循环，采用延迟导入 SearchKnowledgeStandardConfig。
    """
    try:
        from src.tools.searchknowledge_standard import SearchKnowledgeStandardConfig
        return SearchKnowledgeStandardConfig.default_max_results()
    except Exception:  # noqa: BLE001
        import os
        try:
            return int(os.getenv("SEARCHKNOWLEDGE_MAX_RESULTS", "2"))
        except (TypeError, ValueError):
            return 2


class SearchKnowledgeStandardBaseTool(BaseTool):
    """EUVD 段落级标准知识检索基础工具，适配 BudgetControlledSearchTool 包装

    封装 call_searchknowledge_standard 函数为 LangChain BaseTool 接口，
    使其可被 BudgetControlledSearchTool 包装并纳入预算控制。
    """
    name: str = "searchknowledge_standard"
    description: str = (
        "段落级标准知识检索（EUVD）。适用于查询行业政策、研报段落级语义片段等结构化知识库内容。"
        "输入应为完整的检索关键词，返回带相关度评分的段落列表。"
    )
    repository: str = "searchknowledge_standard"
    # 默认值通过 default_factory 动态读 env（SEARCHKNOWLEDGE_MAX_RESULTS），兵底 2
    max_results: int = Field(default_factory=lambda: _resolve_searchknowledge_max_results())

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """执行 EUVD 标准知识检索"""
        from src.tools.searchknowledge_standard import call_searchknowledge_standard
        logger.info(
            f"🔍 searchknowledge_standard | max_results={self.max_results}"
        )
        return call_searchknowledge_standard(
            query=query,
            max_results=self.max_results,
        )


def budget_controlled_searchknowledge_standard_tool(
    session_id: str = "default",
    max_search_calls: int = 5,
    max_tokens: int = 10000,
    max_results: Optional[int] = None,
    hard_token_limit: int = 16000,
) -> BudgetControlledSearchTool:
    """创建预算控制的 EUVD 标准知识检索工具

    与 budget_controlled_online_search 、budget_controlled_bocomsearch 共用同一个预算管理器（同一 session_id），
    确保该会话下总搜索量不超限。

    max_results 优先级：显式传入 > env SEARCHKNOWLEDGE_MAX_RESULTS > 默认 2
    """
    effective_max = (
        max_results
        if (max_results and max_results > 0)
        else _resolve_searchknowledge_max_results()
    )
    base_tool = SearchKnowledgeStandardBaseTool(max_results=effective_max)
    return create_budget_controlled_search_tool(
        wrapped_tool=base_tool,
        session_id=session_id,
        max_search_calls=max_search_calls,
        max_tokens=max_tokens,
        hard_token_limit=hard_token_limit,
    )
