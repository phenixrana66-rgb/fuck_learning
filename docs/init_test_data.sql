USE `chaoxing_ai_course`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DELETE FROM `api_call_logs`;
DELETE FROM `student_section_mastery_logs`;
DELETE FROM `progress_adjust_records`;
DELETE FROM `progress_track_logs`;
DELETE FROM `resume_records`;
DELETE FROM `student_page_progress`;
DELETE FROM `student_section_progress`;
DELETE FROM `student_lesson_progress`;
DELETE FROM `student_practice_answers`;
DELETE FROM `student_practice_attempts`;
DELETE FROM `voice_transcripts`;
DELETE FROM `qa_message_knowledge_refs`;
DELETE FROM `qa_answers`;
DELETE FROM `qa_messages`;
DELETE FROM `qa_sessions`;
DELETE FROM `notification_receipts`;
DELETE FROM `notifications`;
DELETE FROM `lesson_section_knowledge_points`;
DELETE FROM `lesson_section_anchors`;
DELETE FROM `lesson_section_pages`;
DELETE FROM `lesson_sections`;
DELETE FROM `lesson_units`;
DELETE FROM `lessons`;
DELETE FROM `chapter_practice_items`;
DELETE FROM `chapter_practices`;
DELETE FROM `chapter_audio_assets`;
DELETE FROM `chapter_script_sections`;
DELETE FROM `chapter_scripts`;
DELETE FROM `chapter_knowledge_nodes`;
DELETE FROM `chapter_parse_results`;
DELETE FROM `chapter_parse_tasks`;
DELETE FROM `chapter_ppt_assets`;
DELETE FROM `course_chapters`;
DELETE FROM `course_members`;
DELETE FROM `course_classes`;
DELETE FROM `course_platform_bindings`;
DELETE FROM `courses`;
DELETE FROM `user_platform_bindings`;
DELETE FROM `users`;
DELETE FROM `schools`;
DELETE FROM `platforms`;

INSERT INTO `platforms` (`id`, `platform_code`, `platform_name`, `api_base_url`, `status`)
VALUES
  (1, 'chaoxing_demo', '超星泛雅测试平台', 'https://api.chaoxing.example.com', 1);

INSERT INTO `schools` (`id`, `school_code`, `school_name`, `status`)
VALUES
  (1, 'SCH001', '河海大学', 1);

INSERT INTO `users` (`id`, `user_no`, `user_name`, `role`, `school_id`, `phone`, `email`, `auth_token`, `status`)
VALUES
  (1, 'T10001', '王志恒', 'teacher', 1, '13800000001', 'teacher@test.edu.cn', 'test_token_001', 1),
  (2, 'S2026001', '左睿涛', 'student', 1, '13800000002', 'student1@test.edu.cn', 'student_demo_token_001', 1);

INSERT INTO `user_platform_bindings` (`id`, `platform_id`, `user_id`, `external_user_id`, `external_role`, `related_course_ids`, `raw_payload`)
VALUES
  (1, 1, 1, 'T10001', 'teacher', JSON_ARRAY('C10001'), JSON_OBJECT('teacherName', '王志恒')),
  (2, 1, 2, 'S2026001', 'student', JSON_ARRAY('C10001'), JSON_OBJECT('studentName', '左睿涛'));

INSERT INTO `courses` (`id`, `course_code`, `course_name`, `school_id`, `term`, `credit`, `period`, `course_cover_url`, `course_status`, `created_by`)
VALUES
  (1, 'C10001', '材料力学智慧课程 (15期2025春夏)', 1, '2025春夏', 3.0, 48, NULL, 'published', 1);

INSERT INTO `course_platform_bindings` (`id`, `platform_id`, `course_id`, `external_course_id`, `raw_payload`)
VALUES
  (1, 1, 1, 'C10001', JSON_OBJECT('courseName', '材料力学智慧课程 (15期2025春夏)'));

INSERT INTO `course_classes` (`id`, `class_code`, `class_name`, `course_id`, `school_id`, `teacher_id`, `status`)
VALUES
  (1, 'CL10001', '材料力学 AI 智课实验班', 1, 1, 1, 1);

INSERT INTO `course_members` (`id`, `course_id`, `class_id`, `user_id`, `member_role`)
VALUES
  (1, 1, 1, 1, 'teacher'),
  (2, 1, 1, 2, 'student');

INSERT INTO `course_chapters` (`id`, `course_id`, `parent_id`, `chapter_code`, `chapter_name`, `chapter_type`, `chapter_level`, `sort_no`, `status`)
VALUES
  (1, 1, NULL, 'U09', '压杆稳定', 'unit', 1, 1, 'published'),
  (2, 1, 1, 'C0901', '压杆稳定', 'chapter', 2, 1, 'published');

INSERT INTO `chapter_ppt_assets` (`id`, `course_id`, `chapter_id`, `uploader_id`, `file_name`, `file_type`, `file_url`, `file_size`, `page_count`, `upload_status`, `version_no`)
VALUES
  (
    1,
    1,
    2,
    1,
    '第九章 压杆稳定_20260401213017.ppt',
    'ppt',
    'D:/BaiduNetdiskDownload/10-a12基于泛雅平台的AI互动智课生成与实时问答/a12基于泛雅平台的AI互动智课生成与实时问答/课件下载-3月3日/课件下载-3月3日/第九章 压杆稳定_20260401213017.ppt',
    1048576,
    5,
    'parsed',
    1
  );

INSERT INTO `chapter_parse_tasks` (`id`, `parse_no`, `course_id`, `chapter_id`, `ppt_asset_id`, `teacher_id`, `llm_model`, `is_extract_key_point`, `task_status`, `finished_at`)
VALUES
  (1, 'PTEST000001', 1, 2, 1, 1, 'gpt-5.4', 1, 'completed', NOW());

INSERT INTO `chapter_parse_results` (`id`, `parse_task_id`, `course_id`, `chapter_id`, `ppt_asset_id`, `chapter_summary`, `parsed_outline`, `key_points`, `page_mapping`, `normalized_content`)
VALUES
  (
    1,
    1,
    1,
    2,
    1,
    '本章围绕压杆稳定的基本概念、临界载荷、欧拉公式、长细比影响以及工程校核展开。',
    JSON_ARRAY(
      JSON_OBJECT('id', '1', 'name', '稳定平衡条件'),
      JSON_OBJECT('id', '2', 'name', '临界载荷'),
      JSON_OBJECT('id', '3', 'name', '欧拉公式'),
      JSON_OBJECT('id', '4', 'name', '长细比影响'),
      JSON_OBJECT('id', '5', 'name', '工程应用')
    ),
    JSON_ARRAY('稳定平衡条件', '临界载荷', '欧拉公式', '长细比影响', '工程应用'),
    JSON_ARRAY(
      JSON_OBJECT('pageNo', 1, 'title', '稳定平衡条件', 'previewUrl', '/lesson-previews/pressure-stability/page-1.svg'),
      JSON_OBJECT('pageNo', 2, 'title', '临界载荷', 'previewUrl', '/lesson-previews/pressure-stability/page-2.svg'),
      JSON_OBJECT('pageNo', 3, 'title', '欧拉公式', 'previewUrl', '/lesson-previews/pressure-stability/page-3.svg'),
      JSON_OBJECT('pageNo', 4, 'title', '长细比影响', 'previewUrl', '/lesson-previews/pressure-stability/page-4.svg'),
      JSON_OBJECT('pageNo', 5, 'title', '工程应用', 'previewUrl', '/lesson-previews/pressure-stability/page-5.svg')
    ),
    '压杆稳定章节导读：先理解稳定平衡与临界载荷，再掌握欧拉公式和长细比影响，最后结合工程案例完成稳定校核。'
  );

INSERT INTO `chapter_knowledge_nodes` (`id`, `parse_task_id`, `chapter_id`, `parent_id`, `node_code`, `node_name`, `node_type`, `level_no`, `is_key_point`, `page_start`, `page_end`, `sort_no`)
VALUES
  (1, 1, 2, NULL, 'N0901', '压杆稳定', 'chapter', 1, 0, 1, 5, 1),
  (2, 1, 2, 1, 'N0901-01', '稳定平衡条件', 'knowledge', 2, 1, 1, 1, 2),
  (3, 1, 2, 1, 'N0901-02', '临界载荷', 'knowledge', 2, 1, 2, 2, 3),
  (4, 1, 2, 1, 'N0901-03', '欧拉公式', 'knowledge', 2, 1, 3, 3, 4),
  (5, 1, 2, 1, 'N0901-04', '长细比影响', 'knowledge', 2, 1, 4, 4, 5),
  (6, 1, 2, 1, 'N0901-05', '工程应用', 'knowledge', 2, 1, 5, 5, 6);

INSERT INTO `chapter_scripts` (`id`, `script_no`, `course_id`, `chapter_id`, `parse_task_id`, `teacher_id`, `teaching_style`, `speech_speed`, `custom_opening`, `script_status`)
VALUES
  (1, 'STEST000001', 1, 2, 1, 1, 'standard', 'normal', '同学们好，今天我们一起学习压杆稳定。', 'published');

INSERT INTO `chapter_script_sections` (`id`, `script_id`, `section_code`, `section_name`, `section_content`, `duration_sec`, `related_node_id`, `related_page_range`, `sort_no`)
VALUES
  (1, 1, 'STEST000001-01', '压杆稳定导读', '围绕稳定平衡条件、临界载荷、欧拉公式以及工程应用展开讲解。', 420, 1, '1-5', 1);

INSERT INTO `chapter_audio_assets` (`id`, `course_id`, `chapter_id`, `script_id`, `voice_type`, `audio_format`, `audio_url`, `total_duration_sec`, `file_size`, `bit_rate`, `status`)
VALUES
  (1, 1, 2, 1, 'female_standard', 'mp3', 'https://www.w3schools.com/html/horse.mp3', 420, 512000, 128, 'published');

INSERT INTO `chapter_practices` (`id`, `practice_code`, `course_id`, `chapter_id`, `created_by`, `practice_title`, `practice_desc`, `practice_type`, `difficulty_level`, `total_score`, `item_count`, `time_limit_minutes`, `publish_status`, `start_at`, `end_at`)
VALUES
  (1, 'PRAC0901', 1, 2, 1, '压杆稳定章节练习', '用于检验压杆稳定核心概念与公式掌握情况。', 'exercise', 'medium', 100.00, 2, 20, 'published', NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY));

INSERT INTO `chapter_practice_items` (`id`, `practice_id`, `item_no`, `item_type`, `stem`, `options_json`, `correct_answer_json`, `analysis_text`, `score`, `sort_no`)
VALUES
  (1, 1, 'PRAC0901-01', 'single_choice', '压杆临界载荷与下列哪项最直接相关？', JSON_ARRAY('长细比', '泊松比', '热膨胀系数', '材料密度'), JSON_ARRAY('长细比'), '长细比越大，压杆越容易失稳。', 50.00, 1),
  (2, 1, 'PRAC0901-02', 'judge', '压杆越细长，其稳定性通常越差。', NULL, JSON_ARRAY('true'), '细长压杆更容易发生失稳。', 50.00, 2);

INSERT INTO `lessons` (`id`, `lesson_no`, `course_id`, `lesson_name`, `teacher_id`, `publish_version`, `publish_status`, `published_at`)
VALUES
  (1, 'L10001', 1, '材料力学智慧课程 (15期2025春夏)', 1, 1, 'published', NOW());

INSERT INTO `lesson_units` (`id`, `lesson_id`, `course_id`, `source_chapter_id`, `unit_code`, `unit_title`, `sort_no`)
VALUES
  (1, 1, 1, 1, 'LU0901', '压杆稳定', 1);

INSERT INTO `lesson_sections` (`id`, `lesson_id`, `course_id`, `unit_id`, `source_chapter_id`, `parse_result_id`, `ppt_asset_id`, `script_id`, `audio_asset_id`, `section_code`, `section_name`, `section_summary`, `student_visible`, `sort_no`)
VALUES
  (1, 1, 1, 1, 2, 1, 1, 1, 1, 'LS0901', '压杆稳定', '围绕压杆稳定的基本概念、公式分析与工程应用展开课件学习。', 1, 1);

INSERT INTO `lesson_section_pages` (`id`, `lesson_id`, `section_id`, `source_ppt_asset_id`, `source_page_no`, `page_no`, `page_title`, `page_summary`, `ppt_page_url`, `parsed_content`, `sort_no`)
VALUES
  (1, 1, 1, 1, 1, 1, '稳定平衡条件', '理解压杆处于稳定平衡时的受力与位移特征。', '/lesson-previews/pressure-stability/page-1.svg', '本页介绍压杆稳定平衡的基本条件，帮助建立后续临界载荷分析的力学基础。', 1),
  (2, 1, 1, 1, 2, 2, '临界载荷', '掌握压杆发生失稳时的临界载荷概念。', '/lesson-previews/pressure-stability/page-2.svg', '本页说明临界载荷的定义，以及影响临界载荷大小的主要因素。', 2),
  (3, 1, 1, 1, 3, 3, '欧拉公式', '理解欧拉公式的形式和适用前提。', '/lesson-previews/pressure-stability/page-3.svg', '本页围绕欧拉公式展开，帮助学生理解理想压杆稳定分析的经典计算式。', 3),
  (4, 1, 1, 1, 4, 4, '长细比影响', '认识长细比与失稳风险之间的关系。', '/lesson-previews/pressure-stability/page-4.svg', '本页分析长细比变化对压杆稳定承载能力的影响，是工程校核中的关键指标。', 4),
  (5, 1, 1, 1, 5, 5, '工程应用', '结合工程案例理解压杆稳定校核。', '/lesson-previews/pressure-stability/page-5.svg', '本页用工程场景说明压杆稳定分析在结构设计和校核中的实际应用。', 5);

INSERT INTO `lesson_section_anchors` (`id`, `lesson_id`, `section_id`, `lesson_page_id`, `anchor_code`, `anchor_title`, `page_no`, `start_time_sec`, `sort_no`)
VALUES
  (1, 1, 1, 1, 'A0901', '稳定平衡条件', 1, 0, 1),
  (2, 1, 1, 2, 'A0902', '临界载荷', 2, 90, 2),
  (3, 1, 1, 3, 'A0903', '欧拉公式', 3, 180, 3),
  (4, 1, 1, 4, 'A0904', '长细比影响', 4, 270, 4),
  (5, 1, 1, 5, 'A0905', '工程应用', 5, 360, 5);

INSERT INTO `lesson_section_knowledge_points` (`id`, `lesson_id`, `section_id`, `source_node_id`, `point_code`, `point_name`, `point_summary`, `sort_no`)
VALUES
  (1, 1, 1, 2, 'KP0901', '稳定平衡条件', '理解压杆失稳前后的平衡状态。', 1),
  (2, 1, 1, 3, 'KP0902', '临界载荷', '掌握临界载荷的定义与影响因素。', 2),
  (3, 1, 1, 4, 'KP0903', '欧拉公式', '理解欧拉公式的形式与适用前提。', 3),
  (4, 1, 1, 5, 'KP0904', '长细比影响', '掌握长细比对稳定性的影响。', 4),
  (5, 1, 1, 6, 'KP0905', '工程应用', '能够将压杆稳定分析用于工程校核。', 5);

INSERT INTO `notifications` (`id`, `course_id`, `lesson_id`, `section_id`, `title`, `content`, `notification_type`, `created_by`)
VALUES
  (1, 1, 1, 1, '压杆稳定单元已发布', '教师已上传压杆稳定章节 PPT，并生成章节导读与配套音频。', 'course_update', 1);

INSERT INTO `notification_receipts` (`id`, `notification_id`, `student_id`, `is_read`, `read_at`)
VALUES
  (1, 1, 2, 0, NULL);

INSERT INTO `qa_sessions` (`id`, `session_no`, `student_id`, `course_id`, `lesson_id`, `current_section_id`, `session_title`, `status`)
VALUES
  (1, 'QS000001', 2, 1, 1, 1, '压杆稳定概念答疑', 'active');

INSERT INTO `qa_messages` (`id`, `session_id`, `lesson_id`, `section_id`, `role`, `question_type`, `message_content`, `created_at`)
VALUES
  (1, 1, 1, 1, 'user', 'text', '欧拉公式适用于什么情况下的压杆？', NOW()),
  (2, 1, 1, 1, 'assistant', NULL, '欧拉公式主要适用于细长压杆、理想弹性材料、中心受压且初始缺陷可忽略的情况。', NOW());

INSERT INTO `qa_answers` (`id`, `answer_no`, `session_id`, `question_message_id`, `assistant_message_id`, `related_section_id`, `answer_type`, `understanding_level`, `recommended_section_id`, `recommended_page_no`, `recommended_anchor_id`, `next_sections_json`, `suggestions_json`)
VALUES
  (1, 'QA000001', 1, 1, 2, 1, 'text', 'partial', 1, 3, 3, JSON_ARRAY(), JSON_ARRAY('回看欧拉公式页', '结合练习巩固适用前提'));

INSERT INTO `qa_message_knowledge_refs` (`id`, `answer_id`, `knowledge_point_id`, `knowledge_name`, `sort_no`)
VALUES
  (1, 1, 3, '欧拉公式', 1),
  (2, 1, 4, '长细比影响', 2);

INSERT INTO `voice_transcripts` (`id`, `student_id`, `session_id`, `question_message_id`, `lesson_id`, `section_id`, `audio_url`, `duration_seconds`, `language`, `transcript_text`, `confidence_score`)
VALUES
  (1, 2, 1, 1, 1, 1, 'https://example.com/audio/qs000001.webm', 7, 'zh-CN', '欧拉公式适用于什么情况下的压杆？', 97.50);

INSERT INTO `student_practice_attempts` (`id`, `attempt_no`, `practice_id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `started_at`, `submitted_at`, `duration_seconds`, `total_score`, `correct_count`, `accuracy_percent`, `grading_status`, `attempt_status`)
VALUES
  (1, 'ATT0901', 1, 2, 1, 1, 1, NOW(), NOW(), 540, 80.00, 2, 80.00, 'graded', 'graded');

INSERT INTO `student_practice_answers` (`id`, `attempt_id`, `item_id`, `student_answer_json`, `answer_text`, `is_correct`, `earned_score`, `teacher_comment`, `graded_at`)
VALUES
  (1, 1, 1, JSON_ARRAY('长细比'), NULL, 1, 50.00, '回答正确', NOW()),
  (2, 1, 2, JSON_ARRAY('true'), NULL, 1, 30.00, '判断正确', NOW());

INSERT INTO `student_lesson_progress` (`id`, `student_id`, `course_id`, `lesson_id`, `total_progress`, `overall_mastery_percent`, `current_unit_id`, `current_section_id`, `current_anchor_id`, `last_page_no`, `last_operate_time`)
VALUES
  (1, 2, 1, 1, 40.00, 64.00, 1, 1, 2, 2, NOW());

INSERT INTO `student_section_progress` (`id`, `student_id`, `course_id`, `lesson_id`, `unit_id`, `section_id`, `current_anchor_id`, `last_page_no`, `progress_percent`, `mastery_percent`, `understanding_level`, `last_qa_message_id`, `last_practice_attempt_id`, `last_operate_time`)
VALUES
  (1, 2, 1, 1, 1, 1, 2, 2, 40.00, 64.00, 'partial', 1, 1, NOW());

INSERT INTO `student_page_progress` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `lesson_page_id`, `page_no`, `read_percent`, `is_completed`, `stay_seconds`, `first_read_at`, `last_read_at`, `completed_at`)
VALUES
  (1, 2, 1, 1, 1, 1, 1, 100.00, 1, 120, NOW(), NOW(), NOW()),
  (2, 2, 1, 1, 1, 2, 2, 100.00, 1, 95, NOW(), NOW(), NOW());

INSERT INTO `resume_records` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `anchor_id`, `page_no`, `resume_time_sec`, `resume_type`)
VALUES
  (1, 2, 1, 1, 1, 2, 2, 90, 'manual');

INSERT INTO `progress_track_logs` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `anchor_id`, `page_no`, `qa_answer_id`, `track_source`, `progress_percent`, `last_operate_time`)
VALUES
  (1, 2, 1, 1, 1, 1, 1, NULL, 'page_read', 20.00, NOW()),
  (2, 2, 1, 1, 1, 2, 2, NULL, 'page_read', 40.00, NOW());

INSERT INTO `progress_adjust_records` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `qa_answer_id`, `understanding_level`, `adjust_type`, `continue_section_id`, `recommended_page_no`, `recommended_anchor_id`, `supplement_content`, `adjust_payload`)
VALUES
  (1, 2, 1, 1, 1, 1, 'partial', 'review', 1, 3, 3, '建议回到欧拉公式页继续巩固适用前提与长细比影响。', JSON_OBJECT('source', 'qa'));

INSERT INTO `student_section_mastery_logs` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `practice_attempt_id`, `qa_answer_id`, `source_type`, `page_progress_contribution`, `practice_contribution`, `qa_contribution`, `final_mastery_percent`, `rule_version`, `detail_json`)
VALUES
  (1, 2, 1, 1, 1, 1, NULL, 'practice_submit', 16.00, 48.00, 0.00, 64.00, 'v1', JSON_OBJECT('progressPercent', 40, 'practicePercent', 80));

INSERT INTO `api_call_logs` (`id`, `request_id`, `user_id`, `role`, `api_path`, `status_code`, `request_json`, `response_json`)
VALUES
  (1, 'seed-req-0001', 1, 'teacher', '/api/v1/lesson/parse', 200, JSON_OBJECT('parseId', 'PTEST000001'), JSON_OBJECT('status', 'success')),
  (2, 'seed-req-0002', 2, 'student', '/student-api/api/v1/lesson/section/detail', 200, JSON_OBJECT('lessonId', 'L10001', 'sectionId', '1'), JSON_OBJECT('sectionTitle', '压杆稳定'));

SET FOREIGN_KEY_CHECKS = 1;
