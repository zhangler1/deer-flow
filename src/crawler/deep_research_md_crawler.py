# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
深度研究Markdown爬虫 - 集成网页抓取、内容提取、MD转换三大功能
用于为LLM智能体提供高质量的网页内容
"""

import logging
import os
import time
from typing import Optional

import requests
from markdownify import markdownify as md

from src.utils.enhanced_logger import console_print, get_enhanced_logger
from .article import Article

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('crawler.deep_research')


class DeepResearchMdCrawler:
    """
    深度研究Markdown爬虫
    
    功能：
    1. 网页抓取 (HTML Fetching) - 获取原始HTML内容
    2. 内容提取 (Extraction) - 提取主要内容，去除广告/导航等噪声
    3. HTML→MD转换 (Conversion) - 转换为Markdown格式
    
    适用场景：为深度研究智能体提供高质量的网页内容分析
    """
    
    def __init__(
        self,
        extract_api_url: Optional[str] = None,
        timeout: int = 30
    ):
        """
        初始化深度研究爬虫
        
        Args:
            extract_api_url: 内容提取API地址，默认从环境变量读取
            timeout: 请求超时时间（秒）
        """
        self.extract_api_url = extract_api_url or os.getenv(
            'HTML_EXTRACT_API_URL',
            'http://localhost:7986/extract_md'
        )
        self.timeout = timeout
        
        enhanced_logger.logger.info(
            f"🔧 CRAWLER_INIT | DeepResearchMdCrawler初始化 | "
            f"提取API: {self.extract_api_url} | 超时: {timeout}s"
        )
        
    def crawl(self, url: str) -> Article:
        """
        爬取网页并转换为Article对象
        
        工作流程：
        1. 抓取网页HTML
        2. 调用提取API一次性完成：内容清洗 + MD转换
        3. 返回Article对象
        
        Args:
            url: 目标网页URL
            
        Returns:
            Article: 包含标题和Markdown内容的文章对象
            
        Raises:
            Exception: 当爬取失败时抛出异常
        """
        start_time = time.time()
        
        enhanced_logger.logger.info(
            f"🌐 CRAWL_START | 开始爬取网页 | URL: {url}"
        )
        console_print(
            f"\033[32m[🌐 开始爬取]\033[0m \033[35mURL: {url}\033[0m",
            level=logging.INFO
        )
        
        try:
            # Step 1: 抓取HTML
            html_content = self._fetch_html(url)
            
            # Step 2+3: 调用提取API一次性完成内容提取和MD转换
            result = self._extract_and_convert(url, html_content)
            
            # 创建Article对象
            article = Article(
                title=result['title'],
                html_content=result.get('html', ''),  # 可选：保留HTML用于其他用途
                markdown_content=result['markdown']  # 直接传入Markdown，避免重复转换
            )
            article.url = url
            
            duration = time.time() - start_time
            enhanced_logger.logger.info(
                f"✅ CRAWL_SUCCESS | 爬取完成 | URL: {url} | "
                f"标题: {article.title} | MD大小: {len(result['markdown'])} | 耗时: {duration:.2f}s"
            )
            console_print(
                f"\033[32m[✅ 爬取完成]\033[0m \033[35m标题: {article.title} | "
                f"耗时: {duration:.2f}s\033[0m",
                level=logging.INFO
            )
            
            return article
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"爬取失败: {str(e)}"
            enhanced_logger.logger.error(
                f"❌ CRAWL_ERROR | {error_msg} | URL: {url} | 耗时: {duration:.2f}s"
            )
            console_print(
                f"\033[31m[❌ 爬取失败]\033[0m \033[35m{error_msg}\033[0m",
                level=logging.ERROR
            )
            raise
    
    def _fetch_html(self, url: str) -> str:
        """
        步骤1: 抓取网页HTML内容
        
        Args:
            url: 目标网页URL
            
        Returns:
            str: HTML内容
        """
        start_time = time.time()
        
        enhanced_logger.logger.info(
            f"📥 FETCH_HTML_START | 开始抓取HTML | URL: {url}"
        )
        console_print(
            f"\033[32m  [1/3] 抓取HTML...\033[0m",
            level=logging.DEBUG
        )
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            html_content = response.text
            duration = time.time() - start_time
            
            enhanced_logger.logger.info(
                f"✅ FETCH_HTML_SUCCESS | HTML抓取成功 | "
                f"大小: {len(html_content)} 字符 | 耗时: {duration:.2f}s"
            )
            console_print(
                f"\033[35m      ✓ HTML大小: {len(html_content)} 字符\033[0m",
                level=logging.DEBUG
            )
            
            return html_content
            
        except Exception as e:
            duration = time.time() - start_time
            enhanced_logger.logger.error(
                f"❌ FETCH_HTML_ERROR | HTML抓取失败 | 错误: {str(e)} | 耗时: {duration:.2f}s"
            )
            raise Exception(f"Failed to fetch HTML: {str(e)}")
    
    def _extract_and_convert(self, url: str, html_content: str) -> dict:
        """
        步骤2+3: 调用提取API一次性完成内容提取和MD转换
        
        Args:
            url: 原始URL
            html_content: 原始HTML内容
            
        Returns:
            dict: 包含 title, markdown, html 的字典
        """
        start_time = time.time()
        
        enhanced_logger.logger.info(
            f"🔍 EXTRACT_AND_CONVERT_START | 开始提取并转换 | API: {self.extract_api_url}"
        )
        console_print(
            f"\033[32m  [2/2] 提取内容并转换为Markdown...\033[0m",
            level=logging.DEBUG
        )
        
        try:
            payload = {
                "html": html_content,
                "url": url
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # 记录API调用参数
            enhanced_logger.logger.debug(
                f"🔍 EXTRACT_API_CALL | 输入 | "
                f"HTML大小: {len(html_content)} | URL: {url}"
            )
            
            # 调用 /extract_md 接口（如果配置的是/extract，自动替换）
            api_url = self.extract_api_url
            if '/extract' in api_url and '/extract_md' not in api_url:
                api_url = api_url.replace('/extract', '/extract_md')
            
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 解析返回结果
            markdown = result.get('markdown', '')
            title = result.get('title', '未命名文档')
            html = result.get('html', result.get('main_html', ''))
            
            duration = time.time() - start_time
            
            enhanced_logger.logger.info(
                f"✅ EXTRACT_AND_CONVERT_SUCCESS | 提取并转换成功 | "
                f"标题: {title} | MD大小: {len(markdown)} | 耗时: {duration:.2f}s"
            )
            console_print(
                f"\033[35m      ✓ Markdown大小: {len(markdown)} 字符\033[0m",
                level=logging.DEBUG
            )
            
            return {
                'title': title,
                'markdown': markdown,
                'html': html
            }
            
        except Exception as e:
            duration = time.time() - start_time
            enhanced_logger.logger.error(
                f"❌ EXTRACT_AND_CONVERT_ERROR | 提取转换失败 | 错误: {str(e)} | 耗时: {duration:.2f}s"
            )
            raise Exception(f"Failed to extract and convert: {str(e)}")
    

