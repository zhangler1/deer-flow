#!/usr/bin/env python
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
异步爬虫使用示例
演示如何使用异步版本的 DeepResearchMdCrawler
"""

import asyncio
from src.crawler import DeepResearchMdCrawler


async def crawl_single_url():
    """单个URL异步爬取示例"""
    print("=== 单个URL异步爬取 ===")
    
    crawler = DeepResearchMdCrawler()
    url = "https://example.com"
    
    article = await crawler.crawl(url)
    print(f"标题: {article.title}")
    print(f"内容长度: {len(article.to_markdown())} 字符")


async def crawl_multiple_urls():
    """多个URL并发爬取示例"""
    print("\n=== 多个URL并发爬取 ===")
    
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3",
    ]
    
    crawler = DeepResearchMdCrawler()
    
    # 并发爬取多个URL
    tasks = [crawler.crawl(url) for url in urls]
    articles = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(articles):
        if isinstance(result, Exception):
            print(f"URL {i+1} 失败: {result}")
        else:
            from src.crawler import Article
            if isinstance(result, Article):
                print(f"URL {i+1} 成功: {result.title}")


async def main():
    """主函数"""
    # 单个URL爬取
    await crawl_single_url()
    
    # 多个URL并发爬取
    await crawl_multiple_urls()


if __name__ == "__main__":
    asyncio.run(main())
