# SQL 查询脚本使用说明

## 📋 文件说明

- **`ddl.sql`** - scene_map 表结构定义
- **`query_scene_code.py`** - 完整版查询脚本（支持多种查询方式）
- **`query_scene_code_simple.py`** - 简化版查询脚本（快速使用）
- **`.env.example`** - 数据库配置示例

## 🚀 使用方法

### 方式1: 使用简化版脚本

```bash
# 1. 编辑脚本，修改数据库配置
vim query_scene_code_simple.py

# 2. 运行查询
python3 query_scene_code_simple.py
```

### 方式2: 使用完整版脚本（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
vim .env  # 填写实际的数据库配置

# 2. 导出环境变量
export $(cat .env | xargs)

# 3. 运行查询
python3 query_scene_code.py
```

### 方式3: 在代码中使用

```python
from query_scene_code import SceneCodeQuery

# 创建查询对象
query = SceneCodeQuery(
    host="localhost",
    port=3306,
    user="root",
    password="your_password",
    database="omservice"
)

# 查询 scene_code
results = query.query_scene_codes(repository="EUVD")

# 处理结果
for row in results:
    print(row['scene_code'])
```

## 📊 查询条件

当前查询条件：
- `repository = 'EUVD'`
- `prompt_template IS NOT NULL`
- `prompt_template != ''`
- `status = '1'` (正常状态)

## 🔧 依赖安装

```bash
pip install pymysql
```

## 📝 输出示例

```
================================================================================
🔍 查询 scene_map 表中的 scene_code
================================================================================

查询条件:
  - repository = 'EUVD'
  - prompt_template 不为空
  - status = '1' (正常状态)

--------------------------------------------------------------------------------

【方式1】只返回 scene_code:

找到 5 条记录:

  1. SCENE_001
  2. SCENE_002
  3. SCENE_003
  4. SCENE_004
  5. SCENE_005

--------------------------------------------------------------------------------

【方式2】返回详细信息:

找到 5 条记录:

1. scene_code: SCENE_001
   scene_name: 测试场景1
   description: 描述信息
   model: qwen-plus
   prompt_template 长度: 256 字符
   创建时间: 2025-01-01 10:00:00

...

--------------------------------------------------------------------------------

【方式3】导出为 Python 列表:

scene_codes = ['SCENE_001', 'SCENE_002', 'SCENE_003', 'SCENE_004', 'SCENE_005']

================================================================================
✅ 查询完成! 共找到 5 条记录
================================================================================
```

## ⚠️ 注意事项

1. 请确保数据库连接信息正确
2. 确保有相应的表访问权限
3. 生产环境建议使用连接池
4. 敏感信息请使用环境变量或配置文件管理
