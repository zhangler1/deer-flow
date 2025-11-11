# 🔍 init_database() 详细解析

## 📋 函数定义

```python
def init_database(config: Optional[DatabaseConfig] = None):
    """
    初始化数据库连接（便捷函数）
    
    Args:
        config: 数据库配置
    """
    manager = get_db_manager()
    manager.initialize(config)
```

**位置**: [database.py](./database.py#L163-L171)

## 🎯 核心功能

`init_database()` 的作用是**初始化数据库连接池和会话工厂**，为后续的数据库操作做准备。

## 📊 执行流程图

```
init_database() 调用
    ↓
获取单例的 DatabaseManager 实例
    ↓
调用 manager.initialize(config)
    ↓
┌─────────────────────────────────────┐
│  DatabaseManager.initialize()       │
├─────────────────────────────────────┤
│ 1. 检查是否已初始化                │
│    if self._engine is not None:    │
│        return  # 已初始化，直接返回 │
│                                     │
│ 2. 加载配置                        │
│    config = config or 从环境变量加载│
│    ↓                                │
│    从环境变量读取:                  │
│    - DB_HOST → host                │
│    - DB_PORT → port                │
│    - DB_USER → user                │
│    - DB_PASSWORD → password        │
│    - DB_NAME → database            │
│    - DB_POOL_SIZE → pool_size      │
│    等等...                          │
│                                     │
│ 3. 生成连接字符串                  │
│    mysql+pymysql://user:pass@      │
│    host:port/database?charset=...  │
│                                     │
│ 4. 创建 SQLAlchemy Engine          │
│    ↓                                │
│    使用 QueuePool 连接池            │
│    - pool_size=5 (默认)            │
│    - max_overflow=10               │
│    - pool_recycle=3600秒           │
│    - pool_pre_ping=True            │
│                                     │
│ 5. 创建 SessionMaker 工厂          │
│    用于后续创建数据库会话           │
└─────────────────────────────────────┘
    ↓
初始化完成！✅
可以调用 get_session() 进行查询
```

## 🔧 详细步骤解析

### 步骤1: 获取数据库管理器（单例模式）

```python
manager = get_db_manager()  # 返回 DatabaseManager 单例实例
```

**作用**: 确保整个应用只有一个数据库管理器实例，避免重复创建连接。

**单例实现**:
```python
class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    
    def __new__(cls) -> 'DatabaseManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### 步骤2: 加载数据库配置

```python
self._config = config or get_default_config()
```

**从环境变量加载** (如果没有传入 config):

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `DB_HOST` | localhost | 数据库主机地址 |
| `DB_PORT` | 3306 | 数据库端口 |
| `DB_USER` | root | 数据库用户名 |
| `DB_PASSWORD` | (空) | 数据库密码 |
| `DB_NAME` | omservice | 数据库名称 |
| `DB_CHARSET` | utf8mb4 | 字符集 |
| `DB_POOL_SIZE` | 5 | 连接池大小 |
| `DB_MAX_OVERFLOW` | 10 | 最大溢出连接数 |
| `DB_POOL_RECYCLE` | 3600 | 连接回收时间（秒）|
| `DB_POOL_PRE_PING` | true | 使用前测试连接 |
| `DB_ECHO_SQL` | false | 是否打印 SQL |

**实际代码**:
```python
def load_config_from_env() -> DatabaseConfig:
    return DatabaseConfig(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'omservice'),
        charset=os.getenv('DB_CHARSET', 'utf8mb4'),
        # ... 其他配置
    )
```

### 步骤3: 生成数据库连接 URL

```python
connection_url = self._config.get_connection_url()
# 结果示例: 
# mysql+pymysql://omuser@tellmua100#obhfcgb03uat:OceanBase_123#@192.168.0.106:3306/omservice?charset=utf8mb4
```

**URL 格式**:
```
mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=字符集
```

### 步骤4: 创建 SQLAlchemy Engine（数据库引擎）

```python
self._engine = create_engine(
    connection_url,
    poolclass=QueuePool,           # 使用队列连接池
    pool_size=5,                   # 连接池保持5个连接
    max_overflow=10,               # 最多可以额外创建10个连接
    pool_recycle=3600,             # 连接1小时后回收
    pool_pre_ping=True,            # 使用前先ping测试
    echo=False,                    # 不打印SQL（生产环境）
)
```

**连接池工作原理**:

```
应用程序
    ↓
请求连接
    ↓
┌──────────────────────────────────┐
│  QueuePool (连接池)              │
├──────────────────────────────────┤
│  [连接1] [连接2] [连接3]         │ ← pool_size=5
│  [连接4] [连接5]                 │   (预先创建5个)
│                                  │
│  需要时额外创建:                 │
│  [连接6] ... [连接15]            │ ← max_overflow=10
│                                  │   (最多再创建10个)
│                                  │
│  总最大连接数 = 5 + 10 = 15      │
└──────────────────────────────────┘
    ↓
连接使用完后归还给池
```

**连接回收机制**:
- `pool_recycle=3600`: 连接使用超过1小时后会被回收重建
- `pool_pre_ping=True`: 从池中取出连接前，先 ping 数据库确保连接有效

### 步骤5: 创建 SessionMaker（会话工厂）

```python
self._session_factory = sessionmaker(
    bind=self._engine,
    expire_on_commit=False,  # 提交后对象不过期
)
```

**作用**: 创建一个会话工厂，用于后续生成数据库会话（Session）。

## 💡 为什么需要 init_database()？

### ❌ 不调用会怎样？

```python
from SQL.services import SceneMapService

# 直接查询，不初始化
codes = SceneMapService.get_scene_codes(repository='EUVD')
# ❌ RuntimeError: 数据库未初始化，请先调用 initialize() 方法
```

### ✅ 正确使用

```python
from SQL.database import init_database
from SQL.services import SceneMapService

# 1. 先初始化
init_database()

# 2. 再查询
codes = SceneMapService.get_scene_codes(repository='EUVD')
# ✅ 正常返回数据
```

## 🔄 调用链路

```
用户代码
  ↓
init_database()
  ↓
get_db_manager()  → 返回 DatabaseManager 单例
  ↓
manager.initialize(config)
  ↓
1. 从环境变量加载配置
2. 创建 SQLAlchemy Engine (连接池)
3. 创建 SessionMaker (会话工厂)
  ↓
初始化完成
  ↓
后续可以调用:
  ↓
get_session() → 从 SessionMaker 创建 Session
  ↓
SceneMapService.get_scene_codes()
  ↓
  with get_session() as session:
      ↓
  从连接池获取连接
      ↓
  执行 SQL 查询
      ↓
  返回结果
      ↓
  归还连接到池
```

## 📝 实际示例

### 示例1: 最简单的使用

```python
import os
from SQL.database import init_database
from SQL.services import SceneMapService

# 设置环境变量
os.environ['DB_HOST'] = '192.168.0.106'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'omuser@tellmua100#obhfcgb03uat'
os.environ['DB_PASSWORD'] = 'OceanBase_123#'
os.environ['DB_NAME'] = 'omservice'

# 初始化数据库（只需调用一次）
init_database()

# 后续可以多次查询
codes = SceneMapService.get_scene_codes(repository='EUVD')
details = SceneMapService.get_scene_details(repository='EUVD')
scene = SceneMapService.get_scene_by_code('DEMO_EUVD_001')
```

### 示例2: 使用自定义配置

```python
from SQL.database import init_database
from SQL.config import DatabaseConfig

# 创建自定义配置
custom_config = DatabaseConfig(
    host='192.168.0.106',
    port=3306,
    user='omuser@tellmua100#obhfcgb03uat',
    password='OceanBase_123#',
    database='omservice',
    pool_size=10,        # 自定义连接池大小
    max_overflow=20,     # 自定义最大溢出
)

# 使用自定义配置初始化
init_database(config=custom_config)
```

### 示例3: 检查是否已初始化

```python
from SQL.database import get_db_manager

manager = get_db_manager()

if manager.is_initialized():
    print("✅ 数据库已初始化")
else:
    print("❌ 数据库未初始化")
    init_database()
```

## ⚙️ 连接池的优势

### 🚫 不使用连接池（每次查询都创建新连接）

```python
# 查询1
连接1 = 创建新连接()  # 耗时 100ms
执行查询
关闭连接1

# 查询2
连接2 = 创建新连接()  # 耗时 100ms
执行查询
关闭连接2

# 查询3
连接3 = 创建新连接()  # 耗时 100ms
执行查询
关闭连接3

总耗时 = 300ms (创建连接) + 查询时间
```

### ✅ 使用连接池

```python
# 初始化时
init_database()  # 预先创建 5 个连接，耗时 500ms（只执行一次）

# 查询1
连接1 = 从池中获取()  # 耗时 < 1ms
执行查询
归还连接1到池

# 查询2
连接1 = 从池中获取()  # 耗时 < 1ms（复用连接1）
执行查询
归还连接1到池

# 查询3
连接1 = 从池中获取()  # 耗时 < 1ms（复用连接1）
执行查询
归还连接1到池

总耗时 = 500ms (初始化，只一次) + 查询时间
每次查询几乎无连接开销！
```

## 🎓 关键要点总结

1. **必须先初始化**: 使用任何数据库查询前，必须先调用 `init_database()`
2. **只需初始化一次**: 由于单例模式，多次调用不会重复创建连接
3. **自动管理连接**: 连接池自动管理连接的创建、复用和回收
4. **线程安全**: SQLAlchemy 的连接池是线程安全的
5. **自动重连**: `pool_pre_ping=True` 确保连接有效，自动重连
6. **资源优化**: 连接复用大大减少了数据库连接开销

## 🐛 常见问题

### Q1: 为什么要用单例模式？
**A**: 确保全局只有一个连接池，避免创建多个连接池浪费资源。

### Q2: 可以多次调用 init_database() 吗？
**A**: 可以，但只有第一次调用会真正初始化，后续调用会被忽略。

### Q3: 连接池满了会怎样？
**A**: 会等待其他查询释放连接，或者如果有 `max_overflow` 配置，会临时创建新连接。

### Q4: 如何关闭数据库连接？
**A**: 应用退出时调用 `manager.close()` 释放所有连接。

## 📚 相关文档

- [database.py](./database.py) - 数据库连接层实现
- [config.py](./config.py) - 配置管理
- [services.py](./services.py) - 业务逻辑层
- [EXCEPTION_HANDLING.md](./EXCEPTION_HANDLING.md) - 异常处理说明

---

**创建时间**: 2025-11-11  
**维护者**: DeerFlow Team
