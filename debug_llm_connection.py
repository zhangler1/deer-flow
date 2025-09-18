#!/usr/bin/env python3
"""
调试 DeerFlow LLM 连接的详细脚本
模拟项目中的实际连接过程
"""

import os
import sys
import httpx
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_yaml_config
from src.llms.llm import _get_llm_type_config_keys, _get_env_llm_conf, _create_llm_use_conf
from langchain_openai import ChatOpenAI

def debug_config_loading():
    """调试配置加载过程"""
    print("\033[32m=== 1. 配置加载调试 ===\033[0m")
    
    config_path = Path(__file__).parent / "conf.yaml"
    print(f"\033[35m配置文件路径:\033[0m {config_path}")
    print(f"\033[35m配置文件存在:\033[0m {config_path.exists()}")
    
    try:
        conf = load_yaml_config(str(config_path))
        print(f"\033[35m配置加载成功:\033[0m {bool(conf)}")
        
        basic_model_conf = conf.get("BASIC_MODEL", {})
        print(f"\033[35mBASIC_MODEL配置:\033[0m")
        for key, value in basic_model_conf.items():
            if key == 'api_key':
                print(f"  {key}: {value[:10]}...***")
            else:
                print(f"  {key}: {value}")
                
        return conf
    except Exception as e:
        print(f"\033[35m配置加载失败:\033[0m {e}")
        return {}

def debug_environment_variables():
    """调试环境变量"""
    print("\n\033[32m=== 2. 环境变量调试 ===\033[0m")
    
    env_conf = _get_env_llm_conf("basic")
    print(f"\033[35m环境变量配置:\033[0m {env_conf}")
    
    # 检查相关的环境变量
    relevant_vars = [
        "BASIC_MODEL__base_url", "BASIC_MODEL__api_key", "BASIC_MODEL__model",
        "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"
    ]
    
    print("\033[35m相关环境变量:\033[0m")
    for var in relevant_vars:
        value = os.getenv(var, "未设置")
        if "api_key" in var.lower() and value != "未设置":
            value = f"{value[:10]}...***"
        print(f"  {var}: {value}")

def debug_merged_config(conf):
    """调试合并后的配置"""
    print("\n\033[32m=== 3. 合并配置调试 ===\033[0m")
    
    try:
        llm_conf = conf.get("BASIC_MODEL", {})
        env_conf = _get_env_llm_conf("basic")
        merged_conf = {**llm_conf, **env_conf}
        
        print(f"\033[35m合并后的配置:\033[0m")
        for key, value in merged_conf.items():
            if key == 'api_key':
                print(f"  {key}: {value[:10]}...***")
            else:
                print(f"  {key}: {value}")
                
        return merged_conf
    except Exception as e:
        print(f"\033[35m配置合并失败:\033[0m {e}")
        return {}

def debug_http_client_creation(merged_conf):
    """调试HTTP客户端创建"""
    print("\n\033[32m=== 4. HTTP客户端创建调试 ===\033[0m")
    
    verify_ssl = merged_conf.get("verify_ssl", True)
    print(f"\033[35mSSL验证设置:\033[0m {verify_ssl}")
    
    if not verify_ssl:
        print("\033[35m创建自定义HTTP客户端 (禁用SSL验证)\033[0m")
        http_client = httpx.Client(verify=False)
        http_async_client = httpx.AsyncClient(verify=False)
        print(f"\033[35mHTTP客户端创建成功:\033[0m {type(http_client)}")
        print(f"\033[35m异步HTTP客户端创建成功:\033[0m {type(http_async_client)}")
        return http_client, http_async_client
    else:
        print("\033[35m使用默认HTTP客户端 (启用SSL验证)\033[0m")
        return None, None

def debug_chatopen_ai_creation(merged_conf):
    """调试ChatOpenAI实例创建"""
    print("\n\033[32m=== 5. ChatOpenAI实例创建调试 ===\033[0m")
    
    try:
        # 复制配置以避免修改原始配置
        chat_conf = merged_conf.copy()
        
        # 处理SSL验证
        verify_ssl = chat_conf.pop("verify_ssl", True)
        if not verify_ssl:
            http_client = httpx.Client(verify=False)
            http_async_client = httpx.AsyncClient(verify=False)
            chat_conf["http_client"] = http_client
            chat_conf["http_async_client"] = http_async_client
        
        print(f"\033[35m最终传递给ChatOpenAI的参数:\033[0m")
        for key, value in chat_conf.items():
            if key == 'api_key':
                print(f"  {key}: {value[:10]}...***")
            elif key in ['http_client', 'http_async_client']:
                print(f"  {key}: {type(value)}")
            else:
                print(f"  {key}: {value}")
        
        # 创建ChatOpenAI实例
        llm = ChatOpenAI(**chat_conf)
        print(f"\033[35mChatOpenAI实例创建成功:\033[0m {type(llm)}")
        
        return llm
        
    except Exception as e:
        print(f"\033[35mChatOpenAI实例创建失败:\033[0m {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_direct_http_request(merged_conf):
    """调试直接HTTP请求"""
    print("\n\033[32m=== 6. 直接HTTP请求调试 ===\033[0m")
    
    base_url = merged_conf.get("base_url")
    api_key = merged_conf.get("api_key")
    model = merged_conf.get("model")
    verify_ssl = merged_conf.get("verify_ssl", True)
    
    if not base_url:
        print("\033[35m错误: 缺少base_url配置\033[0m")
        return
        
    url = f"{base_url}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello, this is a test"}],
        "max_tokens": 100
    }
    
    print(f"\033[35m请求URL:\033[0m {url}")
    print(f"\033[35m请求头:\033[0m Authorization: Bearer {api_key[:10]}...***")
    print(f"\033[35m请求体:\033[0m {json.dumps(payload, indent=2)}")

    
    try:
        with httpx.Client() as client:
            print("\033[35m发送HTTP请求...\033[0m")
            response = client.post(url, headers=headers, json=payload)
            
            print(f"\033[35m响应状态码:\033[0m {response.status_code}")
            print(f"\033[35m响应头:\033[0m {dict(response.headers)}")
            
            if response.status_code == 200:
                print(f"\033[35m响应成功!\033[0m")
                result = response.json()
                print(f"\033[35m响应内容:\033[0m {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"\033[35m响应失败:\033[0m {response.text}")
                
    except Exception as e:
        print(f"\033[35mHTTP请求失败:\033[0m {e}")
        import traceback
        traceback.print_exc()

def debug_langchain_request(llm):
    """调试LangChain请求"""
    print("\n\033[32m=== 7. LangChain请求调试 ===\033[0m")
    
    if not llm:
        print("\033[35m跳过: LLM实例未创建成功\033[0m")
        return
        
    try:
        print("\033[35m通过LangChain发送请求...\033[0m")
        response = llm.invoke("Hello, this is a test via LangChain")
        print(f"\033[35mLangChain请求成功!\033[0m")
        print(f"\033[35m响应内容:\033[0m {response.content}")
        
    except Exception as e:
        print(f"\033[35mLangChain请求失败:\033[0m {e}")
        import traceback
        traceback.print_exc()

def main():
    """主调试函数"""
    print("\033[32m🔍 DeerFlow LLM连接调试脚本\033[0m")
    print("\033[32m=" * 50 + "\033[0m")
    
    # 1. 配置加载
    conf = debug_config_loading()
    if not conf:
        print("\033[35m❌ 配置加载失败，终止调试\033[0m")
        return
    
    # 2. 环境变量
    debug_environment_variables()
    
    # 3. 合并配置
    merged_conf = debug_merged_config(conf)
    if not merged_conf:
        print("\033[35m❌ 配置合并失败，终止调试\033[0m")
        return
    
    # 4. HTTP客户端创建
    debug_http_client_creation(merged_conf)
    
    # 5. ChatOpenAI实例创建
    llm = debug_chatopen_ai_creation(merged_conf)
    
    # 6. 直接HTTP请求
    debug_direct_http_request(merged_conf)
    
    # 7. LangChain请求
    debug_langchain_request(llm)
    
    print("\n\033[32m🎯 调试完成!\033[0m")

if __name__ == "__main__":
    main()