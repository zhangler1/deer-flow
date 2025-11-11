# 🐳 Docker MySQL 数据库部署指南

## 📋 目录结构

```
SQL/
├── init-scripts/                    # 数据库初始化脚本目录
│   ├── 01-init-database.sql        # 创建数据库和用户
│   ├── 02-create-tables.sql        # 创建表结构
│   ├── 03-insert-sample-data.sql   # 插入示例数据（可选）
│   └── README.md                    # 初始化脚本详细说明
├── my.cnf                           # MySQL 自定义配置文件
├── docker-compose.mysql.yml         # MySQL Docker Compose 配置
├── mysql-manager.sh                 # MySQL 管理脚本
└── DOCKER_SETUP.md                  # 本文档
```

## 🚀 快速开始

### 方式1: 使用管理脚本（推荐）

```bash
# 进入 SQL 目录
cd /home/llm/zhangle/deer-flow/SQL

# 添加执行权限
chmod +x mysql-manager.sh

# 启动 MySQL 服务
./mysql-manager.sh start

# 查看服务状态
./mysql-manager.sh status

# 测试连接
./mysql-manager.sh test

# 查看日志
./mysql-manager.sh logs

# 连接到 MySQL 命令行
./mysql-manager.sh connect

# 查看所有可用命令
./mysql-manager.sh help
```

### 方式2: 使用 Docker Compose

```bash
# 进入 SQL 目录
cd /home/llm/zhangle/deer-flow/SQL

# 启动服务
docker-compose -f docker-compose.mysql.yml up -d

# 查看服务状态
docker-compose -f docker-compose.mysql.yml ps

# 查看日志
docker-compose -f docker-compose.mysql.yml logs -f mysql

# 停止服务
docker-compose -f docker-compose.mysql.yml down
```

### 方式3: 集成到主 docker-compose.yml

在项目根目录的 `docker-compose.yml` 中添加 MySQL 服务：

```yaml
services:
  # ... 现有服务（backend, frontend, nginx）...

  # 添加 MySQL 服务
  mysql:
    image: mysql:8.0
    container_name: deer-flow-mysql
    environment:
      MYSQL_ROOT_PASSWORD: root_password_2024
      MYSQL_DATABASE: omservice
      MYSQL_USER: app_user
      MYSQL_PASSWORD: app_password_2024
      TZ: Asia/Shanghai
    ports:
      - "3306:3306"
    volumes:
      - ./SQL/init-scripts:/docker-entrypoint-initdb.d:ro
      - mysql-data:/var/lib/mysql
      - ./SQL/my.cnf:/etc/mysql/conf.d/custom.cnf:ro
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --default-authentication-plugin=mysql_native_password
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uroot", "-proot_password_2024"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - deer-flow-network

  # 修改 backend 服务，添加 MySQL 依赖
  backend:
    # ... 现有配置 ...
    depends_on:
      mysql:
        condition: service_healthy
    environment:
      # ... 现有环境变量 ...
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_USER=app_user
      - DB_PASSWORD=app_password_2024
      - DB_NAME=omservice

# 添加数据卷
volumes:
  mysql-data:
    driver: local

# ... 现有网络配置 ...
```

然后启动所有服务：

```bash
cd /home/llm/zhangle/deer-flow
docker-compose up -d
```

## 🔧 配置说明

### 环境变量

在项目根目录的 `.env` 文件中配置：

```bash
# MySQL 数据库配置
DB_HOST=localhost          # 或 mysql（Docker 内部网络）
DB_PORT=3306
DB_USER=app_user
DB_PASSWORD=app_password_2024
DB_NAME=omservice
DB_CHARSET=utf8mb4

# 连接池配置
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=3600
DB_ECHO_SQL=false
```

### 默认账号信息

| 用户 | 密码 | 权限 | 用途 |
|------|------|------|------|
| root | root_password_2024 | 全部权限 | 管理员 |
| app_user | app_password_2024 | omservice.* | 应用连接 |

⚠️ **生产环境请务必修改默认密码！**

## 📊 初始化脚本说明

初始化脚本按文件名顺序自动执行（仅在容器首次启动时）：

1. **01-init-database.sql** - 创建数据库和用户
   - 创建 `omservice` 数据库
   - 创建 `app_user` 用户
   - 授予权限

2. **02-create-tables.sql** - 创建表结构
   - 创建 `scene_map` 表
   - 添加索引优化

3. **03-insert-sample-data.sql** - 插入测试数据（可选）
   - 插入 5 条示例数据
   - 覆盖各种测试场景

### 示例数据说明

| scene_code | repository | status | prompt_template | 用途 |
|------------|------------|--------|-----------------|------|
| EUVD_DEMO_001 | EUVD | 1 | 有 | 正常场景 |
| EUVD_DEMO_002 | EUVD | 1 | 有 | 正常场景 |
| SPARK_DEMO_001 | SPARK | 1 | 有 | SPARK库测试 |
| EUVD_EMPTY_TEMPLATE | EUVD | 1 | NULL | 测试空模板过滤 |
| EUVD_DISABLED_SCENE | EUVD | 0 | 有 | 测试状态过滤 |

**查询验证：**

```bash
# 查询 EUVD 库中 status='1' 且 prompt_template 不为空的场景
# 预期结果：2 条记录（EUVD_DEMO_001, EUVD_DEMO_002）
```

## 🧪 测试验证

### 1. 验证容器状态

```bash
# 查看容器是否运行
docker ps | grep deer-flow-mysql

# 查看健康检查状态
docker inspect deer-flow-mysql | grep -A 10 Health
```

### 2. 验证数据库连接

```bash
# 使用 root 连接
docker exec -it deer-flow-mysql mysql -uroot -proot_password_2024

# 使用应用用户连接
docker exec -it deer-flow-mysql mysql -uapp_user -papp_password_2024 -D omservice
```

### 3. 验证表结构

```sql
-- 进入 MySQL 后执行
USE omservice;

-- 查看表
SHOW TABLES;

-- 查看表结构
DESC scene_map;

-- 查看索引
SHOW INDEX FROM scene_map;
```

### 4. 验证示例数据

```sql
-- 查看所有数据
SELECT scene_code, scene_name, repository, status 
FROM scene_map;

-- 查询 EUVD 有效场景
SELECT scene_code, scene_name 
FROM scene_map 
WHERE repository = 'EUVD' 
  AND status = '1' 
  AND prompt_template IS NOT NULL 
  AND prompt_template != '';
```

### 5. 使用 Python 查询脚本测试

```bash
# 设置环境变量
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=app_user
export DB_PASSWORD=app_password_2024
export DB_NAME=omservice

# 运行查询脚本
cd /home/llm/zhangle/deer-flow
python3 -c "
from SQL import get_scene_codes, print_scene_codes

codes = get_scene_codes(repository='EUVD', exclude_empty_template=True)
print_scene_codes(codes, 'EUVD 知识库有效场景')
"
```

预期输出：
```
================================================================================
🔍 EUVD 知识库有效场景
================================================================================

✅ 找到 2 个场景:

  1. EUVD_DEMO_001
  2. EUVD_DEMO_002

Python 列表格式:
scene_codes = ['EUVD_DEMO_001', 'EUVD_DEMO_002']

================================================================================
```

## 🔄 常见操作

### 重新初始化数据库

```bash
# 方式1: 使用管理脚本
./mysql-manager.sh init

# 方式2: 手动执行
docker exec -it deer-flow-mysql mysql -uroot -proot_password_2024 -e "DROP DATABASE IF EXISTS omservice;"
docker exec -i deer-flow-mysql mysql -uroot -proot_password_2024 < init-scripts/01-init-database.sql
docker exec -i deer-flow-mysql mysql -uroot -proot_password_2024 < init-scripts/02-create-tables.sql
docker exec -i deer-flow-mysql mysql -uroot -proot_password_2024 < init-scripts/03-insert-sample-data.sql
```

### 备份数据库

```bash
# 备份整个数据库
docker exec deer-flow-mysql mysqldump -uroot -proot_password_2024 omservice > backup_$(date +%Y%m%d).sql

# 只备份表结构
docker exec deer-flow-mysql mysqldump -uroot -proot_password_2024 --no-data omservice > schema.sql

# 只备份数据
docker exec deer-flow-mysql mysqldump -uroot -proot_password_2024 --no-create-info omservice > data.sql
```

### 恢复数据库

```bash
# 恢复整个数据库
docker exec -i deer-flow-mysql mysql -uroot -proot_password_2024 omservice < backup_20251111.sql

# 恢复特定表
docker exec -i deer-flow-mysql mysql -uroot -proot_password_2024 omservice < scene_map_backup.sql
```

### 查看日志

```bash
# 实时查看 MySQL 日志
docker logs -f deer-flow-mysql

# 查看慢查询日志
docker exec deer-flow-mysql tail -f /var/log/mysql/slow-query.log

# 查看错误日志
docker exec deer-flow-mysql tail -f /var/log/mysql/error.log
```

### 性能监控

```bash
# 查看当前连接
docker exec deer-flow-mysql mysql -uroot -proot_password_2024 -e "SHOW PROCESSLIST;"

# 查看数据库状态
docker exec deer-flow-mysql mysql -uroot -proot_password_2024 -e "SHOW STATUS;"

# 查看变量配置
docker exec deer-flow-mysql mysql -uroot -proot_password_2024 -e "SHOW VARIABLES;"
```

## 🌐 phpMyAdmin 管理界面

如果使用 `docker-compose.mysql.yml` 启动，会自动启动 phpMyAdmin：

- **访问地址**: http://localhost:8080
- **用户名**: root
- **密码**: root_password_2024

## ⚠️ 注意事项

### 1. 首次启动

- 初始化脚本**仅在容器首次启动时执行**
- 如果数据卷已存在，需要先删除才能重新初始化
- 删除数据卷命令: `docker-compose down -v`

### 2. 密码安全

生产环境必须修改默认密码：

```sql
-- 修改 root 密码
ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_strong_password';

-- 修改应用用户密码
ALTER USER 'app_user'@'%' IDENTIFIED BY 'new_app_password';

-- 刷新权限
FLUSH PRIVILEGES;
```

### 3. 网络配置

**宿主机访问**:
```bash
DB_HOST=localhost
DB_PORT=3306
```

**Docker 容器内访问**:
```bash
DB_HOST=mysql  # 使用服务名
DB_PORT=3306
```

### 4. 数据持久化

数据存储在 Docker 数据卷 `mysql-data` 中，即使删除容器也不会丢失数据。

**查看数据卷**:
```bash
docker volume ls | grep mysql
```

**删除数据卷**（会丢失所有数据）:
```bash
docker volume rm deer-flow_mysql-data
```

### 5. 性能调优

根据实际负载修改 `my.cnf` 中的配置：

- `innodb_buffer_pool_size`: 建议设置为可用内存的 50-70%
- `max_connections`: 根据并发量调整
- `slow_query_log`: 生产环境建议启用慢查询日志

## 🐛 故障排查

### 问题1: 容器启动失败

```bash
# 查看容器日志
docker logs deer-flow-mysql

# 常见原因:
# - 端口 3306 已被占用
# - 数据卷权限问题
# - 配置文件语法错误
```

### 问题2: 初始化脚本未执行

```bash
# 检查数据卷是否已存在
docker volume ls | grep mysql-data

# 解决方法: 删除数据卷重新启动
docker-compose -f docker-compose.mysql.yml down -v
docker-compose -f docker-compose.mysql.yml up -d
```

### 问题3: 连接被拒绝

```bash
# 检查容器是否健康
docker ps

# 检查网络连通性
docker exec deer-flow-backend ping mysql

# 检查用户权限
docker exec deer-flow-mysql mysql -uroot -proot_password_2024 -e "SELECT user, host FROM mysql.user;"
```

### 问题4: 中文乱码

确保字符集配置正确：

```sql
-- 检查数据库字符集
SHOW VARIABLES LIKE 'character%';

-- 检查表字符集
SHOW CREATE TABLE scene_map;

-- 应该都是 utf8mb4
```

## 📚 相关文档

- [MySQL 初始化脚本详细说明](./init-scripts/README.md)
- [SQL 查询工具使用指南](./USAGE.md)
- [数据库配置说明](./README.md)
- [MySQL 官方文档](https://dev.mysql.com/doc/)
- [Docker Compose 文档](https://docs.docker.com/compose/)

## 🎯 下一步

1. ✅ 启动 MySQL 服务
2. ✅ 验证数据库连接
3. ✅ 测试 Python 查询脚本
4. 📝 根据需要修改示例数据
5. 🔒 生产环境修改默认密码
6. 📊 配置监控和备份策略

---

**创建时间**: 2025-11-11  
**维护者**: DeerFlow Team
