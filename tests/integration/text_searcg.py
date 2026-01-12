# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
测试 online_search_tool 和 CustomSearchTool 的隔离性
确保 online_search 不会被其他配置覆盖
"""

import pytest
from unittest.mock import patch, MagicMock
from src.tools.online_search import online_search_tool
from src.tools.custom_search import CustomSearchTool, get_custom_search_tool


class TestOnlineSearchIsolation:
    """测试联网搜索工具的配置隔离"""
    
    @patch('src.tools.custom_search.get_custom_search_config')
    def test_online_search_uses_correct_repository(self, mock_config):
        """测试 online_search_tool 使用正确的 repository"""
        # Mock 配置
        mock_repo = MagicMock()
        mock_repo.name = "互联网检索"
        mock_repo.repository = "online-search"
        mock_repo.channel_id = "0"
        
        mock_config_instance = MagicMock()
        mock_config_instance.get_repository.return_value = mock_repo
        mock_config.return_value = mock_config_instance
        
        # 创建工具
        with patch.dict('os.environ', {'CUSTOM_SEARCH_API_URL': 'http://test.com'}):
            tool = online_search_tool(max_results=10)
        
        # 验证
        assert tool.name == "online_search", "工具名称应该是 'online_search'"
        assert "互联网" in tool.description, "工具描述应该包含'互联网'"
        assert tool.repository_id == "online-search", "repository_id 应该是 'online-search'"
        assert tool._repository_config is not None, "repository_config 不应该为 None"
        assert tool._repository_config.repository == "online-search", "实际使用的 repository 应该是 'online-search'"
    
    @patch('src.tools.custom_search.get_custom_search_config')
    def test_custom_search_uses_different_repository(self, mock_config):
        """测试 CustomSearchTool 使用不同的 repository"""
        # Mock 配置
        mock_repo = MagicMock()
        mock_repo.name = "聚合搜索"
        mock_repo.repository = "aggregation-search"
        mock_repo.channel_id = "0"
        
        mock_config_instance = MagicMock()
        mock_config_instance.get_repository.return_value = mock_repo
        mock_config.return_value = mock_config_instance
        
        # 创建工具（不指定 repository_id，使用默认值）
        with patch.dict('os.environ', {'CUSTOM_SEARCH_API_URL': 'http://test.com'}):
            tool = CustomSearchTool(max_results=10)
        
        # 验证
        assert tool.name == "web_search", "默认工具名称应该是 'web_search'"
        assert tool.repository_id == "dynamic_search", "默认 repository_id 应该是 'dynamic_search'"
    
    @patch('src.tools.custom_search.get_custom_search_config')
    def test_tools_are_independent(self, mock_config):
        """测试两个工具互不影响"""
        # Mock 配置 - 返回不同的 repository
        def get_repo_side_effect(repo_id):
            mock_repo = MagicMock()
            if repo_id == "online-search":
                mock_repo.name = "互联网检索"
                mock_repo.repository = "online-search"
            elif repo_id == "dynamic_search":
                mock_repo.name = "交行知道"
                mock_repo.repository = "okic-dynamicSearch"
            else:
                mock_repo.name = "聚合搜索"
                mock_repo.repository = "aggregation-search"
            mock_repo.channel_id = "0"
            return mock_repo
        
        mock_config_instance = MagicMock()
        mock_config_instance.get_repository.side_effect = get_repo_side_effect
        mock_config.return_value = mock_config_instance
        
        # 创建两个工具
        with patch.dict('os.environ', {'CUSTOM_SEARCH_API_URL': 'http://test.com'}):
            online_tool = online_search_tool(max_results=10)
            custom_tool = CustomSearchTool(max_results=10)
        
        # 验证它们使用不同的 repository
        assert online_tool.repository_id == "online-search"
        assert custom_tool.repository_id == "dynamic_search"
        assert online_tool._repository_config is not None
        assert custom_tool._repository_config is not None
        assert online_tool._repository_config.repository != custom_tool._repository_config.repository
        
        # 验证名称不同
        assert online_tool.name == "online_search"
        assert custom_tool.name == "web_search"
    
    @patch('src.tools.custom_search.get_custom_search_config')
    def test_online_search_not_overridden_by_default(self, mock_config):
        """测试 online_search 不会被默认配置覆盖"""
        # Mock 配置
        mock_online_repo = MagicMock()
        mock_online_repo.name = "互联网检索"
        mock_online_repo.repository = "online-search"
        mock_online_repo.channel_id = "0"
        
        mock_default_repo = MagicMock()
        mock_default_repo.name = "聚合搜索"
        mock_default_repo.repository = "aggregation-search"
        mock_default_repo.channel_id = "0"
        
        mock_config_instance = MagicMock()
        # 当查找 online-search 时返回正确的配置
        mock_config_instance.get_repository.return_value = mock_online_repo
        # 默认配置是 aggregation_search
        mock_config_instance.get_default_repository.return_value = mock_default_repo
        mock_config.return_value = mock_config_instance
        
        # 创建 online_search_tool
        with patch.dict('os.environ', {'CUSTOM_SEARCH_API_URL': 'http://test.com'}):
            tool = online_search_tool(max_results=10)
        
        # 关键验证：即使有默认配置，online_search 也应该使用自己的配置
        assert tool._repository_config is not None, "repository_config 不应该为 None"
        assert tool._repository_config.repository == "online-search", \
            "online_search 不应该被默认的 aggregation-search 覆盖"
        assert tool._repository_config.name == "互联网检索"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])