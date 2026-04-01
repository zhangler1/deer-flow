# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
工具结果压缩中间件集成示例

展示如何在 LangGraph 节点中集成工具结果压缩中间件。
"""

from typing import Any, Dict
from langchain_core.runnables import RunnableConfig

from src.middlewares.tool_result_compression import ToolResultCompressionMiddleware
from src.config.loader import load_tool_compression_config
from src.utils.enhanced_logger import setup_logging

# 在应用启动时加载配置
load_tool_compression_config()

# 创建全局中间件实例（可复用）
tool_compression_middleware = ToolResultCompressionMiddleware()

logger = setup_logging(__name__)


# ============================================================================
# 方式 1: 在节点内手动应用压缩
# ============================================================================

async def researcher_node_with_compression(
    state: Dict[str, Any],
    config: RunnableConfig
) -> Dict[str, Any]:
    """研究节点 - 集成工具结果压缩
    
    在执行 agent 前，使用中间件压缩工具调用结果。
    """
    
    # 获取消息历史
    messages = state.get("messages", [])
    
    # 应用工具结果压缩
    compressed_messages = tool_compression_middleware.process_messages_before_invoke(messages)
    
    # 如果消息被压缩，记录日志
    if compressed_messages != messages:
        logger.info(
            f"🔄 COMPRESSION_APPLIED | "
            f"原始: {len(messages)} 条 → 压缩后: {len(compressed_messages)} 条"
        )
    
    # 准备输入数据
    input_data = {
        "messages": compressed_messages,
        "session_id": state.get("session_id"),
    }
    
    # 执行 researcher agent
    # result = await researcher_agent.ainvoke(input_data, config)
    # 
    # return {
    #     "messages": result.get("messages", []),
    # }
    
    # 示例返回（实际应调用 agent）
    return {
        "messages": compressed_messages,
    }


# ============================================================================
# 方式 2: 使用便捷函数
# ============================================================================

async def researcher_node_with_helper(
    state: Dict[str, Any],
    config: RunnableConfig
) -> Dict[str, Any]:
    """研究节点 - 使用便捷函数
    
    使用 invoke_with_tool_compression 便捷函数，自动应用压缩。
    """
    from src.middlewares.tool_result_compression import invoke_with_tool_compression
    
    # 准备输入数据
    input_data = {
        "messages": state.get("messages", []),
        "session_id": state.get("session_id"),
    }
    
    # 使用便捷函数执行 agent（自动应用压缩）
    # result = await invoke_with_tool_compression(
    #     agent=researcher_agent,
    #     input_data=input_data,
    #     config=config,
    # )
    # 
    # return {
    #     "messages": result.get("messages", []),
    # }
    
    # 示例返回
    return input_data


# ============================================================================
# 方式 3: 条件性压缩（基于状态）
# ============================================================================

async def researcher_node_conditional_compression(
    state: Dict[str, Any],
    config: RunnableConfig
) -> Dict[str, Any]:
    """研究节点 - 条件性压缩
    
    根据特定条件决定是否启用压缩。
    例如：深度研究模式下启用，快速查询模式下禁用。
    """
    
    # 获取消息历史
    messages = state.get("messages", [])
    
    # 根据模式决定是否压缩
    research_mode = state.get("mode", "normal")  # normal, deep, quick
    
    if research_mode == "deep":
        # 深度研究模式：启用压缩以节省 tokens
        compressed_messages = tool_compression_middleware.process_messages_before_invoke(messages)
        logger.info(f"🔍 DEEP_MODE | 启用工具结果压缩")
    else:
        # 其他模式：不压缩
        compressed_messages = messages
        logger.info(f"⚡ QUICK_MODE | 跳过工具结果压缩")
    
    # 准备输入数据
    input_data = {
        "messages": compressed_messages,
        "session_id": state.get("session_id"),
    }
    
    # 执行 agent
    # result = await researcher_agent.ainvoke(input_data, config)
    # return {"messages": result.get("messages", [])}
    
    # 示例返回
    return input_data


# ============================================================================
# 方式 4: 自定义压缩配置
# ============================================================================

async def researcher_node_custom_config(
    state: Dict[str, Any],
    config: RunnableConfig
) -> Dict[str, Any]:
    """研究节点 - 自定义压缩配置
    
    为特定节点创建自定义的压缩配置。
    """
    from src.config.tool_compression_config import (
        ToolCompressionConfig,
        TriggerCondition,
        KeepStrategy,
    )
    
    # 创建自定义配置（更激进的压缩）
    custom_config = ToolCompressionConfig(
        enabled=True,
        trigger=[
            TriggerCondition(type="messages", value=10),  # 10 条消息就触发
            TriggerCondition(type="tokens", value=8000),  # 8000 tokens 就触发
        ],
        keep=KeepStrategy(
            recent_tool_messages=2,      # 只保留最近 2 条
            max_content_per_tool=300,    # 其他截断到 300 字符
        ),
    )
    
    # 创建专用中间件实例
    custom_middleware = ToolResultCompressionMiddleware(config=custom_config)
    
    # 应用压缩
    messages = state.get("messages", [])
    compressed_messages = custom_middleware.process_messages_before_invoke(messages)
    
    logger.info(f"🎛️  CUSTOM_CONFIG | 使用自定义压缩配置")
    
    # 准备输入数据
    input_data = {
        "messages": compressed_messages,
        "session_id": state.get("session_id"),
    }
    
    # 执行 agent
    # result = await researcher_agent.ainvoke(input_data, config)
    # return {"messages": result.get("messages", [])}
    
    # 示例返回
    return input_data


# ============================================================================
# 使用建议
# ============================================================================

"""
推荐使用方式：

1. **大多数场景**：使用方式 1（手动应用）
   - 简单直接，容易理解
   - 便于调试和日志记录
   - 性能开销最小

2. **快速集成**：使用方式 2（便捷函数）
   - 代码更简洁
   - 适合快速原型开发

3. **复杂业务逻辑**：使用方式 3（条件性压缩）
   - 根据业务需求动态调整
   - 更灵活的控制

4. **特殊需求**：使用方式 4（自定义配置）
   - 不同节点使用不同压缩策略
   - 更精细的控制

配置建议：

- 对于频繁调用工具的节点（如 researcher）：启用压缩
- 对于简单对话节点：可以禁用压缩
- 对于报告生成节点（如 reporter）：建议禁用压缩（保留完整信息）

注意事项：

1. 压缩是不可逆的，确保不会丢失关键信息
2. 定期检查日志，观察压缩效果
3. 根据实际使用情况调整触发阈值和保留策略
4. 压缩会增加处理时间（虽然很小），权衡性能和 token 消耗
"""


# ============================================================================
# 示例：完整的 researcher 节点集成
# ============================================================================

async def researcher_node_example(
    state: Dict[str, Any],
    config: RunnableConfig
) -> Dict[str, Any]:
    """完整示例：researcher 节点集成工具结果压缩
    
    这是一个完整的示例，展示如何在实际节点中使用中间件。
    """
    logger.info("🔬 RESEARCHER_NODE | 开始执行研究任务")
    
    # 1. 获取消息历史
    messages = state.get("messages", [])
    logger.debug(f"📊 INPUT | 消息数: {len(messages)}")
    
    # 2. 应用工具结果压缩
    compressed_messages = tool_compression_middleware.process_messages_before_invoke(messages)
    
    # 3. 记录压缩效果
    if compressed_messages != messages:
        compression_ratio = len(compressed_messages) / len(messages) if messages else 1
        logger.info(
            f"🔄 COMPRESSION_APPLIED | "
            f"消息数: {len(messages)} → {len(compressed_messages)} | "
            f"压缩比: {compression_ratio:.2%}"
        )
    
    # 4. 准备输入数据
    input_data = {
        "messages": compressed_messages,
        "session_id": state.get("session_id"),
    }
    
    # 5. 执行 researcher agent
    try:
        # result = await researcher_agent.ainvoke(input_data, config)
        # logger.info(f"✅ RESEARCHER_COMPLETE | 研究任务完成")
        # 
        # return {
        #     "messages": result.get("messages", []),
        # }
        
        # 示例返回
        logger.info(f"✅ RESEARCHER_COMPLETE | 研究任务完成（示例）")
        return {"messages": compressed_messages}
        
    except Exception as e:
        logger.error(f"❌ RESEARCHER_ERROR | 执行失败: {e}")
        raise


__all__ = [
    "researcher_node_with_compression",
    "researcher_node_with_helper",
    "researcher_node_conditional_compression",
    "researcher_node_custom_config",
    "researcher_node_example",
]
