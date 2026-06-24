-- ============================================================================
-- 为 reports 表新增 linked_org_name 字段
-- ============================================================================
-- linked_org_name 存储用户所属行政机构名称，来自 queryUserInfo 接口
-- ============================================================================

ALTER TABLE reports
ADD COLUMN IF NOT EXISTS linked_org_name VARCHAR(128);

COMMENT ON COLUMN reports.linked_org_name IS '用户行政机构名称（linkedOrgName），来自 queryUserInfo 接口';
