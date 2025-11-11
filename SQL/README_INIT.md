# 📋 MySQL 初始化脚本使用指南

## 🎯 概述

本目录包含 MySQL Docker 容器的完整初始化方案，根据 `docker-compose.mysql.yml` 配置文件优化，确保配置一致性和自动化部署。

## 🔑 关键特性

### 1. 自动初始化
容器首次启动时，挂载到 `/docker-entrypoint-initdb.d` 的脚本会按文件名顺序自动执行：
- ✅ 01-init-database.sql - 验证数据库配置
- ✅ 02-create-tables.sql - 创建表结构
- ✅ 03-insert-sample-data.sql - 插入测试数据

### 2. 配置一致性
所有配置与 `docker-compose.mysql.yml` 保持一致：
```yaml
MYSQL_ROOT_PASSWORD: 7175723zl
MYSQL_DATABASE: omservice
MYSQL_USER: omuser@tellmua100#obhfcgb03uat
MYSQL_PASSWORD: OceanBase_123#
```

### 3. 测试数据完整
5 条示例数据覆盖所有测试场景（参见 USAGE.md 案例5）：
- 2 条 EUVD 正常场景（有模板）
- 1 条 SPARK 场景
- 1 条 EUVD 空模板场景（测试过滤）
- 1 条 EUVD 停用场景（测试状态）

## 🚀 快速开始

### 一键启动验证

```bash
cd /home/llm/zhangle/deer-flow/SQL

# 1. 启动 MySQL 服务
docker-compose -f docker-compose.mysql.yml up -d

# 2. 等待启动完成
sleep 10

# 3. 自动验证初始化
chmod +x verify-init.sh
./verify-init.sh
```

### 手动验证

```bash
# 连接数据库
docker exec -it deer-flow-mysql mysql \
  -u"omuser@tellmua100#obhfcgb03uat" \
  -p"OceanBase_123#" \
  -D omservice

# 查看示例数据
SELECT scene_code, scene_name, repository, status 
FROM scene_map 
WHERE scene_code LIKE 'DEMO_%';

# 测试案例5查询（EUVD 有效场景）
SELECT scene_code FROM scene_map 
WHERE repository = 'EUVD' 
  AND status = '1' 
  AND prompt_template IS NOT NULL 
  AND prompt_template != '';
-- 预期：2 条记录（DEMO_EUVD_001, DEMO_EUVD_002）
```

### Python 脚本验证

```bash
# 设置环境变量
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER="omuser@tellmua100#obhfcgb03uat"
export DB_PASSWORD="OceanBase_123#"
export DB_NAME=omservice

# 运行查询（匹配 USAGE.md 案例5）
cd /home/llm/zhangle/deer-flow
python3 -c "
from SQL import get_scene_codes, print_scene_codes
codes = get_scene_codes(repository='EUVD', exclude_empty_template=True)
print_scene_codes(codes, 'EUVD 知识库有效场景')
"
```

## 📂 文件结构

```
SQL/
├── init-scripts/                      # 初始化脚本目录
│   ├── 01-init-database.sql          # 验证数据库配置
│   ├── 02-create-tables.sql          # 创建表结构
│   ├── 03-insert-sample-data.sql     # 插入示例数据
│   └── README.md                      # 脚本详细说明
│
├── docker-compose.mysql.yml           # MySQL 服务配置
├── my.cnf                             # MySQL 自定义配置
├── .env.mysql.example                 # 环境变量示例
│
├── mysql-manager.sh                   # 管理脚本（启动/停止/连接）
├── verify-init.sh                     # 验证脚本（检查初始化）
│
└── 文档
    ├── QUICKSTART.md                  # 快速开始（推荐首读）
    ├── DOCKER_SETUP.md                # 完整部署指南
    ├── INIT_SCRIPTS_UPDATE.md         # 更新说明
    ├── USAGE.md                       # Python 查询使用
    └── README_INIT.md                 # 本文档
```

## 🔧 配置说明

### Docker Compose 配置

在 `docker-compose.mysql.yml` 中通过环境变量自动创建数据库和用户：

```yaml
environment:
  MYSQL_ROOT_PASSWORD: 7175723zl           # Root 密码
  MYSQL_DATABASE: omservice                 # 自动创建数据库
  MYSQL_USER: omuser@tellmua100#obhfcgb03uat  # 自动创建用户
  MYSQL_PASSWORD: OceanBase_123#            # 用户密码
  TZ: Asia/Shanghai                         # 时区
```

### 挂载配置

```yaml
volumes:
  # 初始化脚本（容器首次启动时执行）
  - ./init-scripts:/docker-entrypoint-initdb.d:ro
  # 数据持久化
  - mysql-data:/var/lib/mysql
  # 自定义配置
  - ./my.cnf:/etc/mysql/conf.d/custom.cnf:ro
```

### Python 应用配置

在 `.env` 文件中配置（或使用环境变量）：

```bash
DB_HOST=localhost  # 或 mysql（Docker 内部）
DB_PORT=3306
DB_USER=omuser@tellmua100#obhfcgb03uat
DB_PASSWORD=OceanBase_123#
DB_NAME=omservice
DB_CHARSET=utf8mb4
```

## 📊 示例数据说明

### 数据概览

| scene_code | repository | status | prompt_template | 用途 |
|------------|------------|--------|-----------------|------|
| DEMO_EUVD_001 | EUVD | 1 | ✅ 有 | 正常场景 |
| DEMO_EUVD_002 | EUVD | 1 | ✅ 有 | 正常场景 |
| DEMO_SPARK_001 | SPARK | 1 | ✅ 有 | 对比测试 |
| DEMO_EUVD_EMPTY | EUVD | 1 | ❌ NULL | 测试空模板过滤 |
| DEMO_EUVD_DISABLED | EUVD | 0 | ✅ 有 | 测试状态过滤 |

### 测试场景覆盖

✅ **案例1**: 查询所有 EUVD 场景
```sql
WHERE repository = 'EUVD'
-- 结果：4 条（DEMO_EUVD_001, 002, EMPTY, DISABLED）
```

✅ **案例2**: 查询所有正常状态场景
```sql
WHERE status = '1'
-- 结果：4 条（DEMO_EUVD_001, 002, EMPTY, DEMO_SPARK_001）
```

✅ **案例3**: 查询有模板的场景
```sql
WHERE prompt_template IS NOT NULL AND prompt_template != ''
-- 结果：4 条（DEMO_EUVD_001, 002, DISABLED, DEMO_SPARK_001）
```

✅ **案例4**: EUVD 且正常状态
```sql
WHERE repository = 'EUVD' AND status = '1'
-- 结果：3 条（DEMO_EUVD_001, 002, EMPTY）
```

✅ **案例5**: EUVD 且正常状态且有模板（USAGE.md 案例5）
```sql
WHERE repository = 'EUVD' 
  AND status = '1' 
  AND prompt_template IS NOT NULL 
  AND prompt_template != ''
-- 结果：2 条（DEMO_EUVD_001, DEMO_EUVD_002）✅
```

## 🛠️ 常用操作

### 管理命令

```bash
# 使用管理脚本（推荐）
./mysql-manager.sh start      # 启动服务
./mysql-manager.sh status     # 查看状态
./mysql-manager.sh connect    # 连接数据库
./mysql-manager.sh test       # 测试连接
./mysql-manager.sh logs       # 查看日志
./mysql-manager.sh init       # 重新初始化
./mysql-manager.sh clean      # 清理数据

# 或直接使用 Docker Compose
docker-compose -f docker-compose.mysql.yml up -d      # 启动
docker-compose -f docker-compose.mysql.yml down       # 停止
docker-compose -f docker-compose.mysql.yml down -v    # 停止并删除数据
```

### 连接数据库

```bash
# Root 用户
docker exec -it deer-flow-mysql mysql -uroot -p7175723zl

# 应用用户
docker exec -it deer-flow-mysql mysql \
  -u"omuser@tellmua100#obhfcgb03uat" \
  -p"OceanBase_123#" \
  -D omservice

# 或使用 phpMyAdmin
# 访问：http://localhost:8080
# 用户：root
# 密码：7175723zl
```

### 重新初始化

```bash
# 方式1: 删除容器和数据卷（会丢失所有数据）
docker-compose -f docker-compose.mysql.yml down -v
docker-compose -f docker-compose.mysql.yml up -d

# 方式2: 使用管理脚本
./mysql-manager.sh init
```

## ⚠️ 重要提示

### 1. 首次启动执行
- 初始化脚本**仅在容器首次启动时执行**
- 如果数据卷已存在，脚本不会重复执行
- 需要重新初始化时，必须先删除数据卷：`docker-compose down -v`

### 2. 密码安全
当前配置使用示例密码：
- Root: `7175723zl`
- App User: `OceanBase_123#`

⚠️ **生产环境请务必修改为强密码！**

修改方式：
1. 编辑 `docker-compose.mysql.yml` 中的环境变量
2. 编辑 `.env.mysql.example` 并重命名为 `.env.mysql`
3. 重新创建容器：`docker-compose down -v && docker-compose up -d`

### 3. 用户名特殊字符
应用用户名包含特殊字符：`omuser@tellmua100#obhfcgb03uat`

连接时需要用引号包裹：
```bash
mysql -u"omuser@tellmua100#obhfcgb03uat" -p"OceanBase_123#"
```

Python 环境变量也需要引号：
```bash
export DB_USER="omuser@tellmua100#obhfcgb03uat"
```

### 4. 数据持久化
- 数据存储在 Docker 数据卷 `mysql-data` 中
- 删除容器不会丢失数据
- 删除数据卷会永久丢失数据
- 建议定期备份：`docker exec deer-flow-mysql mysqldump ...`

### 5. 字符集配置
- 统一使用 `utf8mb4` 字符集
- 支持存储 emoji 等特殊字符
- 已在 `docker-compose.yml` 和 `my.cnf` 中配置

## 🧪 验证测试

### 自动验证（推荐）

```bash
chmod +x verify-init.sh
./verify-init.sh
```

验证脚本会检查：
- ✅ 容器运行状态
- ✅ 健康检查状态
- ✅ Root 和应用用户连接
- ✅ 数据库和表是否创建
- ✅ 字符集配置
- ✅ 示例数据完整性（5 条记录）
- ✅ 案例5查询结果（2 条记录）
- ✅ 显示数据详情

### 手动验证

参见前面的"快速开始"部分。

## 📚 相关文档

- 📖 [快速开始](./QUICKSTART.md) - 一分钟快速验证（推荐首读）
- 📖 [Docker 部署指南](./DOCKER_SETUP.md) - 完整部署文档
- 📖 [更新说明](./INIT_SCRIPTS_UPDATE.md) - 脚本更新详情
- 📖 [Python 查询使用](./USAGE.md) - 包含案例5
- 📖 [初始化脚本详解](./init-scripts/README.md) - 脚本详细说明

## 🎯 下一步

1. ✅ 阅读 [QUICKSTART.md](./QUICKSTART.md) 快速开始
2. ✅ 运行 `verify-init.sh` 验证初始化
3. ✅ 测试 [USAGE.md](./USAGE.md) 中的案例5
4. 📝 根据实际需求修改示例数据
5. 🔒 生产环境修改默认密码
6. 📊 配置监控和备份策略

## 🆘 故障排查

### 问题1: 容器启动失败
```bash
# 查看日志
docker logs deer-flow-mysql

# 常见原因：
# - 端口 3306 已被占用
# - 数据卷权限问题
# - 配置文件语法错误
```

### 问题2: 初始化脚本未执行
```bash
# 检查数据卷是否已存在
docker volume ls | grep mysql-data

# 解决：删除数据卷重新启动
docker-compose -f docker-compose.mysql.yml down -v
docker-compose -f docker-compose.mysql.yml up -d
```

### 问题3: 连接被拒绝
```bash
# 检查容器健康状态
docker ps

# 检查用户权限
docker exec deer-flow-mysql mysql -uroot -p7175723zl \
  -e "SELECT user, host FROM mysql.user;"
```

### 问题4: 中文乱码
```bash
# 检查字符集
docker exec deer-flow-mysql mysql -uroot -p7175723zl \
  -e "SHOW VARIABLES LIKE 'character%';"

# 应该都是 utf8mb4
```

---

**创建时间**: 2025-11-11  
**版本**: 2.0.0  
**维护者**: DeerFlow Team  
**文档状态**: ✅ 已根据 docker-compose.mysql.yml 优化
