# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import time
from typing import Annotated, Dict, List, Union, Optional

from langchain_core.tools import tool

from src.crawler import Crawler
from src.utils.enhanced_logger import console_print, get_enhanced_logger

from .decorators import log_io

# LangFuse 集成 - 直接导入，失败时降级
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

# Langfuse 集成 - 简洁降级
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

try:
    from langfuse.decorators import langfuse_context, observe
    from langfuse import get_client
except ImportError:
    LANGFUSE_ENABLED = False
    logging.warning("Langfuse not installed. Tracing disabled.")
    
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        # 支持 @observe 和 @observe(...) 两种用法
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return decorator
    
    class langfuse_context:
        @staticmethod
        def update_current_observation(**kwargs): pass
        @staticmethod
        def update_current_trace(**kwargs): pass
        @staticmethod
        def score_current_observation(**kwargs): pass
    
    class DummyClient:
        def auth_check(self): return False
        def flush(self): pass
    
    def get_client():
        return DummyClient()

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('tools.crawl')


class CrawlToolCache:
    """爬虫工具缓存管理器"""
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
    
    def get(self, url: str) -> Optional[Dict]:
        """获取缓存"""
        return self._cache.get(url)
    
    def set(self, url: str, data: Dict) -> None:
        """设置缓存"""
        self._cache[url] = data
    
    def clear(self) -> int:
        """清空缓存"""
        count = len(self._cache)
        self._cache.clear()
        return count
    
    def has(self, url: str) -> bool:
        """检查是否有缓存"""
        return url in self._cache


# 全局缓存实例
_global_cache = CrawlToolCache()


def _smart_truncate(content: str, max_length: int = 8000) -> tuple[str, bool]:
    """
    智能截断内容，保持Markdown结构完整
    
    Args:
        content: 原始Markdown内容
        max_length: 最大长度
        
    Returns:
        (截断后的内容, 是否被截断)
    """
    if len(content) <= max_length:
        return content, False
    
    # 截断到最大长度
    truncated = content[:max_length]
    
    # 尝试在段落边界截断（保挅80%以上）
    last_paragraph = truncated.rfind('\n\n')
    if last_paragraph > max_length * 0.8:
        truncated = truncated[:last_paragraph]
    
    # 添加截断标记
    truncated += f"\n\n---\n**[✂️ 内容过长，已智能截断]**\n\n"
    truncated += f"- 原始长度: {len(content):,} 字符\n"
    truncated += f"- 当前长度: {len(truncated):,} 字符\n"
    truncated += f"- 保留比例: {len(truncated)/len(content)*100:.1f}%"
    
    return truncated, True


@tool
@log_io
@observe(as_type="tool")
async def crawl_tool(
    url: Annotated[str, "The url to crawl."],
    use_cache: Annotated[bool, "Whether to use cache. Default True."] = True,
) -> Union[Dict, str]:
    """使用此工具爬取URL并获取Markdown格式的可读内容。
    
    功能特性：
    - 自动URL验证
    - 带重试机制的HTTP请求
    - 智能内容截断（保持Markdown结构）
    - 缓存机制（避免重复爬取）
    
    适用场景：
    - 分析特定网页内容
    - 提取文章主要信息
    - 为深度研究提供网页数据
    """
    start_time = time.time()
    
    # LangFuse: 记录输入 - 设置更直观的名称
    langfuse_context.update_current_observation(
        name=f"🔍 网页爬取 | {url[:50]}...",  # 显示URL
        input={
            "url": url,
            "use_cache": use_cache
        },
        metadata={
            "tool_name": "crawl_tool",
            "component": "crawler",
            "stage": "web_scraping"
        }
    )
    
    # 检查缓存
    if use_cache and _global_cache.has(url):
        cached_result = _global_cache.get(url)
        if cached_result:
            cached_result['cached'] = True
            cached_result['cache_hit_time'] = time.time() - start_time
            
            enhanced_logger.logger.info(
                f"💾 CACHE_HIT | 命中缓存 | URL: {url}"
            )
            console_print(
                f"\033[36m[💾 缓存命中]\033[0m \033[35m{url}\033[0m",
                level=logging.INFO
            )
            
            # LangFuse: 记录缓存命中
            langfuse_context.update_current_observation(
                output={
                    "status": "cache_hit",
                    "title": cached_result.get('title'),
                    "url": url,
                    "content_length": cached_result.get('full_length', 0)
                },
                metadata={
                    "cached": True,
                    "cache_hit_time": cached_result['cache_hit_time'],
                    "duration_seconds": cached_result['cache_hit_time']
                }
            )
            langfuse_context.score_current_observation(
                name="cache_efficiency",
                value=1.0,
                comment="Cache hit - instant response"
            )
            
            return cached_result
    
    enhanced_logger.logger.info(
        f"🔧 CRAWL_TOOL_START | 开始爬取工具 | URL: {url}"
    )
    console_print(
        f"\033[32m[🔍 网页爬取]\033[0m \033[35mURL: {url}\033[0m",
        level=logging.INFO
    )
    
    try:
        crawler = Crawler()
        article = await crawler.crawl(url)
        
        # 生成Markdown内容
        markdown_content = article.to_markdown()
        
        # 智能截断内容（保持结构完整）
        content_preview, is_truncated = _smart_truncate(markdown_content, max_length=8000)
        
        duration = time.time() - start_time
        
        enhanced_logger.logger.info(
            f"✅ CRAWL_TOOL_SUCCESS | 爬取完成 | "
            f"标题: {article.title} | 内容长度: {len(markdown_content)} | "
            f"截断: {is_truncated} | 耗时: {duration:.2f}s"
        )
        console_print(
            f"\033[32m[✅ 爬取完成]\033[0m \033[35m标题: {article.title} | "
            f"内容: {len(markdown_content)} 字符 | 耗时: {duration:.2f}s\033[0m",
            level=logging.INFO
        )
        
        # 提取内容预览（前100字符作为摘要）
        content_lines = markdown_content.split('\n')
        preview_text = ''
        for line in content_lines:
            if line.strip() and not line.strip().startswith('#'):
                preview_text += line.strip() + ' '
                if len(preview_text) > 100:
                    break
        preview_text = preview_text[:100].strip() + '...' if len(preview_text) > 100 else preview_text.strip()
        
        result = {
            "url": url,
            "title": article.title,
            "content": content_preview,
            "preview": preview_text,  # 添加预览文本
            "full_length": len(markdown_content),
            "truncated": is_truncated,
            "cached": False,
            "duration": duration
        }
        
        # 存入缓存
        if use_cache:
            _global_cache.set(url, result.copy())
            enhanced_logger.logger.debug(f"💾 CACHE_STORED | 已存入缓存 | URL: {url}")
        
        # LangFuse: 记录成功结果
        langfuse_context.update_current_observation(
            output={
                "status": "success",
                "title": article.title,
                "url": url,
                "content_length": len(markdown_content),
                "preview": preview_text,
                "truncated": is_truncated
            },
            metadata={
                "duration_seconds": duration,
                "full_length": len(markdown_content),
                "cached": False,
                "cache_stored": use_cache
            }
        )
        
        # 添加质量评分
        quality_score = 0.8 if is_truncated else 1.0
        if len(markdown_content) < 100:
            quality_score = 0.5  # 内容太少
        
        langfuse_context.score_current_observation(
            name="crawl_quality",
            value=quality_score,
            comment=f"Crawled {len(markdown_content)} chars" + (" (truncated)" if is_truncated else "")
        )
        
        return result
        
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
        
        # LangFuse: 记录错误
        langfuse_context.update_current_observation(
            output={
                "status": "error",
                "error": str(e),
                "url": url
            },
            metadata={
                "duration_seconds": duration,
                "error_type": type(e).__name__
            }
        )
        langfuse_context.score_current_observation(
            name="crawl_quality",
            value=0.0,
            comment=f"Crawl failed: {str(e)[:100]}"
        )
        
        logger.error(error_msg)
        return error_msg


@tool
@log_io
async def batch_crawl_tool(
    urls: Annotated[List[str], "List of URLs to crawl."],
    use_cache: Annotated[bool, "Whether to use cache. Default True."] = True,
) -> Union[List[Dict], str]:
    """批量爬取多个URL并获取Markdown内容。
    
    功能特性：
    - 批量处理多个URL
    - 单个URL失败不影响其他URL
    - 自动统计成功/失败数量
    - 支持缓存机制
    
    适用场景：
    - 批量分析多个网页
    - 收集多个来源的信息
    - 构建知识库
    """
    start_time = time.time()
    
    enhanced_logger.logger.info(
        f"📦 BATCH_CRAWL_START | 开始批量爬取 | 数量: {len(urls)}"
    )
    console_print(
        f"\033[32m[📦 批量爬取]\033[0m \033[35m共 {len(urls)} 个URL\033[0m",
        level=logging.INFO
    )
    
    results = []
    success_count = 0
    cache_hit_count = 0
    
    for i, url in enumerate(urls, 1):
        enhanced_logger.logger.info(
            f"📄 BATCH_PROGRESS | 进度: {i}/{len(urls)} | URL: {url}"
        )
        console_print(
            f"\033[33m  [{i}/{len(urls)}]\033[0m {url}",
            level=logging.INFO
        )
        
        try:
            # 调用单个crawl_tool
            result = await crawl_tool.ainvoke({"url": url, "use_cache": use_cache})
            
            if isinstance(result, dict):
                results.append(result)
                success_count += 1
                if result.get('cached', False):
                    cache_hit_count += 1
            else:
                # 错误消息
                results.append({
                    "url": url,
                    "error": str(result),
                    "success": False
                })
        except Exception as e:
            enhanced_logger.logger.error(
                f"❌ BATCH_ITEM_ERROR | URL处理失败: {url} | 错误: {str(e)}"
            )
            results.append({
                "url": url,
                "error": str(e),
                "success": False
            })
    
    duration = time.time() - start_time
    
    enhanced_logger.logger.info(
        f"✅ BATCH_CRAWL_COMPLETE | 批量爬取完成 | "
        f"成功: {success_count}/{len(urls)} | 缓存命中: {cache_hit_count} | 耗时: {duration:.2f}s"
    )
    console_print(
        f"\033[32m[✅ 批量完成]\033[0m \033[35m成功: {success_count}/{len(urls)} | "
        f"缓存: {cache_hit_count} | 耗时: {duration:.2f}s\033[0m",
        level=logging.INFO
    )
    
    return results


@tool
def clear_crawl_cache() -> str:
    """清空爬虫工具的缓存。
    
    适用场景：
    - 需要重新爬取最新内容
    - 释放内存空间
    """
    count = _global_cache.clear()
    
    enhanced_logger.logger.info(
        f"🗑️ CACHE_CLEARED | 已清空缓存 | 清除数量: {count}"
    )
    console_print(
        f"\033[32m[🗑️ 缓存清空]\033[0m \033[35m已清除 {count} 个缓存项\033[0m",
        level=logging.INFO
    )
    
    return f"已清空爬虫缓存，共清除 {count} 个缓存项"
