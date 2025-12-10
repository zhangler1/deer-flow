# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
DeepResearchMdCrawler单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.crawler.deep_research_md_crawler import DeepResearchMdCrawler
from src.crawler.article import Article


class TestDeepResearchMdCrawler:
    """DeepResearchMdCrawler测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.test_url = "https://example.com/article"
        self.test_html = """
        <html>
            <head><title>Test Article</title></head>
            <body>
                <h1>Test Heading</h1>
                <p>This is test content.</p>
            </body>
        </html>
        """
        self.test_extracted_html = """
        <html>
            <body _item_id="1">
                <h1>Test Heading</h1>
                <p>This is test content.</p>
            </body>
        </html>
        """
    
    @patch('src.crawler.deep_research_md_crawler.requests.get')
    @patch('src.crawler.deep_research_md_crawler.requests.post')
    def test_crawl_success(self, mock_post, mock_get):
        """测试成功爬取网页"""
        # Mock HTTP GET请求（抓取HTML）
        mock_response_get = Mock()
        mock_response_get.text = self.test_html
        mock_response_get.status_code = 200
        mock_response_get.raise_for_status = Mock()
        mock_get.return_value = mock_response_get
        
        # Mock HTTP POST请求（提取并转换为MD）
        mock_response_post = Mock()
        mock_response_post.json.return_value = {
            'title': 'Test Heading',
            'markdown': '## Test Heading\n\nThis is test content.',
            'html': self.test_extracted_html
        }
        mock_response_post.status_code = 200
        mock_response_post.raise_for_status = Mock()
        mock_post.return_value = mock_response_post
        
        # 执行测试
        crawler = DeepResearchMdCrawler(
            extract_api_url='http://localhost:7986/extract_md'
        )
        article = crawler.crawl(self.test_url)
        
        # 验证结果
        assert isinstance(article, Article)
        assert article.url == self.test_url
        assert article.title == "Test Heading"
        # 验证Markdown内容直接来自接口，而非本地转换
        markdown = article.to_markdown(including_title=False)
        assert "Test Heading" in markdown
        assert "This is test content" in markdown
        
        # 验证调用
        mock_get.assert_called_once()
        mock_post.assert_called_once()
    
    @patch('src.crawler.deep_research_md_crawler.requests.get')
    def test_fetch_html_failure(self, mock_get):
        """测试HTML抓取失败"""
        # Mock HTTP错误
        mock_get.side_effect = requests.RequestException("Network error")
        
        # 执行测试
        crawler = DeepResearchMdCrawler()
        
        # 验证抛出异常
        with pytest.raises(Exception) as exc_info:
            crawler.crawl(self.test_url)
        
        assert "Failed to fetch HTML" in str(exc_info.value)
    
    @patch('src.crawler.deep_research_md_crawler.requests.get')
    @patch('src.crawler.deep_research_md_crawler.requests.post')
    def test_extract_api_failure(self, mock_post, mock_get):
        """测试内容提取API失败"""
        # Mock成功的HTML抓取
        mock_response_get = Mock()
        mock_response_get.text = self.test_html
        mock_response_get.raise_for_status = Mock()
        mock_get.return_value = mock_response_get
        
        # Mock提取API失败
        mock_post.side_effect = requests.RequestException("API error")
        
        # 执行测试
        crawler = DeepResearchMdCrawler()
        
        # 验证抛出异常
        with pytest.raises(Exception) as exc_info:
            crawler.crawl(self.test_url)
        
        assert "Failed to extract and convert" in str(exc_info.value)
    
    @patch('src.crawler.deep_research_md_crawler.requests.get')
    @patch('src.crawler.deep_research_md_crawler.requests.post')
    def test_title_extraction(self, mock_post, mock_get):
        """测试标题提取功能"""
        # 测试不同的标题场景
        test_cases = [
            # (HTML, 期望的标题, 返回Markdown)
            ("<html><head><title>Title from tag</title></head><body>Content</body></html>", 
             "Title from API",
             "# Title from API\n\nContent"),
            ("<html><body><h1>Title from h1</h1><p>Content</p></body></html>", 
             "H1 Title",
             "# H1 Title\n\nContent"),
        ]
        
        for html, expected_title, expected_md in test_cases:
            # Mock HTML抓取
            mock_response_get = Mock()
            mock_response_get.text = html
            mock_response_get.raise_for_status = Mock()
            mock_get.return_value = mock_response_get
            
            # Mock内容提取，返回标题和Markdown
            mock_response_post = Mock()
            mock_response_post.json.return_value = {
                'title': expected_title,
                'markdown': expected_md,
                'html': html
            }
            mock_response_post.raise_for_status = Mock()
            mock_post.return_value = mock_response_post
            
            # 执行测试
            crawler = DeepResearchMdCrawler()
            article = crawler.crawl(self.test_url)
            
            # 验证标题直接来自接口
            assert article.title == expected_title
    
    def test_crawler_initialization(self):
        """测试爬虫初始化"""
        # 测试默认初始化
        crawler1 = DeepResearchMdCrawler()
        assert crawler1.extract_api_url == 'http://localhost:7986/extract_md'
        assert crawler1.timeout == 30
        
        # 测试自定义初始化
        crawler2 = DeepResearchMdCrawler(
            extract_api_url='http://custom:8080/api/extract_md',
            timeout=60
        )
        assert crawler2.extract_api_url == 'http://custom:8080/api/extract_md'
        assert crawler2.timeout == 60
    
    @patch('src.crawler.deep_research_md_crawler.requests.get')
    @patch('src.crawler.deep_research_md_crawler.requests.post')
    def test_logging_coverage(self, mock_post, mock_get):
        """测试日志记录覆盖"""
        # Mock成功响应
        mock_response_get = Mock()
        mock_response_get.text = self.test_html
        mock_response_get.raise_for_status = Mock()
        mock_get.return_value = mock_response_get
        
        mock_response_post = Mock()
        mock_response_post.json.return_value = {
            'title': 'Test',
            'markdown': '# Test\n\nContent',
            'html': self.test_extracted_html
        }
        mock_response_post.raise_for_status = Mock()
        mock_post.return_value = mock_response_post
        
        # 执行测试（验证不抛出异常）
        crawler = DeepResearchMdCrawler()
        article = crawler.crawl(self.test_url)
        
        # 验证基本功能正常
        assert article is not None
        assert article.url == self.test_url
