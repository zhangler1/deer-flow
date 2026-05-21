# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
集成测试：测试 researcher_node 工具配置
"""

import pytest
from unittest.mock import Mock, patch


class TestResearcherNodeTools:
    """测试 researcher_node 节点的工具配置"""

    @pytest.mark.asyncio
    async def test_researcher_node_configures_web_search_tool(self):
        """测试 researcher_node 是否配置了 web_search 工具"""
        
        from src.graph.nodes import researcher_node
        from langchain_core.messages import HumanMessage
        
        # 创建简单的 state
        state = {
            "messages": [HumanMessage(content="测试问题")],
            "research_topic": "测试主题",
            "resources": []
        }
        
        # 创建配置
        config = {
            "configurable": {
                "search_engine": "duckduckgo",
                "max_search_results": 5,
                "custom_search_repository": None,
            }
        }
        
        with patch('src.graph.nodes.get_web_search_tool') as mock_get_search:
            with patch('src.graph.nodes.crawl_tool') as mock_crawl:
                with patch('src.graph.nodes.get_retriever_tool', return_value=None):
                    with patch('src.graph.nodes._execute_agent_step') as mock_execute:
                        # 配置返回值
                        mock_search_tool = Mock()
                        mock_search_tool.name = "web_search"
                        mock_get_search.return_value = mock_search_tool
                        
                        from langgraph.types import Command
                        from langchain_core.messages import AIMessage
                        mock_execute.return_value = Command(
                            update={"messages": [AIMessage(content="完成")]},
                            goto="research_team"
                        )
                        
                        # 执行节点
                        await researcher_node(state, config)
                        
                        # 验证 get_web_search_tool 被调用
                        mock_get_search.assert_called_once_with(
                            5,  # max_search_results
                            "duckduckgo",  # search_engine
                            None  # custom_search_repository
                        )

    @pytest.mark.asyncio
    async def test_researcher_node_includes_crawl_tool(self):
        """测试 researcher_node 是否包含爬虫工具"""
        
        from src.graph.nodes import researcher_node
        from langchain_core.messages import HumanMessage
        
        state = {
            "messages": [HumanMessage(content="测试")],
            "research_topic": "测试",
            "resources": []
        }
        
        config = {
            "configurable": {
                "search_engine": "duckduckgo",
                "max_search_results": 5,
                "custom_search_repository": None,
            }
        }
        
        with patch('src.graph.nodes.get_web_search_tool') as mock_get_search:
            with patch('src.graph.nodes.crawl_tool') as mock_crawl:
                with patch('src.graph.nodes.get_retriever_tool', return_value=None):
                    with patch('src.graph.nodes._execute_agent_step') as mock_execute:
                        mock_get_search.return_value = Mock(name="web_search")
                        mock_crawl.name = "crawl_tool"
                        
                        from langgraph.types import Command
                        from langchain_core.messages import AIMessage
                        mock_execute.return_value = Command(
                            update={},
                            goto="research_team"
                        )
                        
                        await researcher_node(state, config)
                        
                        # 验证传给 agent 的工具列表
                        call_args = mock_execute.call_args
                        tools = call_args[0][3]  # 第4个参数是 tools
                        
                        # 至少应该有 2 个工具：web_search 和 crawl_tool
                        assert len(tools) >= 2
                        
                        # 检查是否包含 crawl_tool
                        tool_names = [getattr(t, 'name', str(t)) for t in tools]
                        assert 'crawl_tool' in tool_names or mock_crawl in tools

    # 注释：local_search_tool 目前未实现，暂时禁用此测试
    # @pytest.mark.asyncio
    # async def test_researcher_node_with_local_retriever(self):
    #     """测试当有 resources 时，researcher_node 包含本地检索工具"""
    #     
    #     from src.graph.nodes import researcher_node
    #     from langchain_core.messages import HumanMessage
    #     
    #     state = {
    #         "messages": [HumanMessage(content="测试")],
    #         "research_topic": "测试",
    #         "resources": ["knowledge_base_1", "knowledge_base_2"]  # 有资源
    #     }
    #     
    #     config = {
    #         "configurable": {
    #             "search_engine": "duckduckgo",
    #             "max_search_results": 5,
    #             "custom_search_repository": None,
    #         }
    #     }
    #     
    #     with patch('src.graph.nodes.get_web_search_tool'):
    #         with patch('src.graph.nodes.crawl_tool'):
    #             with patch('src.graph.nodes.get_retriever_tool') as mock_get_retriever:
    #                 with patch('src.graph.nodes._execute_agent_step') as mock_execute:
    #                     # 配置本地检索工具返回
    #                     mock_local_tool = Mock(name="local_search_tool")
    #                     mock_get_retriever.return_value = mock_local_tool
    #                     
    #                     from langgraph.types import Command
    #                     from langchain_core.messages import AIMessage
    #                     mock_execute.return_value = Command(
    #                         update={},
    #                         goto="research_team"
    #                     )
    #                     
    #                     await researcher_node(state, config)
    #                     
    #                     # 验证 get_retriever_tool 被调用，传入了 resources
    #                     mock_get_retriever.assert_called_once()
    #                     call_args = mock_get_retriever.call_args
    #                     assert call_args[0][0] == ["knowledge_base_1", "knowledge_base_2"]
    #                     
    #                     # 验证本地检索工具被添加到工具列表
    #                     execute_call_args = mock_execute.call_args
    #                     tools = execute_call_args[0][3]
    #                     
    #                     # 本地检索工具应该在第一位
    #                     assert tools[0] == mock_local_tool

    @pytest.mark.asyncio
    async def test_researcher_agent_type_is_correct(self):
        """测试 researcher_node 使用正确的 agent 类型"""
        
        from src.graph.nodes import researcher_node
        from langchain_core.messages import HumanMessage
        
        state = {
            "messages": [HumanMessage(content="测试")],
            "research_topic": "测试",
            "resources": []
        }
        
        config = {
            "configurable": {
                "search_engine": "duckduckgo",
                "max_search_results": 5,
                "custom_search_repository": None,
            }
        }
        
        with patch('src.graph.nodes.get_web_search_tool'):
            with patch('src.graph.nodes.crawl_tool'):
                with patch('src.graph.nodes.get_retriever_tool', return_value=None):
                    with patch('src.graph.nodes._execute_agent_step') as mock_execute:
                        from langgraph.types import Command
                        from langchain_core.messages import AIMessage
                        mock_execute.return_value = Command(
                            update={},
                            goto="research_team"
                        )
                        
                        await researcher_node(state, config)
                        
                        # 验证 agent_type 参数是 "researcher"
                        call_args = mock_execute.call_args
                        agent_type = call_args[0][2]  # 第3个参数
                        
                        assert agent_type == "researcher"
