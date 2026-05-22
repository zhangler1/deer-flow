# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
Token 用量统计中间件（对齐 DeerFlow 2.0 RunJournal token 日志）

功能：
- before_model: 记录每轮 LLM 调用前的上下文大小（消息数、字符数、估算 token 数）
- after_model: 提取 LLM 返回的 usage_metadata（实际 prompt/completion tokens）
- after_agent: 输出统计摘要 + 压缩效果对比
- 支持通过 context 将统计数据暴露给外部

日志格式（方便 grep 统计压缩效果）：
    📥 CTX_BEFORE | iter=3 | msgs=12 | chars=8500 | est_tokens=2125
    📤 LLM_USAGE | iter=3 | model=deepseek-chat | finish=tool_calls | tools=2 | 
                  prompt=1800 | completion=350 | total=2150 | est_acc=0.85 | latency=1.23s
    📊 TOKEN_SUMMARY | iters=5 | total_prompt=9000 | total_compl=1500 | total=10500
    ⚠️ FINISH_LENGTH | iter=4 | 模型因上下文上限被截断（压缩未生效）
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage

from src.agents.middleware import AgentMiddleware
from src.utils.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger(__name__).logger

# 默认 token 估算比率（字符数 / token），中英混合取 3.5
DEFAULT_TOKEN_CHARS_RATIO = 3.5


@dataclass
class TokenUsageStats:
    """Token 用量统计数据"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0
    # 按轮次记录（含上下文大小）
    per_iteration: list = field(default_factory=list)


class TokenUsageMiddleware(AgentMiddleware):
    """Token 用量统计中间件（对齐 DeerFlow 2.0 RunJournal）
    
    功能：
    1. before_model: 记录每轮上下文大小（消息数 / 字符数 / 估算 tokens）
    2. after_model: 从 AIMessage.usage_metadata 提取实际 token 用量
    3. after_agent: 输出完整统计摘要 + 写入 context
    
    日志级别全部为 INFO，方便 grep 统计压缩效果：
        grep '📥 CTX_BEFORE' logs/app.log   # 查看每轮上下文大小
        grep '📤 LLM_USAGE' logs/app.log    # 查看每轮实际 token
        grep '📊 TOKEN_SUMMARY' logs/app.log # 查看总计
    
    Usage:
        middleware = TokenUsageMiddleware()
    """
    
    def __init__(self, token_chars_ratio: float = DEFAULT_TOKEN_CHARS_RATIO):
        # session 级累计
        self._session_stats = TokenUsageStats()
        # loop 级统计
        self._loop_stats = TokenUsageStats()
        self._token_chars_ratio = token_chars_ratio
        # 每轮 LLM 调用开始时间
        self._call_start_time: float = 0.0
    
    async def before_agent(self, messages: list, context: dict) -> list:
        """重置 loop 级统计"""
        self._loop_stats = TokenUsageStats()
        return messages
    
    async def before_model(self, messages: list, iteration: int, context: dict) -> list:
        """记录 LLM 调用前的上下文大小（对齐 2.0 RunJournal 的 on_llm_start）"""
        msg_count = len(messages)
        total_chars = sum(len(self._get_content(m)) for m in messages)
        est_tokens = int(total_chars / self._token_chars_ratio)
        
        logger.info(
            f"📥 CTX_BEFORE | iter={iteration+1} | "
            f"msgs={msg_count} | chars={total_chars} | est_tokens={est_tokens}"
        )
        
        # 记录调用开始时间
        self._call_start_time = time.time()
        
        # 存入 context 供其他中间件参考
        context["_ctx_before"] = {
            "iteration": iteration,
            "msg_count": msg_count,
            "total_chars": total_chars,
            "est_tokens": est_tokens,
        }
        return messages
    
    async def after_model(self, response: AIMessage, messages: list, iteration: int, context: dict) -> bool:
        """提取并记录 token 用量（对齐 2.0 RunJournal 的 on_llm_end）"""
        latency = time.time() - self._call_start_time if self._call_start_time else 0.0
        usage = self._extract_usage(response)
        
        # 提取扩展字段：model_name / finish_reason / tool_calls_count
        model_name = self._extract_model_name(response)
        finish_reason = self._extract_finish_reason(response)
        tool_calls_count = len(getattr(response, "tool_calls", []) or [])
        
        # ⚠️ 关键告警：finish_reason=length 说明被上下文上限截断，压缩未生效
        if finish_reason == "length":
            logger.warning(
                f"⚠️ FINISH_LENGTH | iter={iteration+1} | "
                f"模型因上下文上限被截断（压缩未生效，建议降低 max_context_tokens 阈值）"
            )
        
        if usage:
            prompt_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens)
            
            # loop 级累计
            self._loop_stats.prompt_tokens += prompt_tokens
            self._loop_stats.completion_tokens += completion_tokens
            self._loop_stats.total_tokens += total_tokens
            self._loop_stats.llm_calls += 1
            
            # 获取 before_model 记录的上下文信息
            ctx_before = context.get("_ctx_before", {})
            est_tokens = ctx_before.get("est_tokens", 0)
            
            # 估算精度：prompt_tokens / est_tokens（>1 说明估算偏低，<1 说明估算偏高）
            est_accuracy = round(prompt_tokens / est_tokens, 3) if est_tokens > 0 else 0.0
            
            self._loop_stats.per_iteration.append({
                "iteration": iteration,
                "model_name": model_name,
                "finish_reason": finish_reason,
                "tool_calls_count": tool_calls_count,
                "context_msgs": ctx_before.get("msg_count", 0),
                "context_chars": ctx_before.get("total_chars", 0),
                "context_est_tokens": est_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "est_accuracy": est_accuracy,
                "latency_s": round(latency, 2),
            })
            
            # session 级累计
            self._session_stats.prompt_tokens += prompt_tokens
            self._session_stats.completion_tokens += completion_tokens
            self._session_stats.total_tokens += total_tokens
            self._session_stats.llm_calls += 1
            
            logger.info(
                f"📤 LLM_USAGE | iter={iteration+1} | "
                f"model={model_name} | finish={finish_reason} | tools={tool_calls_count} | "
                f"prompt={prompt_tokens} | completion={completion_tokens} | total={total_tokens} | "
                f"est_acc={est_accuracy} | latency={latency:.2f}s | "
                f"loop_total={self._loop_stats.total_tokens}"
            )
        else:
            logger.info(
                f"📤 LLM_USAGE | iter={iteration+1} | "
                f"model={model_name} | finish={finish_reason} | tools={tool_calls_count} | "
                f"usage=N/A (模型未返回 token 统计) | latency={latency:.2f}s"
            )
        
        return False  # 不停止循环
    
    async def after_agent(self, messages: list, context: dict) -> list:
        """输出完整统计摘要 + 压缩效果对比，写入 context"""
        stats = self._loop_stats
        
        if stats.llm_calls > 0:
            # 计算上下文增长趋势（用于判断压缩是否生效）
            ctx_trend = ""
            if len(stats.per_iteration) >= 2:
                first_ctx = stats.per_iteration[0].get("context_est_tokens", 0)
                last_ctx = stats.per_iteration[-1].get("context_est_tokens", 0)
                if first_ctx > 0:
                    growth_pct = ((last_ctx - first_ctx) / first_ctx) * 100
                    ctx_trend = f" | ctx_growth={growth_pct:+.1f}%"
            
            # 计算平均估算精度（用于动态调优 token_chars_ratio）
            est_accs = [r.get("est_accuracy", 0) for r in stats.per_iteration if r.get("est_accuracy", 0) > 0]
            avg_est_acc = round(sum(est_accs) / len(est_accs), 3) if est_accs else 0.0
            avg_acc_str = f" | avg_est_acc={avg_est_acc}" if avg_est_acc else ""
            
            # 统计 finish_reason 异常（length=被截断）
            length_truncated = sum(1 for r in stats.per_iteration if r.get("finish_reason") == "length")
            truncate_str = f" | length_truncated={length_truncated}" if length_truncated else ""
            
            logger.info(
                f"📊 TOKEN_SUMMARY | "
                f"iters={stats.llm_calls} | "
                f"total_prompt={stats.prompt_tokens} | "
                f"total_compl={stats.completion_tokens} | "
                f"total={stats.total_tokens}{ctx_trend}{avg_acc_str}{truncate_str}"
            )
            
            # 输出每轮详情表格（方便统计压缩效果）
            logger.info("📊 TOKEN_DETAIL | iter | model            | finish     | tools | ctx_msgs | ctx_chars | est_tokens | prompt | compl | total | est_acc | latency")
            for rec in stats.per_iteration:
                logger.info(
                    f"📊 TOKEN_DETAIL | {rec['iteration']+1:4d} | "
                    f"{(rec.get('model_name') or 'unknown')[:16]:16s} | "
                    f"{(rec.get('finish_reason') or '-')[:10]:10s} | "
                    f"{rec.get('tool_calls_count', 0):5d} | "
                    f"{rec.get('context_msgs', 0):8d} | "
                    f"{rec.get('context_chars', 0):9d} | "
                    f"{rec.get('context_est_tokens', 0):10d} | "
                    f"{rec.get('prompt_tokens', 0):6d} | "
                    f"{rec.get('completion_tokens', 0):5d} | "
                    f"{rec.get('total_tokens', 0):5d} | "
                    f"{rec.get('est_accuracy', 0):7.3f} | "
                    f"{rec.get('latency_s', 0):7.2f}s"
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
    def _get_content(msg) -> str:
        """安全获取消息内容文本"""
        if isinstance(msg, dict):
            content = msg.get("content", "") or ""
        else:
            content = getattr(msg, "content", "") or ""
        if isinstance(content, list):
            # 多模态消息，只取文本部分
            return "".join(block if isinstance(block, str) else block.get("text", "") for block in content)
        return content if isinstance(content, str) else str(content)
    
    @staticmethod
    def _extract_model_name(response: AIMessage) -> str:
        """从 AIMessage 中提取 model_name
        
        来源优先级：
        1. response.response_metadata["model_name"]（LangChain 标准）
        2. response.response_metadata["model"]（部分 provider）
        3. response.additional_kwargs["model"]（fallback）
        """
        meta = getattr(response, "response_metadata", None) or {}
        if isinstance(meta, dict):
            name = meta.get("model_name") or meta.get("model")
            if name:
                return str(name)
        additional = getattr(response, "additional_kwargs", None) or {}
        if isinstance(additional, dict):
            name = additional.get("model")
            if name:
                return str(name)
        return "unknown"
    
    @staticmethod
    def _extract_finish_reason(response: AIMessage) -> str:
        """从 AIMessage 中提取 finish_reason
        
        关键值：
        - "stop": 正常结束
        - "length": 被上下文上限截断（⚠️ 压缩未生效的信号）
        - "tool_calls": 因调用工具而停止
        - "content_filter": 被内容过滤拦截
        """
        meta = getattr(response, "response_metadata", None) or {}
        if isinstance(meta, dict):
            reason = meta.get("finish_reason") or meta.get("stop_reason")
            if reason:
                return str(reason)
        return "-"
    
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
