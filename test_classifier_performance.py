#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试分类器性能监控"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.graph.classifier import classify_request
from src.utils.enhanced_logger import setup_enhanced_logging
from src.utils.performance_monitor import PerformanceStats
import logging

# 设置日志
setup_enhanced_logging(
    level=logging.INFO,
    enable_colors=True,
    log_file="logs/classifier_performance.log"
)

print("\n" + "="*80)
print("🎯 分类器性能监控测试".center(80))
print("="*80 + "\n")

# 测试查询列表
test_queries = [
    "什么是信用卡？",
    "如何申请贷款？",
    "网上银行怎么使用？",
    "转账需要手续费吗？",
    "理财产品有哪些风险？",
]

print("开始测试分类器性能...\n")

# 创建性能统计收集器
stats = PerformanceStats("分类器批量性能测试")

# 逐个测试
for i, query in enumerate(test_queries, 1):
    print(f"[{i}/{len(test_queries)}] 测试查询: {query}")
    
    with stats.monitor(auto_log=False):
        try:
            result = classify_request(
                query=query,
                department="general",
                enable_smart_routing=True
            )
            print(f"  → 分类路径: {result.path}")
            print(f"  → 复杂度: {result.complexity}")
            print(f"  → 置信度: {result.confidence:.2f}")
            print(f"  → 理由: {result.reasoning}\n")
        except Exception as e:
            print(f"  ✗ 分类失败: {e}\n")

# 打印统计摘要
print("\n" + "="*80)
print("📊 性能统计摘要")
print("="*80)
stats.print_summary()

print(f"\n详细统计:")
print(f"  执行次数: {stats.get_count()}")
print(f"  成功次数: {stats.success_count}")
print(f"  失败次数: {stats.error_count}")
print(f"  平均耗时: {stats.get_average():.3f}s")
print(f"  最小耗时: {stats.get_min():.3f}s")
print(f"  最大耗时: {stats.get_max():.3f}s")
print(f"  P50耗时: {stats.get_percentile(50):.3f}s")
print(f"  P95耗时: {stats.get_percentile(95):.3f}s")
print(f"  总耗时: {stats.get_total():.3f}s")

print("\n" + "="*80)
print("✅ 测试完成！")
print("="*80 + "\n")
