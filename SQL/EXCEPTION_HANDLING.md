# 🛡️ 异常处理机制说明

## 📋 问题背景

原 [services.py](file:///home/llm/zhangle/deer-flow/SQL/services.py) **完全没有异常处理**，导致：
1. 数据库连接失败时直接抛出异常
2. 查询错误时程序崩溃
3. 没有降级方案
4. 缺少错误日志

## ✅ 已实现的异常处理

### 1. 导入日志模块
```python
import logging

logger = logging.getLogger(__name__)
```

### 2. 两层异常处理策略

#### 🔴 **严重异常**（RuntimeError）- 向上抛出
数据库未初始化等严重问题，**不能静默处理**：

```python
except RuntimeError as e:
    logger.error(f"数据库未初始化: {e}")
    raise RuntimeError(
        f"数据库连接失败，请检查配置: {str(e)}"
    ) from e
```

**适用场景**：
- 数据库未初始化
- 配置错误
- 连接失败

**处理方式**：记录错误日志 + 抛出友好的错误信息

#### 🟡 **普通异常**（Exception）- 降级处理
查询失败等非关键异常，**提供降级方案**：

```python
except Exception as e:
    logger.error(f"查询 scene_code 失败: {e}", exc_info=True)
    # 降级处理：返回空列表
    return []
```

**适用场景**：
- 查询失败
- 数据解析错误
- 网络超时

**处理方式**：记录详细日志（含堆栈）+ 返回默认值

### 3. 降级返回值

| 方法 | 正常返回 | 降级返回 | 说明 |
|------|---------|---------|------|
| `get_scene_codes()` | `List[str]` | `[]` | 空列表 |
| `get_scene_details()` | `List[Dict]` | `[]` | 空列表 |
| `get_scene_by_code()` | `Dict` or `None` | `None` | None 表示未找到或出错 |
| `count_scenes()` | `int` | `0` | 0 表示没有数据或出错 |
| `get_active_scenes()` | `List[Dict]` | `[]` | 空列表 |
| `search_scenes_by_name()` | `List[Dict]` | `[]` | 空列表 |
| `get_scenes_by_codes()` | `List[Dict]` | `[]` | 空列表 |
| `get_repository_summary()` | `Dict[str, int]` | `{}` | 空字典 |

## 📝 使用示例

### 示例1: 正常使用（会捕获异常）

```python
from SQL.services import SceneMapService

# 即使数据库未初始化或查询失败，也不会崩溃
codes = SceneMapService.get_scene_codes(repository='EUVD')

if not codes:
    print("未查询到数据或发生错误")
else:
    print(f"找到 {len(codes)} 个场景")
```

### 示例2: 捕获严重异常

```python
from SQL.services import SceneMapService

try:
    codes = SceneMapService.get_scene_codes(repository='EUVD')
    print(f"找到 {len(codes)} 个场景")
except RuntimeError as e:
    # 数据库连接失败等严重问题
    print(f"数据库错误: {e}")
    # 可以尝试重新连接或使用备用数据源
```

### 示例3: 检查是否为降级响应

```python
codes = SceneMapService.get_scene_codes(repository='EUVD')

if codes:
    # 正常数据
    print(f"查询成功: {codes}")
else:
    # 可能是空数据，也可能是出错后的降级
    # 可以查看日志确认
    print("没有数据或查询失败")
```

## 🔍 日志输出

### 普通异常日志示例

```
ERROR:SQL.services:查询 scene_code 失败: Table 'omservice.scene_map' doesn't exist
Traceback (most recent call last):
  File "/home/llm/zhangle/deer-flow/SQL/services.py", line 65, in get_scene_codes
    scenes = repo.find_by_repository(
  ...
sqlalchemy.exc.ProgrammingError: (pymysql.err.ProgrammingError) (1146, "Table 'omservice.scene_map' doesn't exist")
```

### 严重异常日志示例

```
ERROR:SQL.services:数据库未初始化: 数据库未初始化，请先调用 initialize() 方法
```

## ⚙️ 配置日志

在你的应用入口添加日志配置：

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),  # 输出到文件
        logging.StreamHandler()           # 输出到控制台
    ]
)

# 或者只针对 SQL 模块
logger = logging.getLogger('SQL.services')
logger.setLevel(logging.DEBUG)
```

## 🎯 设计原则

遵循项目的 **API错误处理与降级机制规范**：

1. ✅ **完整的异常捕获机制**
   - 所有方法都使用 try-except 包裹

2. ✅ **输入参数验证**
   - 使用类型提示和默认值

3. ✅ **严重异常向上抛出**
   - RuntimeError 等严重问题抛出友好错误信息

4. ✅ **非关键异常降级处理**
   - 查询失败返回空数据
   - 记录详细日志便于排查

5. ✅ **保留服务可用性**
   - 不会因为单次查询失败而导致整个服务不可用

## 📊 异常处理流程图

```
┌─────────────────┐
│  调用 Service   │
└────────┬────────┘
         │
         ▼
    ┌────────┐
    │ 初始化 │
    └────┬───┘
         │
         ▼
  ┌──────────────┐
  │ 数据库连接   │
  └──────┬───────┘
         │
         ├─────────┐
         │         │
    成功 │    失败 │
         │         │
         ▼         ▼
  ┌─────────┐ ┌──────────────┐
  │ 执行查询│ │ RuntimeError │
  └────┬────┘ │  向上抛出    │
       │      └──────────────┘
       │
       ├──────────┐
       │          │
  成功 │     失败 │
       │          │
       ▼          ▼
  ┌────────┐ ┌─────────────┐
  │返回数据│ │记录日志      │
  └────────┘ │返回降级值    │
             └─────────────┘
```

## 🔧 扩展建议

### 1. 添加重试机制

```python
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def get_scene_codes_with_retry(...):
    return SceneMapService.get_scene_codes(...)
```

### 2. 添加缓存机制

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_scene_by_code_cached(scene_code: str):
    return SceneMapService.get_scene_by_code(scene_code)
```

### 3. 添加监控告警

```python
def get_scene_codes(...):
    try:
        # ... 查询逻辑
    except Exception as e:
        logger.error(...)
        # 发送告警
        send_alert(f"数据库查询失败: {e}")
        return []
```

## 📚 相关文档

- [services.py](./services.py) - 业务逻辑层实现
- [database.py](./database.py) - 数据库连接层
- [repositories.py](./repositories.py) - 数据访问层
- [example_query.py](./example_query.py) - 使用示例

---

**更新时间**: 2025-11-11  
**版本**: 1.0.0  
**维护者**: DeerFlow Team
