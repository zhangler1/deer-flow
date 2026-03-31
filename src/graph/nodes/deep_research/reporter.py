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
import time

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.template import apply_prompt_template
from src.utils.enhanced_logger import get_enhanced_logger

from src.graph.types import State

# Langfuse 集成
try:
    from langfuse import observe
except ImportError:
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return decorator


logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('graph.nodes.deep_research.reporter')


@observe(name="📝 报告节点", as_type="agent")
def reporter_node(state: State, config: RunnableConfig):
    """撰写最终报告的报告员节点"""
    start_time = time.time()
    enhanced_logger.logger.info(f"🔄 NODE_ENTRY | reporter | 开始执行报告生成节点")
    
    logger.info("Reporter write final report")
    configurable = Configuration.from_runnable_config(config)
    
    # 记录报告生成的基本信息
    observations = state.get("observations", [])
    enhanced_logger.logger.info(f"📊 REPORT_INIT | 开始生成最终报告 | 研究步骤数: {len(observations)}")
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
    }
    invoke_messages = apply_prompt_template("reporter", input_, configurable)
    observations = state.get("observations", [])

    # 添加关于报告格式、引用风格和表格使用的提醒
    invoke_messages.append(
        HumanMessage(
            content=f"重要提示：请按照提示词中的格式组织您的报告。记得包含：\n\n1. 关键要点 - 最重要发现的要点列表\n2. 概述 - 主题的简要介绍\n3. 详细分析 - 按逻辑部分组织\n4. 调研说明（可选）- 用于更全面的报告\n5. 主要引用 - 在末尾列出所有参考文献\n\n对于引用，不要在正文中包含内联引用。而是将所有引用放在末尾的'主要引用'部分，使用格式：`- [来源标题](URL)`。在每个引用之间包含一个空行以提高可读性。\n\n优先使用MARKDOWN表格进行数据展示和对比。在展示对比数据、统计信息、功能或选项时使用表格。使用清晰的表头和对齐的列来构建表格。示例表格格式：\n\n| 功能 | 描述 | 优点 | 缺点 |\n|------|------|------|------|\n| 功能1 | 描述1 | 优点1 | 缺点1 |\n| 功能2 | 描述2 | 优点2 | 缺点2 |\n\n**请用{state.get('locale', 'zh-CN')}语言编写报告，并充分引用下面的研究结果。**",
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
    logger.debug(f"Current invoke messages: {invoke_messages}")
    
    logger.info(f"Reporter input: {invoke_messages}")
    enhanced_logger.logger.info(f"📝 REPORTER_INPUT | 输入消息数: {len(invoke_messages)} | 观察结果数: {len(observations)} | 计划标题: {plan_title}")
    
    llm_start_time = time.time()
    enhanced_logger.logger.info(f"🤖 LLM_INVOKE | reporter | 开始生成最终报告 | 提示消息数: {len(invoke_messages)}")

    try:
        reporter_llm = get_llm_by_type(AGENT_LLM_MAP["reporter"])
        enhanced_logger.logger.info(f"🔍 LLM_INFO | reporter | 模型类型: {type(reporter_llm).__name__} | 模型名称: {getattr(reporter_llm, 'model_name', 'unknown')}")

        enhanced_logger.logger.info(f"⏳ LLM_CALL_START | reporter | 准备调用LLM.invoke() | 时间: {time.strftime('%H:%M:%S')}")

        response = reporter_llm.invoke(invoke_messages)

        llm_call_end_time = time.time()
        enhanced_logger.logger.info(f"✅ LLM_CALL_END | reporter | LLM调用成功返回 | 时间: {time.strftime('%H:%M:%S')} | 耗时: {llm_call_end_time - llm_start_time:.2f}s")

        response_content = response.content

        llm_duration = time.time() - llm_start_time
        report_length = len(response_content) if response_content else 0
        enhanced_logger.logger.info(f"✅ LLM_COMPLETE | reporter | 报告生成完成 | 报告长度: {report_length} | LLM耗时: {llm_duration:.2f}s")

    except Exception as e:
        llm_duration = time.time() - llm_start_time
        enhanced_logger.logger.error(f"❌ LLM_ERROR | reporter | LLM调用失败 | 耗时: {llm_duration:.2f}s | 错误类型: {type(e).__name__} | 错误信息: {str(e)}")
        logger.exception(f"Reporter LLM调用异常: {e}")
        raise
    
    logger.info(f"reporter response: {response_content}")

    # 保存 observations 为 markdown 文件
    if observations:
        try:
            examples_dir = "md_output"
            os.makedirs(examples_dir, exist_ok=True)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{examples_dir}/research_observations_{timestamp}.md"

            md_content = f"# 研究观察结果\n\n"
            md_content += f"## 研究主题\n\n{plan_title}\n\n"
            md_content += f"---\n\n"

            for i, observation in enumerate(observations):
                md_content += f"{observation}\n\n"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(md_content)

            enhanced_logger.logger.info(f"📄 OBSERVATIONS_SAVED | 观察结果已保存到文件: {filename} | 大小: {len(md_content)} 字节")
            logger.info(f"Observations saved to: {filename}")

        except Exception as e:
            enhanced_logger.logger.error(f"❌ SAVE_OBSERVATIONS_FAILED | 保存观察结果失败: {str(e)}")
            logger.error(f"Failed to save observations: {e}")

    duration = time.time() - start_time
    enhanced_logger.logger.info(f"✅ NODE_EXIT | reporter | 节点执行完成 | 总耗时: {duration:.2f}s")

    return {"final_report": response_content}


def research_team_node(state: State):
    """研究团队节点，协调多智能体协作完成任务"""
    logger.info("研究团队正在协作执行任务")
    pass
