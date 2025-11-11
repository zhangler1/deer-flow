#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理层 (Configuration)

管理数据库连接配置和应用配置
支持从环境变量、配置文件等多种来源加载配置
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


# ==================== 配置类定义 ====================

@dataclass
class DatabaseConfig:
    """
    数据库配置类
    
    使用 dataclass 提供类型安全的配置管理
    """
    
    # 连接配置
    host: str = 'localhost'
    port: int = 3306
    user: str = 'root'
    password: str = ''
    database: str = 'omservice'
    charset: str = 'utf8mb4'
    
    # 连接池配置
    pool_size: int = 5
    max_overflow: int = 10
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    
    # 日志配置
    echo_sql: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'database': self.database,
            'charset': self.charset,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_recycle': self.pool_recycle,
            'pool_pre_ping': self.pool_pre_ping,
            'echo_sql': self.echo_sql,
        }
    
    def get_connection_url(self) -> str:
        """
        生成数据库连接 URL
        
        Returns:
            SQLAlchemy 格式的数据库连接字符串
        """
        return (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
            f"?charset={self.charset}"
        )


# ==================== 配置加载函数 ====================

def load_config_from_env() -> DatabaseConfig:
    """
    从环境变量加载数据库配置
    
    支持的环境变量:
        - DB_HOST: 数据库主机地址
        - DB_PORT: 数据库端口
        - DB_USER: 数据库用户名
        - DB_PASSWORD: 数据库密码
        - DB_NAME: 数据库名称
        - DB_CHARSET: 字符集
        - DB_POOL_SIZE: 连接池大小
        - DB_MAX_OVERFLOW: 最大溢出连接数
        - DB_POOL_RECYCLE: 连接回收时间（秒）
        - DB_ECHO_SQL: 是否打印SQL（true/false）
    
    Returns:
        DatabaseConfig 实例
    """
    return DatabaseConfig(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'omservice'),
        charset=os.getenv('DB_CHARSET', 'utf8mb4'),
        pool_size=int(os.getenv('DB_POOL_SIZE', '5')),
        max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '10')),
        pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '3600')),
        pool_pre_ping=os.getenv('DB_POOL_PRE_PING', 'true').lower() == 'true',
        echo_sql=os.getenv('DB_ECHO_SQL', 'false').lower() == 'true',
    )


def load_config_from_dict(config_dict: Dict[str, Any]) -> DatabaseConfig:
    """
    从字典加载数据库配置
    
    Args:
        config_dict: 配置字典
    
    Returns:
        DatabaseConfig 实例
    """
    return DatabaseConfig(
        host=config_dict.get('host', 'localhost'),
        port=config_dict.get('port', 3306),
        user=config_dict.get('user', 'root'),
        password=config_dict.get('password', ''),
        database=config_dict.get('database', 'omservice'),
        charset=config_dict.get('charset', 'utf8mb4'),
        pool_size=config_dict.get('pool_size', 5),
        max_overflow=config_dict.get('max_overflow', 10),
        pool_recycle=config_dict.get('pool_recycle', 3600),
        pool_pre_ping=config_dict.get('pool_pre_ping', True),
        echo_sql=config_dict.get('echo_sql', False),
    )


def get_default_config() -> DatabaseConfig:
    """
    获取默认配置
    
    优先从环境变量加载，如果环境变量不存在则使用默认值
    
    Returns:
        DatabaseConfig 实例
    """
    return load_config_from_env()


# ==================== 导出 ====================

__all__ = [
    'DatabaseConfig',
    'load_config_from_env',
    'load_config_from_dict',
    'get_default_config',
]
