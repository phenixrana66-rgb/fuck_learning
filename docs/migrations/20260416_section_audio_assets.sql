USE `chaoxing_ai_course`;

CREATE TABLE IF NOT EXISTS `chapter_section_audio_assets` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `audio_asset_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `chapter_id` BIGINT UNSIGNED NOT NULL,
  `script_id` BIGINT UNSIGNED NOT NULL,
  `script_section_id` BIGINT UNSIGNED NOT NULL,
  `voice_type` VARCHAR(32) NOT NULL,
  `audio_format` VARCHAR(16) NOT NULL DEFAULT 'mp3',
  `audio_url` VARCHAR(255) NOT NULL,
  `duration_sec` INT DEFAULT NULL,
  `file_size` BIGINT UNSIGNED DEFAULT NULL,
  `bit_rate` INT DEFAULT NULL,
  `status` ENUM('generated', 'published') NOT NULL DEFAULT 'generated',
  `sort_no` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_section_audio_asset` (`audio_asset_id`, `script_section_id`),
  KEY `idx_section_audio_sort` (`script_id`, `sort_no`),
  CONSTRAINT `fk_section_audio_audio_asset` FOREIGN KEY (`audio_asset_id`) REFERENCES `chapter_audio_assets` (`id`),
  CONSTRAINT `fk_section_audio_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_section_audio_chapter` FOREIGN KEY (`chapter_id`) REFERENCES `course_chapters` (`id`),
  CONSTRAINT `fk_section_audio_script` FOREIGN KEY (`script_id`) REFERENCES `chapter_scripts` (`id`),
  CONSTRAINT `fk_section_audio_script_section` FOREIGN KEY (`script_section_id`) REFERENCES `chapter_script_sections` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='section 级音频资源';

ALTER TABLE `lesson_sections`
  ADD COLUMN IF NOT EXISTS `section_audio_asset_id` BIGINT UNSIGNED DEFAULT NULL AFTER `audio_asset_id`,
  ADD CONSTRAINT `fk_lesson_sections_section_audio`
    FOREIGN KEY (`section_audio_asset_id`) REFERENCES `chapter_section_audio_assets` (`id`);
