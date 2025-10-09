#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单研究API测试脚本
测试 /api/research/simple 接口的功能
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional

import httpx
import requests


class SimpleResearchAPITester:
    """简单研究API测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    def print_green(self, message: str):
        """打印绿色消息"""
        print(f"\033[32m{message}\033[0m")
        
    def print_purple(self, message: str):
        """打印紫色消息"""
        print(f"\033[35m{message}\033[0m")
        
    def print_error(self, message: str):
        """打印错误消息"""
        print(f"\033[31m{message}\033[0m")

    def test_basic_research(self):
        """测试基础研究功能"""
        self.print_green("[测试] 基础研究功能")
        
        url = f"{self.base_url}/api/research/simple"
        
        payload = {
            "messages": [
                {"role": "user", "content": "什么是f1赛车？"}
            ],
            "max_search_results": 3,
            "search_engine": "custom_search",
            "enable_deep_thinking": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                self.print_green("✓ 请求成功")
                data = response.json()
                self.print_purple(f"响应ID: {data.get('id')}")
                self.print_purple(f"模型: {data.get('model')}")
                self.print_purple(f"执行时间: {data.get('execution_time', 0):.2f}秒")
                self.print_purple(f"思考步骤: {data.get('thinking_steps', 0)}")
                
                if data.get('choices'):
                    choice = data['choices'][0]
                    content = choice['message']['content']
                    self.print_purple(f"回答内容（前100字符）: {content[:100]}...")
                    
                    sources = choice.get('sources', [])
                    if sources:
                        self.print_purple(f"参考来源数量: {len(sources)}")
                        for i, source in enumerate(sources[:3]):
                            self.print_purple(f"  来源{i+1}: {source}")
                
                return True
            else:
                self.print_error(f"✗ 请求失败，状态码: {response.status_code}")
                self.print_error(f"错误信息: {response.text}")
                return False
                
        except Exception as e:
            self.print_error(f"✗ 请求异常: {str(e)}")
            return False

    def test_conversation_continuity(self):
        """测试对话连续性"""
        self.print_green("[测试] 对话连续性")
        
        url = f"{self.base_url}/api/research/simple"
        
        # 第一轮对话
        payload1 = {
            "messages": [
                {"role": "user", "content": "介绍一下深度学习的基本概念"}
            ],
            "max_search_results": 2,
            "search_engine": "custom_search"
        }
        
        try:
            response1 = requests.post(url, json=payload1, timeout=60)
            if response1.status_code != 200:
                self.print_error("✗ 第一轮对话失败")
                return False
                
            data1 = response1.json()
            assistant_response = data1['choices'][0]['message']['content']
            
            # 第二轮对话（带上下文）
            payload2 = {
                "messages": [
                    {"role": "user", "content": "介绍一下深度学习的基本概念"},
                    {"role": "assistant", "content": assistant_response},
                    {"role": "user", "content": "深度学习和传统机器学习的区别是什么？"}
                ],
                "max_search_results": 2,
                "search_engine": "custom_search"
            }
            
            response2 = requests.post(url, json=payload2, timeout=60)
            if response2.status_code == 200:
                self.print_green("✓ 对话连续性测试成功")
                data2 = response2.json()
                self.print_purple(f"第二轮回答（前100字符）: {data2['choices'][0]['message']['content'][:100]}...")
                return True
            else:
                self.print_error("✗ 第二轮对话失败")
                return False
                
        except Exception as e:
            self.print_error(f"✗ 对话连续性测试异常: {str(e)}")
            return False

    def test_search_engines(self):
        """测试不同搜索引擎"""
        self.print_green("[测试] 不同搜索引擎")
        
        url = f"{self.base_url}/api/research/simple"
        search_engines = ["custom_search"]
        
        for engine in search_engines:
            self.print_purple(f"测试搜索引擎: {engine}")
            
            payload = {
                "messages": [
                    {"role": "user", "content": "f1赛车 的最新发展趋势是什么？"}
                ],
                "search_engine": engine,
                "max_search_results": 2
            }
            
            try:
                response = requests.post(url, json=payload, timeout=60)
                if response.status_code == 200:
                    self.print_green(f"  ✓ {engine} 搜索引擎测试成功")
                else:
                    self.print_error(f"  ✗ {engine} 搜索引擎测试失败: {response.status_code}")
            except Exception as e:
                self.print_error(f"  ✗ {engine} 搜索引擎测试异常: {str(e)}")

    def test_parameter_variations(self):
        """测试不同参数配置"""
        self.print_green("[测试] 不同参数配置")
        
        url = f"{self.base_url}/api/research/simple"
        
        test_configs = [
            {
                "name": "最大搜索结果=1",
                "params": {"max_search_results": 1}
            },
            {
                "name": "最大搜索结果=5", 
                "params": {"max_search_results": 5}
            },
            {
                "name": "关闭深度思考",
                "params": {"enable_deep_thinking": False}
            },
            {
                "name": "最大思考迭代=1",
                "params": {"max_thinking_iterations": 1}
            },
            {
                "name": "最大递归限制=5",
                "params": {"max_recursion_limit": 5}
            }
        ]
        
        for config in test_configs:
            self.print_purple(f"测试配置: {config['name']}")
            
            payload = {
                "messages": [
                    {"role": "user", "content": "什么是自然语言处理？"}
                ],
                "search_engine": "custom_search",
                **config['params']
            }
            
            try:
                response = requests.post(url, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    self.print_green(f"  ✓ {config['name']} 测试成功")
                    self.print_purple(f"    执行时间: {data.get('execution_time', 0):.2f}秒")
                    self.print_purple(f"    思考步骤: {data.get('thinking_steps', 0)}")
                else:
                    self.print_error(f"  ✗ {config['name']} 测试失败: {response.status_code}")
            except Exception as e:
                self.print_error(f"  ✗ {config['name']} 测试异常: {str(e)}")

    def test_error_handling(self):
        """测试错误处理"""
        self.print_green("[测试] 错误处理")
        
        url = f"{self.base_url}/api/research/simple"
        
        # 测试空消息
        self.print_purple("测试空消息列表")
        try:
            response = requests.post(url, json={"messages": []}, timeout=30)
            if response.status_code != 200:
                self.print_green("  ✓ 正确处理空消息列表")
            else:
                self.print_error("  ✗ 未正确处理空消息列表")
        except Exception as e:
            self.print_purple(f"  空消息测试异常: {str(e)}")

        # 测试无效参数
        self.print_purple("测试无效参数")
        invalid_payload = {
            "messages": [{"role": "user", "content": "测试"}],
            "max_search_results": -1  # 无效值
        }
        
        try:
            response = requests.post(url, json=invalid_payload, timeout=30)
            self.print_purple(f"  无效参数响应状态码: {response.status_code}")
        except Exception as e:
            self.print_purple(f"  无效参数测试异常: {str(e)}")

    def check_server_health(self):
        """检查服务器健康状态"""
        self.print_green("[检查] 服务器健康状态")
        
        try:
            response = requests.get(f"{self.base_url}/api/config", timeout=10)
            if response.status_code == 200:
                self.print_green("✓ 服务器运行正常")
                config = response.json()
                self.print_purple(f"可用模型数量: {len(config.get('models', []))}")
                self.print_purple(f"RAG提供者: {config.get('rag', {}).get('provider', 'Unknown')}")
                return True
            else:
                self.print_error(f"✗ 服务器健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            self.print_error(f"✗ 无法连接到服务器: {str(e)}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        self.print_green("="*60)
        self.print_green("开始测试 /api/research/simple 接口")
        self.print_green("="*60)
        
        # 健康检查
        if not self.check_server_health():
            self.print_error("服务器不可用，停止测试")
            return
        
        print()  # 空行
        
        # 运行各项测试
        tests = [
            self.test_basic_research,
            self.test_conversation_continuity,
            self.test_search_engines,
            self.test_parameter_variations,
            self.test_error_handling
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                self.print_error(f"测试异常: {str(e)}")
            print()  # 空行
        
        # 总结
        self.print_green("="*60)
        self.print_green(f"测试完成: {passed}/{total} 项测试通过")
        self.print_green("="*60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试简单研究API")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="API服务器地址 (默认: http://localhost:8000)")
    parser.add_argument("--test", choices=["basic", "conversation", "engines", "params", "errors", "all"],
                       default="all", help="选择要运行的测试类型")
    
    args = parser.parse_args()
    
    tester = SimpleResearchAPITester(args.url)
    
    if args.test == "basic":
        tester.test_basic_research()
    elif args.test == "conversation":
        tester.test_conversation_continuity()
    elif args.test == "engines":
        tester.test_search_engines()
    elif args.test == "params":
        tester.test_parameter_variations()
    elif args.test == "errors":
        tester.test_error_handling()
    else:  # all
        tester.run_all_tests()


if __name__ == "__main__":
    main()