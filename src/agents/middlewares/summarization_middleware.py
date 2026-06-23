# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
上下文摘要中间件（对齐 DeerFlow 2.0 SummarizationMiddleware 命名）

在 ReactLoop 循环中动态压缩上下文，防止 token 溢出。

两个压缩时机：
1. before_model: 检查总 token 数，超限则对旧消息做全局摘要压缩
2. after_tool: 对刚产生的工具结果做即时截断/压缩，防止单次工具返回过大
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.agents.middleware import AgentMiddleware
from src.utils.enhanced_logger import get_enhanced_logger, current_thread_id
from src.utils.text_utils import _get_message_text, estimate_token_count

logger = get_enhanced_logger(__name__).logger


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
    # 受保护的工具名单：这些工具的返回结果在 after_tool 中标记 protected=True，
    # 全局上下文压缩时不会被摘要化，确保检索召回内容不丢失
    protected_tool_names: list = None  # type: ignore

    def __post_init__(self):
        if self.protected_tool_names is None:
            self.protected_tool_names = ["research_skill_prompt_search"]


# 全局摘要使用的 prompt
SUMMARIZATION_PROMPT = """请将以下对话历史压缩为简洁摘要。保留关键信息：
- 研究主题和目标
- 已找到的重要数据和结论
- 关键来源 URL
- 已完成的步骤

{truncation_warning}
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

        # 计算输入总字符长度（含 tool_calls args，与 _estimate_tokens 口径对齐）
        total_chars = sum(len(_get_message_text(m)) for m in messages)
        logger.info(
            f"CTX_CHECK | thread_id={current_thread_id.get()} | "
            f"tokens={total_tokens} | chars={total_chars} | "
            f"triggered={total_tokens > self.config.max_context_tokens} | "
            f"threshold={self.config.max_context_tokens}"
        )

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

        new_chars = sum(len(_get_message_text(m)) for m in compressed)
        logger.debug(
            f"CTX_COMPRESSED | thread_id={current_thread_id.get()} | "
            f"pre_tokens=~{total_tokens} | pre_chars={total_chars} | "
            f"post_tokens=~{new_tokens} | post_chars={new_chars}"
        )

        return compressed
    
    async def after_tool(self, messages: list, tool_results: list[Any], iteration: int, context: dict) -> list:
        """即时截断过长的工具返回结果，并对受保护工具的结果标记 protected
        
        受保护工具（protected_tool_names）的结果：
        - 不会被即时截断（保留完整内容）
        - 标记 protected=True，全局压缩时也不会被摘要化
        """
        if not self.config.enabled:
            return messages
        
        max_chars = self.config.tool_result_max_chars
        protected_tools = set(self.config.protected_tool_names or [])
        
        for tool_msg in tool_results:
            if not isinstance(tool_msg, ToolMessage):
                continue
            
            tool_name = getattr(tool_msg, "name", "") or ""
            
            # 受保护工具：跳过截断，直接标记 protected
            if tool_name in protected_tools:
                if not hasattr(tool_msg, "additional_kwargs") or tool_msg.additional_kwargs is None:
                    tool_msg.additional_kwargs = {}
                tool_msg.additional_kwargs["protected"] = True
                logger.debug(
                    f"🛡️ ToolResult 保护 | 工具: {tool_name} | "
                    f"跳过截断 + 标记 protected=True"
                )
                continue
            
            # 非保护工具：超过 max_chars 则截断
            content = tool_msg.content or ""
            if len(content) > max_chars:
                original_len = len(content)
                # 优先尝试 JSON 感知截断（保持输出始终为合法 JSON）
                truncated = self._truncate_json_aware(content, max_chars)
                if truncated is not None:
                    tool_msg.content = truncated
                    new_len = len(truncated)
                    mode = "JSON"
                else:
                    # 非 JSON 内容，回退字符级截断
                    tool_msg.content = (
                        content[:max_chars] +
                        f"\n\n... [内容已截断，原始长度: {original_len} 字符，保留前 {max_chars} 字符]"
                    )
                    mode = "CHAR"
                self._tool_truncations_count += 1
                logger.debug(
                    f"✂️ ToolResult 截断 | 工具: {tool_msg.name} | "
                    f"{original_len} → {len(tool_msg.content)} 字符 | "
                    f"模式: {mode}"
                    f"{original_len} → {max_chars} 字符 | "
                    f"tool_msg.content: {tool_msg.content}"
                )
            else:
                logger.debug(
                    f"ToolResult 未截断 | 工具: {tool_msg.name} | "
                    f"tool_msg.content: {tool_msg.content}"
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
    def _is_system_message(msg) -> bool:
        """判断是否为系统提示词消息

        系统提示词（role=system）不能被压缩，否则 LLM 会丢失角色约束和工具使用指导。
        兼容 dict 格式和 LangChain Message 对象两种表示。
        """
        if isinstance(msg, dict):
            return msg.get("role") == "system"
        return getattr(msg, "type", None) == "system"

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
        1. 先提取系统提示词（不参与压缩，压缩后原样拼回 position 0）
        2. 计算安全切割点（保护 AI/Tool 消息对不被拆散）
        3. 保留最近 N 条消息不压缩
        4. 对旧消息生成摘要
        """
        # 1. 提取系统提示词，确保不被压缩
        system_msgs = [m for m in messages if self._is_system_message(m)]
        rest_msgs = [m for m in messages if not self._is_system_message(m)]

        if system_msgs:
            logger.debug(
                f"🛡️ 系统提示词保护 | {len(system_msgs)} 条系统消息从压缩范围排除"
            )

        keep_count = self.config.keep_recent_messages

        if len(rest_msgs) <= keep_count:
            logger.debug(
                f"COMPRESS_SKIP | msgs={len(messages)} | sys={len(system_msgs)} | "
                f"rest={len(rest_msgs)} | keep={keep_count} | 未超过保护阈值跳过 | "
                f"thread_id={current_thread_id.get()}"
            )
            return messages

        # 2. 找到安全的切割点（参考 2.0 的 AI/Tool 对保护）
        cutoff = self._find_safe_cutoff(rest_msgs, keep_count)
        logger.debug(
            f"COMPRESS_ENTRY | msgs={len(messages)} | sys={len(system_msgs)} | "
            f"rest={len(rest_msgs)} | keep={keep_count} | "
            f"candidate={len(rest_msgs) - keep_count} | safe_cutoff={cutoff} | "
            f"thread_id={current_thread_id.get()}"
        )
        
        if cutoff <= 0:
            return messages
        
        to_compress = rest_msgs[:cutoff]
        to_keep = rest_msgs[cutoff:]
        
        # 3. 提取受保护的消息（不参与压缩）
        to_compress, to_keep = self._preserve_protected_messages(to_compress, to_keep)

        # 诊断：待压缩清单
        _compress_types = [type(m).__name__ for m in to_compress]
        _compress_chars = [len(self._get_content(m)) for m in to_compress]
        _keep_protected = sum(1 for m in to_keep if self._is_protected(m))
        _keep_recent = len(to_keep) - _keep_protected
        logger.debug(
            f"COMPRESS_ITEMS | "
            f"待压缩: {len(to_compress)}条 types={_compress_types} chars={_compress_chars} | "
            f"保留: {len(to_keep)}条 ({_keep_protected}保护+{_keep_recent}最近) "
            f"chars_total={sum(len(self._get_content(m)) for m in to_keep)} | "
            f"thread_id={current_thread_id.get()}"
        )
        
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
        
        # 4. 系统提示词拼回 position 0，确保 LLM 角色约束不丢失
        result = system_msgs + [summary_msg] + to_keep
        _pre_tok = self._estimate_tokens(messages)
        _post_tok = self._estimate_tokens(result)
        _pre_char = sum(len(self._get_content(m)) for m in messages)
        _post_char = sum(len(self._get_content(m)) for m in result)
        logger.debug(
            f"COMPRESS_TAIL | "
            f"前: {len(messages)}条/{_pre_tok}tok/{_pre_char}ch → "
            f"后: {len(result)}条/{_post_tok}tok/{_post_char}ch | "
            f"净tok: {_post_tok - _pre_tok:+d} | "
            f"构成: {len(system_msgs)}系统+1摘要+{len(to_keep)}保留"
            f"({_keep_protected}保护+{_keep_recent}最近) | "
            f"thread_id={current_thread_id.get()}"
        )
        return result
    
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
        logger.debug(
            f"CUTOFF_INIT | n={n} | candidate={candidate} | keep_count={keep_count} | "
            f"thread_id={current_thread_id.get()}"
        )
        while idx > 0:
            msg = messages[idx]
            _type = type(msg).__name__
            _has_tc = hasattr(msg, 'tool_calls') and bool(msg.tool_calls) if isinstance(msg, AIMessage) else False
            logger.debug(
                f"CUTOFF_WALK | idx={idx} | type={_type} | tool_calls={_has_tc} | "
                f"thread_id={current_thread_id.get()}"
            )
            if isinstance(msg, ToolMessage):
                idx -= 1
                continue
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                break
            break
        logger.debug(
            f"CUTOFF_FINAL | idx={idx} | to_compress=[0:{idx}]={idx}条 | "
            f"to_keep=[{idx}:]={n - idx}条 | thread_id={current_thread_id.get()}"
        )
        return idx

    @staticmethod
    def _truncate_json_aware(content: str, max_chars: int) -> Optional[str]:
        """JSON 感知截断：以完整 JSON 元素为单位，保持输出始终为合法 JSON。

        支持两种输入格式：
        1. 纯 JSON 数组: [elem1, elem2, ...]
           → 保留头部完整元素 + 追加 {"_reminding": "..."} 说明元素
        2. BudgetEnforcement 打包的对象: {"data": [...], "reminding": "..."}
           → 截断 data 数组内的元素 + 更新 reminding 字段

        非 JSON / 无法解析时返回 None，调用方回退字符级截断。
        """
        stripped = content.strip()

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return None

        # ── 格式 1：纯 JSON 数组 ──
        if isinstance(parsed, list):
            if not parsed:
                return content  # 空数组无需截断

            kept = []
            for item in parsed:
                candidate = json.dumps(kept + [item], ensure_ascii=False, default=str)
                if len(candidate) > max_chars:
                    break
                kept.append(item)

            original_count = len(parsed)
            if len(kept) == original_count:
                return content  # 全部放下，无需截断

            if not kept:
                # 单条结果本身超过 max_chars，至少保留 1 条
                kept = [parsed[0]]

            notice = {
                "_reminding": (
                    f"内容已截断：原始 {original_count} 条结果，"
                    f"保留 {len(kept)} 条，移除 {original_count - len(kept)} 条"
                )
            }
            return json.dumps(kept + [notice], ensure_ascii=False, default=str)

        # ── 格式 2：BudgetEnforcement._append_warning 打包的对象 ──
        if isinstance(parsed, dict) and "data" in parsed and isinstance(parsed["data"], list):
            data = parsed["data"]
            if not data:
                return content

            kept_data = []
            for item in data:
                candidate = json.dumps({
                    **parsed,
                    "data": kept_data + [item],
                }, ensure_ascii=False, default=str)
                if len(candidate) > max_chars:
                    break
                kept_data.append(item)

            if len(kept_data) == len(data):
                return content

            if not kept_data:
                kept_data = [data[0]]

            return json.dumps({
                **parsed,
                "data": kept_data,
                "reminding": (
                    f"内容已截断：原始 {len(data)} 条搜索结果，"
                    f"保留 {len(kept_data)} 条，移除 {len(data) - len(kept_data)} 条。"
                    f"{parsed.get('reminding', '')}"
                ),
            }, ensure_ascii=False, default=str)

        return None  # 非数组 / 非已知格式，回退字符截断

    async def _summarize(self, messages: list) -> str:
        """使用 LLM 生成消息摘要"""
        # 统计 after_tool 阶段被截断的消息数（内容含 "已截断" 标记）
        tool_truncated = sum(1 for m in messages if isinstance(m, ToolMessage) and "已截断" in (self._get_content(m) or ""))

        content_parts = []
        for msg in messages:
            role = msg.__class__.__name__.replace("Message", "") if not isinstance(msg, dict) else msg.get("role", "unknown")
            text = self._get_content(msg)
            if text:
                content_parts.append(f"[{role}] {text}")

        content = "\n".join(content_parts)

        # 构造截断说明：让压缩模型知道输入可能不完整
        truncation_warning = ""
        if tool_truncated > 0:
            truncation_warning = (
                f"【截断说明】注意：有 {tool_truncated} 条工具返回因过长已被截断"
                f"（仅保留前 {self.config.tool_result_max_chars} 字符），"
                f"摘要时请以截断前内容为准。\n\n"
            )

        # 限制总输入长度（兜底，防止超模型窗口）
        max_input_chars = int(self.config.max_context_tokens * self.config.token_chars_ratio * 0.5)
        total_input_truncated = False
        if len(content) > max_input_chars:
            content = content[:max_input_chars] + "\n...[总输入已截断]"
            total_input_truncated = True

        if total_input_truncated:
            truncation_warning += (
                f"【截断说明】总输入过长已被截断（仅保留前 {max_input_chars} 字符）。"
            )

        prompt = SUMMARIZATION_PROMPT.format(
            content=content,
            max_chars=self.config.summary_max_chars,
            truncation_warning=truncation_warning,
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            summary = response.content or ""

            # 诊断：压缩模型输入输出完整内容
            _summary_log = summary
            if len(content) > 3000:
                _input_preview = content[:1500] + f"\n...[中间省略, 原始{len(content)}字符]...\n" + content[-500:]
            else:
                _input_preview = content
            logger.debug(
                f"SUMMARY_IO | input_chars={len(content)} | output_chars={len(summary)} | "
                f"truncated_msgs={tool_truncated} | "
                f"thread_id={current_thread_id.get()}\n"
                f"SUMMARY_INPUT:\n{_input_preview}\n"
                f"SUMMARY_OUTPUT:\n{_summary_log}"
            )

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
        """估算消息列表的 token 数（CJK 感知估算，与 llm.py 口径对齐）"""
        total_tokens = 0
        for msg in messages:
            total_tokens += estimate_token_count(_get_message_text(msg))
        return total_tokens
