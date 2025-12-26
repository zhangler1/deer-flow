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

# Langfuse 集成 - v3 模式 (@observe 装饰器会自动捕获输入输出)
try:
    from langfuse import observe
except ImportError:
    logging.warning("Langfuse not installed. Tracing disabled.")
    
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return decorator

logger = logging.getLogger(__name__)


class DomainFinSearchConfig:
    """金融领域知识搜索配置"""
    
    # API 配置
    BASE_URL = "http://12.244.113.82/EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do"
    
    # 场景映射（子知识库ID - 每次只能查询一个）
    SCENES = {
        "default": ["SP0000010"],  # 默认场景：银行业务
        "banking": ["SP0000010"],  # 银行业务场景
        "investment": ["SP0000001"],  # 投资理财场景
        # 可以根据实际需要添加更多场景
    }
    
    # 团队ID配置
    TEAM_SPACE_CODE = "SP0000010"  # 默认团队ID
    
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
    team_space_code: str = None,
    user_code: str = "9857485",
    caller: str = "SXZSWD_JIAOXIN",
    vector_top_n: int = 6,
    text_top_n: int = 6,
    threshold: float = 0.1
) -> Dict[str, Any]:
    """构建请求体"""
    
    if space_codes is None:
        space_codes = DomainFinSearchConfig.SCENES["default"]
    
    if team_space_code is None:
        team_space_code = DomainFinSearchConfig.TEAM_SPACE_CODE
    
    req_body = {
        "REQ_HEAD": {},
        "REQ_BODY": {
            "param": {
                "keyword": keyword,
                "caller": caller,
                "userCode": user_code,
                "teamSpaceCodeList": [team_space_code],  # 团队ID
                "domainTagList": [],
                "searchType": "0",
                "spaceCodeList": space_codes,  # 子知识库ID列表
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


@observe(name="金融领域知识搜索函数API",as_type="tool")
def call_domain_fin_search(
    keyword: str,
    scene: str = "default",
    space_codes: Optional[List[str]] = None,
    timeout: int = 30
) -> List[Dict[str, Any]]:
    """
    调用金融领域知识搜索API
    
    Args:
        keyword: 搜索关键词
        scene: 场景类型 (default/banking/investment 等)
        space_codes: 自定义场景代码列表，如果提供则覆盖 scene 参数
        timeout: 超时时间（秒）
    
    Returns:
        List[Dict[str, Any]]: 结构化的搜索结果列表
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
        
        # 提取知识内容，返回结构化列表
        knowledge_results = _extract_knowledge(result)
        
        return knowledge_results
        
    except requests.exceptions.Timeout:
        error_msg = f"金融领域知识搜索请求超时 (>{timeout}s)"
        logger.error(f"❌ {error_msg}")
        return [{
            "title": "搜索错误",
            "content": error_msg,
            "score": 0.0,
            "url": "",
            "source": "system"
        }]
        
    except requests.exceptions.RequestException as e:
        error_msg = f"金融领域知识搜索请求失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return [{
            "title": "搜索错误",
            "content": error_msg,
            "score": 0.0,
            "url": "",
            "source": "system"
        }]
        
    except Exception as e:
        error_msg = f"处理金融领域知识搜索响应时出错: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return [{
            "title": "搜索错误",
            "content": error_msg,
            "score": 0.0,
            "url": "",
            "source": "system"
        }]


def _extract_knowledge(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 API 响应中提取知识内容，返回结构化列表"""
    try:
        # 根据实际 API 响应结构提取知识
        if "RSP_BODY" in result:
            rsp_body = result["RSP_BODY"]
            result_data = rsp_body.get("result", {})
            
            # 提取向量检索结果和文本检索结果
            vector_list = result_data.get("vectorGroupList", [])
            text_list = result_data.get("textGroupList", [])
            
            # 合并两种检索结果
            all_results = []
            for idx, item in enumerate(vector_list + text_list, 1):
                content = item.get("content", "")
                score = item.get("score", "")
                para_title = item.get("paraTitle", "")  # 提取段落标题
                
                if content:
                    # 转换为统一的结构化格式
                    all_results.append({
                        "title": para_title if para_title else f"结果 {idx}",
                        "content": content,
                        "score": float(score) if score else 0.0,
                        "url": "",  # 金融知识库通常没有URL
                        "source": "金融知识库"
                    })
            
            # 返回结果列表
            if all_results:
                return all_results
            else:
                return [{
                    "title": "未找到相关知识",
                    "content": "未能找到与查询相关的金融知识，请尝试使用不同的关键词。",
                    "score": 0.0,
                    "url": "",
                    "source": "system"
                }]
        
        # 如果无法提取，返回错误信息
        logger.warning("无法解析金融知识库响应格式")
        return [{
            "title": "解析错误",
            "content": "响应格式异常，请稍后重试。",
            "score": 0.0,
            "url": "",
            "source": "system"
        }]
        
    except Exception as e:
        logger.error(f"提取知识内容失败: {e}")
        return [{
            "title": "解析错误",
            "content": f"处理响应时出错: {str(e)}",
            "score": 0.0,
            "url": "",
            "source": "system"
        }]


# ===== LangChain Tool 封装 =====

@tool
@observe(name="金融领域知识搜索",as_type="tool")
def domain_fin_search(
    keyword: str,
    scene: str = "default"
) -> List[Dict[str, Any]]:
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
        List[Dict[str, Any]]: 结构化的搜索结果列表，每个结果包含:
            - title: 段落标题或结果编号
            - content: 知识内容
            - score: 相关度评分
            - url: 链接（通常为空）
            - source: 来源标识
    
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
