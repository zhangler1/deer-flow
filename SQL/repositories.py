#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据访问层 (Repository Pattern)

职责:
    - 封装数据库访问逻辑
    - 提供领域对象的 CRUD 操作
    - 隔离业务逻辑与数据访问细节

设计模式:
    - Repository Pattern: 提供类似集合的接口访问数据
    - DAO Pattern: 数据访问对象模式
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from models import SceneMap


# ==================== Scene Map Repository ====================

class SceneMapRepository:
    """
    SceneMap 数据访问层
    
    职责:
        - 提供 SceneMap 表的所有数据访问方法
        - 封装复杂查询逻辑
        - 返回领域对象（SceneMap）或原始数据
    """
    
    def __init__(self, session: Session):
        """
        初始化 Repository
        
        Args:
            session: SQLAlchemy 会话对象
        """
        self.session = session
    
    # ==================== 基础 CRUD ====================
    
    def find_by_code(self, scene_code: str) -> Optional[SceneMap]:
        """
        根据 scene_code 查询单个场景
        
        Args:
            scene_code: 场景代码
        
        Returns:
            SceneMap 对象，如果不存在则返回 None
        """
        return self.session.query(SceneMap).filter(
            SceneMap.scene_code == scene_code
        ).first()
    
    def find_all(self) -> List[SceneMap]:
        """
        查询所有场景
        
        Returns:
            SceneMap 对象列表
        """
        return self.session.query(SceneMap).all()
    
    def save(self, scene: SceneMap) -> SceneMap:
        """
        保存场景
        
        Args:
            scene: SceneMap 对象
        
        Returns:
            保存后的 SceneMap 对象
        """
        self.session.add(scene)
        self.session.flush()
        return scene
    
    def delete(self, scene: SceneMap):
        """
        删除场景
        
        Args:
            scene: SceneMap 对象
        """
        self.session.delete(scene)
        self.session.flush()
    
    # ==================== 条件查询 ====================
    
    def find_by_repository(
        self,
        repository: str,
        status: Optional[str] = None,
        exclude_empty_template: bool = False,
    ) -> List[SceneMap]:
        """
        根据知识库类型查询场景
        
        Args:
            repository: 知识库类型（如 'EUVD', 'SPARK'）
            status: 状态过滤（'1'=正常, '0'=停用），None 表示不过滤
            exclude_empty_template: 是否排除空的 prompt_template
        
        Returns:
            SceneMap 对象列表
        """
        query = self.session.query(SceneMap).filter(
            SceneMap.repository == repository
        )
        
        # 状态过滤
        if status is not None:
            query = query.filter(SceneMap.status == status)
        
        # 排除空模板
        if exclude_empty_template:
            query = query.filter(SceneMap.prompt_template.isnot(None))
            query = query.filter(SceneMap.prompt_template != '')
        
        # 按 scene_code 排序
        query = query.order_by(SceneMap.scene_code)
        
        return query.all()
    
    def find_by_model(self, model: str) -> List[SceneMap]:
        """
        根据模型查询场景
        
        Args:
            model: 模型名称（如 'qwen-plus'）
        
        Returns:
            SceneMap 对象列表
        """
        return self.session.query(SceneMap).filter(
            SceneMap.model == model
        ).order_by(SceneMap.scene_code).all()
    
    def find_active_scenes(self) -> List[SceneMap]:
        """
        查询所有活跃场景（status='1'）
        
        Returns:
            SceneMap 对象列表
        """
        return self.session.query(SceneMap).filter(
            SceneMap.status == '1'
        ).order_by(SceneMap.scene_code).all()
    
    def find_with_template(self) -> List[SceneMap]:
        """
        查询所有有提示词模板的场景
        
        Returns:
            SceneMap 对象列表
        """
        return self.session.query(SceneMap).filter(
            SceneMap.prompt_template.isnot(None),
            SceneMap.prompt_template != ''
        ).order_by(SceneMap.scene_code).all()
    
    # ==================== 统计查询 ====================
    
    def count_all(self) -> int:
        """
        统计所有场景数量
        
        Returns:
            场景总数
        """
        return self.session.query(SceneMap).count()
    
    def count_by_repository(
        self,
        repository: str,
        status: Optional[str] = None,
        exclude_empty_template: bool = False,
    ) -> int:
        """
        统计指定知识库的场景数量
        
        Args:
            repository: 知识库类型
            status: 状态过滤
            exclude_empty_template: 是否排除空模板
        
        Returns:
            场景数量
        """
        query = self.session.query(SceneMap).filter(
            SceneMap.repository == repository
        )
        
        if status is not None:
            query = query.filter(SceneMap.status == status)
        
        if exclude_empty_template:
            query = query.filter(SceneMap.prompt_template.isnot(None))
            query = query.filter(SceneMap.prompt_template != '')
        
        return query.count()
    
    def count_by_status(self, status: str) -> int:
        """
        统计指定状态的场景数量
        
        Args:
            status: 状态（'1'=正常, '0'=停用）
        
        Returns:
            场景数量
        """
        return self.session.query(SceneMap).filter(
            SceneMap.status == status
        ).count()
    
    # ==================== 高级查询 ====================
    
    def find_by_codes(self, scene_codes: List[str]) -> List[SceneMap]:
        """
        根据 scene_code 列表批量查询
        
        Args:
            scene_codes: scene_code 列表
        
        Returns:
            SceneMap 对象列表
        """
        return self.session.query(SceneMap).filter(
            SceneMap.scene_code.in_(scene_codes)
        ).all()
    
    def search_by_name(self, keyword: str) -> List[SceneMap]:
        """
        根据场景名称模糊搜索
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            SceneMap 对象列表
        """
        return self.session.query(SceneMap).filter(
            SceneMap.scene_name.like(f'%{keyword}%')
        ).order_by(SceneMap.scene_code).all()
    
    def exists_by_code(self, scene_code: str) -> bool:
        """
        检查场景代码是否存在
        
        Args:
            scene_code: 场景代码
        
        Returns:
            是否存在
        """
        return self.session.query(SceneMap).filter(
            SceneMap.scene_code == scene_code
        ).count() > 0


# ==================== 导出 ====================

__all__ = ['SceneMapRepository']
