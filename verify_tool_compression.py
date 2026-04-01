#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""验证工具结果压缩中间件功能"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.middlewares.tool_result_compression import ToolResultCompressionMiddleware
from src.config.tool_compression_config import (
    ToolCompressionConfig,
    TriggerCondition,
    KeepStrategy,
    ModelConfig,
)
from src.config.loader import load_tool_compression_config


def print_header(text: str):
    """打印分隔符"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def test_basic_initialization():
    """测试 1: 基本初始化"""
    print_header("测试 1: 基本初始化")
    
    middleware = ToolResultCompressionMiddleware()
    print(f"✅ 中间件初始化成功")
    print(f"   - 配置已加载: {middleware.config is not None}")
    print(f"   - 启用状态: {middleware.config.enabled}")
    
    return True


def test_custom_config():
    """测试 2: 自定义配置"""
    print_header("测试 2: 自定义配置")
    
    config = ToolCompressionConfig(
        enabled=True,
        trigger=[
            TriggerCondition(type="messages", value=10),
            TriggerCondition(type="tokens", value=5000),
        ],
        keep=KeepStrategy(
            recent_tool_messages=2,
            max_content_per_tool=300,
        ),
        model=ModelConfig(name=None, temperature=0.3),
    )
    
    middleware = ToolResultCompressionMiddleware(config=config)
    print(f"✅ 自定义配置初始化成功")
    print(f"   - 启用: {middleware.config.enabled}")
    print(f"   - 触发条件数量: {len(middleware.config.trigger)}")
    print(f"   - 保留最近消息数: {middleware.config.keep.recent_tool_messages}")
    print(f"   - 最大内容长度: {middleware.config.keep.max_content_per_tool}")
    
    return True


def test_token_estimation():
    """测试 3: Token 估算"""
    print_header("测试 3: Token 估算")
    
    middleware = ToolResultCompressionMiddleware()
    
    messages = [
        HumanMessage(content="Hello" * 100),  # 500 chars
        AIMessage(content="World" * 100),     # 500 chars
    ]
    
    token_count = middleware.estimate_token_count(messages)
    print(f"✅ Token 估算测试通过")
    print(f"   - 总字符数: {500 + 500} 字符")
    print(f"   - 估算 tokens: {token_count} (约 4 字符/token)")
    
    expected = 1000 // 4
    assert token_count == expected, f"期望 {expected}, 实际 {token_count}"
    
    return True


def test_extract_tool_messages():
    """测试 4: 提取工具消息"""
    print_header("测试 4: 提取工具消息")
    
    middleware = ToolResultCompressionMiddleware()
    
    messages = [
        HumanMessage(content="Query 1"),
        AIMessage(content="Response 1"),
        ToolMessage(content="Tool result 1", tool_call_id="call_1"),
        HumanMessage(content="Query 2"),
        ToolMessage(content="Tool result 2", tool_call_id="call_2"),
    ]
    
    tool_messages = middleware.extract_tool_messages(messages)
    print(f"✅ 工具消息提取测试通过")
    print(f"   - 总消息数: {len(messages)}")
    print(f"   - 工具消息数: {len(tool_messages)}")
    print(f"   - 工具消息索引: {[idx for idx, _ in tool_messages]}")
    
    assert len(tool_messages) == 2
    assert tool_messages[0][0] == 2
    assert tool_messages[1][0] == 4
    
    return True


def test_compress_single_message():
    """测试 5: 压缩单个工具消息"""
    print_header("测试 5: 压缩单个工具消息")
    
    middleware = ToolResultCompressionMiddleware()
    
    # 创建一个长消息
    long_content = "A" * 1000
    tool_msg = ToolMessage(content=long_content, tool_call_id="call_1")
    
    # 压缩到 100 字符
    compressed = middleware.compress_tool_message(tool_msg, max_length=100)
    
    print(f"✅ 单个消息压缩测试通过")
    print(f"   - 原始长度: {len(tool_msg.content)} 字符")
    print(f"   - 压缩后长度: {len(compressed.content)} 字符")
    print(f"   - 包含截断提示: {'已截断' in compressed.content}")
    print(f"   - 压缩后内容预览: {compressed.content[:150]}...")
    
    assert compressed.content.startswith("A" * 100)
    assert "已截断" in compressed.content
    assert "原始长度: 1000" in compressed.content
    
    return True


def test_no_truncation_for_short_message():
    """测试 6: 短消息不截断"""
    print_header("测试 6: 短消息不截断")
    
    middleware = ToolResultCompressionMiddleware()
    
    short_content = "Short message"
    tool_msg = ToolMessage(content=short_content, tool_call_id="call_1")
    
    compressed = middleware.compress_tool_message(tool_msg, max_length=100)
    
    print(f"✅ 短消息保留测试通过")
    print(f"   - 原始内容: {tool_msg.content}")
    print(f"   - 压缩后内容: {compressed.content}")
    print(f"   - 内容未改变: {compressed.content == short_content}")
    
    assert compressed.content == short_content
    assert "已截断" not in compressed.content
    
    return True


def test_compression_trigger():
    """测试 7: 压缩触发条件"""
    print_header("测试 7: 压缩触发条件")
    
    config = ToolCompressionConfig(
        enabled=True,
        trigger=[TriggerCondition(type="messages", value=5)],
    )
    middleware = ToolResultCompressionMiddleware(config=config)
    
    # 少于阈值
    messages_low = [HumanMessage(content="Test")] * 4
    should_compress_low = middleware.should_compress(messages_low)
    
    # 等于阈值
    messages_equal = [HumanMessage(content="Test")] * 5
    should_compress_equal = middleware.should_compress(messages_equal)
    
    # 超过阈值
    messages_high = [HumanMessage(content="Test")] * 10
    should_compress_high = middleware.should_compress(messages_high)
    
    print(f"✅ 触发条件测试通过")
    print(f"   - 4 条消息 (阈值 5): 不触发 = {not should_compress_low}")
    print(f"   - 5 条消息 (阈值 5): 触发 = {should_compress_equal}")
    print(f"   - 10 条消息 (阈值 5): 触发 = {should_compress_high}")
    
    assert not should_compress_low
    assert should_compress_equal
    assert should_compress_high
    
    return True


def test_full_compression_workflow():
    """测试 8: 完整压缩流程"""
    print_header("测试 8: 完整压缩流程")
    
    config = ToolCompressionConfig(
        enabled=True,
        trigger=[TriggerCondition(type="messages", value=5)],
        keep=KeepStrategy(
            recent_tool_messages=2,
            max_content_per_tool=50,
        ),
    )
    middleware = ToolResultCompressionMiddleware(config=config)
    
    messages = [
        HumanMessage(content="Query"),
        ToolMessage(content="Old result " + "A" * 100, tool_call_id="call_1"),
        ToolMessage(content="Old result " + "B" * 100, tool_call_id="call_2"),
        ToolMessage(content="Recent result " + "C" * 100, tool_call_id="call_3"),
        ToolMessage(content="Recent result " + "D" * 100, tool_call_id="call_4"),
    ]
    
    print(f"压缩前:")
    for i, msg in enumerate(messages):
        if isinstance(msg, ToolMessage):
            print(f"  [{i}] ToolMessage: {len(msg.content)} 字符")
    
    result = middleware.compress_messages(messages)
    
    print(f"\n压缩后:")
    for i, msg in enumerate(result):
        if isinstance(msg, ToolMessage):
            is_compressed = "已截断" in msg.content
            print(f"  [{i}] ToolMessage: {len(msg.content)} 字符 {'(已压缩)' if is_compressed else '(完整)'}")
    
    # 验证
    assert "已截断" in result[1].content  # 旧消息应被压缩
    assert "已截断" in result[2].content  # 旧消息应被压缩
    assert "已截断" not in result[3].content  # 最近消息应完整
    assert "已截断" not in result[4].content  # 最近消息应完整
    
    print(f"\n✅ 完整压缩流程测试通过")
    print(f"   - 压缩了前 2 条工具消息")
    print(f"   - 保留了最近 2 条完整内容")
    
    return True


def test_load_from_config_file():
    """测试 9: 从配置文件加载"""
    print_header("测试 9: 从配置文件加载")
    
    try:
        # 加载配置
        load_tool_compression_config()
        
        # 创建中间件（会自动使用加载的配置）
        middleware = ToolResultCompressionMiddleware()
        
        print(f"✅ 配置文件加载测试通过")
        print(f"   - 配置启用: {middleware.config.enabled}")
        print(f"   - 触发条件数: {len(middleware.config.trigger)}")
        
        if middleware.config.trigger:
            for i, trigger in enumerate(middleware.config.trigger):
                print(f"   - 触发条件 {i+1}: {trigger.type} = {trigger.value}")
        
        print(f"   - 保留最近: {middleware.config.keep.recent_tool_messages} 条")
        print(f"   - 最大长度: {middleware.config.keep.max_content_per_tool} 字符")
        
        return True
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "🚀" * 40)
    print("  工具结果压缩中间件验证测试")
    print("🚀" * 40)
    
    tests = [
        test_basic_initialization,
        test_custom_config,
        test_token_estimation,
        test_extract_tool_messages,
        test_compress_single_message,
        test_no_truncation_for_short_message,
        test_compression_trigger,
        test_full_compression_workflow,
        test_load_from_config_file,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test.__name__} 失败")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print_header("测试总结")
    print(f"✅ 通过: {passed}/{len(tests)}")
    print(f"❌ 失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！中间件工作正常。\n")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查错误信息。\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
