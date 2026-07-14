-- SPDX-License-Identifier: MIT
-- ============================================================================
-- 管理员初始化脚本（生产环境首次初始化用）
-- ============================================================================
-- 用途：为管理员看板初始化角色权限表并写入第一个管理员账号。
--
-- 背景：新增管理员的接口 POST /admins 要求调用者本身已是管理员，
--       生产环境首次上线时没有任何管理员，存在"先有鸡还是先有蛋"的问题，
--       因此需要通过本脚本直接写入初始管理员。
--
-- 特性：幂等，可安全重复执行（表、角色、管理员均使用 IF NOT EXISTS / ON CONFLICT）。
--
-- 执行方式（示例）：
-- psql -U deerflow -d deerflow_checkpoint -c "select * from user_roles limit 20; " 
--   psql -h <host> -U <user> -d <database> -f SQL/006_init_admin.sql
-- docker exec -i deer-flow-postgres psql -U deerflow -d deerflow_checkpoint < SQL/002_create_reports_table.sql
-- docker exec -it deer-flow-postgres psql -U deerflow -d deerflow_checkpoint -c "\dt"
-- ============================================================================

BEGIN;

-- ── 1. 角色表 ──
CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(32) NOT NULL UNIQUE,
    description VARCHAR(128)
);

-- ── 2. 用户角色关联表（管理员即 role_name='admin' 的记录）──
CREATE TABLE IF NOT EXISTS user_roles (
    id          SERIAL PRIMARY KEY,
    login_name  VARCHAR(64) NOT NULL,
    role_name   VARCHAR(32) NOT NULL REFERENCES roles(name),
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(login_name, role_name)
);

-- ── 3. 预置 admin 角色 ──
INSERT INTO roles (name, description)
VALUES ('admin', '系统管理员')
ON CONFLICT (name) DO NOTHING;

-- ── 4. 写入初始管理员账号 ──
-- login_name 来自 queryUserInfo.loginName（用户唯一标识）
INSERT INTO user_roles (login_name, role_name)
VALUES ('zhangl_1116', 'admin')
ON CONFLICT (login_name, role_name) DO NOTHING;

COMMIT;

-- ── 校验：确认初始管理员已写入 ──
SELECT login_name, role_name, created_at
FROM user_roles
WHERE role_name = 'admin'
ORDER BY created_at DESC;
