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

    Args:
        observations: Researcher 步骤的输出结果列表

    Returns:
        tuple: (格式化的索引文本, {url: {"index": N, "title": title}} 映射字典)
    """
    url_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
    seen_urls: dict[str, dict] = {}  # url -> {"index": N, "title": title}
    index = 1

    for obs in observations:
        for match in re.finditer(url_pattern, obs):
            title, url = match.group(1), match.group(2)
            # 跳过图片链接（通常以 ![...](url) 格式出现，但正则不匹配 !）
            # 跳过空标题
            if not title.strip():
                continue
            if url not in seen_urls:
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
        
    input_ = {
        "messages": [
            HumanMessage(
                f"# 研究要求\n\n## 任务\n\n{plan_title}\n\n## 描述\n\n{plan_thought}"
            )
        ],
        "locale": state.get("locale", "zh-CN"),
        "system_context": state.get("system_context", ""),
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
                f"**请用{state.get('locale', 'zh-CN')}语言编写报告，并充分引用下面的研究结果。**\n\n"
                f"**引用格式要求：正文中每个数据/事实的句子末尾必须标注来源，格式为 [(N)](URL)，"
                f"其中 N 和 URL 必须来自后面提供的「全局来源索引」。**"
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
                    f"以下是你可以引用的所有来源，请严格使用 [(序号)](URL) 格式引用：\n\n"
                    f"{ref_index_text}\n\n"
                    f"---\n\n"
                    f"**重要规则（必须严格遵守）**：\n"
                    f"- 正文中引用格式：[(1)](对应的URL)\n"
                    f"- 序号必须与上述索引一致\n"
                    f"- 只能引用索引中存在的 URL，禁止编造或修改 URL\n"
                    f"- 同一来源可多次引用，使用相同序号和 URL\n"
                    f"- 末尾「参考资料」章节格式：[N] [来源标题](URL)"
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

    return {"final_report": response_content}


def research_team_node(state: State):
    """研究团队节点，协调多智能体协作完成任务"""
    pass
