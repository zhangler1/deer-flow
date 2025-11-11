#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数层 (Utilities)

职责:
    - 提供通用工具函数
    - 格式化输出
    - 数据转换
"""

from typing import List, Dict, Any, Optional


# ==================== 格式化输出 ====================

def print_scene_codes(
    scene_codes: List[str],
    title: str = "Scene Codes"
):
    """
    格式化打印 scene_code 列表
    
    Args:
        scene_codes: scene_code 列表
        title: 标题
    """
    print("\n" + "=" * 80)
    print(f"🔍 {title}".center(80))
    print("=" * 80)
    
    if not scene_codes:
        print("\n⚠️  未找到任何场景\n")
        return
    
    print(f"\n✅ 找到 {len(scene_codes)} 个场景:\n")
    for idx, code in enumerate(scene_codes, 1):
        print(f"  {idx}. {code}")
    
    print(f"\nPython 列表格式:")
    print(f"scene_codes = {scene_codes}")
    print("\n" + "=" * 80 + "\n")


def print_scene_details(
    scenes: List[Dict[str, Any]],
    show_template: bool = False,
    max_template_length: int = 100,
):
    """
    格式化打印场景详细信息
    
    Args:
        scenes: 场景信息列表
        show_template: 是否显示 prompt_template
        max_template_length: 模板显示的最大长度
    """
    if not scenes:
        print("\n⚠️  未找到任何场景\n")
        return
    
    print(f"\n找到 {len(scenes)} 个场景:\n")
    print("=" * 100)
    
    for idx, scene in enumerate(scenes, 1):
        print(f"\n{idx}. Scene Code: {scene['scene_code']}")
        print(f"   名称: {scene['scene_name']}")
        print(f"   描述: {scene.get('description', 'N/A')}")
        print(f"   模型: {scene.get('model', 'N/A')}")
        print(f"   知识库: {scene['repository']}")
        print(f"   状态: {'正常' if scene['status'] == '1' else '停用'}")
        
        if show_template and scene.get('prompt_template'):
            template = scene['prompt_template']
            if len(template) > max_template_length:
                template = template[:max_template_length] + "..."
            print(f"   Prompt模板: {template}")
        
        print(f"   创建时间: {scene.get('create_time', 'N/A')}")
    
    print("\n" + "=" * 100 + "\n")


def print_summary(
    repository: str,
    total_count: int,
    active_count: Optional[int] = None,
    with_template_count: Optional[int] = None,
):
    """
    打印统计摘要
    
    Args:
        repository: 知识库名称
        total_count: 总数
        active_count: 活跃数量
        with_template_count: 有模板的数量
    """
    print("\n" + "=" * 80)
    print(f"📊 {repository} 知识库统计摘要".center(80))
    print("=" * 80)
    print(f"\n  总场景数: {total_count}")
    
    if active_count is not None:
        print(f"  活跃场景: {active_count}")
    
    if with_template_count is not None:
        print(f"  有模板场景: {with_template_count}")
    
    print("\n" + "=" * 80 + "\n")


def print_repository_summary(summary: Dict[str, int]):
    """
    打印各知识库统计
    
    Args:
        summary: 各知识库的统计字典
    """
    print("\n" + "=" * 80)
    print("📊 各知识库场景统计".center(80))
    print("=" * 80)
    
    if not summary:
        print("\n⚠️  无统计数据\n")
        return
    
    print()
    total = 0
    for repo, count in sorted(summary.items()):
        print(f"  {repo:<15} : {count:>5} 个场景")
        total += count
    
    print(f"\n  {'总计':<15} : {total:>5} 个场景")
    print("\n" + "=" * 80 + "\n")


# ==================== 数据转换 ====================

def export_to_dict(scenes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    将场景列表转换为以 scene_code 为键的字典
    
    Args:
        scenes: 场景列表
    
    Returns:
        以 scene_code 为键的字典
    """
    return {scene['scene_code']: scene for scene in scenes}


def extract_codes(scenes: List[Dict[str, Any]]) -> List[str]:
    """
    从场景列表中提取 scene_code
    
    Args:
        scenes: 场景列表
    
    Returns:
        scene_code 列表
    """
    return [scene['scene_code'] for scene in scenes]


def filter_by_status(
    scenes: List[Dict[str, Any]],
    status: str = '1'
) -> List[Dict[str, Any]]:
    """
    按状态过滤场景
    
    Args:
        scenes: 场景列表
        status: 状态（'1'=正常, '0'=停用）
    
    Returns:
        过滤后的场景列表
    """
    return [scene for scene in scenes if scene.get('status') == status]


def group_by_repository(
    scenes: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    按知识库分组
    
    Args:
        scenes: 场景列表
    
    Returns:
        按知识库分组的字典
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for scene in scenes:
        repo = scene['repository']
        if repo not in groups:
            groups[repo] = []
        groups[repo].append(scene)
    return groups


# ==================== 导出 ====================

__all__ = [
    'print_scene_codes',
    'print_scene_details',
    'print_summary',
    'print_repository_summary',
    'export_to_dict',
    'extract_codes',
    'filter_by_status',
    'group_by_repository',
]
