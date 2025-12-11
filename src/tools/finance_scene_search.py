# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
金融领域知识搜索工具

通过调用金融知识库API，根据不同场景（spaceCodeList）获取专业知识。
支持多个场景：
- SP0000010: 场景1
- SP0000001: 场景2
- 其他场景...
"""

import logging
import requests
import json
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


class DomainFinSearchConfig:
    """金融领域知识搜索配置"""
    
    # API 配置
    BASE_URL = "http://12.244.113.82/EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do"
    
    # 场景映射
    SCENES = {
        "default": ["SP0000010", "SP0000001"],  # 默认场景
        "banking": ["SP0000010"],  # 银行业务场景
        "investment": ["SP0000001"],  # 投资理财场景
        # 可以根据实际需要添加更多场景
    }
    
    # 请求头配置
    HEADERS = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
        "caller": "sjyh",
        "jumpcloud-ENV": "BASE"
    }
    
    # Cookie（如果需要的话，可以从环境变量读取）
    COOKIES = {
        "JSESSIONID": "BB89381BD34DD492A21B327864A184BE"
    }


def _build_request_body(
    keyword: str,
    space_codes: List[str] = None,
    user_code: str = "9857485",
    caller: str = "SXZSWD_JIAOXIN",
    vector_top_n: int = 6,
    text_top_n: int = 6,
    threshold: float = 0.1
) -> Dict[str, Any]:
    """构建请求体"""
    
    if space_codes is None:
        space_codes = DomainFinSearchConfig.SCENES["default"]
    
    req_body = {
        "REQ_HEAD": {},
        "REQ_BODY": {
            "param": {
                "keyword": keyword,
                "caller": caller,
                "userCode": user_code,
                "teamSpaceCodeList": [],
                "domainTagList": [],
                "searchType": "0",
                "spaceCodeList": space_codes,
                "qaType": ["1", "0", "2"],
                "customizedTagList": [],
                "vectorTopN": vector_top_n,
                "textTopN": text_top_n,
                "model": 0,
                "attachFlag": 1,
                "threshold": threshold,
                "publishedFlag": 0,
                "latestFlag": None,
                "delFlag": 0
            }
        }
    }
    
    return req_body


def call_domain_fin_search(
    keyword: str,
    scene: str = "default",
    space_codes: Optional[List[str]] = None,
    timeout: int = 30
) -> str:
    """
    调用金融领域知识搜索API
    
    Args:
        keyword: 搜索关键词
        scene: 场景类型 (default/banking/investment 等)
        space_codes: 自定义场景代码列表，如果提供则覆盖 scene 参数
        timeout: 超时时间（秒）
    
    Returns:
        str: API 返回的知识内容
    """
    try:
        # 确定要使用的场景代码
        if space_codes:
            selected_codes = space_codes
        else:
            selected_codes = DomainFinSearchConfig.SCENES.get(
                scene, 
                DomainFinSearchConfig.SCENES["default"]
            )
        
        logger.info(
            f"🔍 调用金融领域知识搜索 | 关键词: '{keyword}' | "
            f"场景: {scene} | SpaceCodes: {selected_codes}"
        )
        
        # 构建请求体
        request_body = _build_request_body(
            keyword=keyword,
            space_codes=selected_codes
        )
        
        # 将请求体转换为表单数据格式
        form_data = {
            "REQ_MESSAGE": json.dumps(request_body, ensure_ascii=False)
        }
        
        # 发送请求
        response = requests.post(
            DomainFinSearchConfig.BASE_URL,
            headers=DomainFinSearchConfig.HEADERS,
            cookies=DomainFinSearchConfig.COOKIES,
            data=form_data,
            timeout=timeout
        )
        
        # 检查响应状态
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        logger.info(f"✅ 金融领域知识搜索响应成功 | 状态码: {response.status_code}")
        
        # 提取知识内容
        knowledge_content = _extract_knowledge(result)
        
        return knowledge_content
        
    except requests.exceptions.Timeout:
        error_msg = f"金融领域知识搜索请求超时 (>{timeout}s)"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"
        
    except requests.exceptions.RequestException as e:
        error_msg = f"金融领域知识搜索请求失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"
        
    except Exception as e:
        error_msg = f"处理金融领域知识搜索响应时出错: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return f"错误: {error_msg}"


def _extract_knowledge(result: Dict[str, Any]) -> str:
    """从API响应中提取知识内容"""
    try:
        # 根据实际API响应结构提取知识
        # 这里需要根据真实的API响应格式进行调整
        
        if "RSP_BODY" in result and "data" in result["RSP_BODY"]:
            data = result["RSP_BODY"]["data"]
            
            # 如果是列表形式的知识条目
            if isinstance(data, list):
                knowledge_items = []
                for item in data:
                    # 提取标题和内容
                    title = item.get("title", "")
                    content = item.get("content", item.get("answer", ""))
                    score = item.get("score", "")
                    
                    if title and content:
                        knowledge_items.append(
                            f"【{title}】\n{content}\n(相关度: {score})"
                        )
                    elif content:
                        knowledge_items.append(content)
                
                if knowledge_items:
                    return "\n\n---\n\n".join(knowledge_items)
            
            # 如果是字典形式
            elif isinstance(data, dict):
                return json.dumps(data, ensure_ascii=False, indent=2)
        
        # 如果无法提取，返回原始结果
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"提取知识内容失败: {e}")
        return json.dumps(result, ensure_ascii=False, indent=2)


# ===== LangChain Tool 封装 =====

@tool
def domain_fin_search(
    keyword: str,
    scene: str = "default"
) -> str:
    """
    金融领域知识搜索工具
    
    调用金融知识库API，根据不同场景获取专业金融知识。
    
    Args:
        keyword: 要搜索的关键词或问题
        scene: 场景类型，可选值:
            - "default": 默认场景（银行业务+投资理财）
            - "banking": 银行业务场景
            - "investment": 投资理财场景
    
    Returns:
        str: 金融知识库返回的相关知识内容
    
    Examples:
        >>> domain_fin_search("信用卡申请条件", scene="banking")
        >>> domain_fin_search("理财产品收益率", scene="investment")
    """
    return call_domain_fin_search(keyword=keyword, scene=scene)


# 导出工具
__all__ = [
    "DomainFinSearchConfig",
    "call_domain_fin_search",
    "domain_fin_search",
]
