#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检索适配器测试脚本
用于独立测试各种检索接口
"""

import json
import logging
import os
import sys
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.search_adapter_base import (
    test_search_adapter, 
    list_available_adapters,
    register_search_adapter
)
from src.tools.adapters.custom_search_adapter import TBYHCustomSearchAdapter

# 注册交通银行适配器
register_search_adapter("tbyh_custom", TBYHCustomSearchAdapter)

def test_mock_adapter():
    """测试Mock适配器"""
    print("=" * 60)
    print("测试 Mock 适配器")
    print("=" * 60)
    
    results = test_search_adapter("mock", "测试查询")
    print(f"检索结果数量: {len(results)}")
    for i, result in enumerate(results):
        print(f"{i+1}. {result['title']}")
        print(f"   内容: {result['content'][:50]}...")
        print(f"   评分: {result['score']}")
        print()


def test_custom_adapter():
    """测试自定义适配器"""
    print("=" * 60)
    print("测试 自定义 适配器")
    print("=" * 60)
    
    # 配置自定义搜索适配器
    config = {
        "api_url": "http://localhost:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do",
        "api_key": "",  # 如果需要API密钥
    }
    
    results = test_search_adapter("custom", "F1赛车制造", **config)
    print(f"检索结果数量: {len(results)}")
    for i, result in enumerate(results):
        print(f"{i+1}. {result['title']}")
        print(f"   内容: {result['content'][:50]}...")
        print(f"   评分: {result['score']}")
        print()


def test_tbyh_custom_adapter():
    """测试交通银行自定义适配器"""
    print("=" * 60)
    print("测试 交通银行自定义 适配器")
    print("=" * 60)
    
    # 配置交通银行搜索适配器
    config = {
        "api_url": os.getenv("CUSTOM_SEARCH_API_URL", "http://localhost:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do"),
        "api_key": os.getenv("CUSTOM_SEARCH_API_KEY", ""),
    }
    
    results = test_search_adapter("tbyh_custom", "F1赛车制造", **config)
    print(f"检索结果数量: {len(results)}")
    for i, result in enumerate(results):
        print(f"{i+1}. {result['title']}")
        print(f"   内容: {result['content'][:50]}...")
        print(f"   评分: {result['score']}")
        print()


def main():
    """主测试函数"""
    logging.basicConfig(level=logging.INFO)
    
    print("检索适配器测试工具")
    print("=" * 60)
    print(f"可用适配器: {list_available_adapters()}")
    print()
    
    # 测试所有适配器
    test_mock_adapter()
    
    # 如果环境变量配置了自定义搜索，则测试自定义适配器
    if os.getenv("CUSTOM_SEARCH_API_URL"):
        test_custom_adapter()
        test_tbyh_custom_adapter()
    else:
        print("提示: 设置 CUSTOM_SEARCH_API_URL 环境变量以测试自定义搜索适配器")
        print()


if __name__ == "__main__":
    main()
