#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型层 (ORM Models)

定义数据库表结构的 ORM 映射
遵循 SQLAlchemy 声明式基类规范
"""

from typing import Dict, Any
from datetime import datetime

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Integer,
    Float,
    TIMESTAMP,
    Text,
    Boolean,
)
from sqlalchemy.orm import declarative_base


# ==================== 基类定义 ====================

Base = declarative_base()


# ==================== ORM 模型 ====================

class SceneMap(Base):
    """
    scene_map 表 ORM 模型
    
    映射数据库表结构到 Python 类对象
    提供类型安全的数据访问接口
    
    Attributes:
        scene_code: 场景代码（主键）
        scene_name: 场景名称
        description: 场景描述
        model: 使用的AI模型
        repository: 知识库类型
        prompt_template: 提示词模板
        status: 状态（1=正常，0=停用）
        create_time: 创建时间
        update_time: 更新时间
    """
    
    __tablename__ = 'scene_map'
    
    # ==================== 主键 ====================
    scene_code = Column(
        String(120),
        primary_key=True,
        comment='场景代码'
    )
    
    # ==================== 基本信息 ====================
    id = Column(
        BigInteger,
        autoincrement=True,
        comment='自增ID'
    )
    
    scene_name = Column(
        String(120),
        nullable=False,
        comment='场景名称'
    )
    
    description = Column(
        String(258),
        comment='场景描述'
    )
    
    # ==================== 模型配置 ====================
    model = Column(
        String(128),
        comment='当前使用的AI模型'
    )
    
    repository = Column(
        String(128),
        nullable=False,
        default='SPARK',
        comment='知识库类型（SPARK/EUVD等）'
    )
    
    prompt_template = Column(
        Text,
        comment='提示词模板'
    )
    
    # ==================== 知识库配置 ====================
    knowledge_es_name = Column(
        String(128),
        comment='盘古助手代码'
    )
    
    knowledge_code = Column(
        String(128),
        comment='星火助手代码'
    )
    
    space_codes = Column(
        String(256),
        comment='知识服务平台空间编码'
    )
    
    labels = Column(
        String(256),
        comment='向量库标签'
    )
    
    # ==================== LLM 参数配置 ====================
    top_k = Column(
        Integer,
        default=4,
        comment='从k个候选中随机选择，控制回答的随机性[1,6]'
    )
    
    max_tokens = Column(
        Integer,
        default=4096,
        comment='生成文本的最大token数量'
    )
    
    temperature = Column(
        Float,
        default=0.5,
        comment='控制生成文本的多样性和创造力(0, 1]'
    )
    
    embedding_top = Column(
        Integer,
        default=5,
        comment='向量召回条数[1-50]'
    )
    
    threshold_score = Column(
        Float,
        default=0,
        comment='相似度阈值'
    )
    
    qa_top = Column(
        Integer,
        default=0,
        comment='QA对召回条数'
    )
    
    qa_threshold_score = Column(
        Float,
        default=0.9,
        comment='QA对阈值'
    )
    
    # ==================== 状态与权限 ====================
    status = Column(
        String(1),
        default='1',
        comment='状态：1=正常，0=停用'
    )
    
    filter_type = Column(
        Boolean,
        default=False,
        comment='场景类型（0：非金服场景；1：金服场景）'
    )
    
    scene_type = Column(
        Boolean,
        default=False,
        comment='场景助手类型（0：普通；1：定制化；2：链接跳转）'
    )
    
    is_auth_verify = Column(
        Boolean,
        default=False,
        comment='是否开启用户机构权限校验'
    )
    
    # ==================== 时间戳 ====================
    create_time = Column(
        TIMESTAMP,
        default=datetime.now,
        comment='创建时间'
    )
    
    update_time = Column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        comment='更新时间'
    )
    
    # ==================== 辅助方法 ====================
    
    def __repr__(self) -> str:
        """对象字符串表示"""
        return (
            f"<SceneMap("
            f"code='{self.scene_code}', "
            f"name='{self.scene_name}', "
            f"repo='{self.repository}'"
            f")>"
        )
    
    def to_dict(self, include_template: bool = True) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Args:
            include_template: 是否包含 prompt_template（可能很大）
        
        Returns:
            字典格式的场景信息
        """
        result = {
            'scene_code': self.scene_code,
            'scene_name': self.scene_name,
            'description': self.description,
            'model': self.model,
            'repository': self.repository,
            'status': self.status,
            'create_time': self.create_time,
            'update_time': self.update_time,
        }
        
        if include_template:
            result['prompt_template'] = self.prompt_template
        
        return result
    
    def to_dict_full(self) -> Dict[str, Any]:
        """
        转换为完整字典格式（包含所有字段）
        
        Returns:
            包含所有字段的字典
        """
        return {
            'id': self.id,
            'scene_code': self.scene_code,
            'scene_name': self.scene_name,
            'description': self.description,
            'model': self.model,
            'repository': self.repository,
            'prompt_template': self.prompt_template,
            'knowledge_es_name': self.knowledge_es_name,
            'knowledge_code': self.knowledge_code,
            'space_codes': self.space_codes,
            'labels': self.labels,
            'top_k': self.top_k,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'embedding_top': self.embedding_top,
            'threshold_score': self.threshold_score,
            'qa_top': self.qa_top,
            'qa_threshold_score': self.qa_threshold_score,
            'status': self.status,
            'filter_type': self.filter_type,
            'scene_type': self.scene_type,
            'is_auth_verify': self.is_auth_verify,
            'create_time': self.create_time,
            'update_time': self.update_time,
        }
    
    @property
    def is_active(self) -> bool:
        """是否为活跃状态"""
        return bool(self.status == '1')
    
    @property
    def has_template(self) -> bool:
        """是否有提示词模板"""
        return bool(self.prompt_template and self.prompt_template.strip())


# ==================== 导出 ====================

__all__ = ['Base', 'SceneMap']
