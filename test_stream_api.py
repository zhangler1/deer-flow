#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新增的流式研究接口
验证增强日志和流式输出功能
"""

import asyncio
import aiohttp
import json
import time
from typing import AsyncGenerator


async def test_stream_research_api():
    """测试流式研究API"""
    
    # 测试请求数据
    test_request = {
        "messages": [
            {
                "role": "user",
                "content": "请帮我研究一下2024年人工智能大模型的最新发展趋势"
            }
        ],
        "max_search_results": 3,
        "search_engine": "custom_search",
        "enable_deep_thinking": True,
        "max_thinking_iterations": 2,
        "max_recursion_limit": 15
    }
    
    print("🚀 开始测试流式研究接口...")
    print(f"📝 测试问题: {test_request['messages'][0]['content']}")
    print("-" * 80)
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/research/simple/stream",
                json=test_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    print(f"❌ 请求失败: HTTP {response.status}")
                    print(f"错误信息: {await response.text()}")
                    return
                
                print("✅ 流式连接已建立，开始接收事件...")
                print("-" * 80)
                
                event_count = 0
                event_type = "unknown"  # 初始化事件类型
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('event:'):
                        event_type = line[6:].strip()
                        continue
                    elif line.startswith('data:'):
                        try:
                            data_json = line[5:].strip()
                            data = json.loads(data_json)
                            event_count += 1
                            
                            # 根据事件类型处理输出
                            await handle_stream_event(event_type, data, event_count)
                            
                        except json.JSONDecodeError as e:
                            print(f"⚠️  JSON解析错误: {e}")
                            print(f"原始数据: {line}")
                
                total_time = time.time() - start_time
                print("-" * 80)
                print(f"🎉 流式测试完成!")
                print(f"📊 总事件数: {event_count}")
                print(f"⏱️  总耗时: {total_time:.2f}s")
                
    except aiohttp.ClientError as e:
        print(f"❌ 网络连接错误: {e}")
    except Exception as e:
        print(f"❌ 未预期错误: {e}")


async def handle_stream_event(event_type: str, data: dict, event_number: int):
    """处理流式事件"""
    timestamp = time.strftime("%H:%M:%S")
    
    if event_type == "start":
        print(f"🟢 [{timestamp}] #{event_number} 开始事件")
        print(f"   📋 对话ID: {data.get('conversation_id', 'N/A')}")
        print(f"   ❓ 问题: {data.get('question', 'N/A')}")
        
    elif event_type == "thinking_start":
        print(f"🧠 [{timestamp}] #{event_number} 开始思考")
        print(f"   🔧 模型类型: {data.get('model_type', 'N/A')}")
        
    elif event_type == "thinking_iteration":
        print(f"🔄 [{timestamp}] #{event_number} 思考迭代")
        print(f"   📈 进度: {data.get('iteration', 0)}/{data.get('total_iterations', 0)}")
        
    elif event_type == "search_start":
        print(f"🔍 [{timestamp}] #{event_number} 开始搜索")
        print(f"   🔎 查询: {data.get('query', 'N/A')}")
        print(f"   🌐 引擎: {data.get('engine', 'N/A')}")
        
    elif event_type == "search_results":
        print(f"📊 [{timestamp}] #{event_number} 搜索结果")
        print(f"   📈 结果数: {data.get('results_count', 0)}")
        print(f"   ⏱️  耗时: {data.get('duration', 0):.2f}s")
        sources = data.get('sources', [])
        if sources:
            print(f"   🔗 来源: {', '.join(sources[:2])}{'...' if len(sources) > 2 else ''}")
            
    elif event_type == "answer_generation_start":
        print(f"💬 [{timestamp}] #{event_number} 开始生成回答")
        has_context = data.get('has_search_context', False)
        print(f"   📚 搜索上下文: {'是' if has_context else '否'}")
        
    elif event_type == "answer_chunk":
        print(f"📝 [{timestamp}] #{event_number} 回答内容")
        content = data.get('content', '')
        # 显示前100个字符
        preview = content[:100] + "..." if len(content) > 100 else content
        print(f"   💬 内容预览: {preview}")
        
    elif event_type == "complete":
        print(f"✅ [{timestamp}] #{event_number} 完成事件")
        print(f"   🎯 对话ID: {data.get('conversation_id', 'N/A')}")
        print(f"   🧮 思考步骤: {data.get('thinking_steps', 0)}")
        print(f"   ⏱️  执行时间: {data.get('execution_time', 0):.2f}s")
        print(f"   🔗 来源数量: {len(data.get('sources', []))}")
        
    elif event_type == "error":
        print(f"❌ [{timestamp}] #{event_number} 错误事件")
        print(f"   🚨 错误: {data.get('error', 'N/A')}")
        
    elif event_type == "thinking_error":
        print(f"⚠️  [{timestamp}] #{event_number} 思考错误")
        print(f"   📈 迭代: {data.get('iteration', 0)}")
        print(f"   🚨 错误: {data.get('error', 'N/A')}")
        
    else:
        print(f"🔵 [{timestamp}] #{event_number} 未知事件: {event_type}")
        print(f"   📄 数据: {json.dumps(data, ensure_ascii=False)[:200]}...")


async def test_compare_apis():
    """对比测试原始API和流式API"""
    print("\n" + "="*80)
    print("🔄 开始对比测试原始API和流式API")
    print("="*80)
    
    test_question = "什么是大语言模型？"
    
    # 测试原始API
    print(f"1️⃣  测试原始API: /api/research/simple")
    await test_original_api(test_question)
    
    print("\n" + "-"*80)
    
    # 测试流式API  
    print(f"2️⃣  测试流式API: /api/research/simple/stream")
    await test_stream_api_simple(test_question)


async def test_original_api(question: str):
    """测试原始同步API"""
    request_data = {
        "messages": [{"role": "user", "content": question}],
        "max_search_results": 2,
        "search_engine": "custom_search", 
        "enable_deep_thinking": False,
        "max_thinking_iterations": 1
    }
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/research/simple",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    duration = time.time() - start_time
                    
                    print(f"✅ 原始API响应成功")
                    print(f"⏱️  耗时: {duration:.2f}s")
                    print(f"📝 回答长度: {len(result.get('choices', [{}])[0].get('message', {}).get('content', ''))}")
                    print(f"🔗 来源数量: {len(result.get('sources', []))}")
                    print(f"🧮 思考步骤: {result.get('thinking_steps', 0)}")
                else:
                    print(f"❌ 原始API失败: HTTP {response.status}")
                    
    except Exception as e:
        print(f"❌ 原始API错误: {e}")


async def test_stream_api_simple(question: str):
    """测试流式API (简化版)"""
    request_data = {
        "messages": [{"role": "user", "content": question}],
        "max_search_results": 2,
        "search_engine": "custom_search",
        "enable_deep_thinking": False, 
        "max_thinking_iterations": 1
    }
    
    start_time = time.time()
    event_count = 0
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/research/simple/stream",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('event:') or line.startswith('data:'):
                            event_count += 1
                    
                    duration = time.time() - start_time
                    print(f"✅ 流式API响应成功")
                    print(f"⏱️  耗时: {duration:.2f}s")
                    print(f"📊 事件数量: {event_count}")
                else:
                    print(f"❌ 流式API失败: HTTP {response.status}")
                    
    except Exception as e:
        print(f"❌ 流式API错误: {e}")


if __name__ == "__main__":
    print("🧪 DeerFlow 流式研究接口测试")
    print("="*80)
    
    # 首先进行完整的流式测试
    asyncio.run(test_stream_research_api())
    
    # 然后进行对比测试
    asyncio.run(test_compare_apis())