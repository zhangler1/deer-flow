# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
性能监控工具模块
提供上下文管理器方式的性能监控，用于监控函数或代码块的执行耗时
"""

import time
import logging
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from functools import wraps

from src.utils.enhanced_logger import get_enhanced_logger, should_log


class PerformanceMonitor:
    """
    性能监控上下文管理器
    
    使用示例:
        # 基本使用
        with PerformanceMonitor("分类模型推理"):
            result = classify_request(query)
        
        # 指定日志级别
        with PerformanceMonitor("数据处理", level=logging.DEBUG):
            process_data()
        
        # 监控并获取执行时间
        monitor = PerformanceMonitor("复杂计算")
        with monitor:
            complex_calculation()
        print(f"耗时: {monitor.duration}秒")
        
        # 嵌套监控
        with PerformanceMonitor("整体流程"):
            with PerformanceMonitor("步骤1"):
                step1()
            with PerformanceMonitor("步骤2"):
                step2()
    """
    
    def __init__(
        self,
        operation_name: str,
        logger_name: str = "performance",
        level: int = logging.INFO,
        threshold: Optional[float] = None,
        auto_log: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化性能监控器
        
        Args:
            operation_name: 操作名称，用于标识正在监控的操作
            logger_name: 日志记录器名称，默认为 "performance"
            level: 日志级别，默认为 INFO
            threshold: 耗时阈值（秒），超过此值会额外标记警告，None表示不设阈值
            auto_log: 是否自动记录日志，默认为 True
            metadata: 额外的元数据，会在日志中显示
        """
        self.operation_name = operation_name
        self.logger = get_enhanced_logger(logger_name)
        self.level = level
        self.threshold = threshold
        self.auto_log = auto_log
        self.metadata = metadata or {}
        
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        self.success: bool = True
        self.error: Optional[Exception] = None
        
    def __enter__(self):
        """进入上下文时开始计时"""
        self.start_time = time.time()
        
        if self.auto_log and should_log(self.level):
            metadata_str = self._format_metadata()
            self.logger.logger.log(
                self.level,
                f"⏱️  PERF_START | {self.operation_name}{metadata_str} | 开始监控"
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时结束计时并记录"""
        self.end_time = time.time()
        if self.start_time is not None:
            self.duration = self.end_time - self.start_time
        else:
            self.duration = 0.0
        
        # 检查是否有异常
        if exc_type is not None:
            self.success = False
            self.error = exc_val
        
        if self.auto_log and should_log(self.level):
            self._log_result()
        
        # 不抑制异常
        return False
    
    def _format_metadata(self) -> str:
        """格式化元数据为字符串"""
        if not self.metadata:
            return ""
        
        items = [f"{k}={v}" for k, v in self.metadata.items()]
        return f" | {', '.join(items)}"
    
    def _log_result(self):
        """记录监控结果"""
        metadata_str = self._format_metadata()
        
        # 构建基础日志信息
        if self.success:
            status_icon = "✅"
            status_text = "完成"
        else:
            status_icon = "❌"
            status_text = f"失败: {type(self.error).__name__}"
        
        # 检查是否超过阈值
        threshold_warning = ""
        if (self.threshold is not None and 
            self.duration is not None and 
            self.duration > self.threshold):
            threshold_warning = f" ⚠️ 超过阈值 {self.threshold:.2f}s"
        
        # 记录日志
        log_message = (
            f"⏱️  PERF_END | {self.operation_name}{metadata_str} | "
            f"{status_icon} {status_text} | "
            f"耗时: {self.duration:.3f}s{threshold_warning}"
        )
        
        # 如果失败或超过阈值，提升日志级别
        if not self.success:
            self.logger.logger.error(log_message)
        elif threshold_warning:
            self.logger.logger.warning(log_message)
        else:
            self.logger.logger.log(self.level, log_message)
    
    def get_duration_ms(self) -> Optional[float]:
        """
        获取耗时（毫秒）
        
        Returns:
            耗时毫秒数，如果尚未完成则返回 None
        """
        return self.duration * 1000 if self.duration is not None else None
    
    def get_duration_formatted(self) -> str:
        """
        获取格式化的耗时字符串
        
        Returns:
            格式化的耗时字符串，例如 "1.234s" 或 "123.4ms"
        """
        if self.duration is None:
            return "未完成"
        
        if self.duration >= 1.0:
            return f"{self.duration:.3f}s"
        else:
            return f"{self.duration * 1000:.1f}ms"


@contextmanager
def monitor_performance(
    operation_name: str,
    logger_name: str = "performance",
    level: int = logging.INFO,
    threshold: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    性能监控上下文管理器（函数形式）
    
    这是 PerformanceMonitor 的快捷函数版本
    
    Args:
        operation_name: 操作名称
        logger_name: 日志记录器名称
        level: 日志级别
        threshold: 耗时阈值（秒）
        metadata: 额外元数据
        
    Yields:
        PerformanceMonitor: 监控器实例
        
    Example:
        with monitor_performance("数据库查询", threshold=1.0) as monitor:
            query_database()
        print(f"查询耗时: {monitor.get_duration_formatted()}")
    """
    monitor = PerformanceMonitor(
        operation_name=operation_name,
        logger_name=logger_name,
        level=level,
        threshold=threshold,
        metadata=metadata
    )
    
    with monitor:
        yield monitor


def performance_monitor(
    operation_name: Optional[str] = None,
    logger_name: str = "performance",
    level: int = logging.INFO,
    threshold: Optional[float] = None,
    include_args: bool = False
):
    """
    性能监控装饰器
    
    为函数添加性能监控，自动记录执行耗时
    
    Args:
        operation_name: 操作名称，如果为None则使用函数名
        logger_name: 日志记录器名称
        level: 日志级别
        threshold: 耗时阈值（秒）
        include_args: 是否在元数据中包含函数参数
        
    Example:
        @performance_monitor(threshold=2.0)
        def complex_calculation(x, y):
            time.sleep(1)
            return x + y
            
        @performance_monitor("分类器推理", include_args=True)
        def classify(query: str):
            return classifier.predict(query)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 确定操作名称
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            # 构建元数据
            metadata = {}
            if include_args:
                if args:
                    metadata['args'] = str(args)[:100]  # 限制长度
                if kwargs:
                    metadata['kwargs'] = str(kwargs)[:100]
            
            # 执行监控
            with PerformanceMonitor(
                operation_name=op_name,
                logger_name=logger_name,
                level=level,
                threshold=threshold,
                metadata=metadata
            ):
                return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 确定操作名称
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            # 构建元数据
            metadata = {}
            if include_args:
                if args:
                    metadata['args'] = str(args)[:100]
                if kwargs:
                    metadata['kwargs'] = str(kwargs)[:100]
            
            # 执行监控
            with PerformanceMonitor(
                operation_name=op_name,
                logger_name=logger_name,
                level=level,
                threshold=threshold,
                metadata=metadata
            ):
                return await func(*args, **kwargs)
        
        # 根据函数类型返回对应的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class PerformanceStats:
    """
    性能统计收集器
    
    用于收集多次执行的性能统计信息
    
    Example:
        stats = PerformanceStats("分类器")
        
        for query in queries:
            with stats.monitor():
                classify(query)
        
        print(f"平均耗时: {stats.get_average():.3f}s")
        print(f"最大耗时: {stats.get_max():.3f}s")
        stats.print_summary()
    """
    
    def __init__(self, name: str, logger_name: str = "performance.stats"):
        """
        初始化性能统计收集器
        
        Args:
            name: 统计名称
            logger_name: 日志记录器名称
        """
        self.name = name
        self.logger = get_enhanced_logger(logger_name)
        self.durations: list[float] = []
        self.success_count: int = 0
        self.error_count: int = 0
    
    @contextmanager
    def monitor(self, auto_log: bool = False):
        """
        监控单次执行
        
        Args:
            auto_log: 是否自动记录每次执行的日志
            
        Yields:
            PerformanceMonitor: 监控器实例
        """
        monitor = PerformanceMonitor(
            operation_name=self.name,
            logger_name="performance.stats",
            auto_log=auto_log
        )
        
        with monitor:
            yield monitor
        
        # 收集统计信息
        if monitor.duration is not None:
            self.durations.append(monitor.duration)
            if monitor.success:
                self.success_count += 1
            else:
                self.error_count += 1
    
    def get_count(self) -> int:
        """获取执行次数"""
        return len(self.durations)
    
    def get_average(self) -> float:
        """获取平均耗时"""
        return sum(self.durations) / len(self.durations) if self.durations else 0.0
    
    def get_min(self) -> float:
        """获取最小耗时"""
        return min(self.durations) if self.durations else 0.0
    
    def get_max(self) -> float:
        """获取最大耗时"""
        return max(self.durations) if self.durations else 0.0
    
    def get_total(self) -> float:
        """获取总耗时"""
        return sum(self.durations)
    
    def get_percentile(self, percentile: float) -> float:
        """
        获取指定百分位的耗时
        
        Args:
            percentile: 百分位值，0-100之间
            
        Returns:
            对应百分位的耗时
        """
        if not self.durations:
            return 0.0
        
        sorted_durations = sorted(self.durations)
        index = int(len(sorted_durations) * percentile / 100)
        index = min(index, len(sorted_durations) - 1)
        return sorted_durations[index]
    
    def print_summary(self, level: int = logging.INFO):
        """
        打印统计摘要
        
        Args:
            level: 日志级别
        """
        if not self.durations:
            self.logger.logger.log(level, f"📊 PERF_STATS | {self.name} | 无统计数据")
            return
        
        summary = (
            f"📊 PERF_STATS | {self.name} | "
            f"执行次数: {self.get_count()} | "
            f"成功: {self.success_count} | "
            f"失败: {self.error_count} | "
            f"平均: {self.get_average():.3f}s | "
            f"最小: {self.get_min():.3f}s | "
            f"最大: {self.get_max():.3f}s | "
            f"P50: {self.get_percentile(50):.3f}s | "
            f"P95: {self.get_percentile(95):.3f}s | "
            f"P99: {self.get_percentile(99):.3f}s | "
            f"总计: {self.get_total():.3f}s"
        )
        
        self.logger.logger.log(level, summary)
    
    def reset(self):
        """重置统计数据"""
        self.durations.clear()
        self.success_count = 0
        self.error_count = 0


# 导出公共接口
__all__ = [
    "PerformanceMonitor",
    "monitor_performance",
    "performance_monitor",
    "PerformanceStats",
]
