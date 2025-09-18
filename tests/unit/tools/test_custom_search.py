# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
from unittest.mock import Mock, patch

import pytest
import requests

from src.tools.custom_search import CustomSearchTool, get_custom_search_tool


class TestCustomSearchTool:
    @pytest.fixture
    def custom_search_tool(self):
        """创建测试用的自定义搜索工具实例"""
        with patch.dict(os.environ, {
            "CUSTOM_SEARCH_API_URL": "https://test-api.com/search",
            "CUSTOM_SEARCH_API_KEY": "test_key"
        }):
            return CustomSearchTool(max_results=5)

    def test_init_with_env_vars(self):
        """测试使用环境变量初始化"""
        with patch.dict(os.environ, {
            "CUSTOM_SEARCH_API_URL": "https://test-api.com/search",
            "CUSTOM_SEARCH_API_KEY": "test_key"
        }):
            tool = CustomSearchTool()
            assert tool.api_url == "https://test-api.com/search"
            assert tool.api_key == "test_key"

    def test_init_without_url_raises_error(self):
        """测试没有 URL 时抛出错误"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="CUSTOM_SEARCH_API_URL environment variable is required"):
                CustomSearchTool()

    @patch('src.tools.custom_search.requests.post')
    def test_call_search_api_success(self, mock_post, custom_search_tool):
        """测试成功调用搜索 API"""
        # 模拟 API 响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "测试标题",
                    "url": "https://example.com",
                    "snippet": "测试内容"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # 执行搜索
        results = custom_search_tool._call_search_api("测试查询")

        # 验证结果
        assert len(results) == 1
        assert results[0]["title"] == "测试标题"
        assert results[0]["url"] == "https://example.com"
        assert results[0]["content"] == "测试内容"

        # 验证 API 调用
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["query"] == "测试查询"

    @patch('src.tools.custom_search.requests.post')
    def test_call_search_api_failure(self, mock_post, custom_search_tool):
        """测试 API 调用失败"""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        results = custom_search_tool._call_search_api("测试查询")

        assert results == []

    def test_parse_response(self, custom_search_tool):
        """测试响应解析"""
        data = {
            "results": [
                {
                    "title": "标题1",
                    "url": "https://example1.com",
                    "snippet": "内容1",
                    "score": 0.9
                },
                {
                    "title": "标题2",
                    "url": "https://example2.com",
                    "content": "内容2"
                }
            ]
        }

        results = custom_search_tool._parse_response(data)

        assert len(results) == 2
        assert results[0]["title"] == "标题1"
        assert results[0]["score"] == 0.9
        assert results[1]["content"] == "内容2"

    def test_run_method(self, custom_search_tool):
        """测试 _run 方法"""
        with patch.object(custom_search_tool, '_call_search_api') as mock_call:
            mock_call.return_value = [{"title": "测试", "url": "test.com", "content": "内容"}]

            results = custom_search_tool._run("测试查询")

            assert len(results) == 1
            mock_call.assert_called_once_with("测试查询")

    def test_get_custom_search_tool_factory(self):
        """测试工厂函数"""
        with patch.dict(os.environ, {
            "CUSTOM_SEARCH_API_URL": "https://test-api.com/search"
        }):
            tool = get_custom_search_tool(max_results=15)
            assert isinstance(tool, CustomSearchTool)
            assert tool.max_results == 15