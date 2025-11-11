-- ==========================================
-- 创建 scene_map 表
-- ==========================================
-- 说明：
--   定义场景映射表结构
--   包含场景代码、提示词模板、知识库配置等字段
-- ==========================================

USE `omservice`;

-- 删除旧表（可选，首次安装可注释掉）
-- DROP TABLE IF EXISTS `scene_map`;

-- 创建 scene_map 表
CREATE TABLE IF NOT EXISTS `scene_map` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `scene_name` varchar(120) NOT NULL COMMENT '场景名称',
  `scene_code` varchar(120) NOT NULL COMMENT '场景代码（唯一标识）',
  `description` varchar(258) DEFAULT NULL COMMENT '场景描述',
  `model` varchar(128) DEFAULT NULL COMMENT '当前使用的模型',
  `knowledge_es_name` varchar(128) DEFAULT NULL COMMENT '盘古助手代码',
  `knowledge_code` varchar(128) DEFAULT NULL COMMENT '星火助手代码',
  `tags` varchar(128) DEFAULT 'DEFAULT' COMMENT '标签',
  `picture` varchar(128) DEFAULT 'defaultImg' COMMENT '图片key',
  `picture_chat` tinyint(4) DEFAULT '0' COMMENT '是否图文问答(1-是 0-否)（星火）',
  `filter_type` tinyint(4) DEFAULT '0' COMMENT '场景类型（0：非金服场景；1：金服场景）（仅用于后端过滤）',
  `version` varchar(128) DEFAULT '2.3' COMMENT 'docqa版本(2.3、3.4)',
  `url` varchar(128) DEFAULT '/im/websocket/distWebSocket' COMMENT 'docqa请求路径',
  `status` varchar(1) DEFAULT '1' COMMENT '状态：1-正常 0-停用',
  `create_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `prompt_template` text DEFAULT NULL COMMENT '提示词模板',
  `repository` varchar(128) NOT NULL DEFAULT 'SPARK' COMMENT '知识库类型',
  `top_k` int(4) unsigned DEFAULT '4' COMMENT '从k个候选中随机选择⼀个，控制回答的随机性[1,6]',
  `max_tokens` int(9) unsigned DEFAULT '4096' COMMENT '生成文本的最大token数量',
  `temperature` float(2,1) DEFAULT '0.5' COMMENT '用于控制生成文本的多样性和创造力(0, 1]',
  `embedding_top` int(4) unsigned DEFAULT '5' COMMENT '向量召回条数[1-50]',
  `threshold_score` float(2,1) DEFAULT '0' COMMENT '相似度阈值',
  `qa_top` int(4) unsigned DEFAULT '0' COMMENT 'QA对召回条数',
  `qa_threshold_score` float(2,1) DEFAULT '0.9' COMMENT 'QA对阈值',
  `is_auth_verify` tinyint(1) DEFAULT '0' COMMENT '是否开启用户机构权限校验',
  `auth_type` varchar(128) DEFAULT 'or' COMMENT '多个权限的关系：and是交集，or是并集',
  `qq_emb_top` int(4) DEFAULT '0' COMMENT 'QQ对召回条数[0,50]',
  `es_top` int(4) DEFAULT '0' COMMENT 'es查询条数[0-5]',
  `context_enabled` tinyint(1) DEFAULT '0' COMMENT '上下文理解（1为需要，0为不需要）',
  `assistant_order` int(11) DEFAULT '9999' COMMENT '助手顺序',
  `new_label_start_time` timestamp NULL DEFAULT NULL COMMENT '新标识开始时间',
  `new_label_end_time` timestamp NULL DEFAULT NULL COMMENT '新标识结束时间',
  `labels` varchar(256) DEFAULT NULL COMMENT '向量库标签',
  `scene_type` tinyint(4) DEFAULT '0' COMMENT '场景助手类型（0：普通场景；1：定制化开发页面场景；2：链接跳转场景）',
  `page_id` varchar(128) DEFAULT NULL COMMENT '前端跳转的页面ID（用于定制化开发页面场景）',
  `contact_people` decimal(10,0) DEFAULT NULL COMMENT '联系人ID',
  `space_codes` varchar(256) DEFAULT NULL COMMENT '知识服务平台空间编码',
  
  -- 主键和索引
  PRIMARY KEY (`scene_code`),
  UNIQUE KEY `idx_scene_code` (`scene_code`),
  KEY `idx_id` (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_repository` (`repository`),
  KEY `idx_create_time` (`create_time`),
  KEY `idx_update_time` (`update_time`)
  
) ENGINE=InnoDB 
  AUTO_INCREMENT=1 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='场景映射表';

-- 显示创建结果
SELECT '✅ scene_map 表创建成功' AS status;
