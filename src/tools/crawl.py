# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import time
from typing import Annotated, Dict, Union

from langchain_core.tools import tool

from src.crawler import Crawler
from src.utils.enhanced_logger import console_print, get_enhanced_logger

from .decorators import log_io

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('tools.crawl')


@tool
@log_io
def crawl_tool(
    url: Annotated[str, "The url to crawl."],
) -> Union[Dict, str]:
    """使用此工具爬取URL并获取Markdown格式的可读内容。
    
    适用场景：
    - 分析特定网页内容
    - 提取文章主要信息
    - 为深度研究提供网页数据
    """
    start_time = time.time()
    
    enhanced_logger.logger.info(
        f"🔧 CRAWL_TOOL_START | 开始爬取工具 | URL: {url}"
    )
    console_print(
        f"\033[32m[🔍 网页爬取]\033[0m \033[35mURL: {url}\033[0m",
        level=logging.INFO
    )
    
    try:
        crawler = Crawler()
        article = crawler.crawl(url)
        
        # 生成Markdown内容
        markdown_content = article.to_markdown()
        
        # 截断内容以避免过长（保留前5000字符）
        content_preview = markdown_content[:5000]
        if len(markdown_content) > 5000:
            content_preview += "\n\n... (内容过长，已截断)"
        
        duration = time.time() - start_time
        
        enhanced_logger.logger.info(
            f"✅ CRAWL_TOOL_SUCCESS | 爬取完成 | "
            f"标题: {article.title} | 内容长度: {len(markdown_content)} | 耗时: {duration:.2f}s"
        )
        console_print(
            f"\033[32m[✅ 爬取完成]\033[0m \033[35m标题: {article.title} | "
            f"内容: {len(markdown_content)} 字符 | 耗时: {duration:.2f}s\033[0m",
            level=logging.INFO
        )
        
        return {
            "url": url,
            "title": article.title,
            "content": content_preview,
            "full_length": len(markdown_content)
        }
        
    except BaseException as e:
        duration = time.time() - start_time
        error_msg = f"Failed to crawl. Error: {repr(e)}"
        
        enhanced_logger.logger.error(
            f"❌ CRAWL_TOOL_ERROR | 爬取失败 | "
            f"URL: {url} | 错误: {str(e)} | 耗时: {duration:.2f}s"
        )
        console_print(
            f"\033[31m[❌ 爬取失败]\033[0m \033[35m{error_msg}\033[0m",
            level=logging.ERROR
        )
        
        logger.error(error_msg)
        return error_msg
