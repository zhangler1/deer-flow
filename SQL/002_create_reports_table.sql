-- ============================================================================
-- 报告元数据表
-- ============================================================================
-- 用于存储每份报告的用户信息、生成耗时、MinIO 地址等元数据
-- 支撑数据看板的统计与查询
-- ============================================================================

CREATE TABLE IF NOT EXISTS reports (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id     VARCHAR(64),                          -- 关联对话线程
    user_code     VARCHAR(32),                          -- 工号，仅数据保存，不参与查询
    user_name     VARCHAR(64),                          -- 用户姓名
    branch_id     BIGINT,                               -- 分行ID
    login_name    VARCHAR(64) NOT NULL,                 -- 登录名 loginName（数据隔离主键，来自 queryUserInfo.loginName）
    title         VARCHAR(512) NOT NULL,                -- 报告标题
    duration_ms   BIGINT,                               -- 生成耗时（毫秒）
    report_url    VARCHAR(1024),                        -- MinIO OSS 地址
    object_name   VARCHAR(512),                         -- MinIO 对象路径（直接用于读取报告正文）
    file_size     BIGINT,                               -- 文件大小（字节）
    report_type   VARCHAR(32) DEFAULT 'research',       -- 报告类型（research/prose/ppt/podcast）
    status        VARCHAR(16) DEFAULT 'completed',      -- 状态（completed/failed/generating）
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

-- 按用户工号查询
CREATE INDEX IF NOT EXISTS idx_reports_login_name ON reports(login_name);
-- 按创建时间查询（看板统计按天聚合）
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);
-- 按线程ID关联对话
CREATE INDEX IF NOT EXISTS idx_reports_thread_id ON reports(thread_id);
-- 按报告类型筛选
CREATE INDEX IF NOT EXISTS idx_reports_report_type ON reports(report_type);
-- 按状态筛选（completed/cancelled/failed）
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);

-- 添加注释
COMMENT ON TABLE reports IS '报告元数据存储（看板统计、用户绑定）';
COMMENT ON COLUMN reports.user_code IS '工号，仅作数据保存，不参与查询和校验';
COMMENT ON COLUMN reports.login_name IS '登录名 loginName，来自 queryUserInfo 接口（用户唯一标识）';
COMMENT ON COLUMN reports.report_url IS 'MinIO 对象存储返回的文件访问地址';
COMMENT ON COLUMN reports.duration_ms IS '报告生成耗时（毫秒），从请求开始到报告输出完成';
