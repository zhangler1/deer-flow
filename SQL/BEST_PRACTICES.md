# 数据库使用最佳实践

## 📋 目录

- [初始化模式](#初始化模式)
- [单例模式优势](#单例模式优势)
- [使用场景](#使用场景)
- [完整示例](#完整示例)
- [性能对比](#性能对比)

---

## 🔧 初始化模式

### ✅ 推荐做法：程序启动时初始化一次

```python
import os
from database import init_database
from services import SceneMapService

# ==================== 主程序入口 ====================
def main():
    # 1️⃣ 【仅在程序启动时】设置环境变量
    os.environ['DB_HOST'] = '192.168.0.106'
    os.environ['DB_PORT'] = '3306'
    os.environ['DB_USER'] = 'omuser@tellmua100#obhfcgb03uat'
    os.environ['DB_PASSWORD'] = 'OceanBase_123#'
    os.environ['DB_NAME'] = 'omservice'
    
    # 2️⃣ 【仅在程序启动时】初始化数据库连接池
    print("⚙️  初始化数据库连接...")
    init_database()
    print("✅ 数据库连接池已就绪\n")
    
    # 3️⃣ 【无需再次初始化】直接使用 Service 查询
    # 查询多次，连接池自动复用
    for i in range(5):
        codes = SceneMapService.get_scene_codes(repository='EUVD')
        print(f"第 {i+1} 次查询: 找到 {len(codes)} 个场景")

if __name__ == '__main__':
    main()
```

**关键点：**
- ✅ `init_database()` 只在 `main()` 开头调用**一次**
- ✅ 之后所有查询直接调用 `SceneMapService` 方法，无需传入 `db_config`
- ✅ 连接池自动管理连接的创建、复用和释放

---

### ❌ 不推荐做法：每次查询都初始化

```python
# ❌ 错误示例：冗余初始化
def query_multiple_times():
    for i in range(5):
        # 每次都初始化（虽然安全，但不优雅）
        init_database()  # ❌ 冗余调用
        codes = get_scene_codes()
```

**为什么不推荐？**
- ❌ 虽然 `DatabaseManager` 有初始化保护（`if self._engine is not None: return`），但仍有方法调用开销
- ❌ 代码冗余，可读性差
- ❌ 违背连接池设计理念

---

## 🎯 单例模式优势

### 工作原理

```python
class DatabaseManager:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

**保证：**
1. ✅ **全局唯一实例**：无论调用多少次 `get_db_manager()`，返回的都是同一个对象
2. ✅ **线程安全**：双重检查锁定（Double-Checked Locking）
3. ✅ **初始化保护**：`initialize()` 方法内部检查 `if self._engine is not None: return`

### 调用多次 init_database() 的行为

```python
# 第一次调用：真正初始化
init_database()  
# ✅ 创建连接池（5个初始连接 + 10个溢出）
# ✅ 创建会话工厂

# 第二次调用：立即返回
init_database()  
# ✅ 获取单例实例
# ✅ 检查到 self._engine 不为 None
# ✅ 直接 return，什么都不做

# 第 N 次调用：仍然立即返回
init_database()  # 同上
```

**结论：**
- 调用多次是**安全**的（不会创建多个连接池）
- 但仍然有**方法调用开销**（虽然很小）
- **最佳实践**仍然是只初始化一次

---

## 📦 使用场景

### 场景1：独立脚本（推荐做法）

```python
#!/usr/bin/env python3
"""独立脚本：查询数据库"""
import os
from database import init_database
from services import SceneMapService

def main():
    # 1️⃣ 设置环境变量
    os.environ['DB_HOST'] = '192.168.0.106'
    os.environ['DB_PORT'] = '3306'
    os.environ['DB_USER'] = 'omuser@tellmua100#obhfcgb03uat'
    os.environ['DB_PASSWORD'] = 'OceanBase_123#'
    os.environ['DB_NAME'] = 'omservice'
    
    # 2️⃣ 初始化数据库（仅一次）
    init_database()
    
    # 3️⃣ 执行多个查询
    codes = SceneMapService.get_scene_codes(repository='EUVD')
    details = SceneMapService.get_scene_details(repository='EUVD')
    count = SceneMapService.count_scenes(repository='EUVD')
    
    print(f"场景代码: {codes}")
    print(f"场景详情: {len(details)} 条")
    print(f"场景总数: {count}")

if __name__ == '__main__':
    main()
```

---

### 场景2：Web 应用（Flask/FastAPI）

```python
from flask import Flask
from database import init_database
from services import SceneMapService

app = Flask(__name__)

# 🔥 应用启动时初始化数据库（仅一次）
@app.before_first_request
def setup_database():
    init_database()
    print("✅ 数据库连接池已初始化")

# API 路由中直接使用，无需初始化
@app.route('/api/scenes/<repository>')
def get_scenes(repository: str):
    codes = SceneMapService.get_scene_codes(repository=repository)
    return {'codes': codes}

@app.route('/api/scenes/count')
def count_scenes():
    count = SceneMapService.count_scenes()
    return {'count': count}

if __name__ == '__main__':
    app.run()
```

**FastAPI 版本：**

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import init_database
from services import SceneMapService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🔥 应用启动时初始化
    init_database()
    print("✅ 数据库连接池已初始化")
    yield
    # 应用关闭时清理资源
    from database import get_db_manager
    get_db_manager().close()

app = FastAPI(lifespan=lifespan)

@app.get('/api/scenes/{repository}')
def get_scenes(repository: str):
    codes = SceneMapService.get_scene_codes(repository=repository)
    return {'codes': codes}
```

---

### 场景3：测试用例

```python
import pytest
from database import init_database, get_db_manager
from services import SceneMapService

@pytest.fixture(scope='session')
def db_setup():
    """全局测试 fixture：初始化数据库连接"""
    init_database()
    yield
    # 测试结束后清理
    get_db_manager().close()

def test_get_scene_codes(db_setup):
    """测试查询场景代码"""
    codes = SceneMapService.get_scene_codes(repository='EUVD')
    assert len(codes) > 0
    assert all(isinstance(code, str) for code in codes)

def test_count_scenes(db_setup):
    """测试统计场景数量"""
    count = SceneMapService.count_scenes(repository='EUVD')
    assert count >= 0
```

---

### 场景4：多模块应用

```python
# main.py
from database import init_database
from module_a import process_scenes
from module_b import export_scenes

def main():
    # 🔥 主程序入口初始化一次
    init_database()
    
    # 各模块直接使用，无需初始化
    process_scenes()
    export_scenes()

# module_a.py
from services import SceneMapService

def process_scenes():
    # ✅ 直接使用，无需初始化
    codes = SceneMapService.get_scene_codes()
    for code in codes:
        print(f"Processing {code}...")

# module_b.py
from services import SceneMapService

def export_scenes():
    # ✅ 直接使用，无需初始化
    details = SceneMapService.get_scene_details()
    # 导出逻辑...
```

---

## 📊 性能对比

### 实验：1000 次查询

**方案A：每次查询都调用 init_database()**
```python
import time
from database import init_database
from services import SceneMapService

start = time.time()
for i in range(1000):
    init_database()  # 冗余调用
    codes = SceneMapService.get_scene_codes()
elapsed = time.time() - start
print(f"方案A 耗时: {elapsed:.2f}s")
```

**方案B：只初始化一次**
```python
import time
from database import init_database
from services import SceneMapService

init_database()  # 仅一次

start = time.time()
for i in range(1000):
    codes = SceneMapService.get_scene_codes()
elapsed = time.time() - start
print(f"方案B 耗时: {elapsed:.2f}s")
```

**预期结果：**
```
方案A 耗时: 3.45s  (包含 1000 次冗余的方法调用)
方案B 耗时: 3.21s  (省去冗余调用开销)
```

**性能提升：** 约 7-10%（在高并发场景下更明显）

---

## 🔍 常见问题

### Q1: 如果忘记调用 init_database() 会怎样？

**A:** 抛出 `RuntimeError` 异常：

```python
from services import SceneMapService

# ❌ 忘记初始化
codes = SceneMapService.get_scene_codes()

# 输出：
# RuntimeError: 数据库未初始化，请先调用 initialize() 方法
```

---

### Q2: 如何检查是否已初始化？

```python
from database import get_db_manager

manager = get_db_manager()
if manager.is_initialized():
    print("✅ 数据库已初始化")
else:
    print("❌ 数据库未初始化")
```

---

### Q3: 如何在运行时切换数据库配置？

```python
from database import get_db_manager, DatabaseConfig

# 第一次初始化（使用环境变量）
get_db_manager().initialize()

# 需要切换到另一个数据库
new_config = DatabaseConfig(
    host='192.168.0.200',
    port=3306,
    user='other_user',
    password='other_pass',
    database='other_db'
)

# 先关闭当前连接
get_db_manager().close()

# 重新初始化
get_db_manager().initialize(new_config)
```

---

### Q4: 连接池的连接会用完吗？

**A:** 不会，连接池自动管理：

```python
# 连接池配置
pool_size = 5        # 初始连接数
max_overflow = 10    # 最大溢出连接数
# 总计可用：15 个并发连接

# 使用场景：
with get_session() as session:  # ← 从池中获取连接
    # 执行查询...
    pass
# ← 自动归还连接到池中（不关闭）

# 如果池满了：
# - 请求会等待直到有连接释放
# - 最多等待 30 秒（pool_timeout）
# - 超时后抛出 TimeoutError
```

---

## ✅ 最佳实践总结

| 场景 | 初始化时机 | 示例 |
|------|------------|------|
| 独立脚本 | `main()` 函数开头 | `example_query.py` |
| Flask 应用 | `@app.before_first_request` | 见上文 |
| FastAPI 应用 | `lifespan` 事件 | 见上文 |
| 测试用例 | `@pytest.fixture(scope='session')` | 见上文 |
| 多模块应用 | 主程序入口 | 见上文 |

**核心原则：**
1. ✅ **只初始化一次**：在程序启动时
2. ✅ **统一管理**：在入口处集中初始化
3. ✅ **避免冗余**：业务代码中不要调用 `init_database()`
4. ✅ **优雅关闭**：程序退出时调用 `get_db_manager().close()`

---

## 📚 相关文档

- [INIT_DATABASE_EXPLAINED.md](./INIT_DATABASE_EXPLAINED.md) - init_database() 详解
- [EXCEPTION_HANDLING.md](./EXCEPTION_HANDLING.md) - 异常处理机制
- [USAGE.md](./USAGE.md) - API 使用指南
- [QUICKSTART.md](./QUICKSTART.md) - 快速开始指南
