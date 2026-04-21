# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
文本处理工具模块
提供文本清洗、格式化等实用函数
"""

import re
from typing import Optional


def remove_think_tags(text: str) -> str:
    """
    移除文本中的 <think>...</think> 标签及其内部内容
    
    该函数用于过滤LLM输出中的思考过程标签，确保只保留实际的回答内容。
    支持跨行匹配和嵌套标签处理。
    
    Args:
        text: 包含可能的 <think> 标签的原始文本
        
    Returns:
        str: 移除所有 <think> 标签及其内容后的清洁文本
        
    Examples:
        >>> text = "这是答案<think>这是思考过程</think>继续答案"
        >>> remove_think_tags(text)
        '这是答案继续答案'
        
        >>> text = "开始<think>\\n多行\\n思考\\n</think>结束"
        >>> remove_think_tags(text)
        '开始结束'
    """
    if not text:
        return text
    
    # 使用正则表达式匹配并移除 <think>...</think> 标签及其内容
    # re.DOTALL 标志使 . 匹配包括换行符在内的所有字符
    # 使用非贪婪模式 .*? 避免跨标签匹配
    pattern = r'<think>.*?</think>'
    cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 清理可能产生的多余空白行
    # 将多个连续换行符替换为最多两个换行符
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    
    # 移除行首和行尾的空白字符，但保留段落间的空行
    lines = cleaned_text.split('\n')
    lines = [line.rstrip() for line in lines]
    cleaned_text = '\n'.join(lines)
    
    return cleaned_text.strip()


def remove_xml_tags(text: str, tag_name: str) -> str:
    """
    移除指定的XML标签及其内部内容
    
    Args:
        text: 原始文本
        tag_name: 要移除的标签名称（不含尖括号）
        
    Returns:
        str: 移除指定标签后的文本
        
    Examples:
        >>> text = "内容<debug>调试信息</debug>更多内容"
        >>> remove_xml_tags(text, "debug")
        '内容更多内容'
    """
    if not text or not tag_name:
        return text
    
    # 转义标签名称中的特殊字符
    tag_name_escaped = re.escape(tag_name)
    pattern = f'<{tag_name_escaped}>.*?</{tag_name_escaped}>'
    cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 清理多余空白
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    
    return cleaned_text.strip()


def extract_content_between_tags(text: str, tag_name: str) -> Optional[str]:
    """
    提取指定XML标签之间的内容
    
    Args:
        text: 原始文本
        tag_name: 标签名称（不含尖括号）
        
    Returns:
        Optional[str]: 标签内的内容，如果未找到则返回None
        
    Examples:
        >>> text = "前面<answer>这是答案</answer>后面"
        >>> extract_content_between_tags(text, "answer")
        '这是答案'
    """
    if not text or not tag_name:
        return None
    
    tag_name_escaped = re.escape(tag_name)
    pattern = f'<{tag_name_escaped}>(.*?)</{tag_name_escaped}>'
    match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    
    return None


def clean_whitespace(text: str, preserve_paragraphs: bool = True) -> str:
    """
    清理文本中的多余空白字符
    
    Args:
        text: 原始文本
        preserve_paragraphs: 是否保留段落间的空行
        
    Returns:
        str: 清理后的文本
    """
    if not text:
        return text
    
    # 移除每行的首尾空白
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    
    if preserve_paragraphs:
        # 保留空行，但将多个空行合并为一个
        result = []
        prev_empty = False
        for line in lines:
            if line:
                result.append(line)
                prev_empty = False
            elif not prev_empty:
                result.append('')
                prev_empty = True
        return '\n'.join(result)
    else:
        # 移除所有空行
        return '\n'.join(line for line in lines if line)


def estimate_token_count(text: str) -> int:
    """
    粗略估算文本的 token 数：
    - 中文（CJK）字符按 ~1 token 估算
    - 其他字符按 ~4 字符 ≈ 1 token 估算
    """
    if not text:
        return 0
    cjk_chars = re.findall(r'[\u4e00-\u9fff]', text)
    cjk_count = len(cjk_chars)
    other_count = max(0, len(text) - cjk_count)
    return cjk_count + (other_count + 3) // 4


def get_messages_context_stats(messages) -> tuple[int, int]:
    """
    计算上下文长度统计（字符数，估算token数）
    """
    if isinstance(messages, list):
        chars = sum(len(str(m)) for m in messages)
        tokens = sum(estimate_token_count(str(m)) for m in messages)
        return chars, tokens
    text = str(messages)
    return len(text), estimate_token_count(text)
