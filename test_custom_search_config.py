#!/usr/bin/env python3
"""
测试自定义搜索引擎配置功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.custom_search import get_custom_search_config
from src.tools.custom_search import get_available_repositories, create_custom_search_with_repository

def test_custom_search_config():
    """测试自定义搜索配置"""
    print("🔍 测试自定义搜索引擎配置功能")
    print("=" * 50)
    
    # 测试配置加载
    try:
        config = get_custom_search_config()
        print("✅ 自定义搜索配置加载成功")
        
        # 获取可用的仓库
        repositories = config.get_repositories()
        print(f"📚 发现 {len(repositories)} 个可用仓库:")
        
        for repo_id, repo in repositories.items():
            print(f"  - {repo_id}: {repo.name} ({repo.description})")
            print(f"    Repository: {repo.repository}, Channel ID: {repo.channel_id}")
        
        # 测试默认仓库
        default_repo = config.get_default_repository()
        if default_repo:
            print(f"🎯 默认仓库: {default_repo.name} ({default_repo.repository})")
        
        # 测试API接口
        repo_choices = get_available_repositories()
        print(f"🌐 API 返回 {len(repo_choices)} 个仓库选择:")
        for choice in repo_choices:
            print(f"  - {choice['id']}: {choice['name']} - {choice['description']}")
        
        # 测试创建工具
        if repositories:
            first_repo_id = list(repositories.keys())[0]
            tool = create_custom_search_with_repository(first_repo_id)
            print(f"🔧 成功创建搜索工具，使用仓库: {first_repo_id}")
            print(f"   工具名称: {tool.name}")
        
        print("✅ 配置功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🦌 DeerFlow 自定义搜索引擎配置测试")
    print()
    
    # 检查配置文件是否存在
    config_file = "conf.yaml"
    if not os.path.exists(config_file):
        print(f"⚠️  配置文件 {config_file} 不存在，将使用默认配置")
    else:
        print(f"📄 使用配置文件: {config_file}")
    
    print()
    
    # 运行测试
    success = test_custom_search_config()
    
    print()
    print("=" * 50)
    if success:
        print("🎉 所有测试通过！配置功能正常工作。")
        print()
        print("📝 使用说明:")
        print("1. 修改 conf.yaml 文件中的 CUSTOM_SEARCH 配置")
        print("2. 在前端设置页面选择'自定义搜索引擎'")
        print("3. 根据配置的仓库选择不同的数据源")
        print("4. 不同仓库对应不同的检索服务:")
        print("   - aggregation-search: 聚合搜索")
        print("   - euvd-searchByChannelId: 向量库")
        print("   - okic-dynamicSearch: 交行知道")
    else:
        print("💥 测试失败，请检查配置和代码！")
        sys.exit(1)

if __name__ == "__main__":
    main()