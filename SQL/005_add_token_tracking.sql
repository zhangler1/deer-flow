-- ============================================================================
-- 为 reports 表新增 token 追踪字段 + 逻辑删除字段
-- ============================================================================
-- researcher_chars: researcher 节点总输出字符数
-- reporter_chars:   reporter 节点总输出字符数
-- estimated_tokens: 估算 token 数 = (researcher_chars + reporter_chars) / 2.5
-- is_deleted:       逻辑删除标记（TRUE = 已删除，查询时过滤）
-- ============================================================================

ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS researcher_chars BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS reporter_chars   BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS estimated_tokens BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_deleted       BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN reports.researcher_chars IS 'researcher 节点总输出字符数';
COMMENT ON COLUMN reports.reporter_chars   IS 'reporter 节点总输出字符数';
COMMENT ON COLUMN reports.estimated_tokens IS '估算 token 数 = (researcher_chars + reporter_chars) / 2.5';
COMMENT ON COLUMN reports.is_deleted       IS '逻辑删除标记（TRUE=已删除）';

-- 为逻辑删除字段建立索引（加速带过滤的查询）
CREATE INDEX IF NOT EXISTS idx_reports_is_deleted ON reports(is_deleted);
