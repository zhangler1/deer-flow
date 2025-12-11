"""
测试金融场景智能体工具

验证金融知识库API调用功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.tools.finance_scene_agent import (
    call_finance_scene_agent,
    finance_scene_search,
    finance_scene_search_custom,
    _build_request_body,
    _extract_knowledge,
)


@pytest.fixture
def mock_api_response():
    """模拟API响应"""
    return {
        "RSP_BODY": {
            "data": [
                {
                    "title": "信用卡申请条件",
                    "content": "申请信用卡需要满足以下条件：1. 年龄18-65周岁 2. 有稳定收入 3. 信用记录良好",
                    "score": 0.95
                },
                {
                    "title": "信用卡申请流程",
                    "content": "申请流程：1. 填写申请表 2. 提交身份证明 3. 等待审核 4. 激活卡片",
                    "score": 0.88
                }
            ]
        }
    }


def test_build_request_body():
    """测试构建请求体"""
    keyword = "信用卡申请"
    space_codes = ["SP0000010"]
    
    body = _build_request_body(keyword=keyword, space_codes=space_codes)
    
    # 验证结构
    assert "REQ_HEAD" in body
    assert "REQ_BODY" in body
    assert "param" in body["REQ_BODY"]
    
    # 验证参数
    param = body["REQ_BODY"]["param"]
    assert param["keyword"] == keyword
    assert param["spaceCodeList"] == space_codes
    assert param["vectorTopN"] == 6
    assert param["textTopN"] == 6


def test_extract_knowledge(mock_api_response):
    """测试提取知识内容"""
    result = _extract_knowledge(mock_api_response)
    
    # 验证提取的内容
    assert "信用卡申请条件" in result
    assert "信用卡申请流程" in result
    assert "年龄18-65周岁" in result
    assert "相关度" in result


@pytest.mark.asyncio
async def test_call_finance_scene_agent_success(mock_api_response):
    """测试成功调用金融场景智能体"""
    
    with patch('src.tools.finance_scene_agent.requests.post') as mock_post:
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_post.return_value = mock_response
        
        # 调用函数
        result = call_finance_scene_agent(
            keyword="信用卡申请",
            scene="banking"
        )
        
        # 验证调用
        mock_post.assert_called_once()
        
        # 验证结果
        assert "信用卡申请条件" in result
        assert "信用卡申请流程" in result


@pytest.mark.asyncio
async def test_call_finance_scene_agent_timeout():
    """测试超时处理"""
    
    with patch('src.tools.finance_scene_agent.requests.post') as mock_post:
        # 模拟超时
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()
        
        # 调用函数
        result = call_finance_scene_agent(
            keyword="信用卡申请",
            timeout=1
        )
        
        # 验证错误处理
        assert "错误" in result
        assert "超时" in result


@pytest.mark.asyncio
async def test_call_finance_scene_agent_request_error():
    """测试请求错误处理"""
    
    with patch('src.tools.finance_scene_agent.requests.post') as mock_post:
        # 模拟请求错误
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("连接失败")
        
        # 调用函数
        result = call_finance_scene_agent(
            keyword="信用卡申请"
        )
        
        # 验证错误处理
        assert "错误" in result
        assert "连接失败" in result or "请求失败" in result


def test_finance_scene_search_tool(mock_api_response):
    """测试 LangChain tool 封装"""
    
    with patch('src.tools.finance_scene_agent.requests.post') as mock_post:
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_post.return_value = mock_response
        
        # 调用工具
        result = finance_scene_search.invoke({
            "keyword": "信用卡申请",
            "scene": "banking"
        })
        
        # 验证结果
        assert isinstance(result, str)
        assert "信用卡" in result


def test_finance_scene_search_custom_tool(mock_api_response):
    """测试自定义场景工具"""
    
    with patch('src.tools.finance_scene_agent.requests.post') as mock_post:
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_post.return_value = mock_response
        
        # 调用工具
        result = finance_scene_search_custom.invoke({
            "keyword": "螺纹钢价格",
            "space_codes": "SP0000010,SP0000001"
        })
        
        # 验证结果
        assert isinstance(result, str)


def test_scene_mapping():
    """测试场景映射"""
    from src.tools.finance_scene_agent import FinanceSceneAgentConfig
    
    # 验证场景配置
    assert "default" in FinanceSceneAgentConfig.SCENES
    assert "banking" in FinanceSceneAgentConfig.SCENES
    assert "investment" in FinanceSceneAgentConfig.SCENES
    
    # 验证场景代码
    assert isinstance(FinanceSceneAgentConfig.SCENES["default"], list)
    assert len(FinanceSceneAgentConfig.SCENES["default"]) > 0


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
