# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
搜索预算执行中间件（方案 C：原生工具 + 中间件接管预算）

设计目标：
- 让 researcher 节点直接装配原生搜索工具（online_search、searchknowledge_standard、
  financial_summary、product_instance_search、vector_search），不再使用 BudgetControlledSearchTool 包装器。
- 通过 wrap_tool_call 钩子在工具调用边界做预算拦截 + 结果格式化。
- bocomsearch 因 guwp_token 线程安全（state 注入）保留原有包装器，由白名单
  controlled_tool_names 明确排除，避免双重检查。
- vector_search 同为 guwp_token 工具，但已改为无状态 + 中间件注入 guwp_token，列入白名单。

钩子分工：
- before_agent: 取 session_id 拿到/创建预算管理器并 reset；缓存到中间件实例
- before_model: 缓存最新 messages（供 wrap_tool_call 估算 tokens 使用）
- wrap_tool_call: 仅对受控工具拦截。预算耗尽返回伪造 ToolMessage（含 budget_exhausted=True
  与 FINAL_NOTICE）；通过则 call_next 后 record_search_call() 并附加预算警告
- after_agent: 输出 BudgetEnforcement 统计日志

依赖 ReactLoop.context['input'] 与 context['tools']（已在 react_loop.py 中注入）。
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from langchain_core.messages import BaseMessage, ToolMessage

from src.agents.middleware import AgentMiddleware
from src.tools.budget_controlled_search import get_budget_manager
from src.utils.enhanced_logger import get_enhanced_logger
from src.utils.search_budget import SearchBudgetManager

logger = get_enhanced_logger(__name__).logger


# 默认受控工具（白名单）。bocomsearch 不在此处，由 BudgetControlledSearchTool 包装器自行控制；
# vector_search 虽已去掉包装器，但 guwp_token 由本中间件注入，故在此受控。
DEFAULT_CONTROLLED_TOOLS = {
    "online_search",
    "searchknowledge_standard",
    "financial_summary",
    "product_instance_search",
    "vector_search",
}


@dataclass
class BudgetEnforcementConfig:
    """预算执行中间件配置"""
    enabled: bool = True
    max_search_calls: int = 5
    max_tokens: int = 10000
    hard_token_limit: int = 14000
    token_chars_ratio: float = 3.0
    # 仅对集合内的工具名做预算控制；其他工具直接放行
    controlled_tool_names: set[str] = field(default_factory=lambda: set(DEFAULT_CONTROLLED_TOOLS))
    # 是否在每次成功调用后给工具结果附加预算警告
    attach_warning: bool = True


class BudgetEnforcementMiddleware(AgentMiddleware):
    """搜索预算执行中间件（方案 C 中间件实现）

    Usage::

        from src.agents.middlewares.budget_enforcement_middleware import (
            BudgetEnforcementMiddleware, BudgetEnforcementConfig,
        )
        middleware = BudgetEnforcementMiddleware(config=BudgetEnforcementConfig(...))
    """

    def __init__(self, config: Optional[BudgetEnforcementConfig] = None):
        self.config = config or BudgetEnforcementConfig()

        # 运行时状态（每次 before_agent 重新初始化）
        self._budget: Optional[SearchBudgetManager] = None
        self._session_id: str = "default"
        self._latest_messages: list[BaseMessage] = []

        # 统计
        self._total_calls: int = 0      # 受控工具被调用次数（含拦截）
        self._blocked_calls: int = 0    # 因预算耗尽被拦截次数
        self._executed_calls: int = 0   # 实际下放执行次数

    # ------------------------------------------------------------------
    # before_agent: 初始化预算管理器
    # ------------------------------------------------------------------
    async def before_agent(self, messages: list, context: dict) -> list:
        if not self.config.enabled:
            return messages

        state = context.get("input") or {}
        session_id = "default"
        if isinstance(state, dict):
            session_id = state.get("session_id") or "default"
        self._session_id = session_id

        self._budget = get_budget_manager(
            session_id=session_id,
            max_search_calls=self.config.max_search_calls,
            max_tokens=self.config.max_tokens,
            token_chars_ratio=self.config.token_chars_ratio,
            hard_token_limit=self.config.hard_token_limit,
        )
        # 每个 researcher 节点开始时清零计数器
        self._budget.reset()

        # 重置统计
        self._total_calls = 0
        self._blocked_calls = 0
        self._executed_calls = 0
        self._latest_messages = list(messages)

        logger.info(
            f"💰 BudgetEnforcement | session={session_id} | "
            f"max_calls={self.config.max_search_calls} | "
            f"max_tokens={self.config.max_tokens} | "
            f"hard_limit={self.config.hard_token_limit} | "
            f"controlled_tools={sorted(self.config.controlled_tool_names)}"
        )
        return messages

    # ------------------------------------------------------------------
    # before_model: 缓存当前 messages 供 wrap_tool_call 估 token
    # ------------------------------------------------------------------
    async def before_model(self, messages: list, iteration: int, context: dict) -> list:
        self._latest_messages = list(messages)
        return messages

    # ------------------------------------------------------------------
    # wrap_tool_call: 预算拦截（仅受控工具）
    # ------------------------------------------------------------------
    async def wrap_tool_call(
        self,
        tool_name: str,
        tool_args: dict,
        tool_call_id: str,
        call_next: Callable,
        context: dict,
    ) -> ToolMessage:
        # 未启用或非受控工具：直接放行
        if not self.config.enabled or self._budget is None:
            return await call_next(tool_name, tool_args, tool_call_id)
        if tool_name not in self.config.controlled_tool_names:
            return await call_next(tool_name, tool_args, tool_call_id)

        # ── 0. 注入 guwp_token（vector_search 需要，从 state 读取） ──
        # vector_search 已去掉实例属性，改为每次调用时由中间件从 context.input 注入
        if tool_name == "vector_search":
            input_state = context.get("input", {})
            if isinstance(input_state, dict):
                guwp_token = input_state.get("guwp_token")
                if guwp_token:
                    tool_args["guwp_token"] = guwp_token

        self._total_calls += 1
        budget = self._budget
        messages = self._latest_messages

        # ── 1. 预算检查 ──
        if not budget.can_search(messages):
            self._blocked_calls += 1
            content = self._build_budget_exhausted_payload(tool_name, budget, messages)
            logger.warning(
                f"🛑 BudgetEnforcement | BLOCK | tool={tool_name} | "
                f"session={self._session_id} | "
                f"used={budget._search_calls_used}/{self.config.max_search_calls} | "
                f"tokens={budget.estimate_tokens(messages)}/{self.config.hard_token_limit}"
            )
            return ToolMessage(
                content=content,
                tool_call_id=tool_call_id,
                name=tool_name,
            )

        # ── 2. 放行执行 ──
        logger.info(
            f"💰 BudgetEnforcement | EXEC  | tool={tool_name} | "
            f"session={self._session_id} | "
            f"used_before={budget._search_calls_used}/{self.config.max_search_calls}"
        )
        tool_msg = await call_next(tool_name, tool_args, tool_call_id)

        # ── 3. 扣减预算 + 附加警告 ──
        budget.record_search_call()
        self._executed_calls += 1

        status = budget.get_budget_status(self._latest_messages)
        logger.info(
            f"💰 BudgetEnforcement | DEDUCT | tool={tool_name} | "
            f"used_after={status.search_calls_used}/{self.config.max_search_calls} | "
            f"tokens={status.estimated_tokens}/{self.config.max_tokens} | "
            f"warning_level={status.warning_level}"
        )

        if self.config.attach_warning and isinstance(tool_msg, ToolMessage):
            warning = budget.get_warning_message(self._latest_messages)
            if warning:
                tool_msg.content = self._append_warning(tool_msg.content, warning, status)

        return tool_msg

    # ------------------------------------------------------------------
    # after_agent: 统计日志
    # ------------------------------------------------------------------
    async def after_agent(self, messages: list, context: dict) -> list:
        if not self.config.enabled or self._budget is None:
            return messages

        status = self._budget.get_budget_status(messages)
        logger.info(
            f"📊 BudgetEnforcement 统计 | session={self._session_id} | "
            f"受控调用总计={self._total_calls} | "
            f"实际执行={self._executed_calls} | "
            f"被拦截={self._blocked_calls} | "
            f"used={status.search_calls_used}/{self.config.max_search_calls} | "
            f"tokens={status.estimated_tokens}/{self.config.max_tokens}"
        )
        return messages

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_budget_exhausted_payload(
        self, tool_name: str, budget: SearchBudgetManager, messages: list
    ) -> str:
        """构建预算耗尽响应（与 BudgetControlledSearchTool 保持一致格式）"""
        status = budget.get_budget_status(messages)
        warning_msg = budget.get_warning_message(messages) or "搜索预算已耗尽"

        final_notice = (
            f"⛔ FINAL_NOTICE | 搜索预算已耗尽，禁止再次调用任何搜索工具。\n"
            f"已用搜索次数: {status.search_calls_used}/{self.config.max_search_calls}\n"
            f"已用 tokens: {status.estimated_tokens}/{self.config.max_tokens}\n"
            f"任何后续搜索工具调用都将被系统拒绝并返回相同消息。\n"
            f"请立即基于已收集的信息综合分析并输出最终答案，不要再尝试搜索。"
        )

        payload = {
            "status": "budget_exhausted",
            "budget_exhausted": True,  # 结构化标记，便于下游中间件识别
            "tool": tool_name,
            "message": final_notice,
            "warning": warning_msg,
            "search_calls_used": status.search_calls_used,
            "max_search_calls": self.config.max_search_calls,
            "estimated_tokens": status.estimated_tokens,
            "max_tokens": self.config.max_tokens,
            "suggestion": (
                "严禁再次调用任何搜索工具。请立即综合分析已收集的信息，"
                "按用户要求的格式输出最终报告。如信息不足，请如实说明缺口而非继续搜索。"
            ),
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _append_warning(content: Any, warning: str, status) -> str:
        """在工具结果末尾追加预算警告（保持 JSON 格式有效）

        当原始内容为 JSON 数组时，追加 {"_reminding": "..."} 元素到数组末尾；
        当原始内容为 JSON 对象时，将提醒作为 "reminding" 字段嵌入；
        当原始内容为纯文本时，仍采用文本追加方式。
        """
        reminder_text = (
            f"{warning} (已用 {status.search_calls_used} 次, "
            f"剩余 {status.remaining_search_calls} 次)"
        )

        if isinstance(content, str):
            # 尝试判断是否为 JSON 字符串
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    parsed["reminding"] = reminder_text
                    return json.dumps(parsed, ensure_ascii=False)
                elif isinstance(parsed, list):
                    parsed.append({"_reminding": reminder_text})
                    return json.dumps(parsed, ensure_ascii=False, default=str)
            except (json.JSONDecodeError, ValueError):
                pass
            # 纯文本：沿用追加方式
            return content + f"\n\n[💡 预算提示] {reminder_text}"
        else:
            # content 是 dict/list 等非字符串类型
            if isinstance(content, dict):
                result = dict(content)
                result["reminding"] = reminder_text
                return json.dumps(result, ensure_ascii=False)
            elif isinstance(content, list):
                content.append({"_reminding": reminder_text})
                return json.dumps(content, ensure_ascii=False, default=str)
            else:
                body = json.dumps(content, ensure_ascii=False)
                return body + f"\n\n[💡 预算提示] {reminder_text}"
