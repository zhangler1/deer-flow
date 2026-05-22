# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import functools
import logging
import time
from typing import Any, Callable, Type, TypeVar

from src.utils.enhanced_logger import get_enhanced_logger, console_print

logger = get_enhanced_logger(__name__).logger

T = TypeVar("T")


def log_io(func: Callable) -> Callable:
    """
    A decorator that logs the input parameters and output of a tool function.

    Args:
        func: The tool function to be decorated

    Returns:
        The wrapped function with input/output logging
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Log input parameters
        func_name = func.__name__
        params = ", ".join(
            [*(str(arg) for arg in args), *(f"{k}={v}" for k, v in kwargs.items())]
        )
        logger.info(f"Tool {func_name} called with parameters: {params}")

        # Execute the function
        result = func(*args, **kwargs)

        # Log the output
        logger.info(f"Tool {func_name} returned: {result}")

        return result

    return wrapper


class LoggedToolMixin:
    """A mixin class that adds logging functionality to any tool."""

    def _log_operation(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        """Helper method to log tool operations."""
        tool_name = self.__class__.__name__.replace("Logged", "")
        params = ", ".join(
            [*(str(arg)[:100] for arg in args), *(f"{k}={str(v)[:50]}" for k, v in kwargs.items())]
        )
        logger.debug(f"Tool {tool_name}.{method_name} called with parameters: {params}")

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Override _run method to add logging."""
        tool_name = self.__class__.__name__.replace("Logged", "")
        start_time = time.time()
        
        # 记录工具调用开始
        query = args[0] if args else kwargs.get('query', '')
        logger.info(f"🔍 TOOL_CALL_START | {tool_name} | 开始检索")
        console_print(
            f"\033[32m[开始检索] 工具: {tool_name}\033[0m \033[35m| 查询: '{str(query)[:50]}...'\033[0m",
            level=logging.INFO
        )
        
        self._log_operation("_run", *args, **kwargs)
        
        try:
            result = super()._run(*args, **kwargs)
            duration = time.time() - start_time
            
            # 解析结果数量
            result_count = 0
            if isinstance(result, list):
                result_count = len(result)
            elif isinstance(result, str):
                # 对于返回字符串的工具，尝试估算内容长度
                result_count = len(result) if result else 0
            
            # 记录工具调用结果
            logger.info(
                f"✅ TOOL_CALL_END | {tool_name} | 检索完成 | "
                f"耗时: {duration:.2f}s | 结果数: {result_count}"
            )
            
            # 打印检索结果摘要
            if isinstance(result, list) and result:
                console_print(
                    f"\033[32m[检索完成] 工具: {tool_name}\033[0m "
                    f"\033[35m| 返回 {result_count} 条结果 | 耗时: {duration:.2f}s\033[0m",
                    level=logging.INFO
                )
                
                # DEBUG级别打印详细结果
                for i, item in enumerate(result[:3]):  # 只打印前3条
                    if isinstance(item, dict):
                        title = item.get('title', item.get('url', '未知'))
                        content = item.get('content', '')
                        content_preview = content[:60] if content else '无内容'
                        console_print(
                            f"\033[32m  [{i+1}] {title}\033[0m",
                            level=logging.DEBUG
                        )
                        console_print(
                            f"\033[35m      {content_preview}...\033[0m",
                            level=logging.DEBUG
                        )
            elif isinstance(result, str) and result:
                result_preview = result[:100] if len(result) > 100 else result
                console_print(
                    f"\033[32m[检索完成] 工具: {tool_name}\033[0m "
                    f"\033[35m| 返回文本长度: {len(result)} | 耗时: {duration:.2f}s\033[0m",
                    level=logging.INFO
                )
                console_print(
                    f"\033[35m  内容预览: {result_preview}...\033[0m",
                    level=logging.DEBUG
                )
            else:
                console_print(
                    f"\033[32m[检索完成] 工具: {tool_name}\033[0m "
                    f"\033[35m| 无结果返回 | 耗时: {duration:.2f}s\033[0m",
                    level=logging.INFO
                )
            
            logger.debug(
                f"Tool {tool_name} returned: {str(result)[:200]}..."
            )
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"❌ TOOL_CALL_ERROR | {tool_name} | 检索失败 | "
                f"耗时: {duration:.2f}s | 错误: {str(e)}"
            )
            console_print(
                f"\033[31m[检索失败] 工具: {tool_name} | 错误: {str(e)}\033[0m",
                level=logging.ERROR
            )
            raise


def create_logged_tool(base_tool_class: Type[T]) -> Type[T]:
    """
    Factory function to create a logged version of any tool class.

    Args:
        base_tool_class: The original tool class to be enhanced with logging

    Returns:
        A new class that inherits from both LoggedToolMixin and the base tool class
    """

    class LoggedTool(LoggedToolMixin, base_tool_class):
        pass

    # Set a more descriptive name for the class
    LoggedTool.__name__ = f"Logged{base_tool_class.__name__}"
    return LoggedTool
