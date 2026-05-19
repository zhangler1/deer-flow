# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
LLM 错误处理中间件（对齐 DeerFlow 2.0 LLMErrorHandlingMiddleware）

功能：
- 重试：LLM 调用失败时自动重试（指数退避）
- 熔断：连续失败达到阈值后快速失败，避免雪崩
- 错误分类：区分可重试错误（超时/限流/5xx）和不可重试错误（认证/配额）

实现方式：
- 通过 wrap_model_call 洋葱链包装 LLM 调用，在中间件层实现重试和熔断
- ReactLoop 无需任何重试逻辑，完全解耦
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.messages import AIMessage

from src.agents.middleware import AgentMiddleware

logger = logging.getLogger(__name__)


@dataclass
class LLMRetryConfig:
    """LLM 重试配置"""
    # 最大重试次数（不含首次）
    max_retries: int = 3
    # 基础延迟（秒）
    base_delay: float = 1.0
    # 最大延迟（秒）
    max_delay: float = 8.0
    # 退避倍数
    backoff_factor: float = 2.0
    # 熔断器：连续失败多少次后熔断
    circuit_breaker_threshold: int = 5
    # 熔断器：熔断后多少秒尝试恢复
    circuit_breaker_recovery_seconds: float = 30.0


class LLMErrorHandlingMiddleware(AgentMiddleware):
    """LLM 错误处理中间件
    
    功能：
    1. wrap_model_call: 包装 LLM 调用，实现重试 + 熔断
    2. after_agent: 记录统计信息
    
    Usage:
        middleware = LLMErrorHandlingMiddleware(config=LLMRetryConfig(max_retries=3))
    """
    
    def __init__(self, config: LLMRetryConfig = None):
        self.config = config or LLMRetryConfig()
        
        # 熔断器状态（session 级）
        self._consecutive_failures: int = 0
        self._circuit_open: bool = False
        self._circuit_opened_at: float = 0.0
        self._total_retries: int = 0
        self._total_failures: int = 0
    
    async def wrap_model_call(
        self, messages: list, call_next: Callable, context: dict
    ) -> AIMessage:
        """包装 LLM 调用：重试 + 熔断器
        
        - 熔断器打开时直接返回错误 AIMessage
        - 调用失败时指数退避重试
        - 达到重试上限后返回错误 AIMessage（不崩溃）
        """
        # 检查熔断器
        if not self._check_circuit():
            return AIMessage(content="⚠️ LLM 熔断器生效，请稍后重试")
        
        max_retries = self.config.max_retries
        last_error = None
        
        for attempt in range(max_retries + 1):  # +1 因为第 0 次是首次调用
            try:
                response = await call_next(messages)
                # 成功
                self._record_success()
                return response
            except Exception as e:
                last_error = e
                retryable = self.is_retryable(e)
                
                if not retryable or attempt >= max_retries:
                    logger.error(
                        f"❌ LLM 调用失败 | "
                        f"尝试 {attempt+1}/{max_retries+1} | "
                        f"可重试={retryable} | {type(e).__name__}: {str(e)[:200]}"
                    )
                    self._record_failure()
                    break
                
                # 计算延迟并重试
                delay = self.calculate_delay(
                    attempt, self.config.base_delay,
                    self.config.max_delay, self.config.backoff_factor
                )
                logger.warning(
                    f"⚠️ LLM 重试 | "
                    f"尝试 {attempt+1}/{max_retries+1} | "
                    f"延迟 {delay:.1f}s | {type(e).__name__}: {str(e)[:100]}"
                )
                self._total_retries += 1
                await asyncio.sleep(delay)
        
        # 全部失败，返回错误 AIMessage（不崩溃）
        error_msg = (
            f"LLM 调用失败（已重试 {max_retries} 次）: "
            f"{type(last_error).__name__}: {str(last_error)[:200]}"
        )
        logger.error(f"❌ {error_msg}")
        return AIMessage(content=f"⚠️ {error_msg}")
    
    async def after_agent(self, messages: list, context: dict) -> list:
        """记录统计"""
        if self._total_retries > 0 or self._total_failures > 0:
            logger.info(
                f"📊 LLMErrorHandling 统计 | "
                f"总重试: {self._total_retries} 次 | "
                f"总失败: {self._total_failures} 次 | "
                f"熔断器: {'OPEN' if self._circuit_open else 'CLOSED'}"
            )
        return messages
    
    def _check_circuit(self) -> bool:
        """检查熔断器是否允许请求通过
        
        Returns:
            True = 允许通过, False = 熔断中
        """
        if not self._circuit_open:
            return True
        
        # 检查是否过了恢复窗口
        elapsed = time.time() - self._circuit_opened_at
        if elapsed >= self.config.circuit_breaker_recovery_seconds:
            logger.info(f"🔄 LLM 熔断器恢复 | 已等待 {elapsed:.1f}s")
            self._circuit_open = False
            self._consecutive_failures = 0
            return True
        
        logger.warning(
            f"🛑 LLM 熔断器生效 | 剩余 "
            f"{self.config.circuit_breaker_recovery_seconds - elapsed:.1f}s"
        )
        return False
    
    def _record_success(self):
        """记录成功，重置熔断器"""
        self._consecutive_failures = 0
        if self._circuit_open:
            self._circuit_open = False
            logger.info("✅ LLM 熔断器关闭（恢复正常）")
    
    def _record_failure(self):
        """记录失败，可能触发熔断"""
        self._consecutive_failures += 1
        self._total_failures += 1
        
        if self._consecutive_failures >= self.config.circuit_breaker_threshold:
            if not self._circuit_open:
                self._circuit_open = True
                self._circuit_opened_at = time.time()
                logger.error(
                    f"🔴 LLM 熔断器打开 | 连续失败 {self._consecutive_failures} 次 | "
                    f"将在 {self.config.circuit_breaker_recovery_seconds}s 后尝试恢复"
                )
    

    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """判断错误是否可重试
        
        可重试：超时、限流(429)、服务端错误(5xx)、连接错误
        不可重试：认证失败(401)、配额用尽(403)、参数错误(400)
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # 不可重试的
        non_retryable_keywords = ["401", "403", "authentication", "unauthorized", "quota"]
        for keyword in non_retryable_keywords:
            if keyword in error_str:
                return False
        
        # 可重试的
        retryable_keywords = [
            "timeout", "timed out", "429", "rate limit", "rate_limit",
            "500", "502", "503", "504", "connection", "network",
            "temporary", "transient", "busy", "overloaded",
        ]
        for keyword in retryable_keywords:
            if keyword in error_str or keyword in error_type:
                return True
        
        # 特定异常类型
        retryable_types = ["timeout", "connection", "httpx"]
        for t in retryable_types:
            if t in error_type:
                return True
        
        # 默认重试（网络环境不稳定时宁可重试）
        return True
    
    @staticmethod
    def calculate_delay(attempt: int, base_delay: float, max_delay: float, backoff_factor: float) -> float:
        """计算重试延迟（指数退避）"""
        delay = base_delay * (backoff_factor ** attempt)
        return min(delay, max_delay)
