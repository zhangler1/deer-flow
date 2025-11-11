#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scene Map 数据库查询工具包

模块化设计，职责分离：
    - models: ORM 模型定义
    - config: 配置管理
    - database: 数据库连接管理
    - repositories: 数据访问层
    - services: 业务逻辑层
    - utils: 工具函数
    - cli: 命令行工具

快速开始:
    from SQL import get_scene_codes, get_scene_details
    
    # 查询场景代码列表
    codes = get_scene_codes(repository='EUVD')
    
    # 查询详细信息
    details = get_scene_details(repository='EUVD')
"""

__version__ = '1.0.0'

# ==================== 导出公共接口 ====================

# 从 services 导出常用函数
try:
    from .services import SceneMapService
    
    # 导出便捷函数（委托给 Service 层）
    get_scene_codes = SceneMapService.get_scene_codes
    get_scene_details = SceneMapService.get_scene_details
    get_scene_by_code = SceneMapService.get_scene_by_code
    count_scenes = SceneMapService.count_scenes
    get_active_scenes = SceneMapService.get_active_scenes
    search_scenes_by_name = SceneMapService.search_scenes_by_name
    
except ImportError:
    # 如果相对导入失败，使用绝对导入
    pass

# 导出配置类
try:
    from .config import DatabaseConfig, load_config_from_env
except ImportError:
    pass

# 导出工具函数
try:
    from .utils import (
        print_scene_codes,
        print_scene_details,
        print_summary,
    )
except ImportError:
    pass


__all__ = [
    # Service 层函数
    'get_scene_codes',
    'get_scene_details',
    'get_scene_by_code',
    'count_scenes',
    'get_active_scenes',
    'search_scenes_by_name',
    
    # 配置类
    'DatabaseConfig',
    'load_config_from_env',
    
    # 工具函数
    'print_scene_codes',
    'print_scene_details',
    'print_summary',
]
    # 查询场景代码列表
    codes = get_scene_codes(repository='EUVD')
    
    # 查询详细信息
    details = get_scene_details(repository='EUVD')
"""

__version__ = '1.0.0'

# ==================== 导出公共接口 ====================

# 从 services 导出常用函数
try:
    from .services import SceneMapService
    
    # 导出便捷函数（委托给 Service 层）
    get_scene_codes = SceneMapService.get_scene_codes
    get_scene_details = SceneMapService.get_scene_details
    get_scene_by_code = SceneMapService.get_scene_by_code
    count_scenes = SceneMapService.count_scenes
    get_active_scenes = SceneMapService.get_active_scenes
    search_scenes_by_name = SceneMapService.search_scenes_by_name
    
except ImportError:
    # 如果相对导入失败，使用绝对导入
    pass

# 导出配置类
try:
    from .config import DatabaseConfig, load_config_from_env
except ImportError:
    pass

# 导出工具函数
try:
    from .utils import (
        print_scene_codes,
        print_scene_details,
        print_summary,
    )
except ImportError:
    pass


__all__ = [
    # Service 层函数
    'get_scene_codes',
    'get_scene_details',
    'get_scene_by_code',
    'count_scenes',
    'get_active_scenes',
    'search_scenes_by_name',
    
    # 配置类
    'DatabaseConfig',
    'load_config_from_env',
    
    # 工具函数
    'print_scene_codes',
    'print_scene_details',
    'print_summary',
]
