-- 基于泛雅平台的 AI 互动智课生成与实时问答系统
-- MySQL 8 建表脚本（教师端 + 学生端共享主库）

CREATE DATABASE IF NOT EXISTS `chaoxing_ai_course`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE `chaoxing_ai_course`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `api_call_logs`;
DROP TABLE IF EXISTS `voice_transcripts`;
DROP TABLE IF EXISTS `qa_message_knowledge_refs`;
DROP TABLE IF EXISTS `qa_answers`;
DROP TABLE IF EXISTS `qa_messages`;
DROP TABLE IF EXISTS `qa_sessions`;
DROP TABLE IF EXISTS `student_section_mastery_logs`;
DROP TABLE IF EXISTS `student_practice_answers`;
DROP TABLE IF EXISTS `student_practice_attempts`;
DROP TABLE IF EXISTS `progress_adjust_records`;
DROP TABLE IF EXISTS `progress_track_logs`;
DROP TABLE IF EXISTS `resume_records`;
DROP TABLE IF EXISTS `student_page_progress`;
DROP TABLE IF EXISTS `student_section_progress`;
DROP TABLE IF EXISTS `student_lesson_progress`;
DROP TABLE IF EXISTS `notification_receipts`;
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `lesson_section_knowledge_points`;
DROP TABLE IF EXISTS `lesson_section_anchors`;
DROP TABLE IF EXISTS `lesson_section_pages`;
DROP TABLE IF EXISTS `lesson_sections`;
DROP TABLE IF EXISTS `lesson_units`;
DROP TABLE IF EXISTS `lessons`;
DROP TABLE IF EXISTS `chapter_practice_items`;
DROP TABLE IF EXISTS `chapter_practices`;
DROP TABLE IF EXISTS `chapter_audio_assets`;
DROP TABLE IF EXISTS `chapter_script_sections`;
DROP TABLE IF EXISTS `chapter_scripts`;
DROP TABLE IF EXISTS `chapter_knowledge_nodes`;
DROP TABLE IF EXISTS `chapter_parse_results`;
DROP TABLE IF EXISTS `chapter_parse_tasks`;
DROP TABLE IF EXISTS `chapter_ppt_assets`;
DROP TABLE IF EXISTS `course_chapters`;
DROP TABLE IF EXISTS `course_members`;
DROP TABLE IF EXISTS `course_classes`;
DROP TABLE IF EXISTS `course_platform_bindings`;
DROP TABLE IF EXISTS `courses`;
DROP TABLE IF EXISTS `user_platform_bindings`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `schools`;
DROP TABLE IF EXISTS `platforms`;

CREATE TABLE `platforms` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `platform_code` VARCHAR(64) NOT NULL,
  `platform_name` VARCHAR(128) NOT NULL,
  `api_base_url` VARCHAR(255) DEFAULT NULL,
  `status` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_code` (`platform_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='外部平台主表';

CREATE TABLE `schools` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `school_code` VARCHAR(64) NOT NULL,
  `school_name` VARCHAR(128) NOT NULL,
  `status` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_school_code` (`school_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学校主表';

CREATE TABLE `users` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_no` VARCHAR(64) NOT NULL,
  `user_name` VARCHAR(64) NOT NULL,
  `role` ENUM('student', 'teacher', 'admin') NOT NULL,
  `school_id` BIGINT UNSIGNED NOT NULL,
  `phone` VARCHAR(32) DEFAULT NULL,
  `email` VARCHAR(128) DEFAULT NULL,
  `auth_token` VARCHAR(512) DEFAULT NULL,
  `status` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_no` (`user_no`),
  KEY `idx_users_school_role` (`school_id`, `role`),
  CONSTRAINT `fk_users_school` FOREIGN KEY (`school_id`) REFERENCES `schools` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='统一用户表';

CREATE TABLE `user_platform_bindings` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `platform_id` BIGINT UNSIGNED NOT NULL,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `external_user_id` VARCHAR(64) NOT NULL,
  `external_role` VARCHAR(16) NOT NULL,
  `related_course_ids` JSON DEFAULT NULL,
  `raw_payload` JSON DEFAULT NULL,
  `sync_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_user` (`platform_id`, `external_user_id`),
  KEY `idx_upb_user` (`user_id`),
  CONSTRAINT `fk_upb_platform` FOREIGN KEY (`platform_id`) REFERENCES `platforms` (`id`),
  CONSTRAINT `fk_upb_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户与外部平台映射';

CREATE TABLE `courses` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `course_code` VARCHAR(64) NOT NULL,
  `course_name` VARCHAR(255) NOT NULL,
  `school_id` BIGINT UNSIGNED NOT NULL,
  `term` VARCHAR(32) DEFAULT NULL,
  `credit` DECIMAL(4,1) DEFAULT NULL,
  `period` INT DEFAULT NULL,
  `course_cover_url` VARCHAR(255) DEFAULT NULL,
  `course_status` ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'draft',
  `created_by` BIGINT UNSIGNED DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_course_code` (`course_code`),
  KEY `idx_courses_school_status` (`school_id`, `course_status`),
  CONSTRAINT `fk_courses_school` FOREIGN KEY (`school_id`) REFERENCES `schools` (`id`),
  CONSTRAINT `fk_courses_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课程主表';

CREATE TABLE `course_platform_bindings` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `platform_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `external_course_id` VARCHAR(64) NOT NULL,
  `raw_payload` JSON DEFAULT NULL,
  `sync_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_course` (`platform_id`, `external_course_id`),
  KEY `idx_course_platform_course` (`course_id`),
  CONSTRAINT `fk_course_platform_bindings_platform` FOREIGN KEY (`platform_id`) REFERENCES `platforms` (`id`),
  CONSTRAINT `fk_course_platform_bindings_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课程与外部平台映射';

CREATE TABLE `course_classes` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `class_code` VARCHAR(64) NOT NULL,
  `class_name` VARCHAR(128) NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `school_id` BIGINT UNSIGNED NOT NULL,
  `teacher_id` BIGINT UNSIGNED DEFAULT NULL,
  `status` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_class_code` (`class_code`),
  KEY `idx_course_classes_course` (`course_id`),
  CONSTRAINT `fk_course_classes_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_course_classes_school` FOREIGN KEY (`school_id`) REFERENCES `schools` (`id`),
  CONSTRAINT `fk_course_classes_teacher` FOREIGN KEY (`teacher_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教学班表';

CREATE TABLE `course_members` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `class_id` BIGINT UNSIGNED DEFAULT NULL,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `member_role` ENUM('teacher', 'student') NOT NULL,
  `joined_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_course_member` (`course_id`, `user_id`, `member_role`),
  KEY `idx_course_members_user` (`user_id`),
  CONSTRAINT `fk_course_members_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_course_members_class` FOREIGN KEY (`class_id`) REFERENCES `course_classes` (`id`),
  CONSTRAINT `fk_course_members_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课程成员关系';

CREATE TABLE `course_chapters` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `parent_id` BIGINT UNSIGNED DEFAULT NULL,
  `chapter_code` VARCHAR(64) NOT NULL,
  `chapter_name` VARCHAR(255) NOT NULL,
  `chapter_type` ENUM('unit', 'chapter', 'section') NOT NULL DEFAULT 'chapter',
  `chapter_level` TINYINT UNSIGNED NOT NULL DEFAULT 1,
  `sort_no` INT NOT NULL DEFAULT 0,
  `status` ENUM('draft', 'published') NOT NULL DEFAULT 'draft',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_course_chapter_code` (`course_id`, `chapter_code`),
  KEY `idx_course_chapters_parent` (`parent_id`),
  KEY `idx_course_chapters_sort` (`course_id`, `sort_no`),
  CONSTRAINT `fk_course_chapters_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_course_chapters_parent` FOREIGN KEY (`parent_id`) REFERENCES `course_chapters` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教师侧课程章节树';

CREATE TABLE `chapter_ppt_assets` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `chapter_id` BIGINT UNSIGNED NOT NULL,
  `uploader_id` BIGINT UNSIGNED NOT NULL,
  `file_name` VARCHAR(255) NOT NULL,
  `file_type` ENUM('ppt', 'pptx', 'pdf') NOT NULL,
  `file_url` VARCHAR(255) NOT NULL,
  `file_size` BIGINT UNSIGNED DEFAULT NULL,
  `page_count` INT DEFAULT NULL,
  `upload_status` ENUM('uploaded', 'parsing', 'parsed', 'failed') NOT NULL DEFAULT 'uploaded',
  `version_no` INT NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_chapter_ppt_ver` (`chapter_id`, `version_no`),
  KEY `idx_chapter_ppt_course` (`course_id`, `chapter_id`),
  CONSTRAINT `fk_chapter_ppt_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_chapter_ppt_chapter` FOREIGN KEY (`chapter_id`) REFERENCES `course_chapters` (`id`),
  CONSTRAINT `fk_chapter_ppt_uploader` FOREIGN KEY (`uploader_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教师按章节上传的 PPT 原文件';

CREATE TABLE `chapter_parse_tasks` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `parse_no` VARCHAR(64) NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `chapter_id` BIGINT UNSIGNED NOT NULL,
  `ppt_asset_id` BIGINT UNSIGNED NOT NULL,
  `teacher_id` BIGINT UNSIGNED NOT NULL,
  `llm_model` VARCHAR(64) DEFAULT NULL,
  `is_extract_key_point` TINYINT(1) NOT NULL DEFAULT 1,
  `task_status` ENUM('processing', 'completed', 'failed') NOT NULL DEFAULT 'processing',
  `error_msg` VARCHAR(500) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `finished_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_parse_no` (`parse_no`),
  KEY `idx_parse_task_lookup` (`chapter_id`, `task_status`),
  CONSTRAINT `fk_parse_task_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_parse_task_chapter` FOREIGN KEY (`chapter_id`) REFERENCES `course_chapters` (`id`),
  CONSTRAINT `fk_parse_task_ppt` FOREIGN KEY (`ppt_asset_id`) REFERENCES `chapter_ppt_assets` (`id`),
  CONSTRAINT `fk_parse_task_teacher` FOREIGN KEY (`teacher_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='章节 PPT LLM 解析任务';

CREATE TABLE `chapter_parse_results` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `parse_task_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `chapter_id` BIGINT UNSIGNED NOT NULL,
  `ppt_asset_id` BIGINT UNSIGNED NOT NULL,
  `chapter_summary` TEXT,
  `parsed_outline` JSON DEFAULT NULL,
  `key_points` JSON DEFAULT NULL,
  `formulas` JSON DEFAULT NULL,
  `charts` JSON DEFAULT NULL,
  `page_mapping` JSON DEFAULT NULL,
  `raw_llm_output` LONGTEXT,
  `normalized_content` LONGTEXT,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_parse_result_task` (`parse_task_id`),
  KEY `idx_parse_results_chapter` (`chapter_id`),
  CONSTRAINT `fk_parse_results_task` FOREIGN KEY (`parse_task_id`) REFERENCES `chapter_parse_tasks` (`id`),
  CONSTRAINT `fk_parse_results_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_parse_results_chapter` FOREIGN KEY (`chapter_id`) REFERENCES `course_chapters` (`id`),
  CONSTRAINT `fk_parse_results_ppt` FOREIGN KEY (`ppt_asset_id`) REFERENCES `chapter_ppt_assets` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='章节解析结果快照';

CREATE TABLE `chapter_knowledge_nodes` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `parse_task_id` BIGINT UNSIGNED NOT NULL,
  `chapter_id` BIGINT UNSIGNED NOT NULL,
  `parent_id` BIGINT UNSIGNED DEFAULT NULL,
  `node_code` VARCHAR(64) NOT NULL,
  `node_name` VARCHAR(255) NOT NULL,
  `node_type` ENUM('unit', 'chapter', 'subchapter', 'knowledge') NOT NULL DEFAULT 'knowledge',
  `level_no` TINYINT UNSIGNED NOT NULL DEFAULT 1,
  `is_key_point` TINYINT(1) NOT NULL DEFAULT 0,
  `page_start` INT DEFAULT NULL,
  `page_end` INT DEFAULT NULL,
  `sort_no` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_parse_node_code` (`parse_task_id`, `node_code`),
  KEY `idx_ckn_chapter_parent` (`chapter_id`, `parent_id`),
  CONSTRAINT `fk_ckn_parse_task` FOREIGN KEY (`parse_task_id`) REFERENCES `chapter_parse_tasks` (`id`),
  CONSTRAINT `fk_ckn_chapter` FOREIGN KEY (`chapter_id`) REFERENCES `course_chapters` (`id`),
  CONSTRAINT `fk_ckn_parent` FOREIGN KEY (`parent_id`) REFERENCES `chapter_knowledge_nodes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='解析出的章节知识树';

CREATE TABLE `chapter_scripts` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `script_no` VARCHAR(64) NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `chapter_id` BIGINT UNSIGNED NOT NULL,
  `parse_task_id` BIGINT UNSIGNED NOT NULL,
  `teacher_id` BIGINT UNSIGNED NOT NULL,
  `teaching_style` VARCHAR(32) NOT NULL DEFAULT 'standard',
  `speech_speed` VARCHAR(16) NOT NULL DEFAULT 'normal',
  `custom_opening` TEXT,
  `script_status` ENUM('generated', 'edited', 'published') NOT NULL DEFAULT 'generated',
  `version_no` INT NOT NULL DEFAULT 1,
  `edit_url` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_script_no` (`script_no`),
  KEY `idx_chapter_scripts_chapter` (`chapter_id`, `script_status`),
  CONSTRAINT `fk_chapter_scripts_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_chapter_scripts_chapter` FOREIGN KEY (`chapter_id`) REFERENCES `course_chapters` (`id`),
  CONSTRAINT `fk_chapter_scripts_parse_task` FOREIGN KEY (`parse_task_id`) REFERENCES `chapter_parse_tasks` (`id`),
  CONSTRAINT `fk_chapter_scripts_teacher` FOREIGN KEY (`teacher_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='章节讲稿主表';

CREATE TABLE `chapter_script_sections` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `script_id` BIGINT UNSIGNED NOT NULL,
  `section_code` VARCHAR(64) NOT NULL,
  `section_name` VARCHAR(255) NOT NULL,
  `section_content` LONGTEXT NOT NULL,
  `duration_sec` INT DEFAULT NULL,
  `related_node_id` BIGINT UNSIGNED DEFAULT NULL,
  `related_page_range` VARCHAR(64) DEFAULT NULL,
  `sort_no` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_script_section_code` (`script_id`, `section_code`),
  KEY `idx_script_sections_sort` (`script_id`, `sort_no`),
  CONSTRAINT `fk_script_sections_script` FOREIGN KEY (`script_id`) REFERENCES `chapter_scripts` (`id`),
  CONSTRAINT `fk_script_sections_node` FOREIGN KEY (`related_node_id`) REFERENCES `chapter_knowledge_nodes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='讲稿分段';

CREATE TABLE `chapter_audio_assets` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `chapter_id` BIGINT UNSIGNED NOT NULL,
  `script_id` BIGINT UNSIGNED NOT NULL,
  `voice_type` VARCHAR(32) NOT NULL,
  `audio_format` VARCHAR(16) NOT NULL DEFAULT 'mp3',
  `audio_url` VARCHAR(255) NOT NULL,
  `total_duration_sec` INT DEFAULT NULL,
  `file_size` BIGINT UNSIGNED DEFAULT NULL,
  `bit_rate` INT DEFAULT NULL,
  `status` ENUM('generated', 'published') NOT NULL DEFAULT 'generated',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audio_assets_chapter` (`chapter_id`, `status`),
  CONSTRAINT `fk_audio_assets_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_audio_assets_chapter` FOREIGN KEY (`chapter_id`) REFERENCES `course_chapters` (`id`),
  CONSTRAINT `fk_audio_assets_script` FOREIGN KEY (`script_id`) REFERENCES `chapter_scripts` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='章节音频资源';

CREATE TABLE `chapter_practices` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `practice_code` VARCHAR(64) NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `chapter_id` BIGINT UNSIGNED NOT NULL,
  `created_by` BIGINT UNSIGNED NOT NULL,
  `practice_title` VARCHAR(255) NOT NULL,
  `practice_desc` TEXT,
  `practice_type` ENUM('exercise', 'quiz') NOT NULL DEFAULT 'exercise',
  `difficulty_level` ENUM('easy', 'medium', 'hard') NOT NULL DEFAULT 'medium',
  `total_score` DECIMAL(8,2) NOT NULL DEFAULT 100.00,
  `item_count` INT NOT NULL DEFAULT 0,
  `time_limit_minutes` INT DEFAULT NULL,
  `publish_status` ENUM('draft', 'published', 'closed') NOT NULL DEFAULT 'draft',
  `start_at` DATETIME DEFAULT NULL,
  `end_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_practice_code` (`practice_code`),
  KEY `idx_chapter_practices_chapter` (`chapter_id`, `publish_status`),
  CONSTRAINT `fk_chapter_practices_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_chapter_practices_chapter` FOREIGN KEY (`chapter_id`) REFERENCES `course_chapters` (`id`),
  CONSTRAINT `fk_chapter_practices_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教师布置的章节练习';

CREATE TABLE `chapter_practice_items` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `practice_id` BIGINT UNSIGNED NOT NULL,
  `item_no` VARCHAR(64) NOT NULL,
  `item_type` ENUM('single_choice', 'multiple_choice', 'judge', 'short_answer', 'calculation') NOT NULL,
  `stem` LONGTEXT NOT NULL,
  `options_json` JSON DEFAULT NULL,
  `correct_answer_json` JSON DEFAULT NULL,
  `analysis_text` LONGTEXT,
  `score` DECIMAL(8,2) NOT NULL DEFAULT 0.00,
  `sort_no` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_practice_item_no` (`practice_id`, `item_no`),
  KEY `idx_practice_items_sort` (`practice_id`, `sort_no`),
  CONSTRAINT `fk_practice_items_practice` FOREIGN KEY (`practice_id`) REFERENCES `chapter_practices` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='章节练习题目';

CREATE TABLE `lessons` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `lesson_no` VARCHAR(64) NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_name` VARCHAR(255) NOT NULL,
  `teacher_id` BIGINT UNSIGNED NOT NULL,
  `publish_version` INT NOT NULL DEFAULT 1,
  `publish_status` ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'published',
  `published_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_lesson_no` (`lesson_no`),
  UNIQUE KEY `uk_course_publish_ver` (`course_id`, `publish_version`),
  KEY `idx_lessons_course_status` (`course_id`, `publish_status`),
  CONSTRAINT `fk_lessons_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_lessons_teacher` FOREIGN KEY (`teacher_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='发布后的学生端智课';

CREATE TABLE `lesson_units` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `source_chapter_id` BIGINT UNSIGNED DEFAULT NULL,
  `unit_code` VARCHAR(64) NOT NULL,
  `unit_title` VARCHAR(255) NOT NULL,
  `sort_no` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_lesson_unit_code` (`lesson_id`, `unit_code`),
  KEY `idx_lesson_units_sort` (`lesson_id`, `sort_no`),
  CONSTRAINT `fk_lesson_units_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_lesson_units_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_lesson_units_source_chapter` FOREIGN KEY (`source_chapter_id`) REFERENCES `course_chapters` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生端知识单元';

CREATE TABLE `lesson_sections` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `unit_id` BIGINT UNSIGNED NOT NULL,
  `source_chapter_id` BIGINT UNSIGNED NOT NULL,
  `parse_result_id` BIGINT UNSIGNED DEFAULT NULL,
  `ppt_asset_id` BIGINT UNSIGNED DEFAULT NULL,
  `script_id` BIGINT UNSIGNED DEFAULT NULL,
  `audio_asset_id` BIGINT UNSIGNED DEFAULT NULL,
  `section_code` VARCHAR(64) NOT NULL,
  `section_name` VARCHAR(255) NOT NULL,
  `section_summary` TEXT,
  `student_visible` TINYINT(1) NOT NULL DEFAULT 1,
  `sort_no` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_lesson_section_code` (`lesson_id`, `section_code`),
  KEY `idx_lesson_sections_unit_sort` (`unit_id`, `sort_no`),
  CONSTRAINT `fk_lesson_sections_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_lesson_sections_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_lesson_sections_unit` FOREIGN KEY (`unit_id`) REFERENCES `lesson_units` (`id`),
  CONSTRAINT `fk_lesson_sections_source_chapter` FOREIGN KEY (`source_chapter_id`) REFERENCES `course_chapters` (`id`),
  CONSTRAINT `fk_lesson_sections_parse_result` FOREIGN KEY (`parse_result_id`) REFERENCES `chapter_parse_results` (`id`),
  CONSTRAINT `fk_lesson_sections_ppt_asset` FOREIGN KEY (`ppt_asset_id`) REFERENCES `chapter_ppt_assets` (`id`),
  CONSTRAINT `fk_lesson_sections_script` FOREIGN KEY (`script_id`) REFERENCES `chapter_scripts` (`id`),
  CONSTRAINT `fk_lesson_sections_audio` FOREIGN KEY (`audio_asset_id`) REFERENCES `chapter_audio_assets` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生端章节发布快照';

CREATE TABLE `lesson_section_pages` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED NOT NULL,
  `source_ppt_asset_id` BIGINT UNSIGNED DEFAULT NULL,
  `source_page_no` INT DEFAULT NULL,
  `page_no` INT NOT NULL,
  `page_title` VARCHAR(255) DEFAULT NULL,
  `page_summary` TEXT,
  `ppt_page_url` VARCHAR(255) DEFAULT NULL,
  `parsed_content` LONGTEXT,
  `sort_no` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_lesson_section_page` (`section_id`, `page_no`),
  KEY `idx_lesson_page_sort` (`lesson_id`, `section_id`, `sort_no`),
  CONSTRAINT `fk_lesson_pages_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_lesson_pages_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_lesson_pages_source_ppt` FOREIGN KEY (`source_ppt_asset_id`) REFERENCES `chapter_ppt_assets` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生端章节页';

CREATE TABLE `lesson_section_anchors` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED NOT NULL,
  `lesson_page_id` BIGINT UNSIGNED DEFAULT NULL,
  `anchor_code` VARCHAR(64) NOT NULL,
  `anchor_title` VARCHAR(255) NOT NULL,
  `page_no` INT DEFAULT NULL,
  `start_time_sec` INT DEFAULT NULL,
  `sort_no` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_section_anchor_code` (`section_id`, `anchor_code`),
  KEY `idx_section_anchor_sort` (`section_id`, `sort_no`),
  CONSTRAINT `fk_anchors_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_anchors_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_anchors_page` FOREIGN KEY (`lesson_page_id`) REFERENCES `lesson_section_pages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='章节续学锚点';

CREATE TABLE `lesson_section_knowledge_points` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED NOT NULL,
  `source_node_id` BIGINT UNSIGNED DEFAULT NULL,
  `point_code` VARCHAR(64) NOT NULL,
  `point_name` VARCHAR(255) NOT NULL,
  `point_summary` TEXT,
  `sort_no` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_section_point_code` (`section_id`, `point_code`),
  KEY `idx_section_points_sort` (`section_id`, `sort_no`),
  CONSTRAINT `fk_section_points_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_section_points_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_section_points_source_node` FOREIGN KEY (`source_node_id`) REFERENCES `chapter_knowledge_nodes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生端章节知识点快照';

CREATE TABLE `notifications` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED DEFAULT NULL,
  `section_id` BIGINT UNSIGNED DEFAULT NULL,
  `title` VARCHAR(255) NOT NULL,
  `content` TEXT NOT NULL,
  `notification_type` ENUM('course_update', 'reminder', 'practice', 'system') NOT NULL DEFAULT 'course_update',
  `created_by` BIGINT UNSIGNED NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_notifications_course_type` (`course_id`, `notification_type`, `created_at`),
  CONSTRAINT `fk_notifications_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_notifications_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_notifications_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_notifications_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知主表';

CREATE TABLE `notification_receipts` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `notification_id` BIGINT UNSIGNED NOT NULL,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `is_read` TINYINT(1) NOT NULL DEFAULT 0,
  `read_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_notification_student` (`notification_id`, `student_id`),
  KEY `idx_notification_receipts_student` (`student_id`, `is_read`),
  CONSTRAINT `fk_notification_receipts_notification` FOREIGN KEY (`notification_id`) REFERENCES `notifications` (`id`),
  CONSTRAINT `fk_notification_receipts_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知已读回执';

CREATE TABLE `qa_sessions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `session_no` VARCHAR(64) NOT NULL,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `current_section_id` BIGINT UNSIGNED NOT NULL,
  `session_title` VARCHAR(255) DEFAULT NULL,
  `status` ENUM('active', 'archived') NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_session_no` (`session_no`),
  KEY `idx_qa_sessions_student_lesson` (`student_id`, `lesson_id`, `updated_at`),
  CONSTRAINT `fk_qa_sessions_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_qa_sessions_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_qa_sessions_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_qa_sessions_section` FOREIGN KEY (`current_section_id`) REFERENCES `lesson_sections` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生 AI 问答会话';

CREATE TABLE `qa_messages` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `session_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED DEFAULT NULL,
  `role` ENUM('user', 'assistant') NOT NULL,
  `question_type` ENUM('text', 'voice') DEFAULT NULL,
  `message_content` LONGTEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_qa_messages_session_time` (`session_id`, `created_at`),
  KEY `idx_qa_messages_section` (`section_id`),
  CONSTRAINT `fk_qa_messages_session` FOREIGN KEY (`session_id`) REFERENCES `qa_sessions` (`id`),
  CONSTRAINT `fk_qa_messages_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_qa_messages_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='问答消息流';

CREATE TABLE `qa_answers` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `answer_no` VARCHAR(64) NOT NULL,
  `session_id` BIGINT UNSIGNED NOT NULL,
  `question_message_id` BIGINT UNSIGNED NOT NULL,
  `assistant_message_id` BIGINT UNSIGNED NOT NULL,
  `related_section_id` BIGINT UNSIGNED DEFAULT NULL,
  `answer_type` ENUM('text', 'mixed') NOT NULL DEFAULT 'text',
  `understanding_level` ENUM('none', 'partial', 'full') DEFAULT NULL,
  `recommended_section_id` BIGINT UNSIGNED DEFAULT NULL,
  `recommended_page_no` INT DEFAULT NULL,
  `recommended_anchor_id` BIGINT UNSIGNED DEFAULT NULL,
  `next_sections_json` JSON DEFAULT NULL,
  `suggestions_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_answer_no` (`answer_no`),
  UNIQUE KEY `uk_assistant_message` (`assistant_message_id`),
  KEY `idx_qa_answers_session` (`session_id`, `created_at`),
  CONSTRAINT `fk_qa_answers_session` FOREIGN KEY (`session_id`) REFERENCES `qa_sessions` (`id`),
  CONSTRAINT `fk_qa_answers_question_msg` FOREIGN KEY (`question_message_id`) REFERENCES `qa_messages` (`id`),
  CONSTRAINT `fk_qa_answers_assistant_msg` FOREIGN KEY (`assistant_message_id`) REFERENCES `qa_messages` (`id`),
  CONSTRAINT `fk_qa_answers_related_section` FOREIGN KEY (`related_section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_qa_answers_recommended_section` FOREIGN KEY (`recommended_section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_qa_answers_recommended_anchor` FOREIGN KEY (`recommended_anchor_id`) REFERENCES `lesson_section_anchors` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 回答结构化结果';

CREATE TABLE `qa_message_knowledge_refs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `answer_id` BIGINT UNSIGNED NOT NULL,
  `knowledge_point_id` BIGINT UNSIGNED DEFAULT NULL,
  `knowledge_name` VARCHAR(255) NOT NULL,
  `sort_no` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_qa_knowledge_answer` (`answer_id`, `sort_no`),
  CONSTRAINT `fk_qa_knowledge_answer` FOREIGN KEY (`answer_id`) REFERENCES `qa_answers` (`id`),
  CONSTRAINT `fk_qa_knowledge_point` FOREIGN KEY (`knowledge_point_id`) REFERENCES `lesson_section_knowledge_points` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 回答关联知识点';

CREATE TABLE `voice_transcripts` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `session_id` BIGINT UNSIGNED DEFAULT NULL,
  `question_message_id` BIGINT UNSIGNED DEFAULT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED DEFAULT NULL,
  `audio_url` VARCHAR(255) DEFAULT NULL,
  `duration_seconds` INT DEFAULT NULL,
  `language` VARCHAR(16) NOT NULL DEFAULT 'zh-CN',
  `transcript_text` LONGTEXT NOT NULL,
  `confidence_score` DECIMAL(5,2) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_voice_transcripts_student` (`student_id`, `created_at`),
  CONSTRAINT `fk_voice_transcripts_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_voice_transcripts_session` FOREIGN KEY (`session_id`) REFERENCES `qa_sessions` (`id`),
  CONSTRAINT `fk_voice_transcripts_message` FOREIGN KEY (`question_message_id`) REFERENCES `qa_messages` (`id`),
  CONSTRAINT `fk_voice_transcripts_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_voice_transcripts_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='语音转文字记录';

CREATE TABLE `student_practice_attempts` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `attempt_no` VARCHAR(64) NOT NULL,
  `practice_id` BIGINT UNSIGNED NOT NULL,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED DEFAULT NULL,
  `section_id` BIGINT UNSIGNED DEFAULT NULL,
  `started_at` DATETIME DEFAULT NULL,
  `submitted_at` DATETIME DEFAULT NULL,
  `duration_seconds` INT DEFAULT NULL,
  `total_score` DECIMAL(8,2) DEFAULT NULL,
  `correct_count` INT DEFAULT NULL,
  `accuracy_percent` DECIMAL(5,2) DEFAULT NULL,
  `grading_status` ENUM('pending', 'graded') NOT NULL DEFAULT 'pending',
  `attempt_status` ENUM('doing', 'submitted', 'graded') NOT NULL DEFAULT 'doing',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_attempt_no` (`attempt_no`),
  KEY `idx_practice_attempts_student` (`student_id`, `practice_id`, `created_at`),
  CONSTRAINT `fk_practice_attempts_practice` FOREIGN KEY (`practice_id`) REFERENCES `chapter_practices` (`id`),
  CONSTRAINT `fk_practice_attempts_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_practice_attempts_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_practice_attempts_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_practice_attempts_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生练习作答尝试';

CREATE TABLE `student_practice_answers` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `attempt_id` BIGINT UNSIGNED NOT NULL,
  `item_id` BIGINT UNSIGNED NOT NULL,
  `student_answer_json` JSON DEFAULT NULL,
  `answer_text` LONGTEXT,
  `is_correct` TINYINT(1) DEFAULT NULL,
  `earned_score` DECIMAL(8,2) DEFAULT NULL,
  `teacher_comment` TEXT,
  `graded_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_attempt_item` (`attempt_id`, `item_id`),
  CONSTRAINT `fk_practice_answers_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `student_practice_attempts` (`id`),
  CONSTRAINT `fk_practice_answers_item` FOREIGN KEY (`item_id`) REFERENCES `chapter_practice_items` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生逐题作答';

CREATE TABLE `student_lesson_progress` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `total_progress` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `overall_mastery_percent` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `current_unit_id` BIGINT UNSIGNED DEFAULT NULL,
  `current_section_id` BIGINT UNSIGNED DEFAULT NULL,
  `current_anchor_id` BIGINT UNSIGNED DEFAULT NULL,
  `last_page_no` INT DEFAULT NULL,
  `last_operate_time` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_student_lesson_progress` (`student_id`, `lesson_id`),
  KEY `idx_student_lesson_progress_course` (`student_id`, `course_id`, `updated_at`),
  CONSTRAINT `fk_slp_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_slp_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_slp_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_slp_unit` FOREIGN KEY (`current_unit_id`) REFERENCES `lesson_units` (`id`),
  CONSTRAINT `fk_slp_section` FOREIGN KEY (`current_section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_slp_anchor` FOREIGN KEY (`current_anchor_id`) REFERENCES `lesson_section_anchors` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生智课总进度';

CREATE TABLE `student_section_progress` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `unit_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED NOT NULL,
  `current_anchor_id` BIGINT UNSIGNED DEFAULT NULL,
  `last_page_no` INT DEFAULT NULL,
  `progress_percent` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `mastery_percent` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `understanding_level` ENUM('none', 'partial', 'full') DEFAULT NULL,
  `last_qa_message_id` BIGINT UNSIGNED DEFAULT NULL,
  `last_practice_attempt_id` BIGINT UNSIGNED DEFAULT NULL,
  `last_operate_time` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_student_section_progress` (`student_id`, `lesson_id`, `section_id`),
  KEY `idx_ssp_lesson_unit` (`lesson_id`, `unit_id`, `updated_at`),
  CONSTRAINT `fk_ssp_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_ssp_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_ssp_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_ssp_unit` FOREIGN KEY (`unit_id`) REFERENCES `lesson_units` (`id`),
  CONSTRAINT `fk_ssp_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_ssp_anchor` FOREIGN KEY (`current_anchor_id`) REFERENCES `lesson_section_anchors` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生章节进度与掌握度汇总';

CREATE TABLE `student_page_progress` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED NOT NULL,
  `lesson_page_id` BIGINT UNSIGNED NOT NULL,
  `page_no` INT NOT NULL,
  `read_percent` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `is_completed` TINYINT(1) NOT NULL DEFAULT 0,
  `stay_seconds` INT NOT NULL DEFAULT 0,
  `first_read_at` DATETIME DEFAULT NULL,
  `last_read_at` DATETIME DEFAULT NULL,
  `completed_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_student_lesson_page` (`student_id`, `lesson_page_id`),
  KEY `idx_student_page_lookup` (`student_id`, `lesson_id`, `section_id`, `page_no`),
  CONSTRAINT `fk_spp_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_spp_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_spp_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_spp_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_spp_page` FOREIGN KEY (`lesson_page_id`) REFERENCES `lesson_section_pages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生页级阅读进度';

CREATE TABLE `resume_records` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED DEFAULT NULL,
  `anchor_id` BIGINT UNSIGNED DEFAULT NULL,
  `page_no` INT DEFAULT NULL,
  `resume_time_sec` INT DEFAULT NULL,
  `resume_type` ENUM('auto', 'manual', 'ai_recommended') NOT NULL DEFAULT 'auto',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_resume_student_lesson` (`student_id`, `lesson_id`, `created_at`),
  CONSTRAINT `fk_resume_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_resume_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_resume_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_resume_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_resume_anchor` FOREIGN KEY (`anchor_id`) REFERENCES `lesson_section_anchors` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='续学记录';

CREATE TABLE `progress_track_logs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED NOT NULL,
  `anchor_id` BIGINT UNSIGNED DEFAULT NULL,
  `page_no` INT DEFAULT NULL,
  `qa_answer_id` BIGINT UNSIGNED DEFAULT NULL,
  `track_source` ENUM('page_read', 'qa', 'practice', 'manual') NOT NULL DEFAULT 'page_read',
  `progress_percent` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `last_operate_time` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_progress_track_student` (`student_id`, `lesson_id`, `created_at`),
  CONSTRAINT `fk_progress_track_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_progress_track_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_progress_track_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_progress_track_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_progress_track_anchor` FOREIGN KEY (`anchor_id`) REFERENCES `lesson_section_anchors` (`id`),
  CONSTRAINT `fk_progress_track_answer` FOREIGN KEY (`qa_answer_id`) REFERENCES `qa_answers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='进度追踪日志';

CREATE TABLE `progress_adjust_records` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED NOT NULL,
  `qa_answer_id` BIGINT UNSIGNED DEFAULT NULL,
  `understanding_level` ENUM('none', 'partial', 'full') DEFAULT NULL,
  `adjust_type` ENUM('keep', 'review', 'advance', 'supplement') NOT NULL DEFAULT 'keep',
  `continue_section_id` BIGINT UNSIGNED DEFAULT NULL,
  `recommended_page_no` INT DEFAULT NULL,
  `recommended_anchor_id` BIGINT UNSIGNED DEFAULT NULL,
  `supplement_content` TEXT,
  `adjust_payload` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_progress_adjust_student` (`student_id`, `lesson_id`, `created_at`),
  CONSTRAINT `fk_progress_adjust_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_progress_adjust_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_progress_adjust_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_progress_adjust_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_progress_adjust_answer` FOREIGN KEY (`qa_answer_id`) REFERENCES `qa_answers` (`id`),
  CONSTRAINT `fk_progress_adjust_continue_section` FOREIGN KEY (`continue_section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_progress_adjust_anchor` FOREIGN KEY (`recommended_anchor_id`) REFERENCES `lesson_section_anchors` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='进度节奏调整记录';

CREATE TABLE `student_section_mastery_logs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_id` BIGINT UNSIGNED NOT NULL,
  `course_id` BIGINT UNSIGNED NOT NULL,
  `lesson_id` BIGINT UNSIGNED NOT NULL,
  `section_id` BIGINT UNSIGNED NOT NULL,
  `practice_attempt_id` BIGINT UNSIGNED DEFAULT NULL,
  `qa_answer_id` BIGINT UNSIGNED DEFAULT NULL,
  `source_type` ENUM('progress_sync', 'practice_submit', 'qa_answer', 'manual_recalc') NOT NULL,
  `page_progress_contribution` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `practice_contribution` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `qa_contribution` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `final_mastery_percent` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `rule_version` VARCHAR(32) NOT NULL DEFAULT 'v1',
  `detail_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_mastery_logs_student` (`student_id`, `lesson_id`, `section_id`, `created_at`),
  CONSTRAINT `fk_mastery_logs_student` FOREIGN KEY (`student_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_mastery_logs_course` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`),
  CONSTRAINT `fk_mastery_logs_lesson` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`),
  CONSTRAINT `fk_mastery_logs_section` FOREIGN KEY (`section_id`) REFERENCES `lesson_sections` (`id`),
  CONSTRAINT `fk_mastery_logs_attempt` FOREIGN KEY (`practice_attempt_id`) REFERENCES `student_practice_attempts` (`id`),
  CONSTRAINT `fk_mastery_logs_answer` FOREIGN KEY (`qa_answer_id`) REFERENCES `qa_answers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='章节掌握度计算留痕';

CREATE TABLE `api_call_logs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `request_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT UNSIGNED DEFAULT NULL,
  `role` VARCHAR(16) DEFAULT NULL,
  `api_path` VARCHAR(255) NOT NULL,
  `status_code` INT NOT NULL,
  `request_json` JSON DEFAULT NULL,
  `response_json` JSON DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_api_logs_request` (`request_id`),
  KEY `idx_api_logs_path_time` (`api_path`, `created_at`),
  CONSTRAINT `fk_api_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='接口调用日志';

SET FOREIGN_KEY_CHECKS = 1;
