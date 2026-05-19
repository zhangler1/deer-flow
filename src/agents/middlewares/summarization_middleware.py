# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
上下文摘要中间件（对齐 DeerFlow 2.0 SummarizationMiddleware 命名）

在 ReactLoop 循环中动态压缩上下文，防止 token 溢出。

两个压缩时机：
1. before_model: 检查总 token 数，超限则对旧消息做全局摘要压缩
2. after_tool: 对刚产生的工具结果做即时截断/压缩，防止单次工具返回过大
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.agents.middleware import AgentMiddleware

logger = logging.getLogger(__name__)


@dataclass
class SummarizationConfig:
    """上下文摘要配置（对齐 DeerFlow 2.0 命名）"""
    # 是否启用
    enabled: bool = True
    # 触发全局压缩的 token 阈值（估算）
    max_context_tokens: int = 80000
    # 保留最近 N 条消息不压缩
    keep_recent_messages: int = 6
    # 单个工具结果最大字符数（after_tool 即时截断）
    tool_result_max_chars: int = 3000
    # 压缩模式: "summarize"（LLM摘要）或 "truncate"（直接截断）
    compression_mode: str = "summarize"
    # 摘要最大长度（字符数）
    summary_max_chars: int = 1500
    # token 估算比率（字符数 / token）
    token_chars_ratio: float = 4.0


# 全局摘要使用的 prompt
SUMMARIZATION_PROMPT = """请将以下对话历史压缩为简洁摘要。保留关键信息：
- 研究主题和目标
- 已找到的重要数据和结论
- 关键来源 URL
- 已完成的步骤

对话历史:
{content}

请输出简洁的中文摘要（不超过{max_chars}字）："""


class SummarizationMiddleware(AgentMiddleware):
    """上下文摘要中间件（对齐 DeerFlow 2.0 命名）
    
    功能：
    1. before_model: 检查消息总 token 数，超过阈值时对旧消息做摘要压缩
    2. after_tool: 对刚返回的工具结果做即时截断，防止 token 爆炸
    
    Usage:
        middleware = SummarizationMiddleware(
            llm=compression_llm,
            config=SummarizationConfig(max_context_tokens=80000)
        )
    """
    
    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        config: Optional[SummarizationConfig] = None,
    ):
        """
        Args:
            llm: 用于生成摘要的 LLM（如果为 None 则回退到 truncate 模式）
            config: 摘要配置
        """
        self.llm = llm
        self.config = config or SummarizationConfig()
        # 统计
        self._compressions_count = 0
        self._tool_truncations_count = 0
    
    async def before_agent(self, messages: list, context: dict) -> list:
        """重置统计"""
        self._compressions_count = 0
        self._tool_truncations_count = 0
        return messages
    
    async def before_model(self, messages: list, iteration: int, context: dict) -> list:
        """检查并执行全局上下文压缩"""
        if not self.config.enabled:
            return messages
        
        # 估算当前 token 数
        total_tokens = self._estimate_tokens(messages)
        
        if total_tokens <= self.config.max_context_tokens:
            return messages
        
        logger.info(
            f"📦 Summarization 触发 | 第 {iteration+1} 轮 | "
            f"当前 tokens: ~{total_tokens} > 阈值: {self.config.max_context_tokens}"
        )
        
        # 执行压缩
        compressed = await self._compress_messages(messages)
        
        self._compressions_count += 1
        new_tokens = self._estimate_tokens(compressed)
        logger.info(
            f"✅ Summarization 完成 | "
            f"压缩前: ~{total_tokens} tokens ({len(messages)} 条) → "
            f"压缩后: ~{new_tokens} tokens ({len(compressed)} 条) | "
            f"第 {self._compressions_count} 次压缩"
        )
        
        return compressed
    
    async def after_tool(self, messages: list, tool_results: list[Any], iteration: int, context: dict) -> list:
        """即时截断过长的工具返回结果"""
        if not self.config.enabled:
            return messages
        
        max_chars = self.config.tool_result_max_chars
        
        for tool_msg in tool_results:
            if not isinstance(tool_msg, ToolMessage):
                continue
            
            content = tool_msg.content or ""
            if len(content) > max_chars:
                original_len = len(content)
                # 截断并添加提示
                tool_msg.content = (
                    content[:max_chars] +
                    f"\n\n... [内容已截断，原始长度: {original_len} 字符，保留前 {max_chars} 字符]"
                )
                self._tool_truncations_count += 1
                logger.debug(
                    f"✂️ ToolResult 截断 | 工具: {tool_msg.name} | "
                    f"{original_len} → {max_chars} 字符"
                )
        
        return messages
    
    async def after_agent(self, messages: list, context: dict) -> list:
        """记录统计"""
        if self._compressions_count > 0 or self._tool_truncations_count > 0:
            logger.info(
                f"📊 Summarization 统计 | "
                f"全局压缩: {self._compressions_count} 次 | "
                f"工具截断: {self._tool_truncations_count} 次"
            )
        return messages
    
    # ============================================================
    # 内部方法
    # ============================================================
    
    @staticmethod
    def _get_content(msg) -> str:
        """安全获取消息内容，兼容 Message 对象和 dict 格式"""
        if isinstance(msg, dict):
            return msg.get("content", "") or ""
        return getattr(msg, "content", "") or ""
    
    @staticmethod
    def _is_protected(msg) -> bool:
        """判断消息是否受保护（不可压缩）
        
        保护标记通过 additional_kwargs["protected"] = True 设置。
        未来技能系统加载的内容也可以通过这个标记避免被压缩。
        """
        if isinstance(msg, dict):
            return msg.get("additional_kwargs", {}).get("protected", False)
        return getattr(msg, "additional_kwargs", {}).get("protected", False)
    
    def _preserve_protected_messages(self, to_compress: list, to_keep: list) -> tuple:
        """从待压缩列表中提取受保护的消息，前置到保留列表头部
        
        借鉴 DeerFlow 2.0 的 _preserve_dynamic_context_reminders 逻辑。
        受保护的消息不会被摘要压缩，而是原样保留。
        """
        protected = [msg for msg in to_compress if self._is_protected(msg)]
        if not protected:
            return to_compress, to_keep
        
        remaining = [msg for msg in to_compress if not self._is_protected(msg)]
        logger.debug(f"🛡️ 保护消息提取 | {len(protected)} 条受保护消息从压缩列表移至保留列表")
        return remaining, protected + to_keep
    
    async def _compress_messages(self, messages: list) -> list:
        """对消息列表执行压缩
        
        策略：
        1. 计算安全切割点（保护 AI/Tool 消息对不被拆散）
        2. 保留最近 N 条消息不压缩
        3. 对旧消息生成摘要
        """
        keep_count = self.config.keep_recent_messages
        
        if len(messages) <= keep_count:
            return messages
        
        # 找到安全的切割点（参考 2.0 的 AI/Tool 对保护）
        cutoff = self._find_safe_cutoff(messages, keep_count)
        
        if cutoff <= 0:
            return messages
        
        to_compress = messages[:cutoff]
        to_keep = messages[cutoff:]
        
        # 提取受保护的消息（不参与压缩）
        to_compress, to_keep = self._preserve_protected_messages(to_compress, to_keep)
        
        # 根据模式选择压缩方法
        if self.config.compression_mode == "summarize" and self.llm:
            summary = await self._summarize(to_compress)
        else:
            summary = self._truncate_messages(to_compress)
        
        # 用摘要消息替换旧消息
        summary_msg = HumanMessage(
            content=f"[上下文摘要]\n\n{summary}",
            name="context_summary",
        )
        
        return [summary_msg] + to_keep
    
    def _find_safe_cutoff(self, messages: list, keep_count: int) -> int:
        """找到安全的消息切割点，确保不拆散 AI/Tool 消息对
        
        借鉴 DeerFlow 2.0 的 _partition_messages 逻辑：
        - 切割点不能落在 AIMessage(有tool_calls) 和它对应的 ToolMessage 之间
        - 如果候选切割点不安全，向前移动到 AIMessage 之前
        """
        n = len(messages)
        candidate = n - keep_count
        
        if candidate <= 0:
            return 0
        
        # 向前搜索安全点：不拆散 AI + Tool 对
        idx = candidate
        while idx > 0:
            msg = messages[idx]
            if isinstance(msg, ToolMessage):
                idx -= 1
                continue
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                break
            break
        
        return idx
    
    async def _summarize(self, messages: list) -> str:
        """使用 LLM 生成消息摘要"""
        content_parts = []
        for msg in messages:
            role = msg.__class__.__name__.replace("Message", "") if not isinstance(msg, dict) else msg.get("role", "unknown")
            text = self._get_content(msg)
            if text:
                if len(text) > 500:
                    text = text[:500] + "..."
                content_parts.append(f"[{role}] {text}")
        
        content = "\n".join(content_parts)
        
        # 限制总输入长度
        max_input_chars = int(self.config.max_context_tokens * self.config.token_chars_ratio * 0.3)
        if len(content) > max_input_chars:
            content = content[:max_input_chars] + "\n...[已截断]"
        
        prompt = SUMMARIZATION_PROMPT.format(
            content=content,
            max_chars=self.config.summary_max_chars,
        )
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            summary = response.content or ""
            if len(summary) > self.config.summary_max_chars:
                summary = summary[:self.config.summary_max_chars] + "..."
            return summary
        except Exception as e:
            logger.warning(f"⚠️ LLM 摘要失败，回退到截断模式: {e}")
            return self._truncate_messages(messages)
    
    def _truncate_messages(self, messages: list) -> str:
        """将消息截断为简短摘要（不使用 LLM）"""
        parts = []
        total_chars = 0
        max_total = self.config.summary_max_chars
        
        for msg in messages:
            content = self._get_content(msg)
            if not content:
                continue
            
            role = msg.__class__.__name__.replace("Message", "") if not isinstance(msg, dict) else msg.get("role", "unknown")
            snippet = content[:200] + ("..." if len(content) > 200 else "")
            line = f"[{role}] {snippet}"
            
            if total_chars + len(line) > max_total:
                parts.append(f"... [共 {len(messages)} 条消息，已截断]")
                break
            
            parts.append(line)
            total_chars += len(line)
        
        return "\n".join(parts)
    
    def _estimate_tokens(self, messages: list) -> int:
        """估算消息列表的 token 数"""
        total_chars = 0
        for msg in messages:
            content = self._get_content(msg)
            total_chars += len(content)
            tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", None)
            if tool_calls:
                for tc in tool_calls:
                    total_chars += len(str(tc.get("args", {}) if isinstance(tc, dict) else tc))
        
        return int(total_chars / self.config.token_chars_ratio)
