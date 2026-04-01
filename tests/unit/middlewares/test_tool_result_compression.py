# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""Tests for tool result compression middleware"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.middlewares.tool_result_compression import ToolResultCompressionMiddleware
from src.config.tool_compression_config import (
    ToolCompressionConfig,
    TriggerCondition,
    KeepStrategy,
    ModelConfig,
)


def test_middleware_initialization():
    """Test middleware can be initialized with default config"""
    middleware = ToolResultCompressionMiddleware()
    assert middleware.config is not None
    assert isinstance(middleware.config, ToolCompressionConfig)


def test_middleware_with_custom_config():
    """Test middleware can be initialized with custom config"""
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
    assert middleware.config.enabled is True
    assert len(middleware.config.trigger) == 2
    assert middleware.config.keep.recent_tool_messages == 2


def test_estimate_token_count():
    """Test token count estimation"""
    middleware = ToolResultCompressionMiddleware()
    
    messages = [
        HumanMessage(content="Hello" * 100),  # 500 chars ≈ 125 tokens
        AIMessage(content="World" * 100),     # 500 chars ≈ 125 tokens
    ]
    
    token_count = middleware.estimate_token_count(messages)
    # 1000 chars / 4 = 250 tokens
    assert token_count == 250


def test_extract_tool_messages():
    """Test extracting tool messages from message list"""
    middleware = ToolResultCompressionMiddleware()
    
    messages = [
        HumanMessage(content="Query"),
        AIMessage(content="Response"),
        ToolMessage(content="Tool result 1", tool_call_id="call_1"),
        AIMessage(content="Analysis"),
        ToolMessage(content="Tool result 2", tool_call_id="call_2"),
    ]
    
    tool_messages = middleware.extract_tool_messages(messages)
    assert len(tool_messages) == 2
    assert tool_messages[0][0] == 2  # Index of first tool message
    assert tool_messages[1][0] == 4  # Index of second tool message
    assert isinstance(tool_messages[0][1], ToolMessage)
    assert isinstance(tool_messages[1][1], ToolMessage)


def test_compress_tool_message():
    """Test compressing a single tool message"""
    middleware = ToolResultCompressionMiddleware()
    
    # Create a long tool message
    long_content = "A" * 1000
    tool_msg = ToolMessage(content=long_content, tool_call_id="call_1")
    
    # Compress to 100 chars
    compressed = middleware.compress_tool_message(tool_msg, max_length=100)
    
    assert len(compressed.content) > 100  # Includes truncation message
    assert compressed.content.startswith("A" * 100)
    assert "已截断" in compressed.content
    assert "原始长度: 1000" in compressed.content


def test_compress_tool_message_no_truncation():
    """Test that short messages are not truncated"""
    middleware = ToolResultCompressionMiddleware()
    
    short_content = "Short message"
    tool_msg = ToolMessage(content=short_content, tool_call_id="call_1")
    
    compressed = middleware.compress_tool_message(tool_msg, max_length=100)
    
    assert compressed.content == short_content
    assert "已截断" not in compressed.content


def test_should_compress_disabled():
    """Test that compression is skipped when disabled"""
    config = ToolCompressionConfig(enabled=False)
    middleware = ToolResultCompressionMiddleware(config=config)
    
    messages = [HumanMessage(content="Test")] * 100
    assert middleware.should_compress(messages) is False


def test_should_compress_by_message_count():
    """Test compression trigger by message count"""
    config = ToolCompressionConfig(
        enabled=True,
        trigger=[TriggerCondition(type="messages", value=5)],
    )
    middleware = ToolResultCompressionMiddleware(config=config)
    
    # Less than threshold
    messages = [HumanMessage(content="Test")] * 4
    assert middleware.should_compress(messages) is False
    
    # At threshold
    messages = [HumanMessage(content="Test")] * 5
    assert middleware.should_compress(messages) is True
    
    # Above threshold
    messages = [HumanMessage(content="Test")] * 10
    assert middleware.should_compress(messages) is True


def test_should_compress_by_token_count():
    """Test compression trigger by token count"""
    config = ToolCompressionConfig(
        enabled=True,
        trigger=[TriggerCondition(type="tokens", value=100)],
    )
    middleware = ToolResultCompressionMiddleware(config=config)
    
    # Less than threshold (50 chars * 4 = 200 chars = 50 tokens)
    messages = [HumanMessage(content="A" * 50)] * 4
    assert middleware.should_compress(messages) is False
    
    # Above threshold (100 chars * 4 = 400 chars = 100 tokens)
    messages = [HumanMessage(content="A" * 100)] * 4
    assert middleware.should_compress(messages) is True


def test_compress_messages_no_tool_messages():
    """Test that compression is skipped when no tool messages exist"""
    config = ToolCompressionConfig(
        enabled=True,
        trigger=[TriggerCondition(type="messages", value=3)],
    )
    middleware = ToolResultCompressionMiddleware(config=config)
    
    messages = [
        HumanMessage(content="Query 1"),
        AIMessage(content="Response 1"),
        HumanMessage(content="Query 2"),
        AIMessage(content="Response 2"),
    ]
    
    result = middleware.compress_messages(messages)
    assert result == messages  # No changes


def test_compress_messages_keeps_recent():
    """Test that recent tool messages are kept intact"""
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
    
    result = middleware.compress_messages(messages)
    
    # First two should be compressed
    assert "已截断" in result[1].content
    assert "已截断" in result[2].content
    
    # Last two should be intact
    assert "已截断" not in result[3].content
    assert "已截断" not in result[4].content
    assert "Recent result C" in result[3].content
    assert "Recent result D" in result[4].content


def test_compress_messages_preserves_other_messages():
    """Test that non-tool messages are preserved"""
    config = ToolCompressionConfig(
        enabled=True,
        trigger=[TriggerCondition(type="messages", value=3)],
        keep=KeepStrategy(
            recent_tool_messages=1,
            max_content_per_tool=50,
        ),
    )
    middleware = ToolResultCompressionMiddleware(config=config)
    
    original_human = HumanMessage(content="User query")
    original_ai = AIMessage(content="AI response")
    
    messages = [
        original_human,
        original_ai,
        ToolMessage(content="Tool result " + "A" * 100, tool_call_id="call_1"),
        ToolMessage(content="Tool result " + "B" * 100, tool_call_id="call_2"),
    ]
    
    result = middleware.compress_messages(messages)
    
    # Human and AI messages should be unchanged
    assert result[0].content == original_human.content
    assert result[1].content == original_ai.content
    
    # First tool message should be compressed
    assert "已截断" in result[2].content
    
    # Second tool message should be intact
    assert "已截断" not in result[3].content


def test_process_messages_before_invoke_disabled():
    """Test that processing is skipped when disabled"""
    config = ToolCompressionConfig(enabled=False)
    middleware = ToolResultCompressionMiddleware(config=config)
    
    messages = [
        ToolMessage(content="A" * 1000, tool_call_id="call_1"),
        ToolMessage(content="B" * 1000, tool_call_id="call_2"),
    ]
    
    result = middleware.process_messages_before_invoke(messages)
    assert result == messages  # No changes


def test_process_messages_before_invoke_enabled():
    """Test that processing works when enabled"""
    config = ToolCompressionConfig(
        enabled=True,
        trigger=[TriggerCondition(type="messages", value=3)],
        keep=KeepStrategy(
            recent_tool_messages=1,
            max_content_per_tool=50,
        ),
    )
    middleware = ToolResultCompressionMiddleware(config=config)
    
    messages = [
        HumanMessage(content="Query"),
        ToolMessage(content="Old result " + "A" * 100, tool_call_id="call_1"),
        ToolMessage(content="Recent result " + "B" * 100, tool_call_id="call_2"),
    ]
    
    result = middleware.process_messages_before_invoke(messages)
    
    # First tool message should be compressed
    assert "已截断" in result[1].content
    
    # Second tool message should be intact
    assert "已截断" not in result[2].content
