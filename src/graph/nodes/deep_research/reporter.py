# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
报告节点模块

包含：
- reporter_node: 报告员节点（撰写最终研究报告）
- research_team_node: 研究团队节点（协调多智能体协作）
"""

import logging
import os
import re
import time

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.template import apply_prompt_template
from src.utils.enhanced_logger import get_enhanced_logger

from src.graph.types import State




logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.deep_research.reporter')


def build_reference_index(observations: list[str]) -> tuple[str, dict]:
    """从所有 observations 中提取 URL，构建全局来源索引。

    采用多层正则回退策略，确保即使模型输出格式不完全标准，也能尽可能提取来源：
      - 模式 1（主）：标准 Markdown 链接 [title](URL)
      - 模式 2（回退）：[来自: URL] 格式（旧版 researcher 可能输出）
      - 模式 3（兜底）：裸 URL 提取（http/https 开头的完整链接）

    Args:
        observations: Researcher 步骤的输出结果列表

    Returns:
        tuple: (格式化的索引文本, {url: {"index": N, "title": title}} 映射字典)
    """
    # 模式 1：标准 Markdown 链接 [title](URL)
    md_link_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
    # 模式 2：[来自: URL] 格式（兼容旧版输出）
    from_pattern = r'\[来自:\s*(https?://[^\]\s]+)\]'
    # 模式 3：裸 URL（兜底，排除已被 Markdown 链接包裹的 URL）
    bare_url_pattern = r'(?<!\()(https?://[^\s\)\]<>"]+)(?!\))'

    seen_urls: dict[str, dict] = {}  # url -> {"index": N, "title": title}
    index = 1

    for obs in observations:
        # 第一遍：提取标准 Markdown 链接
        for match in re.finditer(md_link_pattern, obs):
            title, url = match.group(1), match.group(2)
            # 跳过空标题
            if not title.strip():
                continue
            # 跳过 "来自" 开头的标题（这类标题信息量低，尝试从 URL 推断更好的标题）
            clean_title = title.strip()
            if clean_title.startswith("来自"):
                clean_title = _extract_domain_title(url)
            if url not in seen_urls:
                seen_urls[url] = {"index": index, "title": clean_title}
                index += 1

        # 第二遍：提取 [来自: URL] 格式（仅提取未被模式1覆盖的）
        for match in re.finditer(from_pattern, obs):
            url = match.group(1).rstrip('.,;，。；')
            if url not in seen_urls:
                title = _extract_domain_title(url)
                seen_urls[url] = {"index": index, "title": title}
                index += 1

        # 第三遍（兜底）：提取裸 URL（仅当前两种模式都未捕获时）
        for match in re.finditer(bare_url_pattern, obs):
            url = match.group(1).rstrip('.,;，。；')
            if url not in seen_urls:
                title = _extract_domain_title(url)
                seen_urls[url] = {"index": index, "title": title}
                index += 1

    # 生成索引文本
    lines = []
    for url, info in seen_urls.items():
        lines.append(f"[{info['index']}] {info['title']} [{url}]({url})")

    index_text = "\n\n".join(lines)

    # 打印索引列表日志
    logger.info(f"\n{'='*60}\n全局来源索引（共 {len(seen_urls)} 条）\n{'='*60}")
    for url, info in seen_urls.items():
        logger.info(f"  [{info['index']}] {info['title']} -> {url}")
    logger.info(f"{'='*60}")

    return index_text, seen_urls


def _extract_domain_title(url: str) -> str:
    """从 URL 中提取可读的域名标题作为来源名称的回退方案。

    示例:
        https://www.stats.gov.cn/data/xxx -> stats.gov.cn
        https://pbc.gov.cn/report/2024 -> pbc.gov.cn
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        # 移除 www. 前缀
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else "未知来源"
    except Exception:
        return "未知来源"


def normalize_citations(content: str, ref_map: dict) -> str:
    """后处理：将模型输出中各种变体引用格式统一修正为 [(N)](URL)。

    模型常见的错误格式：
      - [1]、[2] — 纯方括号数字（最常见）
      - 【1】、【2】 — 中文方括号
      - [^1]、[^2] — 脚注格式
      - [[1]]、[[2]] — 双方括号
    
    本函数利用已构建的 ref_map 回填正确的 URL 链接。
    仅修正那些 **不在** 已有 [(N)](URL) 格式中的裸引用。

    Args:
        content: 模型生成的原始报告文本
        ref_map: build_reference_index 返回的 {url: {"index": N, "title": title}} 映射

    Returns:
        修正后的报告文本
    """
    if not ref_map:
        return content

    # 构建反向索引：index_number -> url
    index_to_url: dict[int, str] = {}
    for url, info in ref_map.items():
        idx = info.get("index")
        if idx is not None:
            index_to_url[int(idx)] = url

    if not index_to_url:
        return content

    # 记录修正统计
    fix_count = 0

    # ── 修正模式 1：[N] 但不是 [(N)](URL) 的一部分 ──
    # 负向前瞻/后顾确保不匹配已正确的 [(N)](...)
    # 匹配 [数字] 但排除前面是 ( 的情况（即 [(N)] 已经是正确格式的一部分）
    def _replace_bracket(m: re.Match) -> str:
        nonlocal fix_count
        # 检查前面字符 —— 如果紧跟 '(' 说明可能是 [(N)](URL) 的一部分
        start = m.start()
        if start > 0 and content[start - 1] == '(':
            return m.group(0)  # 不动
        # 检查前面字符 —— 如果是 '\' 说明是 markdown 转义的 \[N]（参考资料区）
        if start > 0 and content[start - 1] == '\\':
            return m.group(0)  # 不动
        # 检查后面是否紧跟 (URL) —— 如果是，说明格式已经正确
        end = m.end()
        if end < len(content) and content[end] == '(':
            return m.group(0)  # 不动

        n = int(m.group(1))
        url = index_to_url.get(n)
        if url:
            fix_count += 1
            return f"[({n})]({url})"
        return m.group(0)  # 索引不在 ref_map 中，保持原样

    # [数字] 或 [^数字] 模式
    content = re.sub(r'\[\^?(\d+)\]', _replace_bracket, content)

    # ── 修正模式 2：【N】中文方括号 ──
    def _replace_cn_bracket(m: re.Match) -> str:
        nonlocal fix_count
        n = int(m.group(1))
        url = index_to_url.get(n)
        if url:
            fix_count += 1
            return f"[({n})]({url})"
        return m.group(0)

    content = re.sub(r'【(\d+)】', _replace_cn_bracket, content)

    # ── 修正模式 3：[[N]] 双方括号 ──
    def _replace_double_bracket(m: re.Match) -> str:
        nonlocal fix_count
        n = int(m.group(1))
        url = index_to_url.get(n)
        if url:
            fix_count += 1
            return f"[({n})]({url})"
        return m.group(0)

    content = re.sub(r'\[\[(\d+)\]\]', _replace_double_bracket, content)

    if fix_count > 0:
        logger.info(f"[normalize_citations] 修正了 {fix_count} 处引用格式")

    return content


async def reporter_node(state: State, config: RunnableConfig):
    """撰写最终报告的报告员节点"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | reporter | 开始执行报告生成节点")
    
    configurable = Configuration.from_runnable_config(config)
    
    # 记录报告生成的基本信息
    observations = state.get("observations", [])
    current_plan = state.get("current_plan")
    
    # 处理 current_plan 的类型差异
    if hasattr(current_plan, 'title') and hasattr(current_plan, 'thought'):
        plan_title = current_plan.title
        plan_thought = current_plan.thought
    elif isinstance(current_plan, dict):
        plan_title = current_plan.get('title', '未知计划')
        plan_thought = current_plan.get('thought', '计划详情不可用')
    else:
        plan_title = str(current_plan) if current_plan else "未知计划"
        plan_thought = "计划详情不可用"
        
    # reporter 使用文档原文（而非摘要），确保报告能参考完整内容
    base_system_context = state.get("system_context", "")
    doc_original = state.get("document_original", "")
    if doc_original:
        reporter_context = base_system_context
        if reporter_context:
            reporter_context += "\n\n"
        reporter_context += f"以下是用户上传的参考文档原文，请在撰写报告时充分参考：\n\n{doc_original}"
    else:
        reporter_context = base_system_context

    input_ = {
        "messages": [
            HumanMessage(
                f"# 研究要求\n\n## 任务\n\n{plan_title}\n\n## 描述\n\n{plan_thought}"
            )
        ],
        "locale": state.get("locale", "zh-CN"),
        "system_context": reporter_context,
    }
    invoke_messages = apply_prompt_template("reporter", input_, configurable)
    observations = state.get("observations", [])

    # 添加关于报告格式和表格使用的提醒（引用格式由全局索引统一管理）
    invoke_messages.append(
        HumanMessage(
            content=(
                f"重要提示：请按照提示词中的格式组织您的报告。记得包含：\n\n"
                f"1. 关键要点 - 最重要发现的要点列表\n"
                f"2. 概述 - 主题的简要介绍\n"
                f"3. 详细分析 - 按逻辑部分组织\n"
                f"4. 调研说明（可选）- 用于更全面的报告\n"
                f"5. 参考资料 - 在末尾列出所有参考文献\n\n"
                f"优先使用MARKDOWN表格进行数据展示和对比。在展示对比数据、统计信息、功能或选项时使用表格。\n\n"
                f"**请用{state.get('locale', 'zh-CN')}语言编写报告，并充分引用下面的研究结果。**"
            ),
            name="system"
        )
    )

    for i, observation in enumerate(observations):
        invoke_messages.append(
            HumanMessage(
                content=f"# 研究步骤 {i+1} 的结果\n\n{observation}\n\n---",
                name="observation",
            )
        )

    # 构建全局来源索引并注入（三层保障策略 - 第1层：Prompt 约束）
    ref_index_text, ref_map = build_reference_index(observations)
    if ref_index_text:
        # 截断策略：来源数量过多时只保留 top-50
        max_sources = 50
        if len(ref_map) > max_sources:
            lines = ref_index_text.split("\n\n")[:max_sources]
            ref_index_text = "\n\n".join(lines)
            ref_index_text += f"\n\n...（还有 {len(ref_map) - max_sources} 条未列出的来源）"

        invoke_messages.append(
            HumanMessage(
                content=(
                    f"# 全局来源索引（共 {min(len(ref_map), max_sources)} 条，已去重）\n\n"
                    f"以下是你**唯一可以引用**的来源列表。请严格使用 [(序号)](URL) 格式引用：\n\n"
                    f"{ref_index_text}"
                ),
                name="reference_index",
            )
        )
        enhanced_logger.logger.info(f"📚 REFERENCE_INDEX | 已构建全局来源索引 | 来源总数: {len(ref_map)} | 注入数: {min(len(ref_map), max_sources)}")
    else:
        enhanced_logger.logger.info(f"⚠️ REFERENCE_INDEX | 未从 observations 中提取到任何来源 URL")

    enhanced_logger.logger.info(f"📝 REPORTER_INPUT | 输入消息数: {len(invoke_messages)} | 观察结果数: {len(observations)} | 计划标题: {plan_title}")
    
    llm_start_time = time.time()
    enhanced_logger.logger.info(f"🤖 LLM_INVOKE | reporter | 开始生成最终报告 | 消息数: {len(invoke_messages)}")

    try:
        reporter_llm = get_llm_by_type(
            AGENT_LLM_MAP["reporter"],
            reporter_model_key=configurable.reporter_model or None,
        )

        # 获取取消事件（统一封装，一行搞定）
        from src.graph.cancellation import get_from_config as _get_cancel_event
        cancel_event = _get_cancel_event(config)
        enhanced_logger.logger.info(
            f"🔍 CANCEL_EVENT_STATUS | reporter | cancel_event={'已注册' if cancel_event is not None else 'None'}"
        )

        # 如果已取消，直接返回
        if cancel_event and cancel_event.is_set():
            enhanced_logger.logger.info(f"⛔ LLM_SKIPPED | reporter | 客户端已断连，跳过报告生成")
            return {"final_report": "报告生成已被用户取消。"}


        # 使用 astream() 替代 stream()，允许在 chunk 之间检测取消信号
        chunks = []
        cancelled = False
        async for chunk in reporter_llm.astream(invoke_messages):
            if cancel_event and cancel_event.is_set():
                enhanced_logger.logger.info(
                    f"⛔ LLM_CANCELLED | reporter | 客户端断连，中止报告生成 | "
                    f"已生成 {len(chunks)} 个 chunk"
                )
                cancelled = True
                break
            chunks.append(chunk)

        # 拼接所有 chunk 的内容
        response_content = "".join(
            chunk.content for chunk in chunks if hasattr(chunk, 'content') and chunk.content
        )

        llm_call_end_time = time.time()
        if cancelled:
            enhanced_logger.logger.info(
                f"⛔ LLM_CALL_CANCELLED | reporter | 报告生成被中断 | "
                f"耗时: {llm_call_end_time - llm_start_time:.2f}s | "
                f"已生成内容长度: {len(response_content)}"
            )
            if not response_content:
                response_content = "报告生成已被用户取消。"
        else:
            pass

        llm_duration = time.time() - llm_start_time
        report_length = len(response_content) if response_content else 0
        enhanced_logger.logger.info(f"✅ LLM_COMPLETE | reporter | 报告生成完成 | 报告长度: {report_length} | LLM耗时: {llm_duration:.2f}s")

    except Exception as e:
        llm_duration = time.time() - llm_start_time
        enhanced_logger.logger.error(f"❌ LLM_ERROR | reporter | LLM调用失败 | 耗时: {llm_duration:.2f}s | 错误类型: {type(e).__name__} | 错误信息: {str(e)}")
        logger.exception(f"Reporter LLM调用异常: {e}")
        raise
    
    # 长文本日志截断：只保留前300字和后300字
    _resp_str = response_content if isinstance(response_content, str) else str(response_content)
    if len(_resp_str) > 600:
        _resp_preview = f"{_resp_str[:300]}\n...[省略 {len(_resp_str) - 600} 字]...\n{_resp_str[-300:]}"
    else:
        _resp_preview = _resp_str
    logger.info(f"reporter response: /n{_resp_preview}")

    # # 保存 observations 为 markdown 文件
    # if observations:
    #     try:
    #         examples_dir = "md_output"
    #         os.makedirs(examples_dir, exist_ok=True)

    #         timestamp = time.strftime("%Y%m%d_%H%M%S")
    #         filename = f"{examples_dir}/research_observations_{timestamp}.md"

    #         md_content = f"# 研究观察结果\n\n"
    #         md_content += f"## 研究主题\n\n{plan_title}\n\n"
    #         md_content += f"---\n\n"

    #         for i, observation in enumerate(observations):
    #             md_content += f"{observation}\n\n"

    #         with open(filename, 'w', encoding='utf-8') as f:
    #             f.write(md_content)

    #         enhanced_logger.logger.info(f"📄 OBSERVATIONS_SAVED | 观察结果已保存到文件: {filename} | 大小: {len(md_content)} 字节")
    #         logger.info(f"Observations saved to: {filename}")

    #     except Exception as e:
    #         enhanced_logger.logger.error(f"❌ SAVE_OBSERVATIONS_FAILED | 保存观察结果失败: {str(e)}")
    #         logger.error(f"Failed to save observations: {e}")

    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | reporter | 节点执行完成 | 总耗时: {duration:.2f}s")

    # 后处理：修正模型输出中的变体引用格式（[N] → [(N)](URL)）
    if ref_map and response_content:
        response_content = normalize_citations(response_content, ref_map)

    # 构建 reference_index 列表，通过 State 传递给前端（保证 MD 和 UI 参考文献一致）
    reference_index_list = []
    if ref_map:
        for url, info in ref_map.items():
            reference_index_list.append({
                "index": info["index"],
                "url": url,
                "title": info.get("title", ""),
            })
        # 按序号排序
        reference_index_list.sort(key=lambda x: x["index"])
        enhanced_logger.logger.info(f"📚 REFERENCE_INDEX_OUTPUT | 参考文献索引已构建 | 条数: {len(reference_index_list)}")

    return {"final_report": response_content, "reference_index": reference_index_list}


def research_team_node(state: State):
    """研究团队节点，协调多智能体协作完成任务"""
    pass
