#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化版自定义搜索工具测试
"""

import os
import sys
import json
import requests
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "src" / "tools"))
from custom_search import get_custom_search_tool

def test_basic_functionality():
    """测试基本功能"""
    print("🔍 测试自定义搜索工具基本功能...")
    
    # 设置测试环境变量
    os.environ["CUSTOM_SEARCH_API_URL"] = "http://localhost:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do"
    
    try:
        # 创建搜索工具
        search_tool = get_custom_search_tool(max_results=3)
        
        print(f"✅ 工具创建成功")
        print(f"   API URL: {search_tool.api_url}")
        print(f"   Repository: {search_tool.repository}")
        print(f"   Channel ID: {search_tool.channel_id}")
        
        # 测试响应解析功能
        mock_response = {
            "RSP_HEAD": {"TRAN_SUCCESS": "1"},
            "RSP_BODY": {
                "result": [
                    {
                        "title": "测试标题1",
                        "content": "这是测试内容1",
                        "url": "https://example.com/doc001",
                        "source":"测试来源1",
                        "score": "0.95",
                        "docId": "doc001"
                    },
                    {
                        "title": "测试标题2", 
                        "absContent": "这是抽象内容2",
                        "url":"https://example.com/doc002",
                        "source":"测试来源2",
                        "score": "0.85",
                        "docId": "doc002"
                    }
                ]
            }
        }
        
        results = search_tool._parse_response(mock_response)
        print(f"✅ 响应解析测试通过 - 解析了 {len(results)} 个结果")
        
        return True
        
    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        return False

def test_mock_service():
    """测试Mock服务"""
    print("\n🏥 测试Mock服务连接...")
    
    try:
        # 检查健康状态
        health_response = requests.get("http://localhost:8010/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Mock服务健康检查通过")
        else:
            print(f"❌ Mock服务健康检查失败: {health_response.status_code}")
            return False
            
        # 测试搜索API
        search_payload = {
            "REQ_HEAD": {"TRANS_PROCESS": "", "TRAN_ID": ""},
            "REQ_BODY": {
                "param": {
                    "messages": [{"content": "测试查询", "role": "user"}],
                    "repository": "test-repo",
                    "param": {"channelId": "0"}
                },
                "muwpUser": {}
            }
        }
        
        search_response = requests.post(
            "http://localhost:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do",
            json=search_payload,
            timeout=10
        )
        
        if search_response.status_code == 200:
            data = search_response.json()
            if data.get("RSP_HEAD", {}).get("TRAN_SUCCESS") == "1":
                results = data.get("RSP_BODY", {}).get("result", [])
                print(f"✅ Mock服务搜索测试通过 - 返回 {len(results)} 个结果")
                return True
            else:
                print(f"❌ Mock服务返回错误: {data}")
        else:
            print(f"❌ Mock服务搜索失败: HTTP {search_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Mock服务")
        print("   请启动Mock服务: cd middlewares/search && python mock_search_api.py")
    except Exception as e:
        print(f"❌ Mock服务测试失败: {e}")
    
    return False

def test_search_integration():
    """测试搜索集成"""
    print("\n🔗 测试搜索集成...")
    
    os.environ["CUSTOM_SEARCH_API_URL"] = "http://localhost:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do"
    
    try:
        search_tool = get_custom_search_tool(max_results=3)
        
        # 执行实际搜索
        results = search_tool._run("规章制度")
        
        if results and len(results) > 0:
            print(f"✅ 搜索集成测试通过 - 找到 {len(results)} 个结果")
            
            # 显示结果
            for i, result in enumerate(results[:2], 1):
                print(f"\n结果 {i}:")
                print(f"  标题: {result.get('title', '无标题')}")
                print(f"  来源: {result.get('source', '未知')}")
                print(f"  评分: {result.get('score', 0)}")
                content = result.get('content', '')
                if content:
                    preview = content[:80] + "..." if len(content) > 80 else content
                    print(f"  内容: {preview}")
            
            return True
        else:
            print("❌ 搜索集成测试失败 - 未返回结果")
            
    except Exception as e:
        print(f"❌ 搜索集成测试失败: {e}")
    
    return False

def main():
    """主测试函数"""
    print("🚀 开始简化版自定义搜索工具测试...\n")
    
    tests = [
        ("基本功能", test_basic_functionality),
        ("Mock服务", test_mock_service),
        ("搜索集成", test_search_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"{'='*50}")
        print(f"🧪 运行测试: {test_name}")
        print(f"{'='*50}")
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 测试结果汇总")
    print(f"{'='*50}")
    print(f"总测试数: {total}")
    print(f"通过数: {passed}")
    print(f"失败数: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试都通过了!")
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败")
        if passed == 1:  # 只有基本功能通过
            print("💡 提示: 请启动Mock服务进行完整测试")
            print("   cd middlewares/search && python mock_search_api.py")

if __name__ == "__main__":
    main()