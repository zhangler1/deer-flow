#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证新的压缩配置：保留最近2条，其余压缩到1000字符"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.middlewares.tool_result_compression import ToolResultCompressionMiddleware
from src.config.loader import load_tool_compression_config

def print_header(text: str):
    """打印分隔符"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def main():
    """测试新配置"""
    print_header("🔧 验证新的压缩配置")
    
    # 加载配置
    load_tool_compression_config()
    
    # 创建中间件
    middleware = ToolResultCompressionMiddleware()
    
    # 验证配置
    print(f"📋 配置信息:")
    print(f"   - 启用状态: {middleware.config.enabled}")
    print(f"   - 保留最近消息数: {middleware.config.keep.recent_tool_messages}")
    print(f"   - 最大保留字符数: {middleware.config.keep.max_content_per_tool}")
    
    if middleware.config.keep.recent_tool_messages != 2:
        print(f"\n❌ 错误：保留消息数应该是 2，实际是 {middleware.config.keep.recent_tool_messages}")
        return 1
    
    if middleware.config.keep.max_content_per_tool != 1000:
        print(f"\n❌ 错误：最大字符数应该是 1000，实际是 {middleware.config.keep.max_content_per_tool}")
        return 1
    
    print(f"\n✅ 配置验证通过！")
    
    # 测试压缩效果
    print_header("🧪 测试压缩效果")
    
    # 创建测试消息（6条工具消息）
    messages = [
        HumanMessage(content="查询天气"),
        AIMessage(content="好的，我来查询"),
        ToolMessage(content="A" * 1500, tool_call_id="call_1"),  # 旧消息 - 应该被压缩到 1000
        ToolMessage(content="B" * 1500, tool_call_id="call_2"),  # 旧消息 - 应该被压缩到 1000
        ToolMessage(content="C" * 1500, tool_call_id="call_3"),  # 旧消息 - 应该被压缩到 1000
        ToolMessage(content="D" * 1500, tool_call_id="call_4"),  # 旧消息 - 应该被压缩到 1000
        ToolMessage(content="E" * 1500, tool_call_id="call_5"),  # 最近消息 - 应该保留完整
        ToolMessage(content="F" * 1500, tool_call_id="call_6"),  # 最近消息 - 应该保留完整
    ]
    
    print(f"原始消息数: {len(messages)}")
    print(f"工具消息数: 6 条（每条 1500 字符）")
    
    # 应用压缩
    from src.config.tool_compression_config import (
        ToolCompressionConfig,
        TriggerCondition,
        KeepStrategy,
    )
    
    # 使用强制触发的配置
    force_config = ToolCompressionConfig(
        enabled=True,
        trigger=[TriggerCondition(type="messages", value=1)],  # 强制触发
        keep=KeepStrategy(
            recent_tool_messages=2,
            max_content_per_tool=1000,
        ),
    )
    
    middleware_force = ToolResultCompressionMiddleware(config=force_config)
    compressed_messages = middleware_force.compress_messages(messages)
    
    # 验证结果
    print(f"\n压缩后的消息:")
    for i, msg in enumerate(compressed_messages):
        if isinstance(msg, ToolMessage):
            content_len = len(msg.content)
            is_truncated = "已截断" in msg.content
            
            if i == 2:  # call_1 (旧消息，应该压缩)
                expected = "应该被压缩到约 1030 字符"
                status = "✅" if is_truncated and content_len < 1100 else "❌"
            elif i == 3:  # call_2 (旧消息，应该压缩)
                expected = "应该被压缩到约 1030 字符"
                status = "✅" if is_truncated and content_len < 1100 else "❌"
            elif i == 4:  # call_3 (旧消息，应该压缩)
                expected = "应该被压缩到约 1030 字符"
                status = "✅" if is_truncated and content_len < 1100 else "❌"
            elif i == 5:  # call_4 (旧消息，应该压缩)
                expected = "应该被压缩到约 1030 字符"
                status = "✅" if is_truncated and content_len < 1100 else "❌"
            elif i == 6:  # call_5 (最近消息，应该完整)
                expected = "应该保留完整 1500 字符"
                status = "✅" if not is_truncated and content_len == 1500 else "❌"
            elif i == 7:  # call_6 (最近消息，应该完整)
                expected = "应该保留完整 1500 字符"
                status = "✅" if not is_truncated and content_len == 1500 else "❌"
            else:
                expected = "N/A"
                status = "ℹ️"
            
            print(f"  [{i}] ToolMessage: {content_len} 字符 | {expected} | {status}")
    
    # 验证压缩规则
    print_header("📊 压缩规则验证")
    
    # 检查前4条工具消息（索引 2-5）是否被压缩
    old_messages_compressed = all(
        "已截断" in compressed_messages[i].content 
        for i in [2, 3, 4, 5]
    )
    
    # 检查后2条工具消息（索引 6-7）是否完整
    recent_messages_intact = all(
        "已截断" not in compressed_messages[i].content and len(compressed_messages[i].content) == 1500
        for i in [6, 7]
    )
    
    print(f"前 4 条工具消息已压缩: {'✅' if old_messages_compressed else '❌'}")
    print(f"最近 2 条工具消息完整保留: {'✅' if recent_messages_intact else '❌'}")
    
    if old_messages_compressed and recent_messages_intact:
        print(f"\n🎉 所有测试通过！新配置工作正常。")
        print(f"\n📝 配置总结:")
        print(f"   - 保留最近 2 条工具消息的完整内容")
        print(f"   - 其余工具消息压缩到 1000 字符")
        return 0
    else:
        print(f"\n❌ 测试失败，请检查配置。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
