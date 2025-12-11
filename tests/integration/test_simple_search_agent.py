"""
测试 simple_search_node 的多轮工具调用功能

这个测试用例验证 simple_search_node 是否能像 search_agent.py 一样
进行多轮工具调用，使用 LangGraph 框架实现。
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage

from src.graph.nodes import simple_search_node
from src.graph.types import State
from src.config.configuration import Configuration


@pytest.fixture
def mock_state():
    """创建模拟的状态对象"""
    return {
        "research_topic": "信用卡如何申请？",
        "messages": [HumanMessage(content="信用卡如何申请？")],
        "locale": "zh-CN",
        "enable_smart_routing": True
    }


@pytest.fixture
def mock_config():
    """创建模拟的配置对象"""
    mock_runnable_config = Mock()
    return mock_runnable_config


@pytest.fixture
def mock_tools():
    """创建模拟的工具对象"""
    mock_web_search = Mock()
    mock_web_search.name = "web_search"
    mock_web_search.description = "搜索工具"
    
    mock_crawl = Mock()
    mock_crawl.name = "crawl_tool"
    mock_crawl.description = "网页爬取工具"
    
    mock_domain_search = Mock()
    mock_domain_search.name = "domain_fin_search"
    mock_domain_search.description = "金融领域知识库检索工具"
    
    return [mock_web_search, mock_crawl, mock_domain_search]


@pytest.mark.asyncio
async def test_simple_search_uses_agent_with_tools(mock_state, mock_config, mock_tools):
    """测试 simple_search_node 是否使用智能体和工具"""
    
    # 模拟 Configuration
    with patch('src.graph.nodes.Configuration.from_runnable_config') as mock_cfg:
        mock_configuration = Mock()
        mock_configuration.search_engine = "tavily"
        mock_configuration.custom_search_repository = None
        mock_cfg.return_value = mock_configuration
        
        # 模拟 get_web_search_tool
        with patch('src.graph.nodes.get_web_search_tool') as mock_get_search:
            mock_get_search.return_value = mock_tools[0]
            
            # 模拟 crawl_tool
            with patch('src.graph.nodes.crawl_tool', mock_tools[1]):
                
                # 模拟 domain_fin_search
                with patch('src.graph.nodes.domain_fin_search', mock_tools[2]):
                    
                    # 模拟 create_agent
                    with patch('src.graph.nodes.create_agent') as mock_create_agent:
                        # 创建一个模拟的智能体
                        mock_agent = AsyncMock()
                        mock_result = {
                            "messages": [
                                AIMessage(content="申请信用卡需要满足以下条件：\n1. 年龄18-65周岁\n2. 有稳定收入\n3. 信用记录良好")
                            ]
                        }
                        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
                        mock_create_agent.return_value = mock_agent
                        
                        # 调用 simple_search_node
                        result = await simple_search_node(mock_state, mock_config)
                        
                        # 验证 create_agent 被调用
                        mock_create_agent.assert_called_once()
                        call_args = mock_create_agent.call_args
                        
                        # 验证传入的参数
                        assert call_args.kwargs['agent_name'] == "simple_search_assistant"
                        assert call_args.kwargs['agent_type'] == "researcher"
                        assert call_args.kwargs['prompt_template'] == "simple_search"
                        
                        # 验证工具列表包含3个工具
                        tools_arg = call_args.kwargs['tools']
                        assert len(tools_arg) == 3
                        assert any(t.name == "web_search" for t in tools_arg)
                        assert any(t.name == "crawl_tool" for t in tools_arg)
                        assert any(t.name == "domain_fin_search" for t in tools_arg)
                        
                        # 验证 agent.ainvoke 被调用
                        mock_agent.ainvoke.assert_called_once()
                        invoke_args = mock_agent.ainvoke.call_args
                        
                        # 验证输入消息
                        assert "messages" in invoke_args.kwargs['input']
                        assert len(invoke_args.kwargs['input']['messages']) > 0
                        
                        # 验证递归限制
                        assert "recursion_limit" in invoke_args.kwargs['config']
                        assert invoke_args.kwargs['config']['recursion_limit'] == 5
                        
                        # 验证返回结果
                        assert result.update['final_report'] == mock_result['messages'][-1].content
                        assert result.goto == "__end__"


@pytest.mark.asyncio
async def test_simple_search_agent_invokes_multiple_times(mock_state, mock_config):
    """测试智能体可以进行多轮工具调用"""
    
    with patch('src.graph.nodes.Configuration.from_runnable_config') as mock_cfg:
        mock_configuration = Mock()
        mock_configuration.search_engine = "tavily"
        mock_configuration.custom_search_repository = None
        mock_cfg.return_value = mock_configuration
        
        with patch('src.graph.nodes.get_web_search_tool'):
            with patch('src.graph.nodes.crawl_tool'):
                with patch('src.graph.nodes.domain_fin_search'):
                    with patch('src.graph.nodes.create_agent') as mock_create_agent:
                        # 模拟智能体返回多条消息（包含工具调用）
                        mock_agent = AsyncMock()
                        mock_result = {
                            "messages": [
                                AIMessage(content="正在搜索...", tool_calls=[
                                    {"name": "domain_fin_search", "args": {"query": "信用卡申请"}}
                                ]),
                                AIMessage(content="正在获取详细信息...", tool_calls=[
                                    {"name": "web_search", "args": {"query": "信用卡申请条件"}}
                                ]),
                                AIMessage(content="申请信用卡需要满足以下条件...")
                            ]
                        }
                        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
                        mock_create_agent.return_value = mock_agent
                        
                        result = await simple_search_node(mock_state, mock_config)
                        
                        # 验证最终答案
                        assert result.update['final_report'] == mock_result['messages'][-1].content


@pytest.mark.asyncio
async def test_simple_search_handles_error(mock_state, mock_config):
    """测试错误处理"""
    
    with patch('src.graph.nodes.Configuration.from_runnable_config') as mock_cfg:
        mock_configuration = Mock()
        mock_configuration.search_engine = "tavily"
        mock_cfg.return_value = mock_configuration
        
        # 模拟工具抛出异常
        with patch('src.graph.nodes.get_web_search_tool', side_effect=Exception("搜索失败")):
            result = await simple_search_node(mock_state, mock_config)
            
            # 验证错误信息
            assert "抱歉，在处理您的问题时遇到了错误" in result.update['final_report']
            assert "搜索失败" in result.update['final_report']
            assert result.goto == "__end__"


@pytest.mark.asyncio
async def test_simple_search_tool_calls_count(mock_state, mock_config):
    """测试工具调用统计"""
    
    with patch('src.graph.nodes.Configuration.from_runnable_config') as mock_cfg:
        mock_configuration = Mock()
        mock_configuration.search_engine = "tavily"
        mock_configuration.custom_search_repository = None
        mock_cfg.return_value = mock_configuration
        
        with patch('src.graph.nodes.get_web_search_tool'):
            with patch('src.graph.nodes.crawl_tool'):
                with patch('src.graph.nodes.domain_fin_search'):
                    with patch('src.graph.nodes.create_agent') as mock_create_agent:
                        # 模拟多次工具调用
                        mock_agent = AsyncMock()
                        mock_result = {
                            "messages": [
                                AIMessage(content="第一次搜索", tool_calls=[
                                    {"name": "domain_fin_search", "args": {}}
                                ]),
                                AIMessage(content="第二次搜索", tool_calls=[
                                    {"name": "web_search", "args": {}}
                                ]),
                                AIMessage(content="第三次爬取", tool_calls=[
                                    {"name": "crawl_tool", "args": {}}
                                ]),
                                AIMessage(content="最终答案")
                            ]
                        }
                        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
                        mock_create_agent.return_value = mock_agent
                        
                        with patch('src.graph.nodes.enhanced_logger') as mock_logger:
                            result = await simple_search_node(mock_state, mock_config)
                            
                            # 验证日志记录了工具调用统计
                            # 查找包含 "TOOL_CALLS_SUMMARY" 的日志调用
                            log_calls = [
                                call for call in mock_logger.logger.info.call_args_list
                                if "TOOL_CALLS_SUMMARY" in str(call)
                            ]
                            assert len(log_calls) > 0


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
