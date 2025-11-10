#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
性能监控工具使用示例

演示如何使用 PerformanceMonitor 监控分类模型和其他操作的耗时
"""

import sys
import os
import time
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.performance_monitor import (
    PerformanceMonitor,
    monitor_performance,
    performance_monitor,
    PerformanceStats,
)
from src.utils.enhanced_logger import setup_enhanced_logging


def example1_basic_usage():
    """示例1: 基本使用 - 上下文管理器"""
    print("\n" + "="*80)
    print("示例1: 基本使用 - 上下文管理器")
    print("="*80)
    
    # 模拟分类器推理
    with PerformanceMonitor("分类模型推理"):
        time.sleep(0.5)  # 模拟耗时操作
        result = "simple_search"
    
    print(f"分类结果: {result}")


def example2_with_threshold():
    """示例2: 设置耗时阈值"""
    print("\n" + "="*80)
    print("示例2: 设置耗时阈值")
    print("="*80)
    
    # 设置阈值为1秒，超过会有警告
    with PerformanceMonitor("数据库查询", threshold=1.0):
        time.sleep(1.5)  # 故意超过阈值


def example3_with_metadata():
    """示例3: 添加元数据"""
    print("\n" + "="*80)
    print("示例3: 添加元数据")
    print("="*80)
    
    query = "什么是信用卡？"
    with PerformanceMonitor(
        "分类器调用",
        metadata={"query_length": len(query), "model": "qwen-plus"}
    ):
        time.sleep(0.3)


def example4_nested_monitoring():
    """示例4: 嵌套监控"""
    print("\n" + "="*80)
    print("示例4: 嵌套监控")
    print("="*80)
    
    with PerformanceMonitor("完整流程"):
        with PerformanceMonitor("步骤1: 预处理"):
            time.sleep(0.2)
        
        with PerformanceMonitor("步骤2: 分类推理"):
            time.sleep(0.5)
        
        with PerformanceMonitor("步骤3: 后处理"):
            time.sleep(0.1)


def example5_get_duration():
    """示例5: 获取执行时间"""
    print("\n" + "="*80)
    print("示例5: 获取执行时间")
    print("="*80)
    
    monitor = PerformanceMonitor("复杂计算", auto_log=True)
    with monitor:
        time.sleep(0.456)
    
    # 获取不同格式的耗时
    print(f"耗时(秒): {monitor.duration:.3f}s")
    print(f"耗时(毫秒): {monitor.get_duration_ms():.1f}ms")
    print(f"格式化耗时: {monitor.get_duration_formatted()}")


def example6_function_decorator():
    """示例6: 使用装饰器"""
    print("\n" + "="*80)
    print("示例6: 使用装饰器")
    print("="*80)
    
    @performance_monitor(threshold=0.3)
    def classify_request(query: str):
        """模拟分类器"""
        time.sleep(0.2)
        return "simple_search"
    
    @performance_monitor("复杂业务逻辑", include_args=True)
    def complex_business_logic(x: int, y: int):
        """模拟复杂业务"""
        time.sleep(0.15)
        return x + y
    
    # 调用函数，自动监控
    result1 = classify_request("什么是贷款？")
    print(f"分类结果: {result1}")
    
    result2 = complex_business_logic(10, 20)
    print(f"计算结果: {result2}")


def example7_error_handling():
    """示例7: 错误处理"""
    print("\n" + "="*80)
    print("示例7: 错误处理")
    print("="*80)
    
    try:
        with PerformanceMonitor("可能失败的操作"):
            time.sleep(0.2)
            raise ValueError("模拟错误")
    except ValueError as e:
        print(f"捕获到错误: {e}")


def example8_context_manager_function():
    """示例8: 使用函数形式的上下文管理器"""
    print("\n" + "="*80)
    print("示例8: 使用函数形式的上下文管理器")
    print("="*80)
    
    with monitor_performance("API调用", threshold=0.5) as monitor:
        time.sleep(0.3)
    
    print(f"API调用耗时: {monitor.get_duration_formatted()}")


def example9_performance_stats():
    """示例9: 性能统计收集"""
    print("\n" + "="*80)
    print("示例9: 性能统计收集")
    print("="*80)
    
    stats = PerformanceStats("分类器性能测试")
    
    # 模拟多次调用
    queries = [
        "什么是信用卡？",
        "如何申请贷款？",
        "网上银行怎么用？",
        "转账需要手续费吗？",
        "理财产品有哪些？"
    ]
    
    for query in queries:
        with stats.monitor():
            # 模拟不同的处理时间
            time.sleep(0.1 + len(query) * 0.01)
    
    # 打印统计摘要
    stats.print_summary()
    
    # 获取详细统计
    print(f"\n详细统计:")
    print(f"  执行次数: {stats.get_count()}")
    print(f"  平均耗时: {stats.get_average():.3f}s")
    print(f"  最小耗时: {stats.get_min():.3f}s")
    print(f"  最大耗时: {stats.get_max():.3f}s")
    print(f"  P50耗时: {stats.get_percentile(50):.3f}s")
    print(f"  P95耗时: {stats.get_percentile(95):.3f}s")
    print(f"  总耗时: {stats.get_total():.3f}s")


def example10_real_classifier_usage():
    """示例10: 在实际分类器中的使用"""
    print("\n" + "="*80)
    print("示例10: 在实际分类器中的使用示例")
    print("="*80)
    
    # 模拟在 classifier.py 中的实际使用
    def classify_with_monitoring(query: str) -> dict:
        """带性能监控的分类函数"""
        
        # 整体流程监控
        with PerformanceMonitor("分类器整体流程") as overall_monitor:
            
            # 预处理阶段
            with PerformanceMonitor("预处理", level=logging.DEBUG):
                query_lower = query.lower()
                time.sleep(0.05)
            
            # LLM推理阶段（关键监控点）
            with PerformanceMonitor(
                "LLM推理", 
                threshold=2.0,  # LLM调用设置2秒阈值
                metadata={"query_length": len(query)}
            ) as llm_monitor:
                time.sleep(0.5)  # 模拟LLM调用
                llm_result = "simple_search"
            
            # 后处理阶段
            with PerformanceMonitor("后处理", level=logging.DEBUG):
                time.sleep(0.03)
            
            result = {
                "path": llm_result,
                "total_time": overall_monitor.duration,
                "llm_time": llm_monitor.duration
            }
        
        return result
    
    # 调用分类器
    result = classify_with_monitoring("如何申请信用卡？")
    print(f"分类结果: {result}")


def main():
    """主函数"""
    # 设置日志
    setup_enhanced_logging(
        level=logging.INFO,
        enable_colors=True,
        log_file="logs/performance_monitor_example.log"
    )
    
    print("\n" + "🎯"*40)
    print("性能监控工具使用示例".center(80))
    print("🎯"*40)
    
    # 运行所有示例
    example1_basic_usage()
    example2_with_threshold()
    example3_with_metadata()
    example4_nested_monitoring()
    example5_get_duration()
    example6_function_decorator()
    example7_error_handling()
    example8_context_manager_function()
    example9_performance_stats()
    example10_real_classifier_usage()
    
    print("\n" + "="*80)
    print("所有示例运行完成！")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
