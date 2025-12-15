#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过 API 调试迭代研究节点的测试脚本

使用方法：
    1. 启动后端服务: python server.py
    2. 运行此脚本: python test_iterative_research_api.py

功能：
    - 通过 HTTP API 调用迭代研究节点
    - 支持强制路由到 iterative_research 节点
    - 实时查看流式输出
"""

import requests
import json
import sys

# API 配置
API_URL = "http://localhost:8000/api/chat/stream"

# 测试查询
TEST_QUERIES = [
    "详细解释一下量子计算的工作原理",
    "深入分析人工智能在金融领域的应用",
    "全面介绍区块链技术的底层机制",
]


def test_iterative_research_via_api(query: str, max_iterations: int = 3):
    """
    通过 API 测试迭代研究节点
    
    Args:
        query: 测试查询
        max_iterations: 最大迭代次数
    """
    print(f"\n{'='*80}")
    print(f"🧪 开始测试迭代研究节点 (通过 API)")
    print(f"📝 查询: {query}")
    print(f"🔢 最大迭代次数: {max_iterations}")
    print(f"{'='*80}\n")
    
    # 构建请求数据
    payload = {
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "max_iteration": max_iterations,
        "max_search_results": 3,
        "search_engine": "custom_search",
        "auto_accepted_plan": True,
        # 🐛 调试模式：强制路由到迭代研究节点
        "force_routing_path": "iterative_research",
    }
    
    try:
        print("🚀 发送请求到 API...\n")
        
        # 发送流式请求
        response = requests.post(
            API_URL,
            json=payload,
            stream=True,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"❌ API 请求失败: {response.status_code}")
            print(f"错误详情: {response.text}")
            return
        
        print("✅ 开始接收流式响应...\n")
        print("="*80)
        
        # 处理流式响应
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                # 跳过空行
                if not line_str.strip():
                    continue
                
                # 解析 SSE 格式
                if line_str.startswith('event:'):
                    event_type = line_str.split(':', 1)[1].strip()
                    continue
                
                if line_str.startswith('data:'):
                    try:
                        data_str = line_str.split(':', 1)[1].strip()
                        data = json.loads(data_str)
                        
                        # 显示关键信息
                        agent = data.get('agent', 'unknown')
                        content = data.get('content', '')
                        
                        # 路由决策
                        if 'routing_path' in content or '智能路由' in content:
                            print(f"\n🔀 路由决策:")
                            print(content)
                        
                        # Agent 输出
                        elif content and agent != 'unknown':
                            print(f"\n🤖 {agent}:")
                            print(content)
                        
                        # 工具调用
                        if 'tool_calls' in data:
                            tool_calls = data.get('tool_calls', [])
                            for tool in tool_calls:
                                print(f"\n🔧 工具调用: {tool.get('name', 'unknown')}")
                                print(f"   参数: {json.dumps(tool.get('args', {}), ensure_ascii=False, indent=2)}")
                        
                    except json.JSONDecodeError:
                        pass  # 忽略非 JSON 行
        
        print("\n" + "="*80)
        print("✅ 测试完成！")
        
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 请确保后端服务运行在 {API_URL}")
        print("提示: 使用 'python server.py' 启动后端服务")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║        迭代研究节点 API 调试测试脚本                            ║
║                                                                ║
║  功能：                                                         ║
║    - 通过 HTTP API 调用迭代研究节点                             ║
║    - 强制跳过智能分类，直接路由到 iterative_research_node      ║
║    - 实时查看流式输出                                           ║
║                                                                ║
║  前提条件：                                                      ║
║    - 后端服务已启动 (python server.py)                          ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # 选择测试查询
    print("\n可用的测试查询:")
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"  {i}. {query}")
    
    try:
        choice = input(f"\n请选择测试查询 (1-{len(TEST_QUERIES)}) 或输入自定义查询: ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(TEST_QUERIES):
            query = TEST_QUERIES[int(choice) - 1]
        else:
            query = choice if choice else TEST_QUERIES[0]
        
        max_iterations = input("请输入最大迭代次数 (默认 3): ").strip()
        max_iterations = int(max_iterations) if max_iterations.isdigit() else 3
        
        # 执行测试
        test_iterative_research_via_api(query, max_iterations)
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


if __name__ == "__main__":
    main()
