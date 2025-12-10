# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
from typing import Optional

from .article import Article
from .deep_research_md_crawler import DeepResearchMdCrawler
from .jina_client import JinaClient
from .readability_extractor import ReadabilityExtractor


class Crawler:
    def __init__(self, use_deep_research: Optional[bool] = None):
        """
        初始化爬虫
        
        Args:
            use_deep_research: 是否使用DeepResearchMdCrawler
                             如果为None，从环境变量CRAWLER_TYPE读取
                             默认使用DeepResearchMdCrawler
        """
        if use_deep_research is None:
            # 从环境变量读取，默认使用deep_research
            crawler_type = os.getenv('CRAWLER_TYPE', 'deep_research')
            use_deep_research = (crawler_type == 'deep_research')
        
        self.use_deep_research = use_deep_research
    
    async def crawl(self, url: str) -> Article:
        if self.use_deep_research:
            # 使用新的DeepResearchMdCrawler（内网部署）
            crawler = DeepResearchMdCrawler()
            return await crawler.crawl(url)
        else:
            # 使用原有的JinaClient方式（外网依赖）
            # To help LLMs better understand content, we extract clean
            # articles from HTML, convert them to markdown, and split
            # them into text and image blocks for one single and unified
            # LLM message.
            #
            # Jina is not the best crawler on readability, however it's
            # much easier and free to use.
            #
            # Instead of using Jina's own markdown converter, we'll use
            # our own solution to get better readability results.
            jina_client = JinaClient()
            html = jina_client.crawl(url, return_format="html")
            extractor = ReadabilityExtractor()
            article = extractor.extract_article(html)
            article.url = url
            return article
