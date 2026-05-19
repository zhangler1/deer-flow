# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
Token 用量统计中间件（对齐 DeerFlow 2.0 TokenUsageMiddleware）

功能：
- 在 after_model 钩子中提取 LLM 返回的 usage_metadata
- 累计统计 prompt_tokens、completion_tokens、total_tokens
- 在 after_agent 中输出统计摘要（成本监控）
- 支持通过 context 将统计数据暴露给外部
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage

from src.agents.middleware import AgentMiddleware

logger = logging.getLogger(__name__)


@dataclass
class TokenUsageStats:
    """Token 用量统计数据"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0
    # 按轮次记录
    per_iteration: list = field(default_factory=list)


class TokenUsageMiddleware(AgentMiddleware):
    """Token 用量统计中间件
    
    功能：
    1. after_model: 从 AIMessage.usage_metadata 提取 token 用量
    2. after_agent: 输出统计摘要到日志 + 写入 context
    
    统计数据通过 context["token_usage"] 暴露，外部可读取用于计费/监控。
    
    Usage:
        middleware = TokenUsageMiddleware()
        # 执行后通过 context["token_usage"] 获取统计
    """
    
    def __init__(self):
        # session 级累计
        self._session_stats = TokenUsageStats()
        # loop 级统计
        self._loop_stats = TokenUsageStats()
    
    async def before_agent(self, messages: list, context: dict) -> list:
        """重置 loop 级统计"""
        self._loop_stats = TokenUsageStats()
        return messages
    
    async def after_model(self, response: AIMessage, messages: list, iteration: int, context: dict) -> bool:
        """提取并记录 token 用量"""
        usage = self._extract_usage(response)
        
        if usage:
            prompt_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens)
            
            # loop 级累计
            self._loop_stats.prompt_tokens += prompt_tokens
            self._loop_stats.completion_tokens += completion_tokens
            self._loop_stats.total_tokens += total_tokens
            self._loop_stats.llm_calls += 1
            self._loop_stats.per_iteration.append({
                "iteration": iteration,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            })
            
            # session 级累计
            self._session_stats.prompt_tokens += prompt_tokens
            self._session_stats.completion_tokens += completion_tokens
            self._session_stats.total_tokens += total_tokens
            self._session_stats.llm_calls += 1
            
            logger.debug(
                f"📈 TokenUsage | 第 {iteration+1} 轮 | "
                f"本次: {prompt_tokens}+{completion_tokens}={total_tokens} | "
                f"loop累计: {self._loop_stats.total_tokens}"
            )
        
        return False  # 不停止循环
    
    async def after_agent(self, messages: list, context: dict) -> list:
        """输出统计摘要，写入 context"""
        stats = self._loop_stats
        
        if stats.llm_calls > 0:
            logger.info(
                f"📊 TokenUsage 统计 | "
                f"LLM调用: {stats.llm_calls} 次 | "
                f"Prompt: {stats.prompt_tokens} | "
                f"Completion: {stats.completion_tokens} | "
                f"Total: {stats.total_tokens} tokens"
            )
            
            # 将统计写入 context，供外部读取
            context["token_usage"] = {
                "loop": {
                    "prompt_tokens": stats.prompt_tokens,
                    "completion_tokens": stats.completion_tokens,
                    "total_tokens": stats.total_tokens,
                    "llm_calls": stats.llm_calls,
                    "per_iteration": stats.per_iteration,
                },
                "session": {
                    "prompt_tokens": self._session_stats.prompt_tokens,
                    "completion_tokens": self._session_stats.completion_tokens,
                    "total_tokens": self._session_stats.total_tokens,
                    "llm_calls": self._session_stats.llm_calls,
                },
            }
        
        return messages
    
    @staticmethod
    def _extract_usage(response: AIMessage) -> dict:
        """从 AIMessage 中提取 usage_metadata
        
        LangChain 的不同 LLM provider 可能以不同方式存放 usage：
        - response.usage_metadata (标准)
        - response.response_metadata.get("token_usage")
        - response.additional_kwargs.get("usage")
        """
        # 方式1: LangChain 标准 usage_metadata
        usage = getattr(response, "usage_metadata", None)
        if usage and isinstance(usage, dict) and any(v for v in usage.values() if v):
            return usage
        
        # 方式2: response_metadata
        response_meta = getattr(response, "response_metadata", None)
        if response_meta and isinstance(response_meta, dict):
            token_usage = response_meta.get("token_usage")
            if token_usage and isinstance(token_usage, dict):
                return token_usage
        
        # 方式3: additional_kwargs
        additional = getattr(response, "additional_kwargs", None)
        if additional and isinstance(additional, dict):
            usage = additional.get("usage")
            if usage and isinstance(usage, dict):
                return usage
        
        return {}
    
    def get_session_stats(self) -> dict:
        """获取 session 级累计统计（供外部调用）"""
        return {
            "prompt_tokens": self._session_stats.prompt_tokens,
            "completion_tokens": self._session_stats.completion_tokens,
            "total_tokens": self._session_stats.total_tokens,
            "llm_calls": self._session_stats.llm_calls,
        }
