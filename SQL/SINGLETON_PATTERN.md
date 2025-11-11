# DatabaseManager 单例模式详解

## 📋 目录

- [初始化位置](#初始化位置)
- [单例模式实现](#单例模式实现)
- [完整调用链](#完整调用链)
- [核心机制](#核心机制)
- [验证测试](#验证测试)
- [常见问题](#常见问题)

---

## 🎯 初始化位置

### 当前唯一初始化点

```python
# 📁 SQL/example_query.py (第39行)

import os
from database import init_database

# 1️⃣ 设置环境变量
os.environ['DB_HOST'] = '192.168.0.106'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'omuser@tellmua100#obhfcgb03uat'
os.environ['DB_PASSWORD'] = 'OceanBase_123#'
os.environ['DB_NAME'] = 'omservice'

# 2️⃣ 初始化数据库连接（程序启动时调用一次）
print("⚙️  正在初始化数据库连接...")
try:
    init_database()  # ← 唯一调用点
    print("✅ 数据库连接初始化成功\n")
except Exception as e:
    print(f"❌ 数据库初始化失败: {e}")
    sys.exit(1)

# 3️⃣ 之后直接使用 Service，无需再次初始化
codes = SceneMapService.get_scene_codes()
details = SceneMapService.get_scene_details()
```

### 执行时序

```
程序启动
  ↓
┌────────────────────────────────────┐
│  example_query.py 开始执行         │
└────────────────────────────────────┘
  ↓
┌────────────────────────────────────┐
│  设置环境变量                       │
│  - DB_HOST                         │
│  - DB_PORT                         │
│  - DB_USER                         │
│  - DB_PASSWORD                     │
│  - DB_NAME                         │
└────────────────────────────────────┘
  ↓
┌────────────────────────────────────┐
│  调用 init_database()  ← 第39行    │
└────────────────────────────────────┘
  ↓
┌────────────────────────────────────┐
│  创建 DatabaseManager 单例实例      │
│  创建连接池（QueuePool）            │
│  创建会话工厂（SessionMaker）       │
└────────────────────────────────────┘
  ↓
┌────────────────────────────────────┐
│  执行业务查询                       │
│  - example_1_simple_query()        │
│  - example_2_filtered_query()      │
│  - ...                             │
└────────────────────────────────────┘
  ↓
程序结束
```

---

## 🔐 单例模式实现

### Python `__new__` 方法实现

[`DatabaseManager`](database.py) 使用 Python 的 `__new__` 特殊方法实现单例模式：

```python
# 📁 SQL/database.py

class DatabaseManager:
    """
    数据库连接管理器 - 单例模式
    
    使用 __new__ 方法确保全局只有一个实例
    """
    
    # ====== 类级别变量（所有实例共享） ======
    _instance: Optional['DatabaseManager'] = None
    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None
    _config: Optional[DatabaseConfig] = None
    
    def __new__(cls) -> 'DatabaseManager':
        """
        🔑 单例模式的核心实现
        
        __new__ 方法在 __init__ 之前调用
        负责创建并返回实例对象
        
        工作流程:
            1. 检查 cls._instance 是否为 None
            2. 如果为 None：创建新实例
            3. 如果不为 None：返回已存在的实例
        
        Returns:
            DatabaseManager 实例（总是同一个）
        """
        if cls._instance is None:
            # 第一次调用：创建新实例
            cls._instance = super().__new__(cls)
            print("[DEBUG] 创建 DatabaseManager 实例")
        else:
            # 后续调用：返回已存在的实例
            print("[DEBUG] 返回已存在的 DatabaseManager 实例")
        
        return cls._instance
```

### 为什么使用 `__new__` 而不是其他方式？

| 实现方式 | 优点 | 缺点 | 适用场景 |
|---------|------|------|---------|
| **`__new__` 方法** ✅ | 简洁、Pythonic、线程安全 | 需要理解 `__new__` 机制 | 推荐用于大多数场景 |
| 装饰器 | 灵活、可复用 | 需要额外代码 | 多个类需要单例时 |
| 元类 | 强大、灵活 | 复杂、过度设计 | 框架级别开发 |
| 模块级变量 | 简单、直观 | 不够面向对象 | 简单的全局配置 |

**我们选择 `__new__` 的原因：**
1. ✅ 简洁明了，易于理解
2. ✅ Python 官方推荐方式
3. ✅ 不需要额外的装饰器或元类
4. ✅ 与类的其他特性兼容良好

---

## 🔄 完整调用链

### 从用户代码到连接池的完整路径

```python
# ========== 层级1: 用户代码 ==========
# 📁 example_query.py
from database import init_database

init_database()  # ← 用户调用
```

```python
# ========== 层级2: 便捷函数 ==========
# 📁 database.py (第163行)

def init_database(config: Optional[DatabaseConfig] = None):
    """
    初始化数据库连接（便捷函数）
    
    封装了获取管理器和初始化的过程
    提供简洁的外部接口
    """
    manager = get_db_manager()  # ← 获取单例
    manager.initialize(config)   # ← 初始化连接池
```

```python
# ========== 层级3: 获取单例 ==========
# 📁 database.py (第153行)

def get_db_manager() -> DatabaseManager:
    """
    获取数据库管理器实例（单例）
    
    每次调用都返回同一个实例
    """
    return DatabaseManager()  # ← 触发 __new__
```

```python
# ========== 层级4: 单例创建 ==========
# 📁 database.py (第44行)

class DatabaseManager:
    _instance = None  # ← 类变量（全局共享）
    
    def __new__(cls) -> 'DatabaseManager':
        """单例模式实现"""
        if cls._instance is None:
            # 第一次：创建新实例
            cls._instance = super().__new__(cls)
        # 后续：返回已存在的实例
        return cls._instance
```

```python
# ========== 层级5: 初始化连接池 ==========
# 📁 database.py (第49行)

def initialize(self, config: Optional[DatabaseConfig] = None):
    """
    初始化数据库连接
    
    只在第一次调用时真正初始化
    后续调用会被忽略（防护机制）
    """
    if self._engine is not None:
        # 已初始化，直接返回
        return
    
    # 使用配置或默认配置
    self._config = config or get_default_config()
    
    # 🔥 创建数据库引擎（连接池）
    self._engine = create_engine(
        self._config.get_connection_url(),
        poolclass=QueuePool,
        pool_size=5,           # 初始连接数
        max_overflow=10,       # 最大溢出连接数
        pool_recycle=3600,     # 连接回收时间（秒）
        pool_pre_ping=True,    # 连接前检测
        echo=False,            # 不输出 SQL 日志
    )
    
    # 🔥 创建会话工厂
    self._session_factory = sessionmaker(
        bind=self._engine,
        expire_on_commit=False,
    )
```

```python
# ========== 层级6: SQLAlchemy 连接池 ==========
# SQLAlchemy QueuePool 自动管理连接

┌─────────────────────────────────────┐
│      QueuePool（连接池）             │
│                                     │
│  [连接1] [连接2] [连接3]            │
│  [连接4] [连接5]  ← pool_size=5     │
│                                     │
│  [连接6] ... [连接15]               │
│  ↑ max_overflow=10                  │
│                                     │
│  总计: 15 个并发连接                │
└─────────────────────────────────────┘
```

---

## ⚙️ 核心机制

### 1. 单例保证

```python
# 测试代码
manager1 = DatabaseManager()
manager2 = DatabaseManager()
manager3 = get_db_manager()

print(manager1 is manager2)  # ✅ True
print(manager2 is manager3)  # ✅ True
print(id(manager1) == id(manager2) == id(manager3))  # ✅ True
```

**原理：**
- `_instance` 是**类变量**，所有实例共享
- `__new__` 控制实例创建，只创建一次
- 后续调用直接返回已存在的实例

---

### 2. 初始化保护

```python
# 测试代码
init_database()  # 第1次：真正初始化
init_database()  # 第2次：检测到已初始化，直接返回
init_database()  # 第3次：检测到已初始化，直接返回

manager = get_db_manager()
print(manager.is_initialized())  # ✅ True
```

**原理：**
- `initialize()` 方法内部检查 `self._engine`
- 如果 `_engine` 不为 `None`，说明已初始化，直接返回
- 防止重复创建连接池

---

### 3. 状态共享

```python
# 测试代码
manager_a = get_db_manager()
manager_a.initialize()

manager_b = DatabaseManager()
print(manager_b.is_initialized())  # ✅ True（共享状态）

engine_a = manager_a.get_engine()
engine_b = manager_b.get_engine()
print(engine_a is engine_b)  # ✅ True（同一个 Engine）
```

**原理：**
- `_engine`、`_session_factory` 是类变量
- 所有实例共享相同的状态
- 在 A 实例上初始化，B 实例也能看到

---

### 4. 线程安全性

虽然当前实现没有显式的锁，但在 Python 中：

```python
# Python GIL（全局解释器锁）提供了基本的线程安全
class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:  # ← GIL 保护
            cls._instance = super().__new__(cls)
        return cls._instance
```

**如果需要更严格的线程安全：**

```python
from threading import Lock

class DatabaseManager:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:  # ← 双重检查锁定
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

---

## 🧪 验证测试

### 运行测试脚本

```bash
cd /home/llm/zhangle/deer-flow/SQL
python3 test_singleton.py
```

### 测试内容

1. **单例模式验证**：多次创建返回同一个实例
2. **初始化保护验证**：多次初始化不会重复创建 Engine
3. **状态共享验证**：所有实例共享相同的状态
4. **便捷函数验证**：`init_database()` 正常工作

### 预期输出

```
🔬 DatabaseManager 单例模式测试套件
============================================================

🧪 测试1: 单例模式验证
============================================================

manager1 is manager2: True
manager1 is manager3: True

manager1 id: 140123456789
manager2 id: 140123456789
manager3 id: 140123456789

✅ 单例模式验证通过：所有实例都是同一个对象

🧪 测试2: 初始化保护机制
============================================================

初始状态: is_initialized = False

第1次调用 initialize()...
  ✓ 初始化完成: is_initialized = True
  ✓ Engine 地址: 140123987654

第2次调用 initialize()...
  ✓ 状态保持: is_initialized = True
  ✓ Engine 地址: 140123987654

第3次调用 initialize()...
  ✓ 状态保持: is_initialized = True
  ✓ Engine 地址: 140123987654

✅ 初始化保护验证通过：多次调用不会重复创建 Engine

📊 测试结果汇总
============================================================
  单例模式     : ✅ 通过
  初始化保护   : ✅ 通过
  状态共享     : ✅ 通过
  便捷函数     : ✅ 通过

🎉 所有测试通过！单例模式实现正确。
============================================================
```

---

## ❓ 常见问题

### Q1: 为什么使用单例模式？

**A:** 数据库连接池应该全局唯一：
- ✅ 避免创建多个连接池（浪费资源）
- ✅ 所有模块共享同一个连接池（连接复用）
- ✅ 统一管理数据库连接（易于维护）

---

### Q2: 单例模式有什么缺点？

**A:** 单例模式的潜在问题：
- ❌ 全局状态，可能导致耦合
- ❌ 难以进行单元测试（需要 mock）
- ❌ 多线程环境需要特别注意

**我们的应对措施：**
- ✅ 提供 `close()` 方法，便于测试时重置
- ✅ 使用 `__new__` 实现，简洁且可靠
- ✅ 连接池本身是线程安全的

---

### Q3: 如何在测试中重置单例？

```python
# 测试代码
from database import get_db_manager

# 测试前：重置单例
manager = get_db_manager()
manager.close()
DatabaseManager._instance = None  # 重置单例

# 测试：重新初始化
init_database(test_config)
# ... 执行测试 ...

# 测试后：清理
manager.close()
DatabaseManager._instance = None
```

---

### Q4: 单例模式与依赖注入的区别？

| 特性 | 单例模式 | 依赖注入 |
|------|---------|---------|
| 创建方式 | 类内部控制 | 外部传入 |
| 灵活性 | 较低 | 较高 |
| 测试性 | 较难 | 较易 |
| 适用场景 | 全局资源管理 | 复杂依赖关系 |

**我们的选择：**
- 数据库连接池：使用单例模式（全局资源）
- 业务逻辑：可以考虑依赖注入（提高可测试性）

---

### Q5: 如何监控连接池状态？

```python
from database import get_db_manager

manager = get_db_manager()
engine = manager.get_engine()

if engine:
    pool = engine.pool
    print(f"连接池大小: {pool.size()}")
    print(f"当前使用连接数: {pool.checkedout()}")
    print(f"溢出连接数: {pool.overflow()}")
```

---

## 📚 相关文档

- [INIT_DATABASE_EXPLAINED.md](./INIT_DATABASE_EXPLAINED.md) - init_database() 详解
- [BEST_PRACTICES.md](./BEST_PRACTICES.md) - 最佳实践指南
- [EXCEPTION_HANDLING.md](./EXCEPTION_HANDLING.md) - 异常处理机制
- [USAGE.md](./USAGE.md) - API 使用指南

---

## 🎓 延伸阅读

### Python 单例模式的其他实现方式

#### 方式1: 装饰器实现

```python
def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class DatabaseManager:
    pass
```

#### 方式2: 元类实现

```python
class SingletonMeta(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class DatabaseManager(metaclass=SingletonMeta):
    pass
```

#### 方式3: 模块级单例

```python
# database.py
class _DatabaseManager:
    pass

# 模块级单例
db_manager = _DatabaseManager()

# 外部导入
from database import db_manager
```

**我们选择 `__new__` 的原因：**
- 简洁、直观、易于理解
- 不需要额外的装饰器或元类
- Python 官方推荐的方式
