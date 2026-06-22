-- ============================================================================
-- 为 reports 表新增 object_name 字段
-- ============================================================================
-- object_name 用于直接定位 MinIO 中的报告对象，支持历史报告回溯读取
-- 无需从 report_url 中反向解析路径，更可靠且解耦
-- ============================================================================

ALTER TABLE reports
ADD COLUMN IF NOT EXISTS object_name VARCHAR(512);

COMMENT ON COLUMN reports.object_name IS 'MinIO 对象路径（如 reports/2025/06/22/thread_id_research.md），用于直接读取报告正文';

-- 为 object_name 建立唯一索引（可选，方便查找）
CREATE INDEX IF NOT EXISTS idx_reports_object_name ON reports(object_name);
