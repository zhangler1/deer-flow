#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精简范例：查询数据库中的 scene_code

使用方法：
    cd /home/llm/zhangle/deer-flow/SQL
    python3 example_query.py
"""

import os
import sys

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入本地模块
from services import SceneMapService

# 便捷函数
get_scene_codes = SceneMapService.get_scene_codes
get_scene_details = SceneMapService.get_scene_details
get_scene_by_code = SceneMapService.get_scene_by_code

# ==================== 配置数据库连接 ====================

# 方式1: 使用环境变量（推荐）
os.environ['DB_HOST'] = '192.168.0.106'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'omuser@tellmua100#obhfcgb03uat'
os.environ['DB_PASSWORD'] = 'OceanBase_123#'
os.environ['DB_NAME'] = 'omservice'

# 导入数据库初始化函数
from database import init_database

# 初始化数据库连接（关键步骤！）
print("⚙️  正在初始化数据库连接...")
try:
    init_database()
    print("✅ 数据库连接初始化成功\n")
except Exception as e:
    print(f"❌ 数据库初始化失败: {e}")
    print("\n请检查:")
    print("  1. MySQL 容器是否正在运行: docker ps | grep mysql")
    print("  2. 数据库连接信息是否正确")
    print("  3. 网络是否可达")
    sys.exit(1)


# ==================== 查询示例 ====================

def example_1_simple_query():
    """示例1: 最简单的查询 - 获取所有 EUVD 库的 scene_code"""
    print("\n" + "="*60)
    print("示例1: 查询 EUVD 库所有 scene_code")
    print("="*60)
    
    # 查询 EUVD 库中所有有效的场景代码
    codes = get_scene_codes(repository='EUVD')
    
    print(f"找到 {len(codes)} 个场景:")
    for code in codes:
        print(f"  - {code}")
    
    return codes


def example_2_filtered_query():
    """示例2: 带过滤条件的查询 - 只查询有 prompt_template 的场景"""
    print("\n" + "="*60)
    print("示例2: 查询 EUVD 库中有模板的场景")
    print("="*60)
    
    # 查询 EUVD 库中 status='1' 且 prompt_template 不为空的场景
    codes = get_scene_codes(
        repository='EUVD',
        status='1',
        exclude_empty_template=True  # 排除空模板
    )
    
    print(f"找到 {len(codes)} 个有效场景:")
    for code in codes:
        print(f"  ✓ {code}")
    
    return codes


def example_3_get_details():
    """示例3: 获取详细信息"""
    print("\n" + "="*60)
    print("示例3: 获取场景详细信息")
    print("="*60)
    
    # 获取详细信息（包含场景名称、描述、模型等）
    details = get_scene_details(
        repository='EUVD',
        exclude_empty_template=True
    )
    
    print(f"找到 {len(details)} 个场景:\n")
    for scene in details:
        print(f"代码: {scene['scene_code']}")
        print(f"名称: {scene['scene_name']}")
        print(f"模型: {scene['model']}")
        print(f"状态: {'启用' if scene['status'] == '1' else '停用'}")
        print(f"模板长度: {len(scene.get('prompt_template', '')) or 0} 字符")
        print("-" * 40)
    
    return details


def example_4_query_by_code():
    """示例4: 根据 scene_code 查询单个场景"""
    print("\n" + "="*60)
    print("示例4: 查询单个场景")
    print("="*60)
    
    scene_code = 'DEMO_EUVD_001'
    scene = get_scene_by_code(scene_code)
    
    if scene:
        print(f"✓ 找到场景: {scene_code}\n")
        print(f"  场景名称: {scene['scene_name']}")
        print(f"  描述: {scene.get('description', 'N/A')}")
        print(f"  模型: {scene.get('model', 'N/A')}")
        print(f"  知识库: {scene['repository']}")
        print(f"  状态: {'启用' if scene['status'] == '1' else '停用'}")
        if scene.get('prompt_template'):
            preview = scene['prompt_template'][:100] + "..." if len(scene['prompt_template']) > 100 else scene['prompt_template']
            print(f"  模板预览: {preview}")
    else:
        print(f"✗ 未找到场景: {scene_code}")
    
    return scene


def example_5_financial_scenes():

    
    # 先获取所有 EUVD 场景
    all_scenes = get_scene_details(repository='EUVD', exclude_empty_template=False)
    
    # 筛选金融场景
    fin_scenes = [s for s in all_scenes if s['scene_code'].startswith('FIN_')]
    
    print(f"找到 {len(fin_scenes)} 个金融场景:\n")
    
    # 输出三元组: (scene_name, scene_code, description)
    scene_tuples = []
    for scene in fin_scenes:
        scene_tuple = (
            scene['scene_name'],
            scene['scene_code'],
            scene.get('description', 'N/A')
        )
        scene_tuples.append(scene_tuple)
        print(f"  {scene_tuple}")
        print()
    
    print(f"\n三元组列表:")
    print(scene_tuples)
    
    return scene_tuples


# ==================== 主程序 ====================

if __name__ == '__main__':
    print("\n" + "🔍 数据库查询示例程序".center(60, "="))
    
    try:
        # # 运行所有示例
        # example_1_simple_query()
        # example_2_filtered_query()
        # example_3_get_details()
        # example_4_query_by_code()
        example_5_financial_scenes()
        
        print("\n" + "✅ 所有查询完成！".center(60, "=") + "\n")
        
    except Exception as e:
        print(f"\n❌ 查询出错: {e}")
        print("\n提示:")
        print("  1. 确保 MySQL 容器正在运行")
        print("  2. 检查数据库连接配置")
        print("  3. 确保数据已初始化")
        print("\n启动命令:")
        print("  docker compose up -d mysql")
        print()
