ALTER TABLE `qa_messages`
  MODIFY COLUMN `question_type` ENUM('text', 'voice', 'image', 'mixed') DEFAULT NULL;

CREATE TABLE IF NOT EXISTS `qa_message_attachments` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `message_id` BIGINT UNSIGNED NOT NULL,
  `session_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `attachment_type` ENUM('image') NOT NULL DEFAULT 'image',
  `storage_provider` VARCHAR(32) NOT NULL DEFAULT 'local',
  `storage_key` VARCHAR(255) NOT NULL,
  `file_url` VARCHAR(255) NOT NULL,
  `file_name` VARCHAR(255) NOT NULL,
  `mime_type` VARCHAR(64) NOT NULL,
  `file_size` BIGINT UNSIGNED DEFAULT NULL,
  `sort_no` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_qa_message_attachments_message` (`message_id`, `sort_no`),
  KEY `idx_qa_message_attachments_session` (`session_id`, `created_at`),
  CONSTRAINT `fk_qa_message_attachments_message` FOREIGN KEY (`message_id`) REFERENCES `qa_messages` (`id`),
  CONSTRAINT `fk_qa_message_attachments_session` FOREIGN KEY (`session_id`) REFERENCES `qa_sessions` (`id`),
  CONSTRAINT `fk_qa_message_attachments_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='问答消息附件';
