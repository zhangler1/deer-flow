# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Dict, List, Optional
from dataclasses import dataclass

from .loader import load_yaml_config


@dataclass
class CustomSearchRepository:
    """自定义搜索引擎的Repository配置"""
    name: str
    description: str
    repository: str
    channel_id: str = "0"


class CustomSearchConfig:
    """自定义搜索引擎配置管理器"""
    
    def __init__(self, config_file: str = "conf.yaml"):
        self.config_file = config_file
        self._repositories = {}
        self._default_repository = None
        self._load_config()
    
    def _load_config(self) -> None:
        """从配置文件加载自定义搜索配置"""
        config = load_yaml_config(self.config_file)
        custom_search_config = config.get("CUSTOM_SEARCH", {})
        
        # 加载repositories配置
        repositories_config = custom_search_config.get("repositories", {})
        for repo_id, repo_config in repositories_config.items():
            self._repositories[repo_id] = CustomSearchRepository(
                name=repo_config.get("name", repo_id),
                description=repo_config.get("description", ""),
                repository=repo_config.get("repository", repo_id),
                channel_id=repo_config.get("channel_id", "0")
            )
        
        # 设置默认repository
        self._default_repository = custom_search_config.get("default_repository", "aggregation_search")
        
        # 如果没有配置repositories，使用默认配置
        if not self._repositories:
            self._load_default_repositories()
    
    def _load_default_repositories(self) -> None:
        """加载默认的repository配置"""
        default_repos = {
            "aggregation_search": CustomSearchRepository(
                name="聚合搜索",
                description="聚合多个数据源的搜索服务",
                repository="aggregation-search",
                channel_id="0"
            ),
            "vector_search": CustomSearchRepository(
                name="向量库",
                description="基于向量相似度的搜索服务",
                repository="euvd-searchByChannelId",
                channel_id="0"
            ),
            "dynamic_search": CustomSearchRepository(
                name="交行知道",
                description="交通银行内部知识库搜索",
                repository="okic-dynamicSearch",
                channel_id="0"
            )
        }
        self._repositories = default_repos
        self._default_repository = "aggregation_search"
    
    def get_repositories(self) -> Dict[str, CustomSearchRepository]:
        """获取所有可用的repository配置"""
        return self._repositories.copy()
    
    def get_repository(self, repo_id: str) -> Optional[CustomSearchRepository]:
        """根据ID获取特定的repository配置"""
        return self._repositories.get(repo_id)
    
    def get_default_repository(self) -> Optional[CustomSearchRepository]:
        """获取默认的repository配置"""
        if self._default_repository and self._default_repository in self._repositories:
            return self._repositories[self._default_repository]
        elif self._repositories:
            # 如果默认repository不存在，返回第一个可用的
            return next(iter(self._repositories.values()))
        return None
    
    def get_repository_choices(self) -> List[Dict[str, str]]:
        """获取repository选择列表（用于前端显示）"""
        choices = []
        for repo_id, repo in self._repositories.items():
            choices.append({
                "id": repo_id,
                "name": repo.name,
                "description": repo.description,
                "repository": repo.repository
            })
        return choices


# 全局配置实例
_custom_search_config: Optional[CustomSearchConfig] = None


def get_custom_search_config() -> CustomSearchConfig:
    """获取全局自定义搜索配置实例"""
    global _custom_search_config
    if _custom_search_config is None:
        _custom_search_config = CustomSearchConfig()
    return _custom_search_config


def reload_custom_search_config() -> None:
    """重新加载自定义搜索配置"""
    global _custom_search_config
    _custom_search_config = None