# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
金融领域知识库检索工具 - Finance Knowledge Search Tool

基于空间ID(space_id)的向量检索工具，用于从金融领域知识库检索相关文档。
可以被任何节点（researcher、simple_search等）作为工具使用。
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

import requests
from langchain_core.tools import tool
from typing_extensions import Annotated

from src.utils.enhanced_logger import console_print, get_enhanced_logger

logger = logging.getLogger(__name__)
enhanced_logger = get_enhanced_logger('tools.finance_knowledge')


@tool
def domain_fin_search(
    keyword: Annotated[str, "检索关键词"],
    space_codes: Annotated[Optional[List[str]], "空间代码列表，不提供则使用默认值['SP0000001']"] = None,
    vector_top_n: Annotated[int, "返回结果数量，默认3"] = 3,
    threshold: Annotated[float, "相似度阈值，默认0.1"] = 0.1,
) -> str:
    """
    从金融领域知识库检索相关文档内容。
    
    此工具使用向量检索技术，从指定的金融知识空间中查找与关键词最相关的文档片段。
    适用于需要查询金融专业知识、制度文件、产品手册等内部文档的场景。
    
    功能特性：
    - 基于空间ID的知识检索
    - 向量相似度匹配
    - 支持时间范围过滤
    - 自动格式化检索结果
    
    适用场景：
    - 查询银行产品规则
    - 检索制度文件
    - 查找操作手册
    - 获取专业金融知识
    
    Args:
        keyword: 检索关键词，如"持卡人办理挂失"
        space_codes: 空间代码列表，默认 ['SP0000001']
        vector_top_n: 返回Top N结果，默认3
        threshold: 相似度阈值，默认0.1
    
    Returns:
        格式化的检索结果文本或错误信息
    """
    start_time = time.time()
    
    # 设置默认值
    if space_codes is None:
        space_codes = ['SP0000001']
    
    # 从环境变量获取配置
    api_url = os.getenv(
        'FINANCE_KNOWLEDGE_API_URL',
        'http://12.235.192.234/EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do'
    )
    caller = os.getenv('FINANCE_KNOWLEDGE_CALLER', 'SXZSWD_JIAOXIN')
    user_code = os.getenv('FINANCE_KNOWLEDGE_USER_CODE', '123')
    
    # 计算时间范围（默认最近30天）
    days_range = int(os.getenv('FINANCE_KNOWLEDGE_DAYS_RANGE', '30'))
    end_time = datetime.now()
    start_time_dt = end_time - timedelta(days=days_range)
    pub_time_start = start_time_dt.strftime('%Y-%m-%d 00:00:00')
    pub_time_end = end_time.strftime('%Y-%m-%d 23:59:59')
    
    enhanced_logger.logger.info(
        f"📚 FINANCE_SEARCH_START | 开始金融知识库检索 | "
        f"关键词: '{keyword}' | 空间: {space_codes} | Top N: {vector_top_n}"
    )
    console_print(
        f"\033[32m[📚 金融知识库检索]\033[0m \033[35m关键词: '{keyword}' | 空间: {space_codes}\033[0m",
        level=logging.INFO
    )
    
    try:
        # 构建请求参数
        req_message = {
            "REQ_HEAD": {},
            "REQ_BODY": {
                "param": {
                    "keyword": keyword,
                    "caller": caller,
                    "userCode": user_code,
                    "searchType": "2",  # 2表示向量检索
                    "sourceSystems": ["0001"],
                    "domainTagList": [],
                    "spaceCodeList": space_codes,
                    "teamSpaceCodeList": space_codes,
                    "customizedTagList": ["金融业"],
                    "vectorTopN": vector_top_n,
                    "model": 0,
                    "attachFlag": 1,
                    "threshold": threshold,
                    "publishedFlag": 0,
                    "latestFlag": None,
                    "delFlag": 0,
                    "pubTimeStart": pub_time_start,
                    "pubTimeEnd": pub_time_end
                }
            }
        }
        
        # 设置请求头
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'DeerFlow-FinanceKnowledgeSearch/1.0.0',
            'caller': 'sjyh',
            'jumpcloud-ENV': 'BASE'
        }
        
        # 发送请求
        data = {'REQ_MESSAGE': json.dumps(req_message, ensure_ascii=False)}
        
        enhanced_logger.logger.debug(
            f"🌐 API_REQUEST | URL: {api_url} | "
            f"Payload: {json.dumps(req_message, ensure_ascii=False)[:200]}..."
        )
        
        response = requests.post(
            api_url,
            headers=headers,
            data=data,
            timeout=int(os.getenv('FINANCE_KNOWLEDGE_TIMEOUT', '30'))
        )
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        duration = time.time() - start_time
        
        # 提取检索结果
        formatted_result = _parse_and_format_results(result, keyword, duration)
        
        return formatted_result
        
    except requests.exceptions.Timeout:
        duration = time.time() - start_time
        error_msg = f"❌ 金融知识库检索超时（{duration:.2f}s），请稍后重试。"
        enhanced_logger.logger.error(
            f"❌ FINANCE_SEARCH_TIMEOUT | 检索超时 | 耗时: {duration:.2f}s"
        )
        console_print(
            f"\033[31m[❌ 检索超时] {error_msg}\033[0m",
            level=logging.ERROR
        )
        return error_msg
        
    except requests.exceptions.RequestException as e:
        duration = time.time() - start_time
        error_msg = f"❌ 金融知识库检索失败: {str(e)}"
        enhanced_logger.logger.error(
            f"❌ FINANCE_SEARCH_ERROR | 网络错误 | 耗时: {duration:.2f}s | 错误: {str(e)}"
        )
        console_print(
            f"\033[31m[❌ 检索失败] {error_msg}\033[0m",
            level=logging.ERROR
        )
        return error_msg
        
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"❌ 金融知识库检索异常: {str(e)}"
        enhanced_logger.logger.error(
            f"❌ FINANCE_SEARCH_EXCEPTION | 未知错误 | 耗时: {duration:.2f}s | 错误: {str(e)}",
            exc_info=True
        )
        console_print(
            f"\033[31m[❌ 检索异常] {error_msg}\033[0m",
            level=logging.ERROR
        )
        return error_msg


def _parse_and_format_results(
    response: Dict[str, Any],
    keyword: str,
    duration: float
) -> str:
    """
    解析并格式化金融知识库检索API的响应
    
    Args:
        response: API响应数据
        keyword: 原始检索关键词
        duration: 检索耗时
    
    Returns:
        格式化后的检索结果文本
    """
    try:
        # 检查响应状态
        rsp_head = response.get('RSP_HEAD', {})
        if rsp_head.get('TRAN_SUCCESS') != '1':
            error_msg = rsp_head.get('TRAN_MESSAGE', '未知错误')
            logger.warning(f"Finance knowledge search API returned error: {error_msg}")
            return f"⚠️ 检索失败: {error_msg}"
        
        # 提取结果数据
        rsp_body = response.get('RSP_BODY', {})
        documents = rsp_body.get('data', [])
        
        if not documents:
            enhanced_logger.logger.warning(
                f"⚠️  FINANCE_SEARCH_EMPTY | 未找到结果 | 耗时: {duration:.2f}s"
            )
            console_print(
                f"\033[33m[⚠️  无结果] 未找到与 '{keyword}' 相关的金融知识\033[0m",
                level=logging.INFO
            )
            return f'未找到与「{keyword}」相关的金融知识库文档。建议尝试其他关键词。'
        
        enhanced_logger.logger.info(
            f"✅ FINANCE_SEARCH_COMPLETE | 检索完成 | "
            f"结果数: {len(documents)} | 耗时: {duration:.2f}s"
        )
        console_print(
            f"\033[32m[✅ 检索完成]\033[0m \033[35m返回 {len(documents)} 条结果 | 耗时: {duration:.2f}s\033[0m",
            level=logging.INFO
        )
        
        # 格式化结果
        result_text = f'📚 **金融知识库检索结果**（关键词: {keyword}，共{len(documents)}条）\n\n'
        
        for i, doc in enumerate(documents, 1):
            title = doc.get('docTitle', '').strip() or doc.get('title', '').strip() or '未命名文档'
            content = doc.get('content', '').strip() or doc.get('docContent', '').strip()
            score = float(doc.get('score', 0)) if doc.get('score') else 0.0
            doc_id = doc.get('docId', '') or doc.get('id', '')
            
            # 提取元数据
            source_system = doc.get('sourceSystem', '')
            space_code = doc.get('spaceCode', '')
            category = doc.get('fullCategoryName', '')
            pub_time = doc.get('pubTime', '')
            
            result_text += f"### {i}. {title}\n\n"
            
            if content:
                # 限制内容长度
                max_content_length = 500
                if len(content) > max_content_length:
                    content = content[:max_content_length] + "..."
                result_text += f"{content}\n\n"
            
            # 添加元数据
            metadata_parts = []
            if score > 0:
                metadata_parts.append(f"相似度: {score:.4f}")
            if source_system:
                metadata_parts.append(f"来源: {source_system}")
            if category:
                metadata_parts.append(f"分类: {category}")
            if pub_time:
                metadata_parts.append(f"发布时间: {pub_time}")
            if doc_id:
                metadata_parts.append(f"文档ID: {doc_id}")
            
            if metadata_parts:
                result_text += f"*{' | '.join(metadata_parts)}*\n\n"
            
            result_text += "---\n\n"
            
            # 打印详情到日志
            if i <= 3:  # 只打印前3条到DEBUG日志
                console_print(
                    f"\033[32m  {i}. 文档: {title}\033[0m",
                    level=logging.DEBUG
                )
                content_preview = content[:80] if content else '无内容'
                console_print(
                    f"\033[35m     内容: {content_preview}...\033[0m",
                    level=logging.DEBUG
                )
                if score > 0:
                    console_print(
                        f"\033[35m     [相似度: {score:.4f}]\033[0m",
                        level=logging.DEBUG
                    )
        
        return result_text.strip()
        
    except Exception as e:
        logger.error(f"Error parsing finance knowledge search response: {e}", exc_info=True)
        return f"❌ 解析检索结果时出错: {str(e)}"


# 导出工具
__all__ = ['domain_fin_search']
