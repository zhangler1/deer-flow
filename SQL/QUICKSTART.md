# 🚀 MySQL Docker 快速开始指南

## 一分钟快速启动

```bash
# 1. 进入 SQL 目录
cd /home/llm/zhangle/deer-flow/SQL

# 2. 启动 MySQL 服务
docker-compose -f docker-compose.mysql.yml up -d

# 3. 等待 10 秒让服务完全启动
sleep 10

# 4. 测试连接（使用配置文件中的密码）
docker exec -it deer-flow-mysql mysql -u"omuser@tellmua100#obhfcgb03uat" -p"OceanBase_123#" -D omservice -e "SELECT COUNT(*) FROM scene_map;"
```

**预期输出**: 显示表中有 5 条记录

## ✅ 验证初始化成功

### 查看示例数据

```bash
docker exec -it deer-flow-mysql mysql -u"omuser@tellmua100#obhfcgb03uat" -p"OceanBase_123#" -D omservice -e "
SELECT scene_code, scene_name, repository, status 
FROM scene_map
WHERE scene_code LIKE 'DEMO_%';
"
```

### 测试查询（EUVD 有效场景）

```bash
# 设置环境变量
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER="omuser@tellmua100#obhfcgb03uat"
export DB_PASSWORD="OceanBase_123#"
export DB_NAME=omservice

# 运行 Python 查询
cd /home/llm/zhangle/deer-flow
python3 -c "
from SQL import get_scene_codes
codes = get_scene_codes(repository='EUVD', exclude_empty_template=True)
print(f'找到 {len(codes)} 个有效场景:')
for code in codes:
    print(f'  - {code}')
"
```

**预期输出**:
```
找到 2 个有效场景:
  - DEMO_EUVD_001
  - DEMO_EUVD_002
```

## 🔐 账号信息

根据 `docker-compose.mysql.yml` 配置：

| 用户 | 密码 | 权限 | 用途 |
|------|------|------|------|
| root | 7175723zl | 全部权限 | 管理员 |
| omuser@tellmua100#obhfcgb03uat | OceanBase_123# | omservice.* | 应用连接 |

⚠️ **生产环境请务必修改默认密码！**

## 🎯 下一步

- 📖 阅读 [完整部署指南](./DOCKER_SETUP.md)
- 📖 查看 [Python 查询使用](./USAGE.md)
- 🔧 根据需要修改示例数据
- 🔒 生产环境请修改默认密码

## 🛠️ 常用命令

```bash
# 查看日志
docker logs -f deer-flow-mysql

# 进入 MySQL 命令行（root）
docker exec -it deer-flow-mysql mysql -uroot -p7175723zl

# 进入 MySQL 命令行（应用用户）
docker exec -it deer-flow-mysql mysql -u"omuser@tellmua100#obhfcgb03uat" -p"OceanBase_123#" -D omservice

# 停止服务
docker-compose -f docker-compose.mysql.yml down

# 完全清理（删除数据）
docker-compose -f docker-compose.mysql.yml down -v
```

## 🌐 phpMyAdmin 管理界面

访问地址: http://localhost:8080

- **服务器**: mysql
- **用户名**: root
- **密码**: 7175723zl

---

**完整文档**: [DOCKER_SETUP.md](./DOCKER_SETUP.md)
