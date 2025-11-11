#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接层 (Database Connection)

管理数据库引擎和会话
使用单例模式和连接池优化性能
"""

from contextlib import contextmanager
from typing import Optional, Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .config import DatabaseConfig, get_default_config


# ==================== 数据库管理器 ====================

class DatabaseManager:
    """
    数据库连接管理器
    
    职责:
        - 管理数据库引擎（Engine）
        - 管理会话工厂（SessionMaker）
        - 提供会话上下文管理器
        - 实现单例模式，避免重复创建连接
    
    设计模式:
        - Singleton Pattern: 确保全局只有一个数据库管理器实例
        - Factory Pattern: 使用 SessionMaker 工厂创建会话
        - Context Manager: 提供 with 语句支持
    """
    
    _instance: Optional['DatabaseManager'] = None
    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None
    _config: Optional[DatabaseConfig] = None
    
    def __new__(cls) -> 'DatabaseManager':
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, config: Optional[DatabaseConfig] = None):
        """
        初始化数据库连接
        
        Args:
            config: 数据库配置，如果为 None 则使用默认配置
        
        Note:
            此方法可以多次调用，但只有第一次调用会真正初始化引擎
        """
        if self._engine is not None:
            # 已经初始化过，直接返回
            return
        
        # 使用提供的配置或默认配置
        self._config = config or get_default_config()
        
        # 创建数据库引擎
        self._engine = create_engine(
            self._config.get_connection_url(),
            poolclass=QueuePool,
            pool_size=self._config.pool_size,
            max_overflow=self._config.max_overflow,
            pool_recycle=self._config.pool_recycle,
            pool_pre_ping=self._config.pool_pre_ping,
            echo=self._config.echo_sql,
        )
        
        # 创建会话工厂
        self._session_factory = sessionmaker(
            bind=self._engine,
            expire_on_commit=False,  # 提交后对象不过期
        )
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取数据库会话（上下文管理器）
        
        提供事务管理:
            - 自动提交成功的事务
            - 自动回滚失败的事务
            - 自动关闭会话
        
        Yields:
            Session: SQLAlchemy 会话对象
        
        Raises:
            RuntimeError: 如果数据库未初始化
        
        Example:
            >>> manager = DatabaseManager()
            >>> manager.initialize()
            >>> with manager.get_session() as session:
            ...     scenes = session.query(SceneMap).all()
        """
        if self._session_factory is None:
            raise RuntimeError(
                "数据库未初始化，请先调用 initialize() 方法"
            )
        
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        """
        关闭数据库连接
        
        释放所有数据库资源
        通常在应用退出时调用
        """
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._config = None
    
    def get_engine(self) -> Optional[Engine]:
        """
        获取数据库引擎
        
        Returns:
            Engine 实例，如果未初始化则返回 None
        """
        return self._engine
    
    def is_initialized(self) -> bool:
        """
        检查是否已初始化
        
        Returns:
            是否已初始化
        """
        return self._engine is not None


# ==================== 便捷函数 ====================

def get_db_manager() -> DatabaseManager:
    """
    获取数据库管理器实例（单例）
    
    Returns:
        DatabaseManager 实例
    """
    return DatabaseManager()


def init_database(config: Optional[DatabaseConfig] = None):
    """
    初始化数据库连接（便捷函数）
    
    Args:
        config: 数据库配置
    """
    manager = get_db_manager()
    manager.initialize(config)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    获取数据库会话（便捷函数）
    
    Yields:
        Session: SQLAlchemy 会话对象
    
    Example:
        >>> from database import get_session
        >>> with get_session() as session:
        ...     scenes = session.query(SceneMap).all()
    """
    manager = get_db_manager()
    with manager.get_session() as session:
        yield session


# ==================== 导出 ====================

__all__ = [
    'DatabaseManager',
    'get_db_manager',
    'init_database',
    'get_session',
]
