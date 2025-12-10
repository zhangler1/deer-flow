# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import pytest
from src.crawler import Crawler


def test_crawler_initialization():
    """Test that crawler can be properly initialized."""
    crawler = Crawler()
    assert isinstance(crawler, Crawler)


@pytest.mark.asyncio
async def test_crawler_crawl_valid_url():
    """Test crawling with a valid URL."""
    crawler = Crawler()
    test_url = "https://finance.sina.com.cn/stock/relnews/us/2024-08-15/doc-incitsya6536375.shtml"
    result = await crawler.crawl(test_url)
    assert result is not None
    assert hasattr(result, "to_markdown")


@pytest.mark.asyncio
async def test_crawler_markdown_output(capsys):
    """Test that crawler output can be converted to markdown."""
    crawler = Crawler()
    test_url = "https://finance.sina.com.cn/stock/relnews/us/2024-08-15/doc-incitsya6536375.shtml"
    result = await crawler.crawl(test_url)
    markdown = result.to_markdown()
    assert isinstance(markdown, str)
    with capsys.disabled():
        print("Markdown Output:")
        print(markdown)

    assert len(markdown) > 0
