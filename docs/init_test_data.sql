USE `chaoxing_ai_course`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 最小化可运行种子数据
-- 目标：覆盖当前项目实际依赖的最小链路
-- 1. 教师端：平台鉴权 / 课程同步 / 状态查看 / 历史课件、讲稿、音频读取
-- 2. 学生端：课程列表 / 课程播放 / 章节详情 / 页级阅读 / 最近学习记录 / QA 会话
--
-- 当前代码未直接依赖数据库初始化的数据项：
-- - 通知列表：当前走 adapter mock
-- - 练习题 / 作答 / 语音转写 / 大部分日志：运行时可为空

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
DELETE FROM `chapter_section_audio_assets`;
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
  (1, 'SCH001', '尔雅大学', 1);

INSERT INTO `users` (`id`, `user_no`, `user_name`, `role`, `school_id`, `phone`, `email`, `auth_token`, `status`)
VALUES
  (1, 'T10001', '豆哥', 'teacher', 1, '13800000001', 'teacher@test.edu.cn', 'test_token_001', 1),
  (2, 'S2026001', '王尔雅', 'student', 1, '13800000002', 'student@test.edu.cn', 'student_demo_token_001', 1);

INSERT INTO `user_platform_bindings` (`id`, `platform_id`, `user_id`, `external_user_id`, `external_role`, `related_course_ids`, `raw_payload`)
VALUES
  (1, 1, 1, 'T10001', 'teacher', JSON_ARRAY('course-ai-001'), JSON_OBJECT('teacherName', '豆哥')),
  (2, 1, 2, 'S2026001', 'student', JSON_ARRAY('course-ai-001'), JSON_OBJECT('studentName', '王尔雅'));

INSERT INTO `courses` (`id`, `course_code`, `course_name`, `school_id`, `term`, `credit`, `period`, `course_cover_url`, `course_status`, `created_by`)
VALUES
  (1, 'course-ai-001', '汽车构造', 1, '2026春', 2.0, 32, NULL, 'published', 1);

INSERT INTO `course_platform_bindings` (`id`, `platform_id`, `course_id`, `external_course_id`, `raw_payload`)
VALUES
  (1, 1, 1, 'course-ai-001', JSON_OBJECT('courseName', '汽车构造'));

INSERT INTO `course_members` (`id`, `course_id`, `class_id`, `user_id`, `member_role`)
VALUES
  (1, 1, NULL, 1, 'teacher'),
  (2, 1, NULL, 2, 'student');

INSERT INTO `course_chapters` (`id`, `course_id`, `parent_id`, `chapter_code`, `chapter_name`, `chapter_type`, `chapter_level`, `sort_no`, `status`)
VALUES
  (1, 1, NULL, 'course-ai-001-chap-001', '01总论', 'chapter', 1, 1, 'published');

INSERT INTO `chapter_ppt_assets` (`id`, `course_id`, `chapter_id`, `uploader_id`, `file_name`, `file_type`, `file_url`, `file_size`, `page_count`, `upload_status`, `version_no`)
VALUES
  (1, 1, 1, 1, '01总论.pptx', 'ppt', '/mock-remote/examples/01总论.pptx', 1048576, 18, 'parsed', 1);

INSERT INTO `chapter_parse_tasks` (`id`, `parse_no`, `course_id`, `chapter_id`, `ppt_asset_id`, `teacher_id`, `llm_model`, `is_extract_key_point`, `task_status`, `finished_at`)
VALUES
  (1, 'parse20260414122606e35590', 1, 1, 1, 1, 'deepseek-chat', 1, 'completed', NOW());

INSERT INTO `chapter_parse_results` (
  `id`,
  `parse_task_id`,
  `course_id`,
  `chapter_id`,
  `ppt_asset_id`,
  `chapter_summary`,
  `parsed_outline`,
  `key_points`,
  `page_mapping`,
  `raw_llm_output`,
  `normalized_content`
)
VALUES
  (
    1,
    1,
    1,
    1,
    1,
    '课件《01总论.pptx》解析完成，共 18 页。',
    JSON_OBJECT(
      'chapters', JSON_ARRAY(
        JSON_OBJECT(
          'chapterId', 'chapter-01',
          'chapterName', '汽车的定义及分类',
          'subChapters', JSON_ARRAY(
            JSON_OBJECT(
              'subChapterId', 'node-01-01',
              'subChapterName', '汽车的定义与国内分类',
              'isKeyPoint', TRUE,
              'pageRange', '1'
            )
          )
        ),
        JSON_OBJECT(
          'chapterId', 'chapter-02',
          'chapterName', '车辆识别代码编号',
          'subChapters', JSON_ARRAY(
            JSON_OBJECT(
              'subChapterId', 'node-02-01',
              'subChapterName', 'VIN的用途与基本内容',
              'isKeyPoint', TRUE,
              'pageRange', '2'
            ),
            JSON_OBJECT(
              'subChapterId', 'node-02-02',
              'subChapterName', 'VIN的组成与年份代码',
              'isKeyPoint', TRUE,
              'pageRange', '3'
            )
          )
        )
      )
    ),
    JSON_ARRAY(
      '汽车定义',
      '国内汽车分类',
      'GB/T 3730.1—2001',
      'VIN用途',
      '17位识别代码',
      '汽车管理与维修',
      'WMI',
      'VDS',
      '年份代码'
    ),
    JSON_ARRAY(
      JSON_OBJECT(
        'pageNo', 1,
        'title', '一、汽车的定义及分类',
        'previewUrl', '/courseware-previews/parse20260414122606e35590/page-4.png'
      ),
      JSON_OBJECT(
        'pageNo', 2,
        'title', '二、车辆识别代码编号',
        'previewUrl', '/courseware-previews/parse20260414122606e35590/page-7.png'
      ),
      JSON_OBJECT(
        'pageNo', 3,
        'title', '车辆识别代号第10位含义',
        'previewUrl', '/courseware-previews/parse20260414122606e35590/page-9.png'
      )
    ),
    CAST(
      JSON_OBJECT(
        'coursewareId', 'cw-course-ai-001',
        'title', '01总论',
        'chapters', JSON_ARRAY(
          JSON_OBJECT(
            'chapterId', 'chapter-01',
            'chapterName', '汽车的定义及分类',
            'nodes', JSON_ARRAY(
              JSON_OBJECT(
                'nodeId', 'node-01-01',
                'nodeName', '汽车的定义与国内分类',
                'pageRefs', JSON_ARRAY(1),
                'pageContents', JSON_ARRAY(
                  JSON_OBJECT(
                    'slideNumber', 1,
                    'title', '一、汽车的定义及分类',
                    'bodyTexts', JSON_ARRAY('一、汽车的定义及分类。重点理解汽车的定义、乘用车与商用车的国内分类标准，以及 GB/T 3730.1—2001 的基本口径。'),
                    'tableTexts', JSON_ARRAY(),
                    'notes', NULL
                  )
                ),
                'keyPoints', JSON_ARRAY('汽车定义', '国内汽车分类', 'GB/T 3730.1—2001'),
                'summary', '本节点围绕汽车的定义与国内分类展开，帮助学生建立汽车课程的基础概念。',
                'anchors', JSON_ARRAY(
                  JSON_OBJECT(
                    'anchorId', 'anchor-01',
                    'label', '汽车的定义与国内分类',
                    'pageRef', 1,
                    'nodeRef', 'node-01-01',
                    'sourceSpan', '1'
                  )
                ),
                'prerequisiteNodeIds', JSON_ARRAY(),
                'nextNodeId', 'node-02-01'
              )
            )
          ),
          JSON_OBJECT(
            'chapterId', 'chapter-02',
            'chapterName', '车辆识别代码编号',
            'nodes', JSON_ARRAY(
              JSON_OBJECT(
                'nodeId', 'node-02-01',
                'nodeName', 'VIN的用途与基本内容',
                'pageRefs', JSON_ARRAY(2),
                'pageContents', JSON_ARRAY(
                  JSON_OBJECT(
                    'slideNumber', 2,
                    'title', '二、车辆识别代码编号',
                    'bodyTexts', JSON_ARRAY('二、车辆识别代码编号。理解 VIN 由 17 位字母与数字组成，以及它在汽车管理、维修、检测、二手车交易和保险中的用途。'),
                    'tableTexts', JSON_ARRAY(),
                    'notes', NULL
                  )
                ),
                'keyPoints', JSON_ARRAY('VIN用途', '17位识别代码', '汽车管理与维修'),
                'summary', '本节点围绕 VIN 的用途与基本内容展开，突出识别代码在汽车管理、维修和检测中的应用。',
                'anchors', JSON_ARRAY(
                  JSON_OBJECT(
                    'anchorId', 'anchor-02',
                    'label', 'VIN的用途与基本内容',
                    'pageRef', 2,
                    'nodeRef', 'node-02-01',
                    'sourceSpan', '2'
                  )
                ),
                'prerequisiteNodeIds', JSON_ARRAY('node-01-01'),
                'nextNodeId', 'node-02-02'
              ),
              JSON_OBJECT(
                'nodeId', 'node-02-02',
                'nodeName', 'VIN的组成与年份代码',
                'pageRefs', JSON_ARRAY(3),
                'pageContents', JSON_ARRAY(
                  JSON_OBJECT(
                    'slideNumber', 3,
                    'title', '车辆识别代号第10位含义',
                    'bodyTexts', JSON_ARRAY('车辆识别代号第 10 位表示车型年份。本节点还需要掌握 WMI、VDS 和 VIS 三段编码分别表达的含义。'),
                    'tableTexts', JSON_ARRAY(),
                    'notes', NULL
                  )
                ),
                'keyPoints', JSON_ARRAY('WMI', 'VDS', '年份代码'),
                'summary', '本节点围绕 VIN 的组成与年份代码展开，帮助学生理解 WMI、VDS 与年份编码的含义。',
                'anchors', JSON_ARRAY(
                  JSON_OBJECT(
                    'anchorId', 'anchor-03',
                    'label', 'VIN的组成与年份代码',
                    'pageRef', 3,
                    'nodeRef', 'node-02-02',
                    'sourceSpan', '3'
                  )
                ),
                'prerequisiteNodeIds', JSON_ARRAY('node-02-01'),
                'nextNodeId', NULL
              )
            )
          )
        )
      ) AS CHAR CHARACTER SET utf8mb4
    ),
    CONCAT(
      '本节点围绕汽车的定义与国内分类展开，帮助学生建立汽车课程的基础概念。',
      '\n\n本节点围绕 VIN 的用途与基本内容展开，突出识别代码在汽车管理、维修和检测中的应用。',
      '\n\n本节点围绕 VIN 的组成与年份代码展开，帮助学生理解 WMI、VDS 与年份编码的含义。'
    )
  );

INSERT INTO `chapter_knowledge_nodes` (`id`, `parse_task_id`, `chapter_id`, `parent_id`, `node_code`, `node_name`, `node_type`, `level_no`, `is_key_point`, `page_start`, `page_end`, `sort_no`)
VALUES
  (1, 1, 1, NULL, 'node-01-01', '汽车的定义与国内分类', 'knowledge', 1, 1, 1, 1, 0),
  (2, 1, 1, NULL, 'node-02-01', 'VIN的用途与基本内容', 'knowledge', 1, 1, 2, 2, 1),
  (3, 1, 1, NULL, 'node-02-02', 'VIN的组成与年份代码', 'knowledge', 1, 1, 3, 3, 2);

INSERT INTO `chapter_scripts` (`id`, `script_no`, `course_id`, `chapter_id`, `parse_task_id`, `teacher_id`, `teaching_style`, `speech_speed`, `custom_opening`, `script_status`, `edit_url`)
VALUES
  (
    1,
    'mock-script-course-ai-001',
    1,
    1,
    1,
    1,
    'standard',
    'normal',
    '同学们好，这节课我们从汽车的定义和 VIN 识别代码开始进入汽车构造课程。',
    'published',
    '/teacher/script-edit?scriptId=mock-script-course-ai-001'
  );

INSERT INTO `chapter_script_sections` (`id`, `script_id`, `section_code`, `section_name`, `section_content`, `duration_sec`, `related_node_id`, `related_page_range`, `sort_no`)
VALUES
  (
    1,
    1,
    'sec001',
    '汽车的定义与国内分类',
    '下面学习：汽车的定义与国内分类。第 4 页主题是一、汽车的定义及分类。这里首先要掌握汽车的基本定义，以及乘用车和商用车两大类的划分标准。通过这一部分，同学们要建立课程的基础概念框架。',
    156,
    1,
    '1',
    0
  ),
  (
    2,
    1,
    'sec002',
    'VIN的用途与基本内容',
    '下面学习：VIN 的用途与基本内容。VIN 是由 17 位字母和数字组成的车辆识别代码，作用类似于汽车的身份证。它在汽车管理、维修、检测、二手车交易和保险中都有直接应用，因此是后续识别车辆信息的基础。',
    148,
    2,
    '2',
    1
  ),
  (
    3,
    1,
    'sec003',
    'VIN的组成与年份代码',
    '下面学习：VIN 的组成与年份代码。这里要重点掌握三段编码结构，也就是 WMI、VDS 和 VIS。其中第 10 位通常用于标识车型年份，是识别车辆出厂年份和基础信息的重要位置。',
    152,
    3,
    '3',
    2
  );

INSERT INTO `chapter_audio_assets` (`id`, `course_id`, `chapter_id`, `script_id`, `voice_type`, `audio_format`, `audio_url`, `total_duration_sec`, `file_size`, `bit_rate`, `status`)
VALUES
  (1, 1, 1, 1, 'mock', 'mp3', 'https://www.w3schools.com/html/horse.mp3', 456, 512000, 128, 'published');

INSERT INTO `lessons` (`id`, `lesson_no`, `course_id`, `lesson_name`, `teacher_id`, `publish_version`, `publish_status`, `published_at`)
VALUES
  (1, 'mockpub-course-ai-001', 1, '汽车构造', 1, 1, 'published', NOW());

INSERT INTO `lesson_units` (`id`, `lesson_id`, `course_id`, `source_chapter_id`, `unit_code`, `unit_title`, `sort_no`)
VALUES
  (1, 1, 1, 1, 'course-ai-001-unit-001', '01总论', 1);

INSERT INTO `lesson_sections` (
  `id`,
  `lesson_id`,
  `course_id`,
  `unit_id`,
  `source_chapter_id`,
  `parse_result_id`,
  `ppt_asset_id`,
  `script_id`,
  `audio_asset_id`,
  `section_code`,
  `section_name`,
  `section_summary`,
  `student_visible`,
  `sort_no`
)
VALUES
  (
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    'ch1-sec001',
    '汽车的定义与国内分类',
    '下面学习：汽车的定义与国内分类。重点掌握汽车的定义、乘用车与商用车的国内分类标准，以及课程开篇需要建立的基础概念。',
    1,
    0
  ),
  (
    2,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    'ch1-sec002',
    'VIN的用途与基本内容',
    '下面学习：VIN 的用途与基本内容。要理解 17 位识别代码在汽车管理、维修、检测和保险中的实际作用。',
    1,
    1
  ),
  (
    3,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    'ch1-sec003',
    'VIN的组成与年份代码',
    '下面学习：VIN 的组成与年份代码。重点理解 WMI、VDS 和 VIS 三段结构，以及第 10 位年份代码的辨识含义。',
    1,
    2
  );

INSERT INTO `lesson_section_pages` (`id`, `lesson_id`, `section_id`, `source_ppt_asset_id`, `source_page_no`, `page_no`, `page_title`, `page_summary`, `ppt_page_url`, `parsed_content`, `sort_no`)
VALUES
  (
    1,
    1,
    1,
    1,
    4,
    1,
    '一、汽车的定义及分类',
    '查看《汽车的定义与国内分类》课件第 1 页内容。',
    '/courseware-previews/parse20260414122606e35590/page-4.png',
    '一、汽车的定义及分类。重点理解汽车的定义、乘用车与商用车的国内分类标准，以及 GB/T 3730.1—2001 的基本口径。',
    1
  ),
  (
    2,
    1,
    2,
    1,
    7,
    2,
    '二、车辆识别代码编号',
    '查看《VIN的用途与基本内容》课件第 2 页内容。',
    '/courseware-previews/parse20260414122606e35590/page-7.png',
    '二、车辆识别代码编号。VIN 由 17 位字母和数字组成，常被称为汽车的身份证，在车辆管理、维修和检测中都非常重要。',
    2
  ),
  (
    3,
    1,
    3,
    1,
    9,
    3,
    '车辆识别代号第10位含义',
    '查看《VIN的组成与年份代码》课件第 3 页内容。',
    '/courseware-previews/parse20260414122606e35590/page-9.png',
    '车辆识别代码由 WMI、VDS 和 VIS 三部分组成，其中第 10 位常用于表示车型年份，是识别车辆信息的重要位置。',
    3
  );

INSERT INTO `lesson_section_anchors` (`id`, `lesson_id`, `section_id`, `lesson_page_id`, `anchor_code`, `anchor_title`, `page_no`, `start_time_sec`, `sort_no`)
VALUES
  (1, 1, 1, 1, 'anchor-01', '汽车的定义与国内分类', 1, 0, 0),
  (2, 1, 2, 2, 'anchor-02', 'VIN的用途与基本内容', 2, 120, 1),
  (3, 1, 3, 3, 'anchor-03', 'VIN的组成与年份代码', 3, 240, 2);

INSERT INTO `lesson_section_knowledge_points` (`id`, `lesson_id`, `section_id`, `source_node_id`, `point_code`, `point_name`, `point_summary`, `sort_no`)
VALUES
  (1, 1, 1, 1, 'node-01-01', '汽车的定义与国内分类', '掌握汽车定义与国内分类标准。', 0),
  (2, 1, 2, 2, 'node-02-01', 'VIN的用途与基本内容', '理解 VIN 的用途与 17 位识别代码的定位。', 1),
  (3, 1, 3, 3, 'node-02-02', 'VIN的组成与年份代码', '理解 WMI、VDS、VIS 与年份代码。', 2);

INSERT INTO `student_lesson_progress` (`id`, `student_id`, `course_id`, `lesson_id`, `total_progress`, `overall_mastery_percent`, `current_unit_id`, `current_section_id`, `current_anchor_id`, `last_page_no`, `last_operate_time`)
VALUES
  (1, 2, 1, 1, 33.00, 13.00, 1, 2, 2, 2, NOW());

INSERT INTO `student_section_progress` (`id`, `student_id`, `course_id`, `lesson_id`, `unit_id`, `section_id`, `current_anchor_id`, `last_page_no`, `progress_percent`, `mastery_percent`, `understanding_level`, `last_qa_message_id`, `last_practice_attempt_id`, `last_operate_time`)
VALUES
  (1, 2, 1, 1, 1, 1, 1, 1, 100.00, 40.00, 'full', NULL, NULL, NOW()),
  (2, 2, 1, 1, 1, 2, 2, 2, 0.00, 0.00, 'partial', NULL, NULL, NOW()),
  (3, 2, 1, 1, 1, 3, 3, 3, 0.00, 0.00, 'none', NULL, NULL, NOW());

INSERT INTO `student_page_progress` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `lesson_page_id`, `page_no`, `read_percent`, `is_completed`, `stay_seconds`, `first_read_at`, `last_read_at`, `completed_at`)
VALUES
  (1, 2, 1, 1, 1, 1, 1, 100.00, 1, 180, NOW(), NOW(), NOW());

INSERT INTO `resume_records` (`id`, `student_id`, `course_id`, `lesson_id`, `section_id`, `anchor_id`, `page_no`, `resume_time_sec`, `resume_type`)
VALUES
  (1, 2, 1, 1, 2, 2, 2, 120, 'manual');

INSERT INTO `qa_sessions` (`id`, `session_no`, `student_id`, `course_id`, `lesson_id`, `current_section_id`, `session_title`, `status`)
VALUES
  (1, 'session-vin-demo', 2, 1, 1, 2, 'VIN 的 17 位编码有什么用', 'active');

INSERT INTO `qa_messages` (`id`, `session_id`, `lesson_id`, `section_id`, `role`, `question_type`, `message_content`, `created_at`)
VALUES
  (1, 1, 1, 2, 'user', 'text', 'VIN 的 17 位编码主要有什么作用？', NOW()),
  (2, 1, 1, 2, 'assistant', NULL, 'VIN 可以看作车辆的身份证。它由 17 位编码组成，主要用于车辆管理、维修、检测、二手车交易和保险等场景，核心价值是快速、准确地识别车辆身份。', NOW());

INSERT INTO `qa_answers` (`id`, `answer_no`, `session_id`, `question_message_id`, `assistant_message_id`, `related_section_id`, `answer_type`, `understanding_level`, `recommended_section_id`, `recommended_page_no`, `recommended_anchor_id`, `next_sections_json`, `suggestions_json`)
VALUES
  (
    1,
    'answer-vin-demo',
    1,
    1,
    2,
    2,
    'text',
    'partial',
    2,
    2,
    2,
    JSON_ARRAY(),
    JSON_ARRAY('先记住 VIN 是 17 位车辆识别代码', '回看 VIN 的用途与基本内容这一页')
  );

INSERT INTO `qa_message_knowledge_refs` (`id`, `answer_id`, `knowledge_point_id`, `knowledge_name`, `sort_no`)
VALUES
  (1, 1, 2, 'VIN的用途与基本内容', 0);

SET FOREIGN_KEY_CHECKS = 1;
