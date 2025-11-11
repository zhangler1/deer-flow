# Scene Map 查询工具使用指南

## 📦 安装依赖

```bash
pip install sqlalchemy pymysql
```

## 🚀 快速开始

### 1. 配置数据库连接

```bash
# 方式1: 使用环境变量（推荐）
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=omservice

# 方式2: 创建 .env 文件
cp .env.example .env
vim .env  # 编辑配置
```

### 2. 作为模块使用

```python
from query_scene_code_simple import (
    get_scene_codes,
    get_scene_details,
    get_scene_by_code,
    count_scenes,
)

# 示例1: 查询 scene_code 列表
codes = get_scene_codes(repository='EUVD')
print(f"找到 {len(codes)} 个场景")
for code in codes:
    print(f"  - {code}")

# 示例2: 查询详细信息
details = get_scene_details(repository='EUVD')
for item in details:
    print(f"{item['scene_code']}: {item['scene_name']}")

# 示例3: 查询单个场景
scene = get_scene_by_code('SCENE_001')
if scene:
    print(f"场景名称: {scene['scene_name']}")
    print(f"模型: {scene['model']}")

# 示例4: 统计数量
count = count_scenes(repository='EUVD')
print(f"共有 {count} 个场景")
```

### 3. 自定义数据库配置

```python
# 传入自定义配置
db_config = {
    'host': '192.168.1.100',
    'port': 3306,
    'user': 'app_user',
    'password': 'secure_password',
    'database': 'production_db',
}

codes = get_scene_codes(
    repository='EUVD',
    db_config=db_config
)
```

### 4. 直接运行测试

```bash
# 使用环境变量
python3 query_scene_code_simple.py

# 或者直接编辑脚本中的 DB_CONFIG
vim query_scene_code_simple.py  # 修改主程序中的配置
python3 query_scene_code_simple.py
```

## 📖 API 参考

### get_scene_codes()

查询符合条件的 scene_code 列表

```python
def get_scene_codes(
    repository: str = 'EUVD',
    status: str = '1',
    exclude_empty_template: bool = True,
    db_config: Optional[Dict[str, Any]] = None,
) -> List[str]
```

**参数：**
- `repository`: 知识库类型，默认 'EUVD'
- `status`: 状态，'1'=正常，'0'=停用，默认 '1'
- `exclude_empty_template`: 是否排除空的 prompt_template，默认 True
- `db_config`: 数据库配置字典，None 则从环境变量读取

**返回：**
- `List[str]`: scene_code 列表

**示例：**
```python
# 查询 EUVD 知识库的所有正常场景
codes = get_scene_codes(repository='EUVD')

# 包含停用的场景
all_codes = get_scene_codes(repository='EUVD', status='0')

# 包含空模板的场景
codes_with_empty = get_scene_codes(
    repository='EUVD',
    exclude_empty_template=False
)
```

### get_scene_details()

查询符合条件的场景详细信息

```python
def get_scene_details(
    repository: str = 'EUVD',
    status: str = '1',
    exclude_empty_template: bool = True,
    db_config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]
```

**返回：**
- `List[Dict]`: 场景详细信息列表，每个字典包含：
  - `scene_code`: 场景代码
  - `scene_name`: 场景名称
  - `description`: 描述
  - `model`: 模型名称
  - `repository`: 知识库
  - `prompt_template`: 提示词模板
  - `status`: 状态
  - `create_time`: 创建时间
  - `update_time`: 更新时间

**示例：**
```python
details = get_scene_details(repository='EUVD')
for scene in details:
    print(f"代码: {scene['scene_code']}")
    print(f"名称: {scene['scene_name']}")
    print(f"模型: {scene['model']}")
    print(f"提示词长度: {len(scene['prompt_template'])}")
    print("-" * 40)
```

### get_scene_by_code()

根据 scene_code 查询单个场景信息

```python
def get_scene_by_code(
    scene_code: str,
    db_config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]
```

**参数：**
- `scene_code`: 场景代码
- `db_config`: 数据库配置

**返回：**
- `Dict` 或 `None`: 场景信息字典，不存在则返回 None

**示例：**
```python
scene = get_scene_by_code('SCENE_001')
if scene:
    print(f"找到场景: {scene['scene_name']}")
else:
    print("场景不存在")
```

### count_scenes()

统计符合条件的场景数量

```python
def count_scenes(
    repository: str = 'EUVD',
    status: str = '1',
    exclude_empty_template: bool = True,
    db_config: Optional[Dict[str, Any]] = None,
) -> int
```

**返回：**
- `int`: 场景数量

**示例：**
```python
total = count_scenes(repository='EUVD')
print(f"EUVD 知识库共有 {total} 个有效场景")
```

## 🎯 使用场景

### 场景1: 批量处理场景数据

```python
from query_scene_code_simple import get_scene_details

# 获取所有场景
scenes = get_scene_details(repository='EUVD')

# 批量处理
for scene in scenes:
    code = scene['scene_code']
    template = scene['prompt_template']
    
    # 处理逻辑
    print(f"处理场景: {code}")
    # ... 你的业务逻辑
```

### 场景2: 导出场景配置

```python
import json
from query_scene_code_simple import get_scene_details

# 查询场景
scenes = get_scene_details(repository='EUVD')

# 导出为 JSON
with open('scenes_export.json', 'w', encoding='utf-8') as f:
    json.dump(scenes, f, ensure_ascii=False, indent=2, default=str)

print(f"已导出 {len(scenes)} 个场景配置")
```

### 场景3: 校验场景完整性

```python
from query_scene_code_simple import get_scene_details

scenes = get_scene_details(repository='EUVD')

# 检查缺失字段
for scene in scenes:
    code = scene['scene_code']
    
    if not scene.get('model'):
        print(f"⚠️ {code}: 缺少模型配置")
    
    if not scene.get('prompt_template'):
        print(f"⚠️ {code}: 缺少提示词模板")
```

### 场景4: 数据迁移

```python
from query_scene_code_simple import get_scene_details

# 从源库查询
source_config = {
    'host': 'source-db.example.com',
    'user': 'readonly',
    'password': 'pass123',
    'database': 'omservice',
}

scenes = get_scene_details(
    repository='EUVD',
    db_config=source_config
)

# 写入目标库
# ... 迁移逻辑
```

### 场景5: 查询 EUVD 库中有效的场景代码

```python
from query_scene_code_simple import get_scene_codes

# 查询 repository='EUVD' 且 prompt_template 不为空的所有 scene_code
scene_codes = get_scene_codes(
    repository='EUVD',
    status='1',  # 只查询正常状态的场景
    exclude_empty_template=True  # 排除空的 prompt_template
)

# 打印结果
print(f"找到 {len(scene_codes)} 个有效场景:")
for code in scene_codes:
    print(f"  - {code}")

# 或者导出为列表
print(f"\nPython 列表格式:")
print(f"scene_codes = {scene_codes}")
```

**说明：**
- `repository='EUVD'`: 指定知识库为 EUVD
- `status='1'`: 只查询状态为正常的场景（'1'=正常，'0'=停用）
- `exclude_empty_template=True`: 排除 prompt_template 为 NULL 或空字符串的场景

**完整案例：**

```python
from query_scene_code_simple import get_scene_codes, get_scene_details

# 方法1: 只获取 scene_code 列表
print("=" * 80)
print("方法1: 只获取 scene_code 列表")
print("=" * 80)

scene_codes = get_scene_codes(
    repository='EUVD',
    status='1',
    exclude_empty_template=True
)

print(f"\n找到 {len(scene_codes)} 个场景:")
for idx, code in enumerate(scene_codes, 1):
    print(f"  {idx}. {code}")

# 方法2: 获取详细信息（包含场景名称、描述等）
print("\n" + "=" * 80)
print("方法2: 获取详细信息")
print("=" * 80)

scene_details = get_scene_details(
    repository='EUVD',
    status='1',
    exclude_empty_template=True
)

for scene in scene_details:
    print(f"\n场景代码: {scene['scene_code']}")
    print(f"场景名称: {scene['scene_name']}")
    print(f"模型: {scene['model']}")
    print(f"提示词模板长度: {len(scene['prompt_template'])} 字符")
    print("-" * 40)
```

## 🏗️ 架构设计

### 代码结构

```
query_scene_code_simple.py
├── 数据库模型定义
│   └── SceneMap (ORM 模型)
├── 数据库连接管理
│   └── DatabaseManager (单例模式)
├── 核心查询函数
│   ├── get_scene_codes()
│   ├── get_scene_details()
│   ├── get_scene_by_code()
│   └── count_scenes()
└── 工具函数
    ├── _get_db_config_from_env()
    └── print_scene_summary()
```

### 设计特点

1. **ORM 映射**
   - 使用 SQLAlchemy 定义表结构
   - 类型安全，代码可读性高
   - 自动处理字段映射

2. **连接池管理**
   - 使用 QueuePool 管理连接
   - 自动连接回收
   - 连接前 ping 测试

3. **单例模式**
   - DatabaseManager 使用单例
   - 避免重复创建连接
   - 资源高效利用

4. **上下文管理器**
   - 自动提交/回滚事务
   - 自动关闭连接
   - 异常安全

## ⚙️ 高级配置

### 连接池参数

```python
from query_scene_code_simple import DatabaseManager

db = DatabaseManager()
db.initialize(
    host='localhost',
    port=3306,
    user='root',
    password='password',
    database='omservice',
    pool_size=10,        # 连接池大小
    max_overflow=20,     # 最大溢出连接数
    pool_recycle=3600,   # 连接回收时间（秒）
)
```

### 自定义查询

```python
from query_scene_code_simple import DatabaseManager, SceneMap

db = DatabaseManager()
db.initialize(**your_config)

with db.get_session() as session:
    # 自定义复杂查询
    results = session.query(SceneMap).filter(
        SceneMap.repository == 'EUVD',
        SceneMap.model == 'qwen-plus',
        SceneMap.temperature > 0.5
    ).all()
    
    for scene in results:
        print(scene.scene_code, scene.scene_name)
```

## 🔍 故障排查

### 问题1: ModuleNotFoundError

```bash
# 错误: No module named 'sqlalchemy'
# 解决:
pip install sqlalchemy pymysql
```

### 问题2: 数据库连接失败

```python
# 检查连接
from query_scene_code_simple import DatabaseManager

try:
    db = DatabaseManager()
    db.initialize(
        host='localhost',
        user='root',
        password='your_password',
        database='omservice'
    )
    with db.get_session() as session:
        result = session.execute("SELECT 1").scalar()
        print("✅ 数据库连接成功")
except Exception as e:
    print(f"❌ 连接失败: {e}")
```

### 问题3: 表不存在

```bash
# 确保表已创建
mysql -u root -p omservice < ddl.sql
```

## 📊 性能优化建议

1. **使用连接池** - 已默认启用
2. **批量查询** - 使用 `get_scene_details()` 而非循环调用 `get_scene_by_code()`
3. **索引优化** - 确保 `repository` 和 `status` 字段有索引
4. **结果缓存** - 对不常变化的数据进行缓存

## 🔗 相关文件

- [`query_scene_code_simple.py`](./query_scene_code_simple.py) - 主查询模块
- [`ddl.sql`](./ddl.sql) - 表结构定义
- [`.env.example`](./.env.example) - 配置示例
- [`README.md`](./README.md) - 总体说明

---

**更新时间**: 2025-11-10
