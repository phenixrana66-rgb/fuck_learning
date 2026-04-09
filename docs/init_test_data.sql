USE `chaoxing_ai_course`;

SET NAMES utf8mb4;

INSERT INTO `platforms` (`id`, `platform_code`, `platform_name`, `api_base_url`, `status`)
VALUES
  (1, 'chaoxing_demo', '超星泛雅测试平台', 'https://api.chaoxing.example.com', 1);

INSERT INTO `schools` (`id`, `school_code`, `school_name`, `status`)
VALUES
  (1, 'SCH001', '测试大学', 1);

INSERT INTO `users` (`id`, `user_no`, `user_name`, `role`, `school_id`, `phone`, `email`, `auth_token`, `status`)
VALUES
  (1, 'T10001', '张老师', 'teacher', 1, '13800000001', 'teacher@test.edu.cn', 'test_token_001', 1),
  (2, 'S2026001', '左睿涛', 'student', 1, '13800000002', 'student1@test.edu.cn', 'student_demo_token_001', 1),
  (3, 'S2026002', '林雨晴', 'student', 1, '13800000003', 'student2@test.edu.cn', 'student_demo_token_002', 1);

INSERT INTO `user_platform_bindings` (`id`, `platform_id`, `user_id`, `external_user_id`, `external_role`, `related_course_ids`, `raw_payload`)
VALUES
  (1, 1, 1, 'T10001', 'teacher', JSON_ARRAY('C10001', 'C10002', 'C10003'), JSON_OBJECT('teacherName', '张老师')),
  (2, 1, 2, 'S2026001', 'student', JSON_ARRAY('C10001'), JSON_OBJECT('studentName', '左睿涛')),
  (3, 1, 3, 'S2026002', 'student', JSON_ARRAY('C10001'), JSON_OBJECT('studentName', '林雨晴'));

INSERT INTO `courses` (`id`, `course_code`, `course_name`, `school_id`, `term`, `credit`, `period`, `course_cover_url`, `course_status`, `created_by`)
VALUES
  (1, 'C10001', '材料力学智慧课程（15期2025春夏）', 1, '2025春夏', 3.0, 48, NULL, 'published', 1),
  (2, 'C10002', '高等数学 AI 智课示范课', 1, '2025春夏', 4.0, 64, NULL, 'published', 1),
  (3, 'C10003', '计算机基础 AI 智课示范课', 1, '2025春夏', 2.0, 32, NULL, 'published', 1);

INSERT INTO `course_platform_bindings` (`id`, `platform_id`, `course_id`, `external_course_id`, `raw_payload`)
VALUES
  (1, 1, 1, 'C10001', JSON_OBJECT('courseName', '材料力学智慧课程（15期2025春夏）')),
  (2, 1, 2, 'C10002', JSON_OBJECT('courseName', '高等数学 AI 智课示范课')),
  (3, 1, 3, 'C10003', JSON_OBJECT('courseName', '计算机基础 AI 智课示范课'));

INSERT INTO `course_classes` (`id`, `class_code`, `class_name`, `course_id`, `school_id`, `teacher_id`, `status`)
VALUES
  (1, 'CL10001', '材料力学实验班', 1, 1, 1, 1),
  (2, 'CL10002', '高等数学实验班', 2, 1, 1, 1),
  (3, 'CL10003', '计算机基础实验班', 3, 1, 1, 1);

INSERT INTO `course_members` (`id`, `course_id`, `class_id`, `user_id`, `member_role`)
VALUES
  (1, 1, 1, 1, 'teacher'),
  (2, 2, 2, 1, 'teacher'),
  (3, 3, 3, 1, 'teacher'),
  (4, 1, 1, 2, 'student'),
  (5, 1, 1, 3, 'student');

INSERT INTO `course_chapters` (`id`, `course_id`, `parent_id`, `chapter_code`, `chapter_name`, `chapter_type`, `chapter_level`, `sort_no`, `status`)
VALUES
  (1, 1, NULL, 'U09', '第九章 压杆稳定', 'unit', 1, 1, 'published'),
  (2, 1, 1, 'C0901', '压杆稳定基本概念', 'chapter', 2, 1, 'published'),
  (3, 1, 1, 'C0902', '稳定校核与工程应用', 'chapter', 2, 2, 'published');

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
    '本章围绕压杆稳定、临界载荷与工程校核展开。',
    JSON_ARRAY(
      JSON_OBJECT('id', '1', 'name', '压杆稳定基本概念', 'children', JSON_ARRAY(JSON_OBJECT('id', '1-1', 'name', '稳定平衡条件'), JSON_OBJECT('id', '1-2', 'name', '临界载荷'))),
      JSON_OBJECT('id', '2', 'name', '压杆稳定分析', 'children', JSON_ARRAY(JSON_OBJECT('id', '2-1', 'name', '欧拉公式'), JSON_OBJECT('id', '2-2', 'name', '工程应用')))
    ),
    JSON_ARRAY('稳定平衡条件', '临界载荷', '欧拉公式', '工程应用'),
    JSON_ARRAY(
      JSON_OBJECT('pageNo', 1, 'title', '稳定平衡条件'),
      JSON_OBJECT('pageNo', 2, 'title', '临界载荷'),
      JSON_OBJECT('pageNo', 3, 'title', '欧拉公式'),
      JSON_OBJECT('pageNo', 4, 'title', '长细比影响'),
      JSON_OBJECT('pageNo', 5, 'title', '工程应用')
    ),
    '第九章压杆稳定解析内容快照'
  );

INSERT INTO `chapter_knowledge_nodes` (`id`, `parse_task_id`, `chapter_id`, `parent_id`, `node_code`, `node_name`, `node_type`, `level_no`, `is_key_point`, `page_start`, `page_end`, `sort_no`)
VALUES
  (1, 1, 2, NULL, 'N-1', '压杆稳定基本概念', 'chapter', 1, 0, 1, 2, 1),
  (2, 1, 2, 1, 'N-1-1', '稳定平衡条件', 'knowledge', 2, 1, 1, 1, 2),
  (3, 1, 2, 1, 'N-1-2', '临界载荷', 'knowledge', 2, 1, 2, 2, 3),
  (4, 1, 2, NULL, 'N-2', '压杆稳定分析', 'chapter', 1, 0, 3, 5, 4),
  (5, 1, 2, 4, 'N-2-1', '欧拉公式', 'knowledge', 2, 1, 3, 4, 5),
  (6, 1, 2, 4, 'N-2-2', '工程应用', 'knowledge', 2, 1, 5, 5, 6);

INSERT INTO `chapter_scripts` (`id`, `script_no`, `course_id`, `chapter_id`, `parse_task_id`, `teacher_id`, `teaching_style`, `speech_speed`, `custom_opening`, `script_status`)
VALUES
  (1, 'STEST000001', 1, 2, 1, 1, 'standard', 'normal', '同学们好，今天我们学习压杆稳定。', 'published');

INSERT INTO `chapter_script_sections` (`id`, `script_id`, `section_code`, `section_name`, `section_content`, `duration_sec`, `related_node_id`, `related_page_range`, `sort_no`)
VALUES
  (1, 1, 'STEST000001-01', '压杆稳定基本概念', '介绍稳定平衡条件、临界载荷与课堂案例。', 180, 1, '1-2', 1),
  (2, 1, 'STEST000001-02', '压杆稳定分析', '讲解欧拉公式、长细比和工程应用。', 240, 4, '3-5', 2);

INSERT INTO `chapter_audio_assets` (`id`, `course_id`, `chapter_id`, `script_id`, `voice_type`, `audio_format`, `audio_url`, `total_duration_sec`, `file_size`, `bit_rate`, `status`)
VALUES
  (1, 1, 2, 1, 'female_standard', 'mp3', 'https://www.w3schools.com/html/horse.mp3', 420, 512000, 128, 'published');

INSERT INTO `chapter_practices` (`id`, `practice_code`, `course_id`, `chapter_id`, `created_by`, `practice_title`, `practice_desc`, `practice_type`, `difficulty_level`, `total_score`, `item_count`, `time_limit_minutes`, `publish_status`, `start_at`, `end_at`)
VALUES
  (1, 'PRAC0901', 1, 2, 1, '压杆稳定章节练习', '用于验证压杆稳定核心概念掌握度。', 'exercise', 'medium', 100.00, 2, 20, 'published', NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY)),
  (2, 'PRAC0902', 1, 3, 1, '稳定校核章节练习', '用于验证工程应用与稳定校核能力。', 'exercise', 'medium', 100.00, 2, 20, 'published', NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY));

INSERT INTO `chapter_practice_items` (`id`, `practice_id`, `item_no`, `item_type`, `stem`, `options_json`, `correct_answer_json`, `analysis_text`, `score`, `sort_no`)
VALUES
  (1, 1, 'PRAC0901-01', 'single_choice', '压杆临界载荷主要与下列哪项有关？', JSON_ARRAY('材料长度', '临界弯矩', '长细比', '泊松比'), JSON_ARRAY('长细比'), '长细比是压杆稳定分析中的核心指标。', 50.00, 1),
  (2, 1, 'PRAC0901-02', 'judge', '压杆越细长，稳定性越差。', NULL, JSON_ARRAY('true'), '细长杆更容易失稳。', 50.00, 2),
  (3, 2, 'PRAC0902-01', 'single_choice', '稳定校核时常用哪一公式进行基础估算？', JSON_ARRAY('欧拉公式', '胡克定律', '伯努利方程', '牛顿第二定律'), JSON_ARRAY('欧拉公式'), '欧拉公式用于理想压杆临界载荷估算。', 50.00, 1),
  (4, 2, 'PRAC0902-02', 'judge', '工程中压杆稳定校核不需要考虑边界条件。', NULL, JSON_ARRAY('false'), '边界条件直接影响计算长度和稳定承载力。', 50.00, 2);

INSERT INTO `lessons` (`id`, `lesson_no`, `course_id`, `lesson_name`, `teacher_id`, `publish_version`, `publish_status`, `published_at`)
VALUES
  (1, 'L10001', 1, '材料力学智慧课程（15期2025春夏）', 1, 1, 'published', NOW());

INSERT INTO `lesson_units` (`id`, `lesson_id`, `course_id`, `source_chapter_id`, `unit_code`, `unit_title`, `sort_no`)
VALUES
  (1, 1, 1, 1, 'LU0901', '第九章 压杆稳定', 1);

INSERT INTO `lesson_sections` (`id`, `lesson_id`, `course_id`, `unit_id`, `source_chapter_id`, `parse_result_id`, `ppt_asset_id`, `script_id`, `audio_asset_id`, `section_code`, `section_name`, `section_summary`, `student_visible`, `sort_no`)
VALUES
  (1, 1, 1, 1, 2, 1, 1, 1, 1, 'LS0901', '压杆稳定基本概念', '围绕压杆稳定基本概念、临界载荷和欧拉公式展开。', 1, 1),
  (2, 1, 1, 1, 3, NULL, NULL, NULL, NULL, 'LS0902', '稳定校核与工程应用', '围绕稳定校核方法与工程应用场景展开。', 1, 2);

INSERT INTO `lesson_section_pages` (`id`, `lesson_id`, `section_id`, `source_ppt_asset_id`, `source_page_no`, `page_no`, `page_title`, `page_summary`, `ppt_page_url`, `parsed_content`, `sort_no`)
VALUES
  (1, 1, 1, 1, 1, 1, '稳定平衡条件', '理解压杆的稳定平衡。', NULL, '稳定平衡条件页面内容', 1),
  (2, 1, 1, 1, 2, 2, '临界载荷', '掌握临界载荷的定义与影响因素。', NULL, '临界载荷页面内容', 2),
  (3, 1, 1, 1, 3, 3, '欧拉公式', '掌握欧拉公式的基本形式。', NULL, '欧拉公式页面内容', 3),
  (4, 1, 1, 1, 4, 4, '长细比影响', '理解长细比与稳定性的关系。', NULL, '长细比页面内容', 4),
  (5, 1, 1, 1, 5, 5, '工程应用', '结合工程案例理解稳定校核。', NULL, '工程应用页面内容', 5),
  (6, 1, 2, NULL, NULL, 1, '稳定校核步骤', '掌握稳定校核的流程。', NULL, '稳定校核步骤页面内容', 1),
  (7, 1, 2, NULL, NULL, 2, '边界条件影响', '理解边界条件对计算长度的影响。', NULL, '边界条件影响页面内容', 2),
  (8, 1, 2, NULL, NULL, 3, '工程算例', '通过算例理解工程应用。', NULL, '工程算例页面内容', 3),
  (9, 1, 2, NULL, NULL, 4, '课堂总结', '总结本节知识。', NULL, '课堂总结页面内容', 4);

INSERT INTO `lesson_section_anchors` (`id`, `lesson_id`, `section_id`, `lesson_page_id`, `anchor_code`, `anchor_title`, `page_no`, `start_time_sec`, `sort_no`)
VALUES
  (1, 1, 1, 1, 'A0901', '稳定平衡条件', 1, 0, 1),
  (2, 1, 1, 3, 'A0902', '欧拉公式', 3, 120, 2),
  (3, 1, 2, 6, 'A0903', '稳定校核步骤', 1, 0, 1),
  (4, 1, 2, 8, 'A0904', '工程算例', 3, 150, 2);

INSERT INTO `lesson_section_knowledge_points` (`id`, `lesson_id`, `section_id`, `source_node_id`, `point_code`, `point_name`, `point_summary`, `sort_no`)
VALUES
  (1, 1, 1, 2, 'KP0901', '稳定平衡条件', '理解压杆失稳前的平衡状态。', 1),
  (2, 1, 1, 3, 'KP0902', '临界载荷', '掌握临界载荷的定义。', 2),
  (3, 1, 1, 5, 'KP0903', '欧拉公式', '掌握欧拉公式的适用条件。', 3),
  (4, 1, 2, NULL, 'KP0904', '稳定校核步骤', '掌握工程中的稳定校核流程。', 1),
  (5, 1, 2, NULL, 'KP0905', '边界条件影响', '理解边界条件对稳定的影响。', 2);

INSERT INTO `notifications` (`id`, `course_id`, `lesson_id`, `section_id`, `title`, `content`, `notification_type`, `created_by`)
VALUES
  (1, 1, 1, 1, '压杆稳定智课已发布', '教师已发布第九章压杆稳定的 PPT、讲稿和音频资源。', 'course_update', 1),
  (2, 1, 1, 1, '章节练习已开放', '压杆稳定章节练习已开放，请在规定时间内完成。', 'practice', 1);

INSERT INTO `notification_receipts` (`id`, `notification_id`, `student_id`, `is_read`, `read_at`)
VALUES
  (1, 1, 2, 1, NOW()),
  (2, 2, 2, 0, NULL),
  (3, 1, 3, 0, NULL);

INSERT INTO `qa_sessions` (`id`, `session_no`, `student_id`, `course_id`, `lesson_id`, `current_section_id`, `session_title`, `status`)
VALUES
  (1, 'QS000001', 2, 1, 1, 1, '压杆稳定概念答疑', 'active'),
  (2, 'QS000002', 2, 1, 1, 2, '稳定校核工程应用', 'archived');

INSERT INTO `qa_messages` (`id`, `session_id`, `lesson_id`, `section_id`, `role`, `question_type`, `message_content`, `created_at`)
VALUES
  (1, 1, 1, 1, 'user', 'text', '什么是压杆的临界载荷？', NOW()),
  (2, 1, 1, 1, 'assistant', NULL, '临界载荷是压杆刚好失稳时所对应的载荷。', NOW()),
  (3, 2, 1, 2, 'user', 'text', '工程里如何做稳定校核？', NOW()),
  (4, 2, 1, 2, 'assistant', NULL, '通常结合边界条件、计算长度和欧拉公式进行稳定校核。', NOW());

INSERT INTO `qa_answers` (`id`, `answer_no`, `session_id`, `question_message_id`, `assistant_message_id`, `related_section_id`, `answer_type`, `understanding_level`, `recommended_section_id`, `recommended_page_no`, `recommended_anchor_id`, `next_sections_json`, `suggestions_json`)
VALUES
  (1, 'QA000001', 1, 1, 2, 1, 'text', 'partial', 1, 3, 2, JSON_ARRAY('LS0902'), JSON_ARRAY('回看欧拉公式', '继续练习临界载荷')),
  (2, 'QA000002', 2, 3, 4, 2, 'text', 'full', 2, 1, 3, JSON_ARRAY(), JSON_ARRAY('结合工程算例复习'));

INSERT INTO `qa_message_knowledge_refs` (`id`, `answer_id`, `knowledge_point_id`, `knowledge_name`, `sort_no`)
VALUES
  (1, 1, 2, '临界载荷', 1),
  (2, 1, 3, '欧拉公式', 2),
  (3, 2, 4, '稳定校核步骤', 1);

INSERT INTO `voice_transcripts` (`id`, `student_id`, `session_id`, `question_message_id`, `lesson_id`, `section_id`, `audio_url`, `duration_seconds`, `language`, `transcript_text`, `confidence_score`)
VALUES
  (1, 2, 1, 1, 1, 1, 'https://example.com/audio/qs000001.webm', 8, 'zh-CN', '什么是压杆的临界载荷', 96.50);

INSERT INTO `student_practice_attempts` (`id`, `attempt_no`, `practice_id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `started_at`, `submitted_at`, `duration_seconds`, `total_score`, `correct_count`, `accuracy_percent`, `grading_status`, `attempt_status`)
VALUES
  (1, 'ATT0901', 1, 2, 1, 1, 1, NOW(), NOW(), 600, 80.00, 2, 80.00, 'graded', 'graded'),
  (2, 'ATT0902', 2, 2, 1, 1, 2, NOW(), NOW(), 700, 30.00, 1, 30.00, 'graded', 'graded'),
  (3, 'ATT0903', 1, 3, 1, 1, 1, NOW(), NOW(), 800, 40.00, 1, 40.00, 'graded', 'graded');

INSERT INTO `student_practice_answers` (`id`, `attempt_id`, `item_id`, `student_answer_json`, `answer_text`, `is_correct`, `earned_score`, `teacher_comment`, `graded_at`)
VALUES
  (1, 1, 1, JSON_ARRAY('长细比'), NULL, 1, 50.00, '回答正确', NOW()),
  (2, 1, 2, JSON_ARRAY('true'), NULL, 1, 30.00, '判断正确', NOW()),
  (3, 2, 3, JSON_ARRAY('欧拉公式'), NULL, 1, 30.00, '公式识别正确', NOW()),
  (4, 2, 4, JSON_ARRAY('true'), NULL, 0, 0.00, '边界条件不可忽略', NOW()),
  (5, 3, 1, JSON_ARRAY('材料长度'), NULL, 0, 0.00, '应关注长细比', NOW()),
  (6, 3, 2, JSON_ARRAY('true'), NULL, 1, 40.00, '判断正确', NOW());

INSERT INTO `student_lesson_progress` (`id`, `student_id`, `course_id`, `lesson_id`, `total_progress`, `overall_mastery_percent`, `current_unit_id`, `current_section_id`, `current_anchor_id`, `last_page_no`, `last_operate_time`)
VALUES
  (1, 2, 1, 1, 70.00, 61.00, 1, 2, 4, 4, NOW()),
  (2, 3, 1, 1, 20.00, 20.00, 1, 1, 1, 1, NOW());

INSERT INTO `student_section_progress` (`id`, `student_id`, `course_id`, `lesson_id`, `unit_id`, `section_id`, `current_anchor_id`, `last_page_no`, `progress_percent`, `mastery_percent`, `understanding_level`, `last_qa_message_id`, `last_practice_attempt_id`, `last_operate_time`)
VALUES
  (1, 2, 1, 1, 1, 1, 2, 2, 40.00, 64.00, 'partial', 2, 1, NOW()),
  (2, 2, 1, 1, 1, 2, 4, 4, 100.00, 58.00, 'full', 4, 2, NOW()),
  (3, 3, 1, 1, 1, 1, 1, 1, 20.00, 32.00, 'partial', NULL, 3, NOW()),
  (4, 3, 1, 1, 1, 2, NULL, NULL, 0.00, 0.00, NULL, NULL, NULL, NOW());

INSERT INTO `student_page_progress` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `lesson_page_id`, `page_no`, `read_percent`, `is_completed`, `stay_seconds`, `first_read_at`, `last_read_at`, `completed_at`)
VALUES
  (1, 2, 1, 1, 1, 1, 1, 100.00, 1, 90, NOW(), NOW(), NOW()),
  (2, 2, 1, 1, 1, 2, 2, 100.00, 1, 120, NOW(), NOW(), NOW()),
  (3, 2, 1, 1, 2, 6, 1, 100.00, 1, 80, NOW(), NOW(), NOW()),
  (4, 2, 1, 1, 2, 7, 2, 100.00, 1, 85, NOW(), NOW(), NOW()),
  (5, 2, 1, 1, 2, 8, 3, 100.00, 1, 100, NOW(), NOW(), NOW()),
  (6, 2, 1, 1, 2, 9, 4, 100.00, 1, 60, NOW(), NOW(), NOW()),
  (7, 3, 1, 1, 1, 1, 1, 100.00, 1, 70, NOW(), NOW(), NOW());

INSERT INTO `resume_records` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `anchor_id`, `page_no`, `resume_time_sec`, `resume_type`)
VALUES
  (1, 2, 1, 1, 2, 4, 4, 180, 'manual'),
  (2, 3, 1, 1, 1, 1, 1, 0, 'auto');

INSERT INTO `progress_track_logs` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `anchor_id`, `page_no`, `qa_answer_id`, `track_source`, `progress_percent`, `last_operate_time`)
VALUES
  (1, 2, 1, 1, 1, 2, 2, NULL, 'page_read', 40.00, NOW()),
  (2, 2, 1, 1, 2, 4, 4, NULL, 'page_read', 100.00, NOW()),
  (3, 3, 1, 1, 1, 1, 1, NULL, 'page_read', 20.00, NOW());

INSERT INTO `progress_adjust_records` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `qa_answer_id`, `understanding_level`, `adjust_type`, `continue_section_id`, `recommended_page_no`, `recommended_anchor_id`, `supplement_content`, `adjust_payload`)
VALUES
  (1, 2, 1, 1, 1, 1, 'partial', 'advance', 2, 1, 3, '建议进入稳定校核与工程应用继续学习。', JSON_OBJECT('source', 'qa')),
  (2, 2, 1, 1, 2, 2, 'full', 'keep', 2, 4, 4, '可继续完成章节练习巩固知识。', JSON_OBJECT('source', 'qa'));

INSERT INTO `student_section_mastery_logs` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `practice_attempt_id`, `qa_answer_id`, `source_type`, `page_progress_contribution`, `practice_contribution`, `qa_contribution`, `final_mastery_percent`, `rule_version`, `detail_json`)
VALUES
  (1, 2, 1, 1, 1, 1, 1, 'practice_submit', 16.00, 48.00, 0.00, 64.00, 'v1', JSON_OBJECT('progressPercent', 40, 'practicePercent', 80)),
  (2, 2, 1, 1, 2, 2, 2, 'practice_submit', 40.00, 18.00, 0.00, 58.00, 'v1', JSON_OBJECT('progressPercent', 100, 'practicePercent', 30)),
  (3, 3, 1, 1, 1, 3, NULL, 'practice_submit', 8.00, 24.00, 0.00, 32.00, 'v1', JSON_OBJECT('progressPercent', 20, 'practicePercent', 40));

INSERT INTO `api_call_logs` (`id`, `request_id`, `user_id`, `role`, `api_path`, `status_code`, `request_json`, `response_json`)
VALUES
  (1, 'seed-req-0001', 1, 'teacher', '/api/v1/lesson/parse', 200, JSON_OBJECT('parseId', 'PTEST000001'), JSON_OBJECT('status', 'success')),
  (2, 'seed-req-0002', 2, 'student', '/student-api/api/v1/progress/get', 200, JSON_OBJECT('lessonId', 'L10001'), JSON_OBJECT('totalProgress', 70));
