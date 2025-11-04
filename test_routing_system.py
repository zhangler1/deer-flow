#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
智能路由系统测试脚本

演示如何使用新的智能路由功能，包括：
1. 简单问答路径
2. 深度研究路径
3. 部门专用路径
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.graph.classifier import classify_request, RouteDecision
from src.graph.department_agents import get_available_departments


def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*20} {title} {'='*20}\n")
    else:
        print(f"\n{'='*60}\n")


def test_classifier():
    """测试分类器功能"""
    print_separator("测试分类器")
    
    test_cases = [
        # 简单问答测试
        {
            "query": "什么是Python?",
            "department": "general",
            "expected_path": "simple_qa"
        },
        {
            "query": "今天天气如何?",
            "department": "general",
            "expected_path": "simple_qa"
        },
        {
            "query": "如何定义一个函数?",
            "department": "general",
            "expected_path": "simple_qa"
        },
        
        # 深度研究测试
        {
            "query": "分析人工智能在医疗行业的应用现状和未来发展趋势",
            "department": "general",
            "expected_path": "deep_research"
        },
        {
            "query": "对比React、Vue、Angular三种前端框架的优劣",
            "department": "general",
            "expected_path": "deep_research"
        },
        
        # 部门专用测试
        {
            "query": "设计一个用户认证系统的数据库架构",
            "department": "tech",
            "expected_path": "department_specific"
        },
        {
            "query": "分析竞品的市场定位和营销策略",
            "department": "marketing",
            "expected_path": "department_specific"
        },
        {
            "query": "计算项目的投资回报率和成本效益分析",
            "department": "finance",
            "expected_path": "department_specific"
        },
    ]
    
    print(f"运行 {len(test_cases)} 个测试用例...\n")
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        department = test_case["department"]
        expected = test_case["expected_path"]
        
        print(f"测试 #{i}:")
        print(f"  查询: {query}")
        print(f"  部门: {department}")
        print(f"  期望路径: {expected}")
        
        try:
            # 调用分类器
            decision = classify_request(
                query=query,
                department=department,
                enable_smart_routing=True
            )
            
            print(f"  实际路径: {decision.path}")
            print(f"  复杂度: {decision.complexity}")
            print(f"  置信度: {decision.confidence:.2f}")
            print(f"  理由: {decision.reasoning}")
            
            # 检查结果
            if decision.path == expected:
                print("  ✅ 通过")
                passed += 1
            else:
                print(f"  ❌ 失败 (期望: {expected}, 实际: {decision.path})")
                failed += 1
                
        except Exception as e:
            print(f"  ❌ 错误: {str(e)}")
            failed += 1
        
        print()
    
    print_separator("测试结果")
    print(f"总计: {len(test_cases)}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print(f"成功率: {passed/len(test_cases)*100:.1f}%")
    
    return passed, failed


def test_departments():
    """测试部门配置"""
    print_separator("部门配置信息")
    
    departments = get_available_departments()
    
    print(f"可用部门数量: {len(departments)}\n")
    
    for dept in departments:
        print(f"部门ID: {dept['id']}")
        print(f"  名称: {dept['name']}")
        print(f"  描述: {dept['description']}")
        print()


def demo_routing_scenarios():
    """演示不同路由场景"""
    print_separator("路由场景演示")
    
    scenarios = [
        {
            "title": "场景1: 技术部员工询问代码问题",
            "query": "如何优化数据库查询性能?",
            "department": "tech",
            "description": "技术部员工询问专业技术问题，应该路由到部门专用路径"
        },
        {
            "title": "场景2: 市场部员工询问简单事实",
            "query": "什么是SEO?",
            "department": "marketing",
            "description": "虽然是市场部，但问题很简单，应该路由到简单问答"
        },
        {
            "title": "场景3: 普通用户询问复杂分析",
            "query": "研究区块链技术在供应链管理中的应用前景",
            "department": "general",
            "description": "通用部门但问题复杂，应该路由到深度研究"
        },
        {
            "title": "场景4: 财务部员工进行数据分析",
            "query": "基于历史数据预测下季度的营收增长率",
            "department": "finance",
            "description": "财务部专业问题，需要Python计算，路由到部门专用"
        },
    ]
    
    for scenario in scenarios:
        print(f"【{scenario['title']}】")
        print(f"背景: {scenario['description']}")
        print(f"查询: {scenario['query']}")
        print(f"部门: {scenario['department']}")
        
        decision = classify_request(
            query=scenario['query'],
            department=scenario['department'],
            enable_smart_routing=True
        )
        
        print(f"\n路由决策:")
        print(f"  → 路径: {decision.path}")
        print(f"  → 复杂度: {decision.complexity}")
        print(f"  → 部门匹配: {'是' if decision.department_match else '否'}")
        print(f"  → 置信度: {decision.confidence:.2f}")
        print(f"  → 理由: {decision.reasoning}")
        print()


def main():
    """主函数"""
    print("\n" + "🚀 DeerFlow 智能路由系统测试".center(60, "="))
    
    try:
        # 1. 测试部门配置
        test_departments()
        
        # 2. 测试分类器
        passed, failed = test_classifier()
        
        # 3. 演示路由场景
        demo_routing_scenarios()
        
        print_separator("测试完成")
        print("✅ 所有测试已完成!")
        
        return 0 if failed == 0 else 1
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
