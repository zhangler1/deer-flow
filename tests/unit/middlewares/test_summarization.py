# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""Unit tests for summarization middleware configuration"""

import pytest
from src.config.summarization_config import (
    SummarizationConfig,
    ContextSize,
    get_summarization_config,
    set_summarization_config,
    load_summarization_config_from_dict,
)


def test_context_size_to_tuple():
    """Test ContextSize conversion to tuple"""
    cs = ContextSize(type="messages", value=10)
    assert cs.to_tuple() == ("messages", 10)
    
    cs_tokens = ContextSize(type="tokens", value=4000)
    assert cs_tokens.to_tuple() == ("tokens", 4000)
    
    cs_fraction = ContextSize(type="fraction", value=0.8)
    assert cs_fraction.to_tuple() == ("fraction", 0.8)


def test_summarization_config_defaults():
    """Test default values of SummarizationConfig"""
    config = SummarizationConfig()
    
    assert config.enabled == False
    assert config.model_name is None
    assert config.trigger is None
    assert config.keep.type == "messages"
    assert config.keep.value == 10
    assert config.trim_tokens_to_summarize == 4000
    assert config.summary_prompt is None


def test_summarization_config_custom():
    """Test custom SummarizationConfig"""
    config = SummarizationConfig(
        enabled=True,
        model_name="gpt-4",
        trigger=ContextSize(type="tokens", value=15564),
        keep=ContextSize(type="messages", value=20),
        trim_tokens_to_summarize=10000,
    )
    
    assert config.enabled == True
    assert config.model_name == "gpt-4"
    assert config.trigger.type == "tokens"
    assert config.trigger.value == 15564
    assert config.keep.type == "messages"
    assert config.keep.value == 20
    assert config.trim_tokens_to_summarize == 10000


def test_load_from_dict():
    """Test loading configuration from dictionary"""
    config_dict = {
        "enabled": True,
        "model_name": None,
        "trigger": [
            {"type": "tokens", "value": 15564},
            {"type": "messages", "value": 50},
        ],
        "keep": {"type": "messages", "value": 10},
        "trim_tokens_to_summarize": 15564,
        "summary_prompt": None,
    }
    
    load_summarization_config_from_dict(config_dict)
    config = get_summarization_config()
    
    assert config.enabled == True
    assert config.model_name is None
    assert isinstance(config.trigger, list)
    assert len(config.trigger) == 2
    assert config.trigger[0].type == "tokens"
    assert config.trigger[0].value == 15564
    assert config.trigger[1].type == "messages"
    assert config.trigger[1].value == 50
    assert config.keep.type == "messages"
    assert config.keep.value == 10


def test_get_set_summarization_config():
    """Test get and set summarization config"""
    custom_config = SummarizationConfig(
        enabled=True,
        model_name="test-model",
        keep=ContextSize(type="messages", value=15),
    )
    
    set_summarization_config(custom_config)
    retrieved_config = get_summarization_config()
    
    assert retrieved_config.enabled == True
    assert retrieved_config.model_name == "test-model"
    assert retrieved_config.keep.value == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
