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
  ),
  
  -- ========== 金融场景示例数据 ==========
  
  -- 金融场景1: 个人风险评估
  (
    'FIN_RISK_ASSESS_001',
    '个人投资风险评估助手',
    '基于用户的财务状况、投资经验和风险承受能力，提供个性化的风险评估和投资建议',
    'qwen-plus',
    'EUVD',
    '你是一位专业的金融风险评估顾问。请根据以下客户信息进行风险评估：\n\n客户信息：{context}\n\n评估要求：\n1. 分析客户的风险承受能力（保守型/稳健型/积极型/激进型）\n2. 评估当前投资组合的风险等级\n3. 提供风险控制建议\n4. 推荐适合的资产配置比例\n\n请提供专业、客观的评估报告。',
    '1',
    0.3,
    3072,
    5,
    8,
    '金融,风险评估,投资顾问',
    'fin_risk_001'
  ),
  
  -- 金融场景2: 智能投顾
  (
    'FIN_INVESTMENT_ADV_001',
    '智能投资顾问',
    '为客户提供基于市场分析和个人需求的智能投资建议，包括股票、基金、债券等多种资产配置方案',
    'qwen-max',
    'EUVD',
    '你是一位资深的投资顾问，擅长资产配置和投资策略规划。\n\n市场信息：{context}\n客户问题：{question}\n\n请提供：\n1. 当前市场环境分析\n2. 投资机会识别\n3. 风险提示\n4. 具体的资产配置建议（包括比例）\n5. 操作时机建议\n\n注意：投资建议仅供参考，市场有风险，投资需谨慎。',
    '1',
    0.4,
    4096,
    6,
    10,
    '金融,投资顾问,资产配置,智能投顾',
    'fin_invest_001'
  ),
  
  -- 金融场景3: 贷款咨询
  (
    'FIN_LOAN_CONSULT_001',
    '个人贷款咨询助手',
    '为客户提供房贷、车贷、消费贷等各类贷款产品咨询，包括额度评估、利率计算、还款规划等',
    'qwen-plus',
    'EUVD',
    '你是一位专业的贷款咨询顾问。请基于以下信息为客户提供贷款咨询：\n\n贷款产品信息：{context}\n客户咨询：{question}\n\n咨询内容应包括：\n1. 贷款产品介绍（类型、期限、利率）\n2. 客户资质评估\n3. 可贷额度预估\n4. 月供计算\n5. 还款方式建议（等额本息/等额本金）\n6. 申请流程说明\n7. 注意事项提醒\n\n请用通俗易懂的语言解释专业术语。',
    '1',
    0.5,
    2048,
    4,
    6,
    '金融,贷款,咨询,房贷,车贷',
    'fin_loan_001'
  ),
  
  -- 金融场景4: 财务规划
  (
    'FIN_PLANNING_001',
    '家庭财务规划师',
    '为家庭提供全方位的财务规划服务，包括收支管理、储蓄计划、保险配置、子女教育金、养老规划等',
    'qwen-max',
    'EUVD',
    '你是一位专业的家庭财务规划师，擅长制定长期财务规划方案。\n\n家庭财务状况：{context}\n规划需求：{question}\n\n请提供完整的财务规划方案：\n1. 家庭财务现状分析（收入、支出、资产、负债）\n2. 财务目标设定（短期/中期/长期）\n3. 应急储备金建议\n4. 保险配置方案（寿险、重疾、意外、医疗）\n5. 子女教育金规划\n6. 养老金储备计划\n7. 投资理财建议\n8. 税务优化建议\n\n规划应切实可行，符合家庭实际情况。',
    '1',
    0.4,
    4096,
    5,
    10,
    '金融,财务规划,家庭理财,保险,养老',
    'fin_plan_001'
  ),
  
  -- 金融场景5: 信用卡服务
  (
    'FIN_CREDITCARD_001',
    '信用卡智能客服',
    '提供信用卡申请、额度查询、账单解读、积分兑换、分期业务等全方位服务',
    'qwen-turbo',
    'EUVD',
    '你是银行信用卡部门的智能客服，请为客户提供专业、友好的服务。\n\n知识库：{context}\n客户问题：{question}\n\n服务内容包括：\n1. 信用卡产品介绍（权益、年费、优惠）\n2. 申请条件和流程\n3. 额度查询和提升\n4. 账单解读和还款指导\n5. 积分查询和兑换\n6. 分期业务办理（账单分期、消费分期）\n7. 安全用卡提示\n8. 常见问题解答\n\n请用简洁、清晰的语言回答，必要时提供具体操作步骤。',
    '1',
    0.6,
    2048,
    4,
    5,
    '金融,信用卡,客服,分期,积分',
    'fin_card_001'
  ),
  
  -- 金融场景6: 基金投资
  (
    'FIN_FUND_INVEST_001',
    '基金投资顾问',
    '为投资者提供基金选择、定投策略、组合优化等专业建议，涵盖股票型、债券型、混合型、指数型等各类基金',
    'qwen-plus',
    'EUVD',
    '你是一位专业的基金投资顾问，精通各类基金产品和投资策略。\n\n基金市场信息：{context}\n投资者咨询：{question}\n\n请提供：\n1. 基金类型介绍和特点分析\n2. 基金筛选标准（业绩、基金经理、规模、费率）\n3. 投资策略建议（一次性买入/定投）\n4. 基金组合配置方案\n5. 风险收益评估\n6. 买卖时机判断\n7. 持仓调整建议\n\n提醒：基金投资有风险，过往业绩不代表未来表现。',
    '1',
    0.4,
    3072,
    5,
    8,
    '金融,基金,投资,定投,理财',
    'fin_fund_001'
  ),
  
  -- 金融场景7: 保险咨询
  (
    'FIN_INSURANCE_001',
    '保险规划顾问',
    '为客户提供寿险、健康险、财产险等全方位保险规划服务，包括需求分析、产品推荐、保额测算等',
    'qwen-plus',
    'EUVD',
    '你是一位专业的保险规划顾问，以客户需求为导向，提供科学的保险配置方案。\n\n客户信息：{context}\n保险需求：{question}\n\n咨询服务包括：\n1. 保险需求分析（人身风险、财产风险）\n2. 保额测算（寿险保额、重疾保额）\n3. 产品类型推荐（定期/终身、消费型/储蓄型）\n4. 保险组合方案设计\n5. 保费预算规划\n6. 投保注意事项\n7. 理赔流程说明\n8. 常见误区提醒\n\n坚持"先保障后理财"原则，优先配置基础保障。',
    '1',
    0.4,
    3072,
    5,
    8,
    '金融,保险,规划,寿险,健康险',
    'fin_insure_001'
  ),
  
  -- 金融场景8: 外汇交易
  (
    'FIN_FOREX_TRADE_001',
    '外汇交易助手',
    '为外汇交易者提供市场分析、交易策略、风险管理等专业指导',
    'qwen-max',
    'EUVD',
    '你是一位经验丰富的外汇交易分析师，精通技术分析和基本面分析。\n\n市场数据：{context}\n交易咨询：{question}\n\n分析内容包括：\n1. 主要货币对走势分析（EUR/USD、GBP/USD、USD/JPY等）\n2. 技术指标解读（MA、MACD、RSI、布林带）\n3. 支撑位和阻力位判断\n4. 基本面因素分析（经济数据、央行政策、地缘政治）\n5. 交易策略建议（做多/做空、入场点位、止损止盈）\n6. 风险管理方案（仓位控制、杠杆使用）\n7. 市场情绪分析\n\n警告：外汇交易杠杆高、风险大，请严格控制仓位和风险。',
    '1',
    0.3,
    4096,
    6,
    10,
    '金融,外汇,交易,投资,风险管理',
    'fin_forex_001'
  ),
  
  -- 金融场景9: 企业融资
  (
    'FIN_CORPORATE_FIN_001',
    '企业融资顾问',
    '为中小企业提供融资咨询服务，包括银行贷款、股权融资、债券发行、融资租赁等多种融资渠道',
    'qwen-max',
    'EUVD',
    '你是一位资深的企业融资顾问，熟悉各类融资渠道和融资工具。\n\n企业情况：{context}\n融资需求：{question}\n\n咨询服务包括：\n1. 融资需求诊断（金额、期限、用途）\n2. 融资渠道分析\n   - 银行贷款（流动资金贷款、固定资产贷款、信用贷款、抵押贷款）\n   - 股权融资（天使投资、VC、PE、IPO）\n   - 债券融资（企业债、公司债、中期票据）\n   - 其他方式（融资租赁、保理、供应链金融）\n3. 融资方案设计\n4. 融资成本测算\n5. 融资风险评估\n6. 资料准备清单\n7. 融资流程指导\n\n根据企业发展阶段和实际情况，提供最适合的融资方案。',
    '1',
    0.4,
    4096,
    5,
    10,
    '金融,企业融资,贷款,股权融资,债券',
    'fin_corp_001'
  ),
  
  -- 金融场景10: 财税咨询
  (
    'FIN_TAX_CONSULT_001',
    '个人财税咨询顾问',
    '为个人提供税务筹划、个税计算、专项扣除、退税申报等财税咨询服务',
    'qwen-plus',
    'EUVD',
    '你是一位专业的个人财税顾问，精通个人所得税法和税务筹划。\n\n税务政策：{context}\n客户咨询：{question}\n\n咨询内容包括：\n1. 个人所得税计算\n   - 工资薪金所得\n   - 劳务报酬所得\n   - 稿酬所得\n   - 特许权使用费所得\n   - 经营所得\n   - 财产转让所得等\n2. 专项附加扣除指导\n   - 子女教育\n   - 继续教育\n   - 大病医疗\n   - 住房贷款利息\n   - 住房租金\n   - 赡养老人\n   - 婴幼儿照护\n3. 年度汇算清缴指导\n4. 退税申报流程\n5. 合理避税建议\n6. 税务风险提示\n\n请依法纳税，合理筹划。',
    '1',
    0.5,
    3072,
    5,
    8,
    '金融,税务,个税,财税咨询,退税',
    'fin_tax_001'
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

-- 金融场景数据统计
SELECT '
✅ 金融场景数据统计
' AS '统计说明';

SELECT 
  COUNT(*) AS '金融场景总数',
  COUNT(CASE WHEN status = '1' THEN 1 END) AS '启用场景数',
  COUNT(CASE WHEN prompt_template IS NOT NULL THEN 1 END) AS '有模板场景数'
FROM `scene_map`
WHERE scene_code LIKE 'FIN_%';

-- 金融场景列表
SELECT 
  scene_code AS '场景代码',
  scene_name AS '场景名称',
  tags AS '标签',
  status AS '状态'
FROM `scene_map`
WHERE scene_code LIKE 'FIN_%'
ORDER BY scene_code;
