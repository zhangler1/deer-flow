# Scene Map 查询工具 - 模块化架构说明

## 📦 目录结构

```
SQL/
├── models.py              # 数据库模型层 (ORM Models)
├── config.py              # 配置管理层 (Configuration)
├── database.py            # 数据库连接层 (Database Connection)
├── repositories.py        # 数据访问层 (Repository Pattern)
├── services.py            # 业务逻辑层 (Service Layer)
├── utils.py               # 工具函数层 (Utilities)
├── cli.py                 # 命令行工具 (CLI)
├── __init__.py            # 包初始化 (Public API)
├── ddl.sql                # 数据库表结构
├── .env.example           # 环境变量示例
└── MODULE_STRUCTURE.md    # 本文档
```

## 🏗️ 分层架构设计

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    CLI / 应用层                          │
│                      (cli.py)                            │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────┐
│                   业务逻辑层                             │
│                  (services.py)                           │
│   - SceneMapService                                      │
│   - 封装业务逻辑                                         │
│   - 事务管理                                             │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────┐
│                   数据访问层                             │
│               (repositories.py)                          │
│   - SceneMapRepository                                   │
│   - CRUD 操作                                            │
│   - 查询封装                                             │
└───┬─────────────────────────────────────────────────┬───┘
    │                                                 │
┌───┴────────────────────┐              ┌────────────┴────┐
│    数据库连接层         │              │   ORM 模型层     │
│    (database.py)       │              │   (models.py)    │
│  - DatabaseManager     │              │  - SceneMap      │
│  - 连接池管理          │              │  - Base          │
│  - 会话管理            │              │                  │
└───┬────────────────────┘              └─────────────────┘
    │
┌───┴────────────────────┐
│      配置管理层         │
│     (config.py)        │
│  - DatabaseConfig      │
│  - 环境变量加载        │
└────────────────────────┘
```

## 📚 模块职责说明

### 1. models.py - 数据库模型层

**职责:**
- 定义 ORM 模型（SceneMap）
- 映射数据库表结构到 Python 类
- 提供类型安全的数据访问

**核心类:**
```python
class SceneMap(Base):
    """scene_map 表的 ORM 映射"""
    - 字段定义（scene_code, scene_name, repository 等）
    - to_dict(): 转换为字典
    - to_dict_full(): 完整字典
    - is_active: 是否活跃
    - has_template: 是否有模板
```

**设计模式:**
- Active Record Pattern (SQLAlchemy ORM)

---

### 2. config.py - 配置管理层

**职责:**
- 管理数据库配置
- 支持多种配置源（环境变量、字典、文件）
- 生成数据库连接 URL

**核心类:**
```python
@dataclass
class DatabaseConfig:
    """数据库配置类"""
    - host, port, user, password, database
    - pool_size, max_overflow, pool_recycle
    - to_dict(): 转换为字典
    - get_connection_url(): 生成连接 URL
```

**核心函数:**
```python
load_config_from_env()      # 从环境变量加载
load_config_from_dict()     # 从字典加载
get_default_config()        # 获取默认配置
```

---

### 3. database.py - 数据库连接层

**职责:**
- 管理数据库引擎（Engine）
- 管理会话工厂（SessionMaker）
- 提供会话上下文管理器
- 连接池管理

**核心类:**
```python
class DatabaseManager:
    """数据库连接管理器（单例模式）"""
    - initialize(config): 初始化连接
    - get_session(): 获取会话（上下文管理器）
    - close(): 关闭连接
```

**便捷函数:**
```python
get_db_manager()    # 获取管理器实例
init_database()     # 初始化数据库
get_session()       # 获取会话
```

**设计模式:**
- Singleton Pattern: 单例模式
- Context Manager Pattern: 上下文管理器
- Connection Pool: 连接池

---

### 4. repositories.py - 数据访问层

**职责:**
- 封装数据库访问逻辑
- 提供 CRUD 操作
- 复杂查询封装
- 返回领域对象

**核心类:**
```python
class SceneMapRepository:
    """SceneMap 数据访问层"""
    
    # 基础 CRUD
    - find_by_code(scene_code): 根据代码查询
    - find_all(): 查询所有
    - save(scene): 保存
    - delete(scene): 删除
    
    # 条件查询
    - find_by_repository(repository, status, ...): 按知识库查询
    - find_by_model(model): 按模型查询
    - find_active_scenes(): 查询活跃场景
    - find_with_template(): 查询有模板的场景
    
    # 统计查询
    - count_all(): 统计总数
    - count_by_repository(...): 按知识库统计
    - count_by_status(status): 按状态统计
    
    # 高级查询
    - find_by_codes(scene_codes): 批量查询
    - search_by_name(keyword): 名称搜索
    - exists_by_code(scene_code): 检查存在
```

**设计模式:**
- Repository Pattern: 仓储模式
- DAO Pattern: 数据访问对象

---

### 5. services.py - 业务逻辑层

**职责:**
- 封装业务逻辑
- 协调多个 Repository
- 提供面向应用的接口
- 处理事务边界
- 数据转换（ORM → Dict）

**核心类:**
```python
class SceneMapService:
    """业务逻辑层（所有方法都是静态方法）"""
    
    # 核心业务接口
    - get_scene_codes(...): 获取代码列表
    - get_scene_details(...): 获取详细信息
    - get_scene_by_code(...): 查询单个场景
    - count_scenes(...): 统计数量
    
    # 扩展业务接口
    - get_active_scenes(): 获取活跃场景
    - search_scenes_by_name(keyword): 搜索场景
    - get_scenes_by_codes(codes): 批量查询
    - get_repository_summary(): 统计摘要
```

**设计模式:**
- Service Layer Pattern: 服务层模式
- Facade Pattern: 外观模式

---

### 6. utils.py - 工具函数层

**职责:**
- 提供通用工具函数
- 格式化输出
- 数据转换

**核心函数:**
```python
# 格式化输出
print_scene_codes(codes, title)         # 打印代码列表
print_scene_details(scenes, ...)        # 打印详细信息
print_summary(repository, total, ...)   # 打印摘要
print_repository_summary(summary)       # 打印统计

# 数据转换
export_to_dict(scenes)                  # 转换为字典
extract_codes(scenes)                   # 提取代码
filter_by_status(scenes, status)        # 过滤场景
group_by_repository(scenes)             # 分组
```

---

### 7. cli.py - 命令行工具

**职责:**
- 提供命令行接口
- 演示功能使用
- 快速测试

**使用方式:**
```bash
python3 cli.py
```

---

### 8. __init__.py - 包初始化

**职责:**
- 导出公共 API
- 提供便捷访问接口

**导出内容:**
```python
# 核心函数
from SQL import (
    get_scene_codes,
    get_scene_details,
    get_scene_by_code,
    count_scenes,
)

# 配置类
from SQL import DatabaseConfig, load_config_from_env

# 工具函数
from SQL import print_scene_codes, print_scene_details
```

## 🎯 设计原则

### 1. 单一职责原则 (SRP)
每个模块只负责一个明确的功能：
- `models.py` - 只负责 ORM 定义
- `database.py` - 只负责连接管理
- `repositories.py` - 只负责数据访问
- `services.py` - 只负责业务逻辑

### 2. 依赖倒置原则 (DIP)
高层模块不依赖低层模块：
```
services (高层) → repositories (低层) → models (底层)
```

### 3. 开闭原则 (OCP)
对扩展开放，对修改关闭：
- 新增查询方法：在 Repository 层添加
- 新增业务逻辑：在 Service 层添加
- 不修改现有代码

### 4. 接口隔离原则 (ISP)
提供细粒度的接口：
- Service 层提供特定业务接口
- Repository 层提供专门的查询接口

### 5. 关注点分离 (SoC)
- **数据访问** → repositories.py
- **业务逻辑** → services.py
- **配置管理** → config.py
- **连接管理** → database.py

## 📖 使用示例

### 示例 1: 基础使用

```python
from SQL import get_scene_codes

# 查询场景代码
codes = get_scene_codes(repository='EUVD')
print(codes)
```

### 示例 2: 自定义配置

```python
from SQL import DatabaseConfig, get_scene_details

# 自定义数据库配置
config = DatabaseConfig(
    host='192.168.1.100',
    port=3306,
    user='app_user',
    password='secret',
    database='production_db'
)

# 使用自定义配置查询
details = get_scene_details(
    repository='EUVD',
    db_config=config
)
```

### 示例 3: 直接使用 Service 层

```python
from SQL.services import SceneMapService

# 使用 Service 层的所有方法
codes = SceneMapService.get_scene_codes(repository='EUVD')
details = SceneMapService.get_scene_details(repository='EUVD')
count = SceneMapService.count_scenes(repository='EUVD')
```

### 示例 4: 直接使用 Repository 层

```python
from SQL.database import get_session
from SQL.repositories import SceneMapRepository

# 直接使用 Repository（更底层的控制）
with get_session() as session:
    repo = SceneMapRepository(session)
    
    # 使用 Repository 的各种查询方法
    scenes = repo.find_by_repository('EUVD')
    active = repo.find_active_scenes()
    count = repo.count_all()
```

## 🔄 数据流转

```
┌──────────┐
│   CLI    │  命令行调用
└────┬─────┘
     │
     ▼
┌────────────┐
│  Services  │  业务逻辑处理
└─────┬──────┘
      │
      ▼
┌──────────────┐
│ Repositories │  数据访问
└──────┬───────┘
       │
       ▼
┌──────────┐
│ Database │  数据库会话
└────┬─────┘
     │
     ▼
┌────────┐
│  MySQL │  数据库
└────────┘
```

## 🎨 命名规范

### 文件命名
- **models.py** - 复数形式，包含多个模型定义
- **repositories.py** - 复数形式，包含多个 Repository
- **services.py** - 复数形式，包含多个 Service
- **utils.py** - 复数形式，包含多个工具函数
- **config.py** - 单数形式，配置管理
- **database.py** - 单数形式，数据库管理
- **cli.py** - 单数形式，命令行工具

### 类命名
- **Model**: `SceneMap`
- **Repository**: `SceneMapRepository`
- **Service**: `SceneMapService`
- **Config**: `DatabaseConfig`
- **Manager**: `DatabaseManager`

## 🔧 扩展指南

### 添加新的查询方法

**步骤 1: 在 Repository 层添加查询方法**
```python
# repositories.py
def find_by_custom_condition(self, ...):
    return self.session.query(SceneMap).filter(...).all()
```

**步骤 2: 在 Service 层封装业务逻辑**
```python
# services.py
@staticmethod
def get_custom_data(...):
    with get_session() as session:
        repo = SceneMapRepository(session)
        scenes = repo.find_by_custom_condition(...)
        return [scene.to_dict() for scene in scenes]
```

**步骤 3: 在 __init__.py 导出（可选）**
```python
# __init__.py
from .services import SceneMapService
get_custom_data = SceneMapService.get_custom_data
```

### 添加新的模型

**步骤 1: 在 models.py 添加新模型**
```python
class NewModel(Base):
    __tablename__ = 'new_table'
    # 字段定义...
```

**步骤 2: 创建对应的 Repository**
```python
# repositories.py
class NewModelRepository:
    # CRUD 方法...
```

**步骤 3: 创建对应的 Service**
```python
# services.py
class NewModelService:
    # 业务逻辑...
```

## 📊 性能优化

### 1. 连接池配置
```python
config = DatabaseConfig(
    pool_size=10,       # 增加连接池大小
    max_overflow=20,    # 增加溢出连接数
    pool_recycle=1800,  # 缩短回收时间
)
```

### 2. 查询优化
- 使用 Repository 层的批量查询方法
- 避免 N+1 查询问题
- 合理使用 `to_dict(include_template=False)` 减少数据传输

### 3. 缓存策略
可以在 Service 层添加缓存逻辑

## 🧪 测试建议

### 单元测试结构
```
tests/
├── test_models.py         # 测试 ORM 模型
├── test_repositories.py   # 测试数据访问层
├── test_services.py       # 测试业务逻辑层
└── test_utils.py          # 测试工具函数
```

---

**创建时间**: 2025-11-10  
**版本**: 1.0.0
