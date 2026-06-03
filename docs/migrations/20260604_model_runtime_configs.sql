-- 模型能力运行时配置：capability 多行表
-- 真实 API Key 不入库；表内仅保存 api_key_ref。

CREATE TABLE IF NOT EXISTS `model_runtime_configs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `scope_key` VARCHAR(64) NOT NULL,
  `capability` VARCHAR(64) NOT NULL,
  `provider` VARCHAR(64) NOT NULL,
  `base_url` VARCHAR(512) NOT NULL,
  `api_key_ref` VARCHAR(128) NOT NULL,
  `model_name` VARCHAR(128) NOT NULL,
  `timeout_seconds` DOUBLE NOT NULL DEFAULT 60,
  `settings_json` TEXT,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_runtime_scope_capability` (`scope_key`, `capability`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型能力运行时配置（不存真实 API Key）';

CREATE TABLE IF NOT EXISTS `student_qa_retrieval_runtime_configs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `scope_key` VARCHAR(64) NOT NULL,
  `retrieval_enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `retrieval_top_k` INT NOT NULL DEFAULT 5,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_student_qa_retrieval_runtime_scope` (`scope_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生 QA 检索运行时配置';

-- 旧 qa_runtime_configs -> 新 capability 行。
-- base_url / api_key_ref 使用当前 DashScope 默认引用；真实 key 仍来自 config.local.py。
INSERT INTO `model_runtime_configs`
  (`scope_key`, `capability`, `provider`, `base_url`, `api_key_ref`, `model_name`, `timeout_seconds`, `settings_json`)
SELECT 'global', 'student_text_chat', 'dashscope', 'https://dashscope.aliyuncs.com', 'dashscope_api_key',
       `qa_llm_model`, 60, NULL
FROM `qa_runtime_configs`
WHERE `scope_key` = 'student_qa_global'
ON DUPLICATE KEY UPDATE
  `model_name` = VALUES(`model_name`),
  `updated_at` = CURRENT_TIMESTAMP;

INSERT INTO `model_runtime_configs`
  (`scope_key`, `capability`, `provider`, `base_url`, `api_key_ref`, `model_name`, `timeout_seconds`, `settings_json`)
SELECT 'global', 'student_vision_chat', 'dashscope', 'https://dashscope.aliyuncs.com', 'dashscope_api_key',
       `qa_multimodal_model`, 60, NULL
FROM `qa_runtime_configs`
WHERE `scope_key` = 'student_qa_global'
ON DUPLICATE KEY UPDATE
  `model_name` = VALUES(`model_name`),
  `updated_at` = CURRENT_TIMESTAMP;

INSERT INTO `model_runtime_configs`
  (`scope_key`, `capability`, `provider`, `base_url`, `api_key_ref`, `model_name`, `timeout_seconds`, `settings_json`)
SELECT 'global', 'student_embedding', 'dashscope', 'https://dashscope.aliyuncs.com', 'dashscope_api_key',
       `qa_embedding_model`, 120, JSON_OBJECT('dimensions', 1024)
FROM `qa_runtime_configs`
WHERE `scope_key` = 'student_qa_global'
ON DUPLICATE KEY UPDATE
  `model_name` = VALUES(`model_name`),
  `settings_json` = VALUES(`settings_json`),
  `updated_at` = CURRENT_TIMESTAMP;

INSERT INTO `student_qa_retrieval_runtime_configs`
  (`scope_key`, `retrieval_enabled`, `retrieval_top_k`)
SELECT 'student_qa_global', `retrieval_enabled`, `retrieval_top_k`
FROM `qa_runtime_configs`
WHERE `scope_key` = 'student_qa_global'
ON DUPLICATE KEY UPDATE
  `retrieval_enabled` = VALUES(`retrieval_enabled`),
  `retrieval_top_k` = VALUES(`retrieval_top_k`),
  `updated_at` = CURRENT_TIMESTAMP;
