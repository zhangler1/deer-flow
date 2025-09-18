#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试自定义搜索工具
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 直接导入custom_search模块
import sys
sys.path.insert(0, str(project_root / "src" / "tools"))
from custom_search import get_custom_search_tool

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_custom_search():
    """测试自定义搜索工具"""
    print("🔍 测试自定义搜索工具...")
    
    # 设置测试用的API URL（使用本地mock服务）
    os.environ["CUSTOM_SEARCH_API_URL"] = "http://localhost:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do"
    
    try:
        # 创建搜索工具实例
        search_tool = get_custom_search_tool(max_results=5)
        
        # 测试查询
        test_queries = [
            "规章制度"
        ]
        
        for query in test_queries:
            print(f"\n📝 测试查询: {query}")
            print("-" * 50)
            
            # 执行搜索
            results = search_tool._run(query)
            
            if results:
                print(f"✅ 找到 {len(results)} 个结果:")
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. {result.get('title', '无标题')}")
                    print(f"   来源: {result.get('source', '未知')}")
                    print(f"   评分: {result.get('score', 0)}")
                    content = result.get('content', '')
                    if content:
                        # 截取前100个字符显示
                        preview = content[:100] + "..." if len(content) > 100 else content
                        print(f"   内容: {preview}")
            else:
                print("❌ 未找到结果")
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    
    print("\n✅ 测试完成!")
    return True

def test_api_format():
    """测试API请求格式"""
    print("\n🔧 测试API请求格式...")
    
    # 设置环境变量
    os.environ["CUSTOM_SEARCH_API_URL"] = "http://localhost:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do"
    
    try:
        search_tool = get_custom_search_tool()
        
        # 打印工具配置
        print(f"API URL: {search_tool.api_url}")
        print(f"Repository: {search_tool.repository}")
        print(f"Channel ID: {search_tool.channel_id}")
        print(f"Max Results: {search_tool.max_results}")
        
        # 测试构建请求参数
        query = "测试查询"
        print(f"\n🔨 构建查询参数: {query}")
        
        # 模拟构建请求（不实际发送）
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "User-Agent": "DeerFlow-SearchTool/1.0.0",
            "jumpCloud-Env": "BASE"
        }
        
        payload = {
            "REQ_HEAD": {
                "TRANS_PROCESS": "",
                "TRAN_ID": ""
            },
            "REQ_BODY": {
                "param": {
                    "messages": [
                        {
                            "content": query,
                            "role": "user"
                        }
                    ],
                    "repository": search_tool.repository,
                    "param": {
                        "channelId": search_tool.channel_id
                    }
                },
                "muwpUser": search_tool.muwp_user
            }
        }
        
        print("📋 请求头:")
        for key, value in headers.items():
            print(f"  {key}: {value}")
        
        print("\n📋 请求体:")
        import json
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"❌ 格式测试失败: {e}")
        return False
    
    print("\n✅ 格式测试完成!")
    return True

if __name__ == "__main__":
    print("🚀 开始测试自定义搜索工具...")
    
    # 运行格式测试
    test_api_format()
    
    # 提示启动mock服务
    print("\n💡 要进行完整测试，请先启动mock搜索服务:")
    print("   cd middlewares/search")
    print("   python mock_search_api.py")
    print("\n⏳ 如果mock服务已启动，按回车键继续测试...")
    input()
    
    # 运行搜索测试
    test_custom_search()

def test_error_handling():
    """测试错误处理机制"""
    print("\n⚠️ 测试错误处理机制...")
    
    # 测试无效API URL
    os.environ["CUSTOM_SEARCH_API_URL"] = "http://invalid-url:9999/api"
    
    try:
        search_tool = get_custom_search_tool(max_results=3)
        results = search_tool._run("测试查询")
        
        # 应该返回错误提示
        if results and len(results) > 0:
            first_result = results[0]
            if "错误" in first_result.get("title", "") or "错误" in first_result.get("content", ""):
                print("✅ 错误处理正常 - 返回了错误提示")
            else:
                print("❌ 错误处理异常 - 未返回预期的错误提示")
        else:
            print("❌ 错误处理异常 - 未返回任何结果")
            
    except Exception as e:
        print(f"✅ 错误处理正常 - 抛出了预期异常: {e}")
    
    print("✅ 错误处理测试完成!")

def test_environment_variables():
    """测试环境变量配置"""
    print("\n🔧 测试环境变量配置...")
    
    # 保存原始环境变量
    original_vars = {}
    env_vars = [
        "CUSTOM_SEARCH_API_URL",
        "CUSTOM_SEARCH_REPOSITORY", 
        "CUSTOM_SEARCH_CHANNEL_ID",
        "MUWP_BRANCH_ID",
        "MUWP_LOGIN_NAME",
        "MUWP_USER_CODE",
        "MUWP_USER_NAME",
        "MUWP_USER_ID"
    ]
    
    for var in env_vars:
        original_vars[var] = os.environ.get(var)
    
    try:
        # 设置测试用环境变量
        test_config = {
            "CUSTOM_SEARCH_API_URL": "http://localhost:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do",
            "CUSTOM_SEARCH_REPOSITORY": "test-repository",
            "CUSTOM_SEARCH_CHANNEL_ID": "999",
            "MUWP_BRANCH_ID": "test-branch",
            "MUWP_LOGIN_NAME": "test-user",
            "MUWP_USER_CODE": "12345",
            "MUWP_USER_NAME": "测试用户",
            "MUWP_USER_ID": "67890"
        }
        
        for key, value in test_config.items():
            os.environ[key] = value
        
        # 创建搜索工具并检查配置
        search_tool = get_custom_search_tool()
        
        print(f"✅ API URL: {search_tool.api_url}")
        print(f"✅ Repository: {search_tool.repository}")
        print(f"✅ Channel ID: {search_tool.channel_id}")
        print(f"✅ User Info: {search_tool.muwp_user}")
        
        # 验证配置是否正确加载
        assert search_tool.api_url == test_config["CUSTOM_SEARCH_API_URL"]
        assert search_tool.repository == test_config["CUSTOM_SEARCH_REPOSITORY"]
        assert search_tool.channel_id == test_config["CUSTOM_SEARCH_CHANNEL_ID"]
        assert search_tool.muwp_user["muwp_branchID"] == test_config["MUWP_BRANCH_ID"]
        
        print("✅ 环境变量配置测试通过!")
        
    finally:
        # 恢复原始环境变量
        for var, original_value in original_vars.items():
            if original_value is not None:
                os.environ[var] = original_value
            elif var in os.environ:
                del os.environ[var]

def test_response_parsing():
    """测试响应解析功能"""
    print("\n📊 测试响应解析功能...")
    
    # 设置API URL
    os.environ["CUSTOM_SEARCH_API_URL"] = "http://localhost:8010/ELLM.ELLM-OFFICE.V-1.0/querySources.do"
    
    try:
        search_tool = get_custom_search_tool(max_results=5)
        
        # 创建模拟响应数据
        mock_response = {
            "RSP_HEAD": {
                "TRAN_SUCCESS": "1",
                "TRACE_NO": "test-trace"
            },
            "RSP_BODY": {
                "result": [
                    {
                        "title": "测试标题1",
                        "content": "这是测试内容1",
                        "source": "测试来源1",
                        "score": "0.95",
                        "docId": "doc001",
                        "repository": "test-repo",
                        "createTime": "2024-01-01",
                        "fullCategoryName": "测试分类",
                        "fullOrgName": "测试组织"
                    },
                    {
                        "title": "测试标题2",
                        "absContent": "这是抽象内容2",  # 测试absContent回退
                        "source": "测试来源2", 
                        "score": "0.85",
                        "docId": "doc002"
                    },
                    {
                        "title": "",  # 空标题
                        "content": "",  # 空内容
                        "source": "应该被过滤的结果"
                    }
                ]
            }
        }
        
        # 测试解析功能
        results = search_tool._parse_response(mock_response)
        
        print(f"解析结果数量: {len(results)}")
        
        # 验证解析结果
        assert len(results) == 2, f"期望2个结果，实际得到{len(results)}个"
        
        # 验证第一个结果
        result1 = results[0]
        assert result1["title"] == "测试标题1"
        assert result1["content"] == "这是测试内容1"
        assert result1["score"] == 0.95
        assert "category" in result1
        assert "organization" in result1
        
        # 验证第二个结果（absContent回退）
        result2 = results[1]
        assert result2["title"] == "测试标题2"
        assert result2["content"] == "这是抽象内容2"  # 应该使用absContent
        assert result2["score"] == 0.85
        
        # 验证结果按分数排序（降序）
        assert results[0]["score"] >= results[1]["score"]
        
        print("✅ 响应解析测试通过!")
        
        # 显示解析结果
        for i, result in enumerate(results, 1):
            print(f"\n结果 {i}:")
            print(f"  标题: {result['title']}")
            print(f"  内容: {result['content'][:50]}...")
            print(f"  分数: {result['score']}")
            print(f"  来源: {result['source']}")
            
    except Exception as e:
        print(f"❌ 响应解析测试失败: {e}")
        return False
    
    return True

def test_mock_service_health():
    """测试Mock服务健康状态"""
    print("\n🏥 测试Mock服务健康状态...")
    
    try:
        import requests
        
        # 测试健康检查端点
        health_url = "http://localhost:8010/health"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print("✅ Mock服务运行正常")
                return True
            else:
                print(f"❌ Mock服务状态异常: {data}")
        else:
            print(f"❌ Mock服务健康检查失败: HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Mock服务，请确保服务已启动")
        print("   启动命令: cd middlewares/search && python mock_search_api.py")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
    
    return False

def run_comprehensive_test():
    """运行全面的测试套件"""
    print("\n🧪 开始运行全面测试套件...")
    
    tests = [
        ("环境变量配置", test_environment_variables),
        ("API请求格式", test_api_format),
        ("响应解析", test_response_parsing),
        ("错误处理", test_error_handling),
        ("Mock服务健康", test_mock_service_health),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🔍 正在运行: {test_name}")
        print(f"{'='*60}")
        
        try:
            result = test_func()
            if result is not False:  # None 或 True 都算通过
                passed += 1
                print(f"\n✅ {test_name} - 通过")
            else:
                print(f"\n❌ {test_name} - 失败")
        except Exception as e:
            print(f"\n❌ {test_name} - 异常: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 测试结果汇总")
    print(f"{'='*60}")
    print(f"总测试数: {total}")
    print(f"通过数: {passed}")
    print(f"失败数: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试都通过了!")
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查相关配置")
    
    return passed == total

if __name__ == "__main__":
    print("🚀 开始测试自定义搜索工具...")
    print(f"\n\033[32m项目路径:\033[0m {project_root}")
    print(f"\033[35mPython路径:\033[0m {sys.path[0]}")
    
    # 检查是否要运行全面测试
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--comprehensive":
        print("\n🧪 运行全面测试模式...")
        run_comprehensive_test()
    else:
        # 运行基础测试
        print("\n📝 运行基础测试模式...")
        print("💡 使用 --comprehensive 参数运行全面测试")
        
        # 运行格式测试
        test_api_format()
        
        # 检查Mock服务状态
        if not test_mock_service_health():
            print("\n💡 要进行完整测试，请先启动mock搜索服务:")
            print("   \033[32mcd middlewares/search\033[0m")
            print("   \033[35mpython mock_search_api.py\033[0m")
            print("\n⏳ 如果mock服务已启动，按回车键继续测试...")
            input()
        else:
            print("\n✅ Mock服务已就绪，继续测试...")
        
        # 运行搜索测试
        test_custom_search()
        
        print("\n🎯 基础测试完成!")
        print("💡 运行 'python test_custom_search.py --comprehensive' 进行全面测试")