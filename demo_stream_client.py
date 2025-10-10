#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版本的流式接口测试客户端
演示增强日志和流式输出效果
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any


async def test_simple_stream():
    """测试流式简化研究接口"""
    
    # 简单的测试请求
    request_data = {
        "messages": [
            {
                "role": "user",
                "content": "什么是大语言模型？它有哪些应用？"
            }
        ],
        "max_search_results": 2,
        "search_engine": "custom_search",
        "enable_deep_thinking": False,
        "max_thinking_iterations": 1,
        "max_recursion_limit": 10
    }
    
    print("🧪 DeerFlow 流式研究接口演示")
    print("=" * 60)
    print(f"📝 测试问题: {request_data['messages'][0]['content']}")
    print("-" * 60)
    
    start_time = time.time()
    event_count = 0
    
    try:
        timeout = aiohttp.ClientTimeout(total=60)  # 60秒超时
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "http://localhost:8000/api/research/simple/stream",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ 请求失败: HTTP {response.status}")
                    print(f"错误详情: {error_text}")
                    return
                
                print("✅ 流式连接建立成功，开始接收事件...")
                print("-" * 60)
                
                current_event_type = "unknown"
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if not line_str:
                        continue
                        
                    if line_str.startswith('event:'):
                        current_event_type = line_str[6:].strip()
                        continue
                        
                    elif line_str.startswith('data:'):
                        try:
                            data_json = line_str[5:].strip()
                            data = json.loads(data_json)
                            event_count += 1
                            
                            # 显示事件
                            show_event(current_event_type, data, event_count)
                            
                        except json.JSONDecodeError as e:
                            print(f"⚠️  JSON解析错误: {e}")
                            print(f"   原始数据: {line_str}")
                
                total_time = time.time() - start_time
                print("-" * 60)
                print(f"🎉 流式演示完成!")
                print(f"📊 总事件数: {event_count}")
                print(f"⏱️  总耗时: {total_time:.2f}s")
                
    except asyncio.TimeoutError:
        print("❌ 请求超时")
    except aiohttp.ClientError as e:
        print(f"❌ 网络连接错误: {e}")
    except Exception as e:
        print(f"❌ 未预期错误: {e}")


def show_event(event_type: str, data: Dict[str, Any], event_number: int):
    """显示流式事件"""
    timestamp = time.strftime("%H:%M:%S")
    
    if event_type == "start":
        print(f"🟢 [{timestamp}] #{event_number:02d} 开始事件")
        print(f"    📋 对话ID: {data.get('conversation_id', 'N/A')}")
        print(f"    ❓ 问题: {data.get('question', 'N/A')[:50]}...")
        
    elif event_type == "thinking_start":
        print(f"🧠 [{timestamp}] #{event_number:02d} 开始思考")
        print(f"    🤖 模型: {data.get('model_type', 'N/A')}")
        
    elif event_type == "thinking_iteration":
        iteration = data.get('iteration', 0)
        total = data.get('total_iterations', 0)
        print(f"🔄 [{timestamp}] #{event_number:02d} 思考迭代 {iteration}/{total}")
        
    elif event_type == "search_start":
        print(f"🔍 [{timestamp}] #{event_number:02d} 开始搜索")
        print(f"    🔎 查询: {data.get('query', 'N/A')}")
        print(f"    🌐 引擎: {data.get('engine', 'N/A')}")
        
    elif event_type == "search_results":
        count = data.get('results_count', 0)
        duration = data.get('duration', 0)
        print(f"📊 [{timestamp}] #{event_number:02d} 搜索结果")
        print(f"    📈 找到 {count} 条结果, 耗时 {duration:.2f}s")
        
    elif event_type == "answer_generation_start":
        has_context = data.get('has_search_context', False)
        print(f"💬 [{timestamp}] #{event_number:02d} 开始生成回答")
        print(f"    📚 使用搜索上下文: {'是' if has_context else '否'}")
        
    elif event_type == "answer_chunk":
        content = data.get('content', '')
        print(f"📝 [{timestamp}] #{event_number:02d} 回答内容")
        # 显示回答的前几行
        lines = content.split('\\n')[:3]
        for i, line in enumerate(lines):
            if line.strip():
                print(f"    💬 {line.strip()[:80]}{'...' if len(line) > 80 else ''}")
        if len(content.split('\\n')) > 3:
            print(f"    ... (共 {len(content)} 字符)")
            
    elif event_type == "complete":
        print(f"✅ [{timestamp}] #{event_number:02d} 完成")
        print(f"    🎯 会话ID: {data.get('conversation_id', 'N/A')}")
        print(f"    🧮 思考步骤: {data.get('thinking_steps', 0)}")
        print(f"    ⏱️  执行时间: {data.get('execution_time', 0):.2f}s")
        print(f"    🔗 来源数量: {len(data.get('sources', []))}")
        if data.get('sources'):
            print(f"    📚 参考来源: {', '.join(data['sources'][:2])}{'...' if len(data['sources']) > 2 else ''}")
            
    elif event_type == "error":
        print(f"❌ [{timestamp}] #{event_number:02d} 错误")
        print(f"    🚨 {data.get('error', 'N/A')}")
        
    elif event_type == "thinking_error":
        print(f"⚠️  [{timestamp}] #{event_number:02d} 思考错误")
        print(f"    📈 迭代 {data.get('iteration', 0)}")
        print(f"    🚨 {data.get('error', 'N/A')}")
        
    else:
        print(f"🔵 [{timestamp}] #{event_number:02d} {event_type}")
        print(f"    📄 {json.dumps(data, ensure_ascii=False)[:100]}...")


async def main():
    """主函数"""
    print("检查服务器是否运行在 http://localhost:8000")
    
    try:
        # 先检查服务器是否在线
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/config") as response:
                if response.status == 200:
                    print("✅ 服务器在线")
                else:
                    print(f"⚠️  服务器响应异常: HTTP {response.status}")
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        print("请确保服务器已启动:")
        print("   cd /home/llm/zhangle/deer-flow")
        print("   python -m uvicorn src.server.app:app --reload --host 0.0.0.0 --port 8000")
        return
    
    # 运行流式测试
    await test_simple_stream()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n👋 测试被用户中断")
    except Exception as e:
        print(f"\\n❌ 测试失败: {e}")