# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
测试 researcher 智能体是否能正确调用工具
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool

from src.agents.agents import create_agent
from src.graph.types import State


class TestResearcherAgent:
    """测试 researcher 智能体的工具调用能力"""

    @pytest.fixture
    def mock_web_search_tool(self):
        """模拟 web_search 工具"""
        @tool
        def mock_web_search(query: str) -> str:
            """模拟的网络搜索工具"""
            return f"搜索结果: {query}"
        
        mock_web_search.name = "web_search"
        mock_web_search.description = "用于执行网络搜索"
        return mock_web_search

    @pytest.fixture
    def mock_crawl_tool(self):
        """模拟 crawl_tool 工具"""
        @tool
        def mock_crawl(url: str) -> str:
            """模拟的网页爬取工具"""
            return f"爬取内容: {url}"
        
        mock_crawl.name = "crawl_tool"
        mock_crawl.description = "用于爬取网页内容"
        return mock_crawl

    # 注释：local_search_tool 目前未实现，暂时禁用
    # @pytest.fixture
    # def mock_local_search_tool(self):
    #     """模拟 local_search_tool 工具"""
    #     @tool
    #     def mock_local_search(query: str) -> str:
    #         """模拟的本地知识库搜索工具"""
    #         return f"本地搜索结果: {query}"
    #     
    #     mock_local_search.name = "local_search_tool"
    #     mock_local_search.description = "用于从本地知识库检索信息"
    #     return mock_local_search

    @pytest.fixture
    def researcher_prompt_template(self):
        """研究员提示词模板"""
        return """你是一个研究员智能体。
可用工具: web_search, crawl_tool
请使用工具来回答用户的问题。"""

    def test_researcher_agent_receives_tools(
        self, 
        mock_web_search_tool, 
        mock_crawl_tool,
        researcher_prompt_template
    ):
        """测试 researcher 智能体能否接收到工具"""
        tools = [mock_web_search_tool, mock_crawl_tool]
        
        # 模拟 LLM
        with patch('src.agents.agents.get_llm_by_type') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.model_name = "test-model"
            mock_get_llm.return_value = mock_llm
            
            # 模拟 create_react_agent
            with patch('src.agents.agents.create_react_agent') as mock_create_react:
                mock_agent = Mock()
                mock_create_react.return_value = mock_agent
                
                # 创建 agent
                agent = create_agent(
                    agent_name="researcher",
                    agent_type="researcher",
                    tools=tools,
                    prompt_template=researcher_prompt_template
                )
                
                # 验证 create_react_agent 被调用，并且传入了工具
                mock_create_react.assert_called_once()
                call_args = mock_create_react.call_args
                
                # 检查传入的工具参数
                assert 'tools' in call_args.kwargs
                assert len(call_args.kwargs['tools']) == 2
                assert call_args.kwargs['tools'][0].name == "web_search"
                assert call_args.kwargs['tools'][1].name == "crawl_tool"



    def test_researcher_agent_without_tools_warning(self, researcher_prompt_template):
        """测试 researcher 智能体在没有工具时是否会发出警告"""
        tools = []  # 空工具列表
        
        with patch('src.agents.agents.get_llm_by_type') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.model_name = "test-model"
            mock_get_llm.return_value = mock_llm
            
            with patch('src.agents.agents.create_react_agent') as mock_create_react:
                mock_agent = Mock()
                mock_create_react.return_value = mock_agent
                
                # 捕获日志警告
                with patch('src.agents.agents.logger') as mock_logger:
                    agent = create_agent(
                        agent_name="researcher",
                        agent_type="researcher",
                        tools=tools,
                        prompt_template=researcher_prompt_template
                    )
                    
                    # 验证警告日志被调用
                    assert any(
                        'NO_TOOLS' in str(call) or 'no tools' in str(call).lower()
                        for call in mock_logger.warning.call_args_list
                    )

    def test_researcher_agent_tool_invocation(
        self,
        mock_web_search_tool,
        mock_crawl_tool
    ):
        """测试 researcher 智能体实际调用工具的场景（同步测试）"""
        tools = [mock_web_search_tool, mock_crawl_tool]
        
        # 创建一个模拟的智能体响应
        mock_response = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "web_search",
                            "args": {"query": "Python测试框架"},
                            "id": "call_1"
                        }
                    ]
                )
            ]
        }
        
        with patch('src.agents.agents.get_llm_by_type') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.model_name = "test-model"
            mock_get_llm.return_value = mock_llm
            
            with patch('src.agents.agents.create_react_agent') as mock_create_react:
                # 创建一个可调用的 mock agent
                mock_agent = Mock()
                mock_agent.invoke = Mock(return_value=mock_response)
                mock_create_react.return_value = mock_agent
                
                # 创建 agent
                agent = create_agent(
                    agent_name="researcher",
                    agent_type="researcher",
                    tools=tools,
                    prompt_template="你是一个研究员"
                )
                
                # 调用 agent
                result = agent.invoke({
                    "messages": [HumanMessage(content="搜索Python测试框架")]
                })
                
                # 验证返回结果包含工具调用
                assert "messages" in result
                assert len(result["messages"]) > 0
                assert hasattr(result["messages"][0], "tool_calls")

    def test_researcher_agent_tool_count_logging(
        self,
        mock_web_search_tool,
        mock_crawl_tool,
        researcher_prompt_template
    ):
        """测试 researcher 智能体创建时的工具数量日志"""
        tools = [mock_web_search_tool, mock_crawl_tool]
        
        with patch('src.agents.agents.get_llm_by_type') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.model_name = "test-model"
            mock_get_llm.return_value = mock_llm
            
            with patch('src.agents.agents.create_react_agent') as mock_create_react:
                mock_agent = Mock()
                mock_create_react.return_value = mock_agent
                
                # 捕获日志
                with patch('src.agents.agents.logger') as mock_logger:
                    agent = create_agent(
                        agent_name="researcher",
                        agent_type="researcher",
                        tools=tools,
                        prompt_template=researcher_prompt_template
                    )
                    
                    # 验证工具数量日志
                    log_calls = [str(call) for call in mock_logger.info.call_args_list]
                    assert any('TOOLS_COUNT' in call and '2' in call for call in log_calls)
                    assert any('web_search' in call for call in log_calls)
                    assert any('crawl_tool' in call for call in log_calls)
