-- ==========================================
-- 插入示例数据
-- ==========================================
-- 说明：
--   插入一些示例场景数据用于测试
--   生产环境可以删除此文件或注释掉
--   配合 USAGE.md 中的案例5：查询 EUVD 库中有效场景
-- ==========================================

USE `omservice`;

-- 删除旧数据（如果存在）
DELETE FROM `scene_map` WHERE scene_code LIKE 'DEMO_%';

-- 插入示例场景数据
INSERT INTO `scene_map` (
  `scene_code`,
  `scene_name`,
  `description`,
  `model`,
  `repository`,
  `prompt_template`,
  `status`,
  `temperature`,
  `max_tokens`,
  `top_k`,
  `embedding_top`,
  `tags`,
  `picture`
) VALUES 
  -- 案例1: EUVD 正常场景（有模板）
  (
    'DEMO_EUVD_001',
    'EUVD AI助手场景1',
    '这是一个EUVD知识库的AI助手示例场景，用于测试prompt_template不为空的查询',
    'qwen-plus',
    'EUVD',
    '你是一个专业的AI助手，请根据以下上下文回答用户问题：\n\n上下文：{context}\n\n用户问题：{question}\n\n请提供详细、准确的回答。',
    '1',
    0.7,
    2048,
    4,
    5,
    'AI助手,EUVD',
    'euvd_demo_001'
  ),
  
  -- 案例2: EUVD 正常场景（有模板）
  (
    'DEMO_EUVD_002',
    'EUVD 客服助手场景',
    '另一个EUVD知识库的客服助手示例场景',
    'qwen-turbo',
    'EUVD',
    '你是一个友好的客服助手，请根据知识库内容回答：\n\n知识库内容：{context}\n\n客户问题：{question}\n\n回答要求：简洁、专业、友好',
    '1',
    0.5,
    1024,
    3,
    3,
    '客服,EUVD',
    'euvd_demo_002'
  ),
  
  -- 案例3: SPARK 场景（用于对比测试）
  (
    'DEMO_SPARK_001',
    'SPARK 知识问答场景',
    '这是一个SPARK知识库的示例场景，用于测试repository过滤',
    'spark-v3',
    'SPARK',
    '基于以下信息回答问题：{context}\n问题：{question}',
    '1',
    0.6,
    2048,
    4,
    5,
    '知识问答,SPARK',
    'spark_demo_001'
  ),
  
  -- 案例4: EUVD 空模板场景（用于测试 exclude_empty_template=True 过滤）
  (
    'DEMO_EUVD_EMPTY',
    'EUVD 空模板测试场景',
    '这个场景没有提示词模板，用于测试 exclude_empty_template 参数过滤功能',
    'qwen-plus',
    'EUVD',
    NULL,  -- 故意设置为 NULL
    '1',
    0.5,
    2048,
    4,
    5,
    '测试,EUVD',
    'euvd_empty'
  ),
  
  -- 案例5: EUVD 已停用场景（用于测试 status 过滤）
  (
    'DEMO_EUVD_DISABLED',
    'EUVD 已停用测试场景',
    '这个场景已停用，用于测试 status 参数过滤功能',
    'qwen-plus',
    'EUVD',
    '这是一个已停用的提示词模板，不应该被查询到',
    '0',  -- 状态设置为停用
    0.5,
    2048,
    4,
    5,
    '测试,EUVD,停用',
    'euvd_disabled'
  );

-- 显示插入结果
SELECT '✅ 示例数据插入成功' AS status;
SELECT COUNT(*) AS '插入记录数' FROM `scene_map` WHERE scene_code LIKE 'DEMO_%';

-- 查看插入的数据概览
SELECT 
  scene_code AS '场景代码',
  scene_name AS '场景名称',
  repository AS '知识库',
  status AS '状态',
  CASE 
    WHEN prompt_template IS NULL THEN 'NULL'
    WHEN prompt_template = '' THEN '空字符串'
    ELSE CONCAT(LEFT(prompt_template, 20), '...')
  END AS '模板预览'
FROM `scene_map`
WHERE scene_code LIKE 'DEMO_%'
ORDER BY scene_code;

-- 测试查询：查找 EUVD 库中 status='1' 且 prompt_template 不为空的场景
SELECT '
✅ 测试查询：查找 EUVD 库中有效场景（repository=EUVD AND status=1 AND prompt_template 不为空）
' AS '测试说明';

SELECT 
  scene_code AS '场景代码',
  scene_name AS '场景名称',
  CONCAT(LEFT(prompt_template, 30), '...') AS '模板预览'
FROM `scene_map`
WHERE repository = 'EUVD'
  AND status = '1'
  AND prompt_template IS NOT NULL
  AND prompt_template != ''
  AND scene_code LIKE 'DEMO_%'
ORDER BY scene_code;

SELECT CONCAT('
预期结果：2 条记录 (DEMO_EUVD_001, DEMO_EUVD_002)
实际结果：', COUNT(*), ' 条记录
') AS '验证结果'
FROM `scene_map`
WHERE repository = 'EUVD'
  AND status = '1'
  AND prompt_template IS NOT NULL
  AND prompt_template != ''
  AND scene_code LIKE 'DEMO_%';
