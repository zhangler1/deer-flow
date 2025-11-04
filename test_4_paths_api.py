#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试4种路径智能路由系统的API接口
"""

import requests
import json
import time

# API配置
API_BASE_URL = "http://localhost:8000"
CHAT_STREAM_URL = f"{API_BASE_URL}/api/chat/stream"

# 终端颜色输出（绿色+紫色配色）
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    GREEN = Fore.GREEN
    PURPLE = Fore.MAGENTA
    RESET = Style.RESET_ALL
except ImportError:
    # 降级使用ANSI转义序列
    GREEN = "\033[92m"
    PURPLE = "\033[95m"
    RESET = "\033[0m"


def print_header(text):
    """打印标题（绿色）"""
    print(f"\n{GREEN}{'=' * 80}")
    print(f"{text}")
    print(f"{'=' * 80}{RESET}\n")


def print_result(label, value):
    """打印结果（绿色标签+紫色值）"""
    print(f"{GREEN}{label}:{RESET} {PURPLE}{value}{RESET}")


def test_chat_stream(query, description, expected_path):
    """
    测试流式聊天接口
    
    Args:
        query: 用户查询
        description: 测试描述
        expected_path: 期望的路由路径
    """
    print_header(f"测试场景：{description}")
    print_result("查询内容", query)
    print_result("期望路径", expected_path)
    print()
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "thread_id": f"test_{int(time.time())}",
        "max_plan_iterations": 1,
        "max_step_num": 2,
        "max_search_results": 3,
        "search_engine": "custom_search",
        "auto_accepted_plan": True,
        "enable_background_investigation": False,
        "enable_smart_routing": True  # 启用智能路由
    }
    
    try:
        print(f"{GREEN}📡 发送请求到: {CHAT_STREAM_URL}{RESET}")
        response = requests.post(
            CHAT_STREAM_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"{PURPLE}❌ 请求失败: {response.status_code}{RESET}")
            print(f"{PURPLE}响应内容: {response.text}{RESET}")
            return
        
        print(f"{GREEN}✅ 连接成功，接收流式响应...{RESET}\n")
        
        # 解析流式响应
        routing_path = None
        final_report = ""
        event_count = 0
        
        for line in response.iter_lines(decode_unicode=True):
            if line:
                event_count += 1
                # 解析SSE事件
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        
                        # 检测路由决策
                        if "routing_path" in data:
                            routing_path = data["routing_path"]
                            print_result("🎯 检测到路由决策", routing_path)
                        
                        # 检测节点信息
                        if "langgraph_node" in data:
                            node_name = data["langgraph_node"]
                            if node_name in ["router", "direct_answer_node", "simple_search_node", 
                                            "domain_knowledge_node", "coordinator"]:
                                print_result("📍 当前节点", node_name)
                        
                        # 收集最终报告
                        if "content" in data and data.get("content"):
                            content = data["content"]
                            if len(content) > 50:  # 过滤掉短消息
                                final_report += content
                        
                        # 检测完成信号
                        if data.get("finish_reason") == "stop":
                            print(f"{GREEN}✅ 接收完成{RESET}")
                            
                    except json.JSONDecodeError:
                        pass
        
        print()
        print_result("📊 总事件数", event_count)
        if routing_path:
            print_result("🎯 实际路由路径", routing_path)
            if routing_path == expected_path:
                print(f"{GREEN}✅ 路由路径匹配！{RESET}")
            else:
                print(f"{PURPLE}⚠️  路由路径不匹配（期望: {expected_path}）{RESET}")
        else:
            print(f"{PURPLE}⚠️  未检测到路由路径信息{RESET}")
        
        if final_report:
            print_result("📝 最终报告（前200字）", final_report[:200] + "...")
        
    except requests.exceptions.Timeout:
        print(f"{PURPLE}❌ 请求超时{RESET}")
    except requests.exceptions.ConnectionError:
        print(f"{PURPLE}❌ 连接失败，请确保服务已启动{RESET}")
    except Exception as e:
        print(f"{PURPLE}❌ 错误: {str(e)}{RESET}")


def main():
    """主测试函数"""
    print_header("DeerFlow 4种路径智能路由系统 API 测试")
    
    print(f"{GREEN}测试目标: /api/chat/stream 接口{RESET}")
    print(f"{GREEN}服务地址: {API_BASE_URL}{RESET}")
    print()
    
    # 测试场景列表
    test_cases = [
        {
            "query": "什么是汽车？",
            "description": "直接回答路径 - 通用常识",
            "expected_path": "direct_answer"
        },
        {
            "query": "信用卡如何申请？",
            "description": "简单检索路径 - 银行业务（主流）",
            "expected_path": "simple_search"
        },
        {
            "query": "分析金融科技对传统银行业的影响趋势",
            "description": "深度研究路径 - 复杂分析",
            "expected_path": "deep_research"
        },
        {
            "query": "SWIFT报文MT103的字段详细说明",
            "description": "领域知识路径 - 专业知识",
            "expected_path": "domain_knowledge"
        }
    ]
    
    # 执行测试
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{PURPLE}【测试 {i}/{len(test_cases)}】{RESET}")
        test_chat_stream(**test_case)
        
        # 测试间隔
        if i < len(test_cases):
            print(f"\n{GREEN}等待3秒后继续下一个测试...{RESET}")
            time.sleep(3)
    
    # 测试总结
    print_header("测试完成")
    print(f"{GREEN}✅ 已完成所有4种路径的测试{RESET}")
    print(f"{GREEN}📊 如需查看详细日志，请检查服务端输出{RESET}")
    print()
    print(f"{GREEN}提示：{RESET}")
    print(f"{PURPLE}1. 确保后端服务运行在 {API_BASE_URL}{RESET}")
    print(f"{PURPLE}2. 检查 enhanced_logger 输出以查看路由决策详情{RESET}")
    print(f"{PURPLE}3. 路由路径: direct_answer, simple_search, deep_research, domain_knowledge{RESET}")
    print()


if __name__ == "__main__":
    main()
