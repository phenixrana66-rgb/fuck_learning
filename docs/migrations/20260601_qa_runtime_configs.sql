-- 学生 QA 实验台运行时配置表

CREATE TABLE IF NOT EXISTS `qa_runtime_configs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `scope_key` VARCHAR(64) NOT NULL,
  `qa_llm_model` VARCHAR(128) NOT NULL,
  `qa_multimodal_model` VARCHAR(128) NOT NULL,
  `qa_embedding_model` VARCHAR(128) NOT NULL,
  `retrieval_enabled` TINYINT(1) NOT NULL DEFAULT 1,
  `retrieval_top_k` INT NOT NULL DEFAULT 5,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_qa_runtime_configs_scope` (`scope_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生 QA 运行时实验配置';
