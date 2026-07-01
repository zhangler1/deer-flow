-- SPDX-License-Identifier: MIT
-- 角色权限表（管理员看板权限控制）

CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(32) NOT NULL UNIQUE,
    description VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS user_roles (
    id          SERIAL PRIMARY KEY,
    login_name  VARCHAR(64) NOT NULL,
    role_name   VARCHAR(32) NOT NULL REFERENCES roles(name),
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(login_name, role_name)
);

-- 预置管理员角色
INSERT INTO roles (name, description)
VALUES ('admin', '系统管理员')
ON CONFLICT DO NOTHING;
