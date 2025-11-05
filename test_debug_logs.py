#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试新增节点的DEBUG级别日志输出

使用方法:
1. 设置环境变量启用DEBUG级别：
   export LOG_LEVEL=DEBUG

2. 运行测试：
   python test_debug_logs.py
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置DEBUG日志级别
os.environ['LOG_LEVEL'] = 'DEBUG'

from src.graph.nodes import direct_answer_node, simple_search_node, domain_knowledge_node, department_node
from src.graph.types import State
from langchain_core.messages import HumanMessage

def test_direct_answer_debug():
    """测试direct_answer_node的DEBUG日志"""
    print("\n" + "="*80)
    print("🧪 测试 direct_answer_node 的 DEBUG 日志输出")
    print("="*80 + "\n")
    
    state: State = {
        "messages": [HumanMessage(content="什么是人工智能？")],
        "research_topic": "什么是人工智能？",
        "locale": "zh-CN",
        "observations": [],
        "resources": [],
        "plan_iterations": 0,
        "current_plan": None,
        "final_report": "",
        "auto_accepted_plan": False,
        "enable_background_investigation": True,
        "background_investigation_results": None,
        "system_context": "",
        "user_department": "general",
        "query_complexity": "simple",
        "routing_path": "direct_answer",
        "enable_smart_routing": True,
        "department_context": {}
    }
    
    config = {
        "configurable": {
            "max_step_num": 3,
            "search_engine": "custom_search",
            "custom_search_repository": "okic-dynamicSearch"
        }
    }
    
    try:
        result = direct_answer_node(state, config)
        print(f"\n✅ direct_answer_node 测试完成")
        print(f"📝 返回结果类型: {type(result)}")
    except Exception as e:
        print(f"\n❌ direct_answer_node 测试失败: {e}")


def test_simple_search_debug():
    """测试simple_search_node的DEBUG日志"""
    print("\n" + "="*80)
    print("🧪 测试 simple_search_node 的 DEBUG 日志输出")
    print("="*80 + "\n")
    
    state: State = {
        "messages": [HumanMessage(content="信用卡如何办理？")],
        "research_topic": "信用卡如何办理？",
        "locale": "zh-CN",
        "observations": [],
        "resources": [],
        "plan_iterations": 0,
        "current_plan": None,
        "final_report": "",
        "auto_accepted_plan": False,
        "enable_background_investigation": True,
        "background_investigation_results": None,
        "system_context": "",
        "user_department": "retail",
        "query_complexity": "simple",
        "routing_path": "simple_search",
        "enable_smart_routing": True,
        "department_context": {}
    }
    
    config = {
        "configurable": {
            "max_step_num": 3,
            "search_engine": "custom_search",
            "custom_search_repository": "okic-dynamicSearch"
        }
    }
    
    try:
        result = simple_search_node(state, config)
        print(f"\n✅ simple_search_node 测试完成")
        print(f"📝 返回结果类型: {type(result)}")
    except Exception as e:
        print(f"\n❌ simple_search_node 测试失败: {e}")


def test_domain_knowledge_debug():
    """测试domain_knowledge_node的DEBUG日志"""
    print("\n" + "="*80)
    print("🧪 测试 domain_knowledge_node 的 DEBUG 日志输出")
    print("="*80 + "\n")
    
    state: State = {
        "messages": [HumanMessage(content="什么是巴塞尔协议III？")],
        "research_topic": "什么是巴塞尔协议III？",
        "locale": "zh-CN",
        "observations": [],
        "resources": [],
        "plan_iterations": 0,
        "current_plan": None,
        "final_report": "",
        "auto_accepted_plan": False,
        "enable_background_investigation": True,
        "background_investigation_results": None,
        "system_context": "",
        "user_department": "risk",
        "query_complexity": "complex",
        "routing_path": "domain_knowledge",
        "enable_smart_routing": True,
        "department_context": {}
    }
    
    config = {
        "configurable": {
            "max_step_num": 3,
            "search_engine": "custom_search",
            "custom_search_repository": "okic-dynamicSearch"
        }
    }
    
    try:
        result = domain_knowledge_node(state, config)
        print(f"\n✅ domain_knowledge_node 测试完成")
        print(f"📝 返回结果类型: {type(result)}")
    except Exception as e:
        print(f"\n❌ domain_knowledge_node 测试失败: {e}")


if __name__ == "__main__":
    print("\n" + "🎯"*40)
    print("开始测试新增节点的 DEBUG 日志功能")
    print("🎯"*40)
    
    print(f"\n📋 当前日志级别: {os.getenv('LOG_LEVEL', 'INFO')}")
    print("💡 提示: 应该看到绿色的INFO日志和青色的DEBUG日志\n")
    
    # 测试各个节点
    test_direct_answer_debug()
    test_simple_search_debug()
    test_domain_knowledge_debug()
    
    print("\n" + "🎉"*40)
    print("所有测试完成！")
    print("🎉"*40 + "\n")
    
    print("\n📖 日志说明:")
    print("  🤖 LLM_INPUT  - 大模型输入 (DEBUG级别，包含完整Prompt)")
    print("  🤖 LLM_OUTPUT - 大模型输出 (DEBUG级别，包含完整响应)")
    print("  🤖 AGENT_INPUT  - 智能体输入 (DEBUG级别，department_node)")
    print("  🤖 AGENT_OUTPUT - 智能体输出 (DEBUG级别，department_node)")
    print("  💬 ANSWER_GENERATED - 回答生成摘要 (INFO级别)")
    print("\n💡 如需查看详细日志，请设置: export LOG_LEVEL=DEBUG\n")
