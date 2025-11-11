#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
业务逻辑层 (Service Layer)

职责:
    - 封装业务逻辑
    - 协调多个 Repository
    - 提供面向应用的接口
    - 处理事务边界

设计模式:
    - Service Layer Pattern: 业务逻辑封装
    - Facade Pattern: 简化复杂的子系统调用
"""

from typing import List, Dict, Optional, Any

# 使用绝对导入，避免相对导入问题
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import SceneMap
from repositories import SceneMapRepository
from database import get_session, init_database
from config import DatabaseConfig


# ==================== Scene Map Service ====================

class SceneMapService:
    """
    SceneMap 业务逻辑层
    
    职责:
        - 提供高层业务接口
        - 封装数据转换逻辑
        - 管理事务
    """
    
    @staticmethod
    def get_scene_codes(
        repository: str = 'EUVD',
        status: str = '1',
        exclude_empty_template: bool = True,
        db_config: Optional[DatabaseConfig] = None,
    ) -> List[str]:
        """
        获取场景代码列表
        
        Args:
            repository: 知识库类型
            status: 状态过滤
            exclude_empty_template: 是否排除空模板
            db_config: 数据库配置
        
        Returns:
            scene_code 列表
        """
        # 初始化数据库连接
        if db_config:
            init_database(db_config)
        
        with get_session() as session:
            repo = SceneMapRepository(session)
            scenes = repo.find_by_repository(
                repository=repository,
                status=status,
                exclude_empty_template=exclude_empty_template
            )
            return [str(scene.scene_code) for scene in scenes]
    
    @staticmethod
    def get_scene_details(
        repository: str = 'EUVD',
        status: str = '1',
        exclude_empty_template: bool = True,
        include_template: bool = True,
        db_config: Optional[DatabaseConfig] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取场景详细信息
        
        Args:
            repository: 知识库类型
            status: 状态过滤
            exclude_empty_template: 是否排除空模板
            include_template: 是否包含 prompt_template
            db_config: 数据库配置
        
        Returns:
            场景详细信息列表（字典格式）
        """
        if db_config:
            init_database(db_config)
        
        with get_session() as session:
            repo = SceneMapRepository(session)
            scenes = repo.find_by_repository(
                repository=repository,
                status=status,
                exclude_empty_template=exclude_empty_template
            )
            return [scene.to_dict(include_template=include_template) for scene in scenes]
    
    @staticmethod
    def get_scene_by_code(
        scene_code: str,
        db_config: Optional[DatabaseConfig] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        根据 scene_code 获取单个场景
        
        Args:
            scene_code: 场景代码
            db_config: 数据库配置
        
        Returns:
            场景信息字典，不存在则返回 None
        """
        if db_config:
            init_database(db_config)
        
        with get_session() as session:
            repo = SceneMapRepository(session)
            scene = repo.find_by_code(scene_code)
            return scene.to_dict() if scene else None
    
    @staticmethod
    def count_scenes(
        repository: str = 'EUVD',
        status: str = '1',
        exclude_empty_template: bool = True,
        db_config: Optional[DatabaseConfig] = None,
    ) -> int:
        """
        统计场景数量
        
        Args:
            repository: 知识库类型
            status: 状态过滤
            exclude_empty_template: 是否排除空模板
            db_config: 数据库配置
        
        Returns:
            场景数量
        """
        if db_config:
            init_database(db_config)
        
        with get_session() as session:
            repo = SceneMapRepository(session)
            return repo.count_by_repository(
                repository=repository,
                status=status,
                exclude_empty_template=exclude_empty_template
            )
    
    @staticmethod
    def get_active_scenes(
        db_config: Optional[DatabaseConfig] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取所有活跃场景
        
        Args:
            db_config: 数据库配置
        
        Returns:
            活跃场景列表
        """
        if db_config:
            init_database(db_config)
        
        with get_session() as session:
            repo = SceneMapRepository(session)
            scenes = repo.find_active_scenes()
            return [scene.to_dict() for scene in scenes]
    
    @staticmethod
    def search_scenes_by_name(
        keyword: str,
        db_config: Optional[DatabaseConfig] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据名称搜索场景
        
        Args:
            keyword: 搜索关键词
            db_config: 数据库配置
        
        Returns:
            匹配的场景列表
        """
        if db_config:
            init_database(db_config)
        
        with get_session() as session:
            repo = SceneMapRepository(session)
            scenes = repo.search_by_name(keyword)
            return [scene.to_dict() for scene in scenes]
    
    @staticmethod
    def get_scenes_by_codes(
        scene_codes: List[str],
        db_config: Optional[DatabaseConfig] = None,
    ) -> List[Dict[str, Any]]:
        """
        批量获取场景信息
        
        Args:
            scene_codes: scene_code 列表
            db_config: 数据库配置
        
        Returns:
            场景信息列表
        """
        if db_config:
            init_database(db_config)
        
        with get_session() as session:
            repo = SceneMapRepository(session)
            scenes = repo.find_by_codes(scene_codes)
            return [scene.to_dict() for scene in scenes]
    
    @staticmethod
    def get_repository_summary(
        db_config: Optional[DatabaseConfig] = None,
    ) -> Dict[str, int]:
        """
        获取各知识库的场景统计
        
        Args:
            db_config: 数据库配置
        
        Returns:
            各知识库的场景数量统计
        """
        if db_config:
            init_database(db_config)
        
        with get_session() as session:
            repo = SceneMapRepository(session)
            all_scenes = repo.find_all()
            
            # 按 repository 分组统计
            summary: Dict[str, int] = {}
            for scene in all_scenes:
                repo_name = str(scene.repository)
                summary[repo_name] = summary.get(repo_name, 0) + 1
            
            return summary


# ==================== 导出 ====================

__all__ = ['SceneMapService']
