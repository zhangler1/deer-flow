# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
循环检测中间件

检测 Agent 重复调用相同工具组合的情况，防止无限循环。

状态分层：
- loop 级：单次 ainvoke 调用内的状态，每次 before_agent 重置
- session 级：跨多次 ainvoke 调用的累计状态，不自动重置

检测机制：
1. 哈希检测：相同 tool_calls 组合重复 N 次（loop 级）
2. 频率检测：同一工具被调用超过 M 次（session 级）
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from src.agents.middleware import AgentMiddleware
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger


@dataclass
class LoopDetectionConfig:
    """循环检测配置"""
    # --- loop 级检测 ---
    # 哈希检测：相同 tool_calls 组合重复多少次触发
    hash_threshold: int = 3
    # 哈希历史窗口大小
    hash_window_size: int = 20
    # 软提示：第几轮开始注入停止警告（设为 0 则禁用软提示）
    warn_at: int = 5
    
    # --- session 级检测 ---
    # 频率检测：同一工具累计调用多少次触发警告（跨多次 loop）
    freq_warn_threshold: int = 15
    # 频率检测：同一工具累计调用多少次强制停止（跨多次 loop）
    freq_hard_threshold: int = 25
    # session 级总工具调用次数上限（0=不限制）
    session_max_tool_calls: int = 0
    # session 级总迭代轮次上限（0=不限制）
    session_max_iterations: int = 0


class LoopDetectionMiddleware(AgentMiddleware):
    """循环检测 + 软提示中间件
    
    功能：
    1. before_model: 接近上限时注入软提示，引导 LLM 主动停止
    2. after_model: 检测重复的工具调用模式
       - Layer 1（哈希检测）：相同 tool_calls 组合（顺序无关）重复 N 次
       - Layer 2（频率检测）：同一工具名累计调用超过阈值
    
    Usage:
        middleware = LoopDetectionMiddleware(config=LoopDetectionConfig(hash_threshold=3, warn_at=5))
    """
    
    def __init__(self, config: LoopDetectionConfig = None):
        self.config = config or LoopDetectionConfig()
        
        # --- loop 级状态（每次 before_agent 重置） ---
        self._loop_hash_history: list[str] = []
        
        # --- session 级状态（跨多次 ainvoke，不自动重置） ---
        self._session_tool_freq: dict[str, int] = {}
        self._session_warned_tools: set[str] = set()
        self._session_total_tool_calls: int = 0
        self._session_total_iterations: int = 0
        self._session_loop_count: int = 0  # 累计多少次 ainvoke
    
    def reset_session(self):
        """手动重置 session 级状态"""
        self._session_tool_freq = {}
        self._session_warned_tools = set()
        self._session_total_tool_calls = 0
        self._session_total_iterations = 0
        self._session_loop_count = 0
    
    async def before_agent(self, messages: list, context: dict) -> list:
        """Agent 执行前：重置 loop 级状态，session 级累加"""
        # loop 级重置
        self._loop_hash_history = []
        # session 级累加
        self._session_loop_count += 1
        return messages
    
    async def before_model(self, messages: list, iteration: int, context: dict) -> list:
        """软提示：接近上限时注入消息引导 LLM 主动停止"""
        warn_at = self.config.warn_at
        if warn_at <= 0:
            return messages
        
        max_iterations = context.get("max_iterations", 8)
        if iteration >= warn_at:
            remaining = max_iterations - iteration
            tool_calls_count = context.get("tool_calls_count", 0)
            messages.append(HumanMessage(
                content=(
                    f"⚠️ 系统提示：你已经进行了 {iteration} 轮工具调用（共计 {tool_calls_count} 次工具使用），"
                    f"剩余 {remaining} 轮机会。"
                    f"请尽快基于已收集的信息总结结果，停止继续搜索。"
                    f"如果信息已经足够，请直接输出最终答案。"
                ),
                name="system",
            ))
            logger.info(f"💡 LoopDetection 软提示已注入 | 第 {iteration+1} 轮 | 剩余 {remaining} 轮")
        
        return messages
    
    async def after_model(self, response: AIMessage, messages: list, iteration: int, context: dict) -> bool:
        """检测循环，返回 True 表示强制停止"""
        if not response.tool_calls:
            return False
        
        # 累加 session 级统计
        self._session_total_iterations += 1
        self._session_total_tool_calls += len(response.tool_calls)
        
        # === session 级总量检测 ===
        if self.config.session_max_tool_calls > 0 and self._session_total_tool_calls >= self.config.session_max_tool_calls:
            logger.warning(
                f"🛑 LoopDetection session 总工具调用上限触发 | "
                f"累计 {self._session_total_tool_calls} 次 | 上限 {self.config.session_max_tool_calls}"
            )
            return True
        
        if self.config.session_max_iterations > 0 and self._session_total_iterations >= self.config.session_max_iterations:
            logger.warning(
                f"🛑 LoopDetection session 总迭代上限触发 | "
                f"累计 {self._session_total_iterations} 轮 | 上限 {self.config.session_max_iterations}"
            )
            return True
        
        # === loop 级: 哈希检测 ===
        hash_stop = self._check_hash_loop(response, iteration)
        if hash_stop:
            return True
        
        # === session 级: 频率检测 ===
        freq_stop = self._check_frequency(response, iteration)
        if freq_stop:
            return True
        
        return False
    
    def _check_hash_loop(self, response: AIMessage, iteration: int) -> bool:
        """loop 级: 检测相同 tool_calls 组合是否重复（单次 ainvoke 内）"""
        call_signature = self._hash_tool_calls(response.tool_calls)
        self._loop_hash_history.append(call_signature)
        
        # 只看最近的窗口
        window = self._loop_hash_history[-self.config.hash_window_size:]
        repeat_count = window.count(call_signature)
        
        if repeat_count >= self.config.hash_threshold:
            tool_names = [tc["name"] for tc in response.tool_calls]
            logger.warning(
                f"🔄 LoopDetection 哈希检测触发 | 第 {iteration+1} 轮 | "
                f"相同组合重复 {repeat_count} 次 | 工具: {tool_names}"
            )
            return True
        
        return False
    
    def _check_frequency(self, response: AIMessage, iteration: int) -> bool:
        """session 级: 检测单个工具的累计调用频率（跨多次 loop）"""
        for tc in response.tool_calls:
            tool_name = tc["name"]
            self._session_tool_freq[tool_name] = self._session_tool_freq.get(tool_name, 0) + 1
            count = self._session_tool_freq[tool_name]
            
            # 硬限制
            if count >= self.config.freq_hard_threshold:
                logger.warning(
                    f"🛑 LoopDetection 频率硬限制触发 | 第 {iteration+1} 轮 | "
                    f"工具 {tool_name} session 累计调用 {count} 次"
                )
                return True
            
            # 软警告（仅首次）
            if count >= self.config.freq_warn_threshold and tool_name not in self._session_warned_tools:
                self._session_warned_tools.add(tool_name)
                logger.info(
                    f"⚠️ LoopDetection 频率警告 | 第 {iteration+1} 轮 | "
                    f"工具 {tool_name} session 累计调用 {count} 次，接近上限 {self.config.freq_hard_threshold}"
                )
        
        return False
    
    @staticmethod
    def _hash_tool_calls(tool_calls: list) -> str:
        """生成 tool_calls 的顺序无关哈希"""
        signatures = []
        for tc in tool_calls:
            name = tc.get("name", "")
            args = tc.get("args", {})
            args_str = str(sorted(args.items())) if isinstance(args, dict) else str(args)
            signatures.append(f"{name}:{args_str}")
        
        combined = "|".join(sorted(signatures))
        return hashlib.md5(combined.encode()).hexdigest()[:12]
