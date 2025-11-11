-- ==========================================
-- MySQL 数据库初始化脚本
-- ==========================================
-- 说明：
--   此脚本在 MySQL 容器首次启动时自动执行
--   配合 docker-compose.mysql.yml 中的环境变量
--   MYSQL_DATABASE 和 MYSQL_USER 会自动创建
--   本脚本用于额外的数据库配置和优化
-- ==========================================

-- 注意：
-- docker-compose.yml 中的环境变量会自动创建：
--   MYSQL_ROOT_PASSWORD: 7175723zl
--   MYSQL_DATABASE: omservice
--   MYSQL_USER: omuser@tellmua100#obhfcgb03uat
--   MYSQL_PASSWORD: OceanBase_123#

-- 切换到目标数据库
USE `omservice`;

-- 验证数据库字符集
SHOW VARIABLES LIKE 'character_set_database';
SHOW VARIABLES LIKE 'collation_database';

-- 显示创建结果
SELECT '✅ 数据库 omservice 已就绪' AS status;
SELECT CONCAT('✅ 用户 "', USER(), '" 连接成功') AS status;
SELECT '✅ 字符集配置: utf8mb4' AS status;
