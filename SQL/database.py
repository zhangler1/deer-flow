#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接层 (Database Connection)

管理数据库引擎和会话
使用单例模式和连接池优化性能
"""

from contextlib import contextmanager
from typing import Optional, Generator, Dict, Any

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from config import DatabaseConfig, get_default_config

# 轻量日志记录器（与增强日志系统解耦）
import logging
logger = logging.getLogger(__name__)


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
    
    def test_connection(self) -> bool:
        """快速连接测试：执行 SELECT 1 验证连接是否可用"""
        try:
            if self._engine is None:
                return False
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False

    def get_engine(self) -> Optional[Engine]:
        """获取数据库引擎（未初始化返回None）"""
        return self._engine

    def is_initialized(self) -> bool:
        """是否已初始化（存在Engine即视为已初始化）"""
        return self._engine is not None

    def close(self):
        """关闭并释放数据库资源"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._config = None


def get_db_status() -> Dict[str, Any]:
    """返回数据库当前状态（用于调试与确认）。不包含敏感信息。"""
    manager = DatabaseManager()
    engine = manager.get_engine()
    config = None
    try:
        # 私有属性仅用于调试展示（如有）
        config = getattr(manager, "_config", None)
    except Exception:
        config = None
    status = {
        "initialized": manager.is_initialized(),
        "can_connect": manager.test_connection() if manager.is_initialized() else False,
        "engine_present": engine is not None,
        "engine_url": str(engine.url) if engine else None,
    }
    # 附加非敏感配置（掩码用户信息）
    if config:
        masked_user = (config.user[:3] + "***") if config.user else None
        status.update({
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "user": masked_user,
            "echo_sql": config.echo_sql,
        })
    return status

# ==================== 便捷函数 ====================

def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例（单例）"""
    return DatabaseManager()


def init_database(config: Optional[DatabaseConfig] = None):
    """初始化数据库连接（便捷函数）"""
    manager = DatabaseManager()
    manager.initialize(config)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """获取数据库会话（便捷函数，带懒加载初始化）"""
    manager = DatabaseManager()
    # 懒加载初始化，避免“未初始化”报错
    if not manager.is_initialized():
        try:
            manager.initialize()
        except Exception as e:
            raise RuntimeError(f"数据库初始化失败，请检查连接配置与网络可达性: {e}") from e
    with manager.get_session() as session:
        yield session


# ==================== 导出 ====================

__all__ = [
    'DatabaseManager',
    'get_db_manager',
    'init_database',
    'get_session',
    'get_db_status',
]
