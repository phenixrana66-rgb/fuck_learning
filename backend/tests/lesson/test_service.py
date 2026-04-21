import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backend.app.lesson.service as lesson_service_module
from backend.app.cir.schemas import CIR, CirChapter, LessonNode
from backend.app.common.db import configure_database_url, reset_database_url, session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import clear_parse_tasks, create_parse_task, run_parse_task
from backend.app.lesson.schemas import GenerateAudioRequest, PlayRequest, PublishRequest
from backend.app.lesson.service import _sync_lesson_pages, clear_lessons, generate_audio, play_lesson, publish_lesson
from backend.app.lesson.tts_client import TtsSynthesisResult
from backend.app.parser.schemas import ExtractedPresentation, ExtractedSlide, FileInfo, StructurePreview
from backend.app.script.schemas import GenerateScriptRequest
from backend.app.script.service import clear_scripts, generate_script, get_script as get_script_detail
from backend.app.student_runtime.db_learning_service import get_section_detail
from backend.chaoxing_db.models import ChapterAudioAsset, ChapterParseTask, ChapterPptAsset, ChapterScript, ChapterScriptSection, ChapterSectionAudioAsset, Course, CourseChapter, Lesson, LessonSection, LessonSectionPage, LessonUnit


class LessonServiceTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    parse_payload: ParseRequest | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'lesson-test.db'}")
        clear_scripts()
        clear_parse_tasks()
        clear_lessons()
        self.parse_payload = ParseRequest(
            schoolId='school-001',
            userId='teacher-001',
            courseId='course-001',
            fileType='ppt',
            fileUrl='file:///tmp/demo.pptx',
            isExtractKeyPoint=True,
            enc='demo-signature',
        )

    def tearDown(self) -> None:
        clear_scripts()
        clear_parse_tasks()
        clear_lessons()
        reset_database_url()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_generate_audio_publish_and_play_form_demo_chain(self, mock_parse_courseware, mock_build_cir, mock_synthesize_speech, mock_get_voice_cache_dir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        voice_cache_dir = Path(self.temp_dir.name) / 'voice-cache'
        mock_get_voice_cache_dir.return_value = voice_cache_dir
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=3500,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId='cw-course-001',
            title='??????',
            chapters=[
                CirChapter(
                    chapterId='course-001-chap-001',
                    chapterName='???',
                    nodes=[
                        LessonNode(nodeId='node-01-01', nodeName='???????', pageRefs=[1, 2], keyPoints=['??'], summary='????????????'),
                        LessonNode(nodeId='node-01-02', nodeName='???????', pageRefs=[3], keyPoints=['??'], summary='????????????????'),
                    ],
                )
            ],
        )
        script_summary = self._create_script_summary(parse_payload)
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        for index, section in enumerate(script_detail.scriptStructure[:2], start=1):
            section.content = f'short audio test section {index}'
        section_ids = [section.sectionId for section in script_detail.scriptStructure[:2]]

        with patch('backend.app.lesson.service.get_script', return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=script_summary.scriptId,
                    voiceType='female_standard',
                    audioFormat='mp3',
                    sectionIds=section_ids,
                    enc='demo-signature',
                ),
                base_url='http://testserver/',
            )
            publish = publish_lesson(
                PublishRequest(
                    coursewareId='cw-course-001',
                    scriptId=script_summary.scriptId,
                    audioId=audio['audioId'],
                    publisherId='teacher-demo',
                    chapterName='发布章节名',
                    enc='demo-signature',
                )
            )
        lesson_service_module._AUDIO_STORE.clear()
        lesson_service_module._LESSON_PACKAGES.clear()
        play = play_lesson(
            PlayRequest(
                lessonId=publish['lessonId'],
                userId='student-demo',
                resumeContext={'currentSectionId': script_detail.scriptStructure[0].sectionId},
                enc='demo-signature',
            )
        )

        with session_scope() as db:
            stored_audio = db.query(ChapterAudioAsset).join(ChapterScript).filter(ChapterScript.script_no == script_summary.scriptId).first()
            stored_section_audios = (
                db.query(ChapterSectionAudioAsset)
                .join(ChapterAudioAsset, ChapterSectionAudioAsset.audio_asset_id == ChapterAudioAsset.id)
                .join(ChapterScript, ChapterAudioAsset.script_id == ChapterScript.id)
                .filter(ChapterScript.script_no == script_summary.scriptId)
                .all()
            )
            published_lesson = db.query(Lesson).filter(Lesson.lesson_no == publish['lessonId']).first()
            published_sections = db.query(LessonSection).filter(LessonSection.lesson_id == published_lesson.id).all() if published_lesson else []
            script_entity = db.query(ChapterScript).filter(ChapterScript.script_no == script_summary.scriptId).first()
            chapter_name = script_entity.chapter.chapter_name if script_entity and script_entity.chapter else None

        generated_filename = audio['audioUrl'].rsplit('/', 1)[-1]
        generated_file = voice_cache_dir / generated_filename
        section_files = [voice_cache_dir / item['audioUrl'].rsplit('/', 1)[-1] for item in audio['sectionAudios']]

        self.assertIsNotNone(stored_audio)
        self.assertEqual(len(stored_section_audios), len(section_ids))
        self.assertEqual(audio['taskStatus'], 'completed')
        self.assertEqual(audio['status'], 'success')
        self.assertEqual(audio['scriptId'], script_summary.scriptId)
        self.assertEqual(len(audio['sectionAudios']), len(section_ids))
        self.assertTrue(audio['audioUrl'].startswith('http://testserver/cache/voice/'))
        self.assertTrue(generated_file.exists())
        self.assertTrue(all(section_file.exists() for section_file in section_files))
        self.assertTrue(all(item['sectionAudioId'] for item in audio['sectionAudios']))
        self.assertEqual(audio['audioInfo']['fileSize'], sum(section_file.stat().st_size for section_file in section_files))
        self.assertEqual(publish['publishStatus'], 'published')
        self.assertIsNotNone(published_lesson)
        self.assertEqual(len(published_sections), len(section_ids))
        self.assertEqual(chapter_name, '发布章节名')
        self.assertEqual(play['nodeSequence'], ['node-01-01', 'node-01-02'])
        self.assertEqual(play['scriptRefs'][0]['scriptId'], script_summary.scriptId)
        self.assertEqual(play['audioRefs'][0]['audioId'], audio['audioId'])
        self.assertTrue(play['audioRefs'][0]['sectionAudioId'])

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_publish_rejects_mismatched_courseware(self, mock_parse_courseware, mock_build_cir, mock_synthesize_speech, mock_get_voice_cache_dir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / 'voice-cache'
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=1800,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId='cw-course-001',
            title='??????',
            chapters=[CirChapter(chapterId='course-001-chap-001', chapterName='???', nodes=[LessonNode(nodeId='node-01-01', nodeName='???????', pageRefs=[1], keyPoints=[], summary='???????')])],
        )
        script_summary = self._create_script_summary(parse_payload)
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        for index, section in enumerate(script_detail.scriptStructure[:2], start=1):
            section.content = f'short audio mismatch section {index}'
        section_ids = [section.sectionId for section in script_detail.scriptStructure[:2]]
        with patch('backend.app.lesson.service.get_script', return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(scriptId=script_summary.scriptId, voiceType='female_standard', audioFormat='mp3', sectionIds=section_ids, enc='demo-signature'),
                base_url='http://testserver/',
            )

            with self.assertRaises(ApiError) as context:
                publish_lesson(
                    PublishRequest(
                        coursewareId='cw-course-999',
                        scriptId=script_summary.scriptId,
                        audioId=audio['audioId'],
                        publisherId='teacher-demo',
                        enc='demo-signature',
                    )
                )

        self.assertEqual(context.exception.status_code, 409)

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_generate_audio_skips_empty_sections_instead_of_rolling_back(self, mock_parse_courseware, mock_build_cir, mock_synthesize_speech, mock_get_voice_cache_dir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        voice_cache_dir = Path(self.temp_dir.name) / 'voice-cache'
        mock_get_voice_cache_dir.return_value = voice_cache_dir
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=2200,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId='cw-course-001',
            title='demo',
            chapters=[
                CirChapter(
                    chapterId='course-001-chap-001',
                    chapterName='chapter',
                    nodes=[
                        LessonNode(nodeId='node-01-01', nodeName='node-1', pageRefs=[1], keyPoints=['k1'], summary='summary-1'),
                        LessonNode(nodeId='node-01-02', nodeName='node-2', pageRefs=[2], keyPoints=['k2'], summary='summary-2'),
                        LessonNode(nodeId='node-01-03', nodeName='node-3', pageRefs=[3], keyPoints=['k3'], summary='summary-3'),
                    ],
                )
            ],
        )
        script_summary = self._create_script_summary(parse_payload)
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        script_detail.scriptStructure[0].content = 'audio section one'
        script_detail.scriptStructure[1].content = 'audio section two'
        script_detail.scriptStructure[2].content = ''
        section_ids = [section.sectionId for section in script_detail.scriptStructure[:3]]

        with patch('backend.app.lesson.service.get_script', return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=script_summary.scriptId,
                    voiceType='female_standard',
                    audioFormat='mp3',
                    sectionIds=section_ids,
                    enc='demo-signature',
                ),
                base_url='http://testserver/',
            )

        with session_scope() as db:
            stored_section_audios = (
                db.query(ChapterSectionAudioAsset)
                .join(ChapterAudioAsset, ChapterSectionAudioAsset.audio_asset_id == ChapterAudioAsset.id)
                .join(ChapterScript, ChapterAudioAsset.script_id == ChapterScript.id)
                .filter(ChapterScript.script_no == script_summary.scriptId)
                .order_by(ChapterSectionAudioAsset.sort_no.asc(), ChapterSectionAudioAsset.id.asc())
                .all()
            )

        self.assertEqual(audio['taskStatus'], 'completed')
        self.assertEqual(len(audio['sectionAudios']), 2)
        self.assertEqual([item['sectionId'] for item in audio['sectionAudios']], section_ids[:2])
        self.assertEqual(audio['skippedSections'], [{'sectionId': section_ids[2], 'reason': 'empty_content'}])
        self.assertEqual(len(stored_section_audios), 2)

    def test_play_rejects_missing_lesson(self) -> None:
        with self.assertRaises(ApiError) as context:
            play_lesson(PlayRequest(lessonId='lesson-missing', userId='student-demo', resumeContext=None, enc='demo-signature'))

        self.assertEqual(context.exception.status_code, 404)

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_publish_assigns_next_publish_version_when_course_already_has_lesson(self, mock_parse_courseware, mock_build_cir, mock_synthesize_speech, mock_get_voice_cache_dir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / 'voice-cache'
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=1800,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId='cw-course-001',
            title='demo',
            chapters=[CirChapter(chapterId='course-001-chap-001', chapterName='chapter', nodes=[LessonNode(nodeId='node-01-01', nodeName='node-1', pageRefs=[1], keyPoints=['k1'], summary='summary-1')])],
        )
        script_summary = self._create_script_summary(parse_payload)
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        script_detail.scriptStructure[0].content = 'publish version test'

        with patch('backend.app.lesson.service.get_script', return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=script_summary.scriptId,
                    voiceType='female_standard',
                    audioFormat='mp3',
                    sectionIds=[script_detail.scriptStructure[0].sectionId],
                    enc='demo-signature',
                ),
                base_url='http://testserver/',
            )

        with session_scope() as db:
            script_entity = db.query(ChapterScript).filter(ChapterScript.script_no == script_summary.scriptId).first()
            assert script_entity is not None
            db.add(
                Lesson(
                    lesson_no='lesson-existing',
                    course_id=script_entity.course_id,
                    lesson_name='existing',
                    teacher_id=script_entity.teacher_id,
                    publish_version=1,
                    publish_status='published',
                    published_at=None,
                )
            )
            db.commit()

        publish = publish_lesson(
            PublishRequest(
                coursewareId='cw-course-001',
                scriptId=script_summary.scriptId,
                audioId=audio['audioId'],
                publisherId='teacher-demo',
                enc='demo-signature',
            )
        )

        with session_scope() as db:
            lesson = db.query(Lesson).filter(Lesson.lesson_no == publish['lessonId']).first()
            lesson_publish_version = lesson.publish_version if lesson is not None else None

        self.assertIsNotNone(lesson)
        self.assertEqual(publish['lessonId'], 'lesson-existing')
        self.assertEqual(lesson_publish_version, 2)

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_publish_reuses_existing_lesson_and_appends_sections(self, mock_parse_courseware, mock_build_cir, mock_synthesize_speech, mock_get_voice_cache_dir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / 'voice-cache'
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=1800,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId='cw-course-001',
            title='demo',
            chapters=[CirChapter(chapterId='course-001-chap-001', chapterName='chapter', nodes=[LessonNode(nodeId='node-01-01', nodeName='node-1', pageRefs=[1], keyPoints=['k1'], summary='summary-1')])],
        )
        script_summary = self._create_script_summary(parse_payload)
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        script_detail.scriptStructure[0].content = 'publish append test'

        with patch('backend.app.lesson.service.get_script', return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=script_summary.scriptId,
                    voiceType='female_standard',
                    audioFormat='mp3',
                    sectionIds=[script_detail.scriptStructure[0].sectionId],
                    enc='demo-signature',
                ),
                base_url='http://testserver/',
            )

        with session_scope() as db:
            script_entity = db.query(ChapterScript).filter(ChapterScript.script_no == script_summary.scriptId).first()
            assert script_entity is not None
            course_id = script_entity.course_id
            course = db.query(Course).filter(Course.id == script_entity.course_id).first()
            expected_course_name = course.course_name if course is not None else 'Published Lesson'
            lesson = Lesson(
                lesson_no='lesson-existing',
                course_id=script_entity.course_id,
                lesson_name='existing',
                teacher_id=script_entity.teacher_id,
                publish_version=1,
                publish_status='published',
                published_at=None,
            )
            db.add(lesson)
            db.flush()
            unit = LessonUnit(
                lesson_id=lesson.id,
                course_id=script_entity.course_id,
                source_chapter_id=script_entity.chapter_id,
                unit_code='existing-unit',
                unit_title='Existing Unit',
                sort_no=0,
            )
            db.add(unit)
            db.flush()
            db.add(
                LessonSection(
                    lesson_id=lesson.id,
                    course_id=script_entity.course_id,
                    unit_id=unit.id,
                    source_chapter_id=script_entity.chapter_id,
                    section_code='legacy-section',
                    section_name='Legacy Section',
                    section_summary='legacy',
                    student_visible=True,
                    sort_no=0,
                )
            )
            db.commit()

        publish = publish_lesson(
            PublishRequest(
                coursewareId='cw-course-001',
                scriptId=script_summary.scriptId,
                audioId=audio['audioId'],
                publisherId='teacher-demo',
                enc='demo-signature',
            )
        )

        with session_scope() as db:
            lessons = db.query(Lesson).filter(Lesson.course_id == course_id).all()
            lesson = db.query(Lesson).filter(Lesson.lesson_no == publish['lessonId']).first()
            lesson_name = lesson.lesson_name if lesson is not None else None
            sections = (
                db.query(LessonSection)
                .filter(LessonSection.lesson_id == lesson.id)
                .order_by(LessonSection.sort_no.asc(), LessonSection.id.asc())
                .all()
                if lesson is not None
                else []
            )
            section_codes = {section.section_code for section in sections}
            stored_script = db.query(ChapterScript).filter(ChapterScript.script_no == script_summary.scriptId).first()
            expected_chapter_id = stored_script.chapter_id if stored_script is not None else None
            expected_scoped_section_code = f"ch{expected_chapter_id}-{script_detail.scriptStructure[0].sectionId}" if expected_chapter_id is not None else script_detail.scriptStructure[0].sectionId

        self.assertEqual(len(lessons), 1)
        self.assertEqual(publish['lessonId'], 'lesson-existing')
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson_name, expected_course_name)
        self.assertEqual(section_codes, {'legacy-section', expected_scoped_section_code})

    def test_publish_reuses_section_pages_by_source_page_and_preserves_parse_fields(self) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        accepted = create_parse_task(parse_payload)
        with session_scope() as db:
            parse_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == accepted.parseId).first()
            self.assertIsNotNone(parse_task)
            lesson = Lesson(
                lesson_no='lesson-page-sync',
                course_id=parse_task.course_id,
                lesson_name='页面同步课程',
                teacher_id=parse_task.teacher_id,
                publish_version=1,
                publish_status='published',
                published_at=None,
            )
            db.add(lesson)
            db.flush()
            unit = LessonUnit(
                lesson_id=lesson.id,
                course_id=parse_task.course_id,
                source_chapter_id=parse_task.chapter_id,
                unit_code='unit-page-sync',
                unit_title='页面同步单元',
                sort_no=0,
            )
            db.add(unit)
            db.flush()
            section = LessonSection(
                lesson_id=lesson.id,
                course_id=parse_task.course_id,
                unit_id=unit.id,
                source_chapter_id=parse_task.chapter_id,
                ppt_asset_id=parse_task.ppt_asset_id,
                section_code='sec001',
                section_name='页面同步章节',
                section_summary='summary',
                student_visible=True,
                sort_no=0,
            )
            db.add(section)
            db.flush()

            _sync_lesson_pages(
                db,
                lesson_id=lesson.id,
                lesson_section=section,
                source_ppt_asset_id=parse_task.ppt_asset_id,
                page_numbers=[1, 2, 3],
                page_mapping_lookup={
                    1: {'pageNo': 1, 'title': '第一页标题', 'previewUrl': '/courseware-previews/rev-a/page-1.png', 'bodyTexts': ['第一页正文'], 'tableTexts': ['第一页表格'], 'notes': '第一页备注'},
                    2: {'pageNo': 2, 'title': '第一页二标题', 'previewUrl': '/courseware-previews/rev-a/page-2.png', 'bodyTexts': ['第二页正文'], 'tableTexts': ['第二页表格'], 'notes': '第二页备注'},
                    3: {'pageNo': 3, 'title': '第一页三标题', 'previewUrl': '/courseware-previews/rev-a/page-3.png', 'bodyTexts': ['第三页正文'], 'tableTexts': ['第三页表格'], 'notes': '第三页备注'},
                },
            )
            db.flush()
            _sync_lesson_pages(
                db,
                lesson_id=lesson.id,
                lesson_section=section,
                source_ppt_asset_id=parse_task.ppt_asset_id,
                page_numbers=[2, 3, 4],
                page_mapping_lookup={
                    2: {'pageNo': 2, 'title': '第二版第2页', 'previewUrl': '/courseware-previews/rev-b/page-2.png', 'bodyTexts': ['第二版正文2'], 'tableTexts': ['第二版表格2'], 'notes': '第二版备注2'},
                    3: {'pageNo': 3, 'title': '第二版第3页', 'previewUrl': '/courseware-previews/rev-b/page-3.png', 'bodyTexts': ['第二版正文3'], 'tableTexts': ['第二版表格3'], 'notes': '第二版备注3'},
                    4: {'pageNo': 4, 'title': '第二版第4页', 'previewUrl': '/courseware-previews/rev-b/page-4.png', 'bodyTexts': ['第二版正文4'], 'tableTexts': ['第二版表格4'], 'notes': '第二版备注4'},
                },
            )
            db.flush()
            pages_payload = [
                {
                    'source_page_no': page.source_page_no,
                    'page_no': page.page_no,
                    'page_title': page.page_title,
                    'page_summary': page.page_summary,
                    'ppt_page_url': page.ppt_page_url,
                    'parsed_content': page.parsed_content,
                }
                for page in db.query(LessonSectionPage)
                .filter(LessonSectionPage.section_id == section.id)
                .order_by(LessonSectionPage.sort_no.asc(), LessonSectionPage.id.asc())
                .all()
            ]

        self.assertEqual([page['source_page_no'] for page in pages_payload], [2, 3, 4])
        self.assertEqual([page['page_no'] for page in pages_payload], [2, 3, 4])
        self.assertEqual([page['page_title'] for page in pages_payload], ['第二版第2页', '第二版第3页', '第二版第4页'])
        self.assertEqual([page['page_summary'] for page in pages_payload], [f'查看《页面同步章节》课件第 {page_no} 页内容。' for page_no in [2, 3, 4]])
        self.assertEqual([page['ppt_page_url'] for page in pages_payload], ['/courseware-previews/rev-b/page-2.png', '/courseware-previews/rev-b/page-3.png', '/courseware-previews/rev-b/page-4.png'])
        self.assertEqual(
            [page['parsed_content'] for page in pages_payload],
            [
                '第二版正文2\n第二版表格2\n第二版备注2',
                '第二版正文3\n第二版表格3\n第二版备注3',
                '第二版正文4\n第二版表格4\n第二版备注4',
            ],
        )

    def test_sync_lesson_pages_fills_preview_url_from_courseware_preview_folder(self) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        accepted = create_parse_task(parse_payload)
        preview_root = Path(self.temp_dir.name) / 'courseware-previews'
        parse_preview_dir = preview_root / accepted.parseId
        parse_preview_dir.mkdir(parents=True, exist_ok=True)
        (parse_preview_dir / 'page-1.png').write_bytes(b'demo-preview')

        with session_scope() as db:
            parse_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == accepted.parseId).first()
            self.assertIsNotNone(parse_task)
            assert parse_task is not None
            lesson = Lesson(
                lesson_no='lesson-preview-sync',
                course_id=parse_task.course_id,
                lesson_name='图片补齐课程',
                teacher_id=parse_task.teacher_id,
                publish_version=1,
                publish_status='published',
                published_at=None,
            )
            db.add(lesson)
            db.flush()
            unit = LessonUnit(
                lesson_id=lesson.id,
                course_id=parse_task.course_id,
                source_chapter_id=parse_task.chapter_id,
                unit_code='unit-preview-sync',
                unit_title='图片补齐单元',
                sort_no=0,
            )
            db.add(unit)
            db.flush()
            section = LessonSection(
                lesson_id=lesson.id,
                course_id=parse_task.course_id,
                unit_id=unit.id,
                source_chapter_id=parse_task.chapter_id,
                ppt_asset_id=parse_task.ppt_asset_id,
                section_code='sec001',
                section_name='图片补齐章节',
                section_summary='summary',
                student_visible=True,
                sort_no=0,
            )
            db.add(section)
            db.flush()

            with patch.object(lesson_service_module, 'COURSEWARE_PREVIEW_ROOT', preview_root):
                _sync_lesson_pages(
                    db,
                    lesson_id=lesson.id,
                    lesson_section=section,
                    source_ppt_asset_id=parse_task.ppt_asset_id,
                    page_numbers=[1],
                    page_mapping_lookup={
                        1: {
                            'pageNo': 1,
                            'title': '第一页',
                            'previewUrl': '',
                            'bodyTexts': ['第一页正文'],
                            'tableTexts': [],
                            'notes': '',
                        }
                    },
                    parse_no=accepted.parseId,
                )
                db.flush()
                page = (
                    db.query(LessonSectionPage)
                    .filter(LessonSectionPage.section_id == section.id)
                    .order_by(LessonSectionPage.page_no.asc(), LessonSectionPage.id.asc())
                    .first()
                )
                page_preview_url = page.ppt_page_url if page is not None else None

        self.assertIsNotNone(page_preview_url)
        self.assertEqual(page_preview_url, f'/courseware-previews/{accepted.parseId}/page-1.png')

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_publish_multiple_courseware_in_same_course_keeps_sections_and_scripts_isolated(self, mock_parse_courseware, mock_build_cir, mock_synthesize_speech, mock_get_voice_cache_dir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / 'voice-cache'
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=1800,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )
        mock_parse_courseware.side_effect = [
            (
                FileInfo(fileName='demo-a.pptx', fileSize=1024, pageCount=1),
                StructurePreview(chapters=[]),
                self._build_extracted_presentation(self._build_slide(1, '课件一首页', '/courseware-previews/cw-a/page-1.png', ['课件一正文'], ['课件一表格'], '课件一备注')),
            ),
            (
                FileInfo(fileName='demo-b.pptx', fileSize=1024, pageCount=1),
                StructurePreview(chapters=[]),
                self._build_extracted_presentation(self._build_slide(1, '课件二首页', '/courseware-previews/cw-b/page-1.png', ['课件二正文'], ['课件二表格'], '课件二备注')),
            ),
        ]
        mock_build_cir.side_effect = [
            CIR(
                coursewareId='cw-course-001-a',
                title='demo-a',
                chapters=[CirChapter(chapterId='course-001-chap-001', chapterName='chapter-a', nodes=[LessonNode(nodeId='node-01-01', nodeName='node-a', pageRefs=[1], keyPoints=['k1'], summary='summary-a')])],
            ),
            CIR(
                coursewareId='cw-course-001-b',
                title='demo-b',
                chapters=[CirChapter(chapterId='course-001-chap-002', chapterName='chapter-b', nodes=[LessonNode(nodeId='node-02-01', nodeName='node-b', pageRefs=[1], keyPoints=['k2'], summary='summary-b')])],
            ),
        ]

        first_script = self._create_script_summary(parse_payload)
        self._persist_script_section_content(first_script.scriptId, {'sec001': 'chapter one script content'})
        first_script_detail = get_script_detail(first_script.scriptId).model_copy(deep=True)
        first_script_detail.scriptStructure[0].content = 'chapter one script content'
        with patch('backend.app.lesson.service.get_script', return_value=first_script_detail):
            first_audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=first_script.scriptId,
                    voiceType='female_standard',
                    audioFormat='mp3',
                    sectionIds=[first_script_detail.scriptStructure[0].sectionId],
                    enc='demo-signature',
                ),
                base_url='http://testserver/',
            )
        publish_lesson(
            PublishRequest(
                coursewareId='cw-course-001-a',
                scriptId=first_script.scriptId,
                audioId=first_audio['audioId'],
                publisherId='teacher-demo',
                enc='demo-signature',
            )
        )

        second_payload = parse_payload.model_copy(update={'fileUrl': 'file:///tmp/demo-b.pptx'})
        second_script = self._create_script_summary(second_payload)
        self._reassign_script_to_new_chapter(second_script.scriptId, 'chapter-b')
        self._persist_script_section_content(second_script.scriptId, {'sec001': 'chapter two script content'})
        second_script_detail = get_script_detail(second_script.scriptId).model_copy(deep=True)
        second_script_detail.scriptStructure[0].content = 'chapter two script content'
        with patch('backend.app.lesson.service.get_script', return_value=second_script_detail):
            second_audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=second_script.scriptId,
                    voiceType='female_standard',
                    audioFormat='mp3',
                    sectionIds=[second_script_detail.scriptStructure[0].sectionId],
                    enc='demo-signature',
                ),
                base_url='http://testserver/',
            )
        publish = publish_lesson(
            PublishRequest(
                coursewareId='cw-course-001-b',
                scriptId=second_script.scriptId,
                audioId=second_audio['audioId'],
                publisherId='teacher-demo',
                enc='demo-signature',
            )
        )

        lesson_service_module._LESSON_PACKAGES.clear()
        play = play_lesson(
            PlayRequest(
                lessonId=publish['lessonId'],
                userId='student-demo',
                resumeContext=None,
                enc='demo-signature',
            )
        )

        with session_scope() as db:
            lessons = db.query(Lesson).all()
            lesson = db.query(Lesson).filter(Lesson.lesson_no == publish['lessonId']).first()
            self.assertIsNotNone(lesson)
            sections = (
                db.query(LessonSection)
                .filter(LessonSection.lesson_id == lesson.id)
                .order_by(LessonSection.source_chapter_id.asc(), LessonSection.id.asc())
                .all()
            )
            detail_by_section_id = {
                str(section.id): get_section_detail(db, student_id=None, lesson_identifier=publish['lessonId'], section_identifier=str(section.id))
                for section in sections
            }
            section_rows = [
                {
                    'id': str(section.id),
                    'source_chapter_id': section.source_chapter_id,
                    'section_code': section.section_code,
                    'script_id': section.script_id,
                    'script_no': section.script.script_no if section.script else '',
                }
                for section in sections
            ]

        self.assertEqual(len(lessons), 1)
        self.assertEqual(len(section_rows), 2)
        self.assertEqual(len({section['section_code'] for section in section_rows}), 2)
        self.assertTrue(all(section['section_code'].startswith(f"ch{section['source_chapter_id']}-") for section in section_rows))
        self.assertEqual(len({section['script_id'] for section in section_rows}), 2)
        self.assertEqual(len({item['sectionId'] for item in play['scriptRefs']}), 2)
        self.assertEqual({item['sectionId'] for item in play['scriptRefs']}, {section['id'] for section in section_rows})
        self.assertEqual(
            {(item['sectionId'], item['scriptId']) for item in play['scriptRefs']},
            {(section['id'], section['script_no']) for section in section_rows},
        )
        self.assertEqual({detail['scriptContent'] for detail in detail_by_section_id.values()}, {'chapter one script content', 'chapter two script content'})

    def _create_script_summary(self, parse_payload: ParseRequest):
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        return generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening=None,
                enc='demo-signature',
            )
        )

    def test_student_detail_reads_full_script_content_from_scoped_lesson_section_code(self) -> None:
        long_script = "这是一个用于验证学生端全文消费能力的超长讲稿。" * 20

        with session_scope() as db:
            course = Course(course_code="COURSE-LONG-SCRIPT", course_name="测试课程", school_id=1)
            chapter = CourseChapter(course=course, chapter_code="CH-LONG-001", chapter_name="第一章", sort_no=1)
            db.add_all([course, chapter])
            db.flush()
            course_id = course.id
            chapter_id = chapter.id
            ppt_asset = ChapterPptAsset(
                course_id=course_id,
                chapter_id=chapter_id,
                uploader_id=1,
                file_name="demo.pptx",
                file_type="pptx",
                file_url="/uploads/demo.pptx",
                upload_status="parsed",
                version_no=1,
            )
            db.add(ppt_asset)
            db.flush()
            parse_task = ChapterParseTask(
                parse_no="parse-long-script",
                course_id=course_id,
                chapter_id=chapter_id,
                ppt_asset_id=ppt_asset.id,
                teacher_id=1,
                task_status="completed",
            )
            script = ChapterScript(
                course_id=course_id,
                chapter=chapter,
                parse_task=parse_task,
                teacher_id=1,
                script_no="script-long-content",
                teaching_style="standard",
                speech_speed="normal",
                script_status="published",
            )
            db.add_all([parse_task, script])
            db.flush()

            db.add(
                ChapterScriptSection(
                    script_id=script.id,
                    section_code="sec001",
                    section_name="长讲稿章节",
                    section_content=long_script,
                    sort_no=0,
                )
            )

            lesson = Lesson(
                lesson_no="lesson-long-script",
                course_id=course.id,
                teacher_id=1,
                lesson_name=course.course_name,
                publish_status="published",
                publish_version=1,
            )
            db.add(lesson)
            db.flush()

            unit = LessonUnit(
                lesson_id=lesson.id,
                course_id=course_id,
                source_chapter_id=chapter_id,
                unit_code="unit001",
                unit_title="第一章",
                sort_no=0,
            )
            db.add(unit)
            db.flush()

            db.add(
                LessonSection(
                    lesson_id=lesson.id,
                    course_id=course_id,
                    unit_id=unit.id,
                    source_chapter_id=chapter_id,
                    script_id=script.id,
                    section_code=f"ch{chapter_id}-sec001",
                    section_name="长讲稿章节",
                    section_summary=long_script[:120],
                    student_visible=True,
                    sort_no=0,
                )
            )
            db.commit()

        with session_scope() as db:
            detail = get_section_detail(
                db=db,
                student_id=None,
                lesson_identifier="lesson-long-script",
                section_identifier=f"ch{chapter_id}-sec001",
            )

        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["scriptContent"], long_script)

    def _build_slide(
        self,
        slide_number: int,
        title: str,
        preview_url: str,
        body_texts: list[str] | None = None,
        table_texts: list[str] | None = None,
        notes: str | None = None,
    ) -> ExtractedSlide:
        return ExtractedSlide(
            slideNumber=slide_number,
            title=title,
            bodyTexts=body_texts or [],
            tableTexts=table_texts or [],
            notes=notes,
            previewUrl=preview_url,
        )

    def _build_extracted_presentation(self, *slides: ExtractedSlide) -> ExtractedPresentation:
        return ExtractedPresentation(slides=list(slides))

    def _persist_script_section_content(self, script_id: str, content_by_section: dict[str, str]) -> None:
        with session_scope() as db:
            sections = (
                db.query(ChapterScriptSection)
                .join(ChapterScript, ChapterScriptSection.script_id == ChapterScript.id)
                .filter(ChapterScript.script_no == script_id)
                .order_by(ChapterScriptSection.sort_no.asc(), ChapterScriptSection.id.asc())
                .all()
            )
            for section in sections:
                content = content_by_section.get(section.section_code)
                if content is None:
                    continue
                section.section_content = content

    def _reassign_script_to_new_chapter(self, script_id: str, chapter_name: str) -> None:
        with session_scope() as db:
            script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
            assert script is not None
            parse_task = script.parse_task
            assert parse_task is not None
            next_sort_no = max(
                [value for (value,) in db.query(CourseChapter.sort_no).filter(CourseChapter.course_id == script.course_id).all()],
                default=0,
            ) + 1
            chapter = CourseChapter(
                course_id=script.course_id,
                chapter_code=f'test-chapter-{next_sort_no}',
                chapter_name=chapter_name,
                chapter_type='chapter',
                chapter_level=1,
                sort_no=next_sort_no,
                status='draft',
            )
            db.add(chapter)
            db.flush()

            script.chapter_id = chapter.id
            parse_task.chapter_id = chapter.id
            if parse_task.ppt_asset is not None:
                parse_task.ppt_asset.chapter_id = chapter.id
            if parse_task.parse_result is not None:
                parse_task.parse_result.chapter_id = chapter.id
