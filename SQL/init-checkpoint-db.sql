-- ============================================================================
-- LangGraph Checkpoint 数据库初始化脚本
-- ============================================================================
-- 该脚本会被 AsyncPostgresSaver.setup() 自动执行，此处提供手动初始化参考
-- ============================================================================

-- 创建 Checkpoints 表（存储对话状态快照）
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_id TEXT,
    checkpoint BYTEA,
    metadata JSONB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- 创建 Checkpoint Blobs 表（存储大对象数据）
CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    blob_id TEXT NOT NULL,
    data BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, blob_id)
);

-- 创建 Checkpoint Writes 表（存储待写入的操作）
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    value BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel)
);

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id ON checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_blobs_thread_id ON checkpoint_blobs(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_writes_thread_id ON checkpoint_writes(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_metadata ON checkpoints USING GIN(metadata);

-- 添加注释
COMMENT ON TABLE checkpoints IS 'LangGraph checkpoint 快照存储';
COMMENT ON TABLE checkpoint_blobs IS 'LangGraph checkpoint 大对象存储';
COMMENT ON TABLE checkpoint_writes IS 'LangGraph checkpoint 待写入操作';

-- 授权给 deerflow 用户（如果需要）
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO deerflow;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO deerflow;
