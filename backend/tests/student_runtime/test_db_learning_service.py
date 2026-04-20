import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.cir.schemas import CIR, CirChapter, LessonNode
from backend.app.common.db import configure_database_url, reset_database_url, session_scope
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import clear_parse_tasks, create_parse_task, run_parse_task
from backend.app.lesson.schemas import GenerateAudioRequest, PublishRequest
from backend.app.lesson.service import clear_lessons, generate_audio, publish_lesson
from backend.app.lesson.tts_client import TtsSynthesisResult
from backend.app.parser.schemas import FileInfo, StructurePreview
from backend.app.script.schemas import GenerateScriptRequest
from backend.app.script.service import clear_scripts, generate_script, get_script as get_script_detail
from backend.app.student_runtime.db_learning_service import get_db_progress_state, get_section_detail, get_student_lessons_from_db, mark_page_read
from backend.chaoxing_db.models import ChapterScript, ChapterScriptSection, LessonSection, LessonSectionPage, StudentPageProgress, User


class StudentDbLearningServiceTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'student-runtime-test.db'}")
        clear_scripts()
        clear_parse_tasks()
        clear_lessons()

    def tearDown(self) -> None:
        clear_scripts()
        clear_parse_tasks()
        clear_lessons()
        reset_database_url()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_published_lesson_is_visible_to_student_runtime(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        assert self.temp_dir is not None
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / "voice-cache"
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b"ID3demo-audio",
            duration_ms=2200,
            reqid="req-001",
            log_id="log-001",
            voice_type="volcano-voice",
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId="cw-course-001",
            title="demo",
            chapters=[
                CirChapter(
                    chapterId="course-001-chap-001",
                    chapterName="chapter",
                    nodes=[
                        LessonNode(nodeId="node-01-01", nodeName="node-1", pageRefs=[1, 2], keyPoints=["k1"], summary="summary-1"),
                        LessonNode(nodeId="node-01-02", nodeName="node-2", pageRefs=[3], keyPoints=["k2"], summary="summary-2"),
                    ],
                )
            ],
        )
        parse_payload = ParseRequest(
            schoolId="school-001",
            userId="teacher-001",
            courseId="course-001",
            fileType="ppt",
            fileUrl="file:///tmp/demo.pptx",
            isExtractKeyPoint=True,
            enc="demo-signature",
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        script_summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle="standard",
                speechSpeed="normal",
                customOpening=None,
                enc="demo-signature",
            )
        )
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        for index, section in enumerate(script_detail.scriptStructure[:2], start=1):
            section.content = f"student runtime short section {index}"
        section_ids = [section.sectionId for section in script_detail.scriptStructure[:2]]

        with session_scope() as db:
            persisted_sections = (
                db.query(ChapterScriptSection)
                .join(ChapterScript, ChapterScriptSection.script_id == ChapterScript.id)
                .filter(ChapterScript.script_no == script_summary.scriptId)
                .order_by(ChapterScriptSection.sort_no.asc(), ChapterScriptSection.id.asc())
                .all()
            )
            for index, section in enumerate(persisted_sections[:2], start=1):
                section.section_content = f"student runtime short section {index}"

        with patch("backend.app.lesson.service.get_script", return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=script_summary.scriptId,
                    voiceType="female_standard",
                    audioFormat="mp3",
                    sectionIds=section_ids,
                    enc="demo-signature",
                ),
                base_url="http://testserver/",
            )
            publish = publish_lesson(
                PublishRequest(
                    coursewareId="cw-course-001",
                    scriptId=script_summary.scriptId,
                    audioId=audio["audioId"],
                    publisherId="teacher-demo",
                    enc="demo-signature",
                )
            )

        with session_scope() as db:
            lessons = get_student_lessons_from_db(db=db, student_id=None)
        lesson = next((item for item in lessons if item["lessonId"] == publish["lessonId"]), None)

        self.assertIsNotNone(lesson)
        assert lesson is not None
        self.assertTrue(lesson["audioUrl"].startswith("/cache/voice/") or lesson["audioUrl"].startswith("http://testserver/cache/voice/"))
        self.assertEqual(lesson["audioStatus"], "published")
        self.assertEqual(len(lesson["units"]), 1)
        self.assertEqual(len(lesson["units"][0]["chapters"]), 2)

        with session_scope() as db:
            progress = get_db_progress_state(db=db, student_id="missing-student", lesson_identifier=publish["lessonId"])
            detail = get_section_detail(
                db=db,
                student_id="missing-student",
                lesson_identifier=publish["lessonId"],
                section_identifier=lesson["units"][0]["chapters"][0]["sectionId"],
            )

        self.assertIsNotNone(progress)
        self.assertIsNotNone(detail)
        assert progress is not None
        assert detail is not None
        self.assertEqual(progress["progressPercent"], 0)
        self.assertEqual(progress["sectionId"], lesson["units"][0]["chapters"][0]["sectionId"])
        self.assertNotEqual(detail["aiGuideContent"], "summary-1\n\nsummary-2")
        self.assertEqual(detail["scriptContent"], "student runtime short section 1")
        self.assertTrue(detail["audioUrl"].startswith("/cache/voice/") or detail["audioUrl"].startswith("http://testserver/cache/voice/"))
        self.assertEqual(detail["audioStatus"], "published")
        self.assertEqual(detail["pages"][0]["imageUrl"], "")

    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_get_section_detail_keeps_real_preview_payload(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        assert self.temp_dir is not None
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / "voice-cache"
        preview_root = Path(self.temp_dir.name) / "lesson-previews"
        preview_root.mkdir(parents=True, exist_ok=True)
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b"ID3demo-audio",
            duration_ms=2200,
            reqid="req-001",
            log_id="log-001",
            voice_type="volcano-voice",
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId="cw-course-001",
            title="demo",
            chapters=[
                CirChapter(
                    chapterId="course-001-chap-001",
                    chapterName="chapter",
                    nodes=[
                        LessonNode(nodeId="node-01-01", nodeName="node-1", pageRefs=[1], keyPoints=["k1"], summary="summary-1"),
                    ],
                )
            ],
        )
        parse_payload = ParseRequest(
            schoolId="school-001",
            userId="teacher-001",
            courseId="course-001",
            fileType="ppt",
            fileUrl="file:///tmp/demo.pptx",
            isExtractKeyPoint=True,
            enc="demo-signature",
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        script_summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle="standard",
                speechSpeed="normal",
                customOpening=None,
                enc="demo-signature",
            )
        )
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        script_detail.scriptStructure[0].content = "student runtime short section 1"

        with patch("backend.app.lesson.service.get_script", return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=script_summary.scriptId,
                    voiceType="female_standard",
                    audioFormat="mp3",
                    sectionIds=[script_detail.scriptStructure[0].sectionId],
                    enc="demo-signature",
                ),
                base_url="http://testserver/",
            )
            publish = publish_lesson(
                PublishRequest(
                    coursewareId="cw-course-001",
                    scriptId=script_summary.scriptId,
                    audioId=audio["audioId"],
                    publisherId="teacher-demo",
                    enc="demo-signature",
                )
            )

        with session_scope() as db:
            section = (
                db.query(LessonSection)
                .filter(LessonSection.lesson.has(lesson_no=publish["lessonId"]))
                .order_by(LessonSection.id.asc())
                .first()
            )
            assert section is not None
            page = (
                db.query(LessonSectionPage)
                .filter(LessonSectionPage.section_id == section.id)
                .order_by(LessonSectionPage.page_no.asc(), LessonSectionPage.id.asc())
                .first()
            )
            assert page is not None
            page.ppt_page_url = "/courseware-previews/parse-pdf/page-1.png"
            page.page_summary = "真实 PDF 页摘要"
            page.parsed_content = "真实 PDF 页正文"
            section_id = section.id
            source_chapter_id = section.source_chapter_id
            db.commit()

        preview_dir = Path(self.temp_dir.name) / "lesson-previews" / f"chapter-{source_chapter_id}"
        preview_dir.mkdir(parents=True, exist_ok=True)
        (preview_dir / "page-1.png").write_bytes(b"demo-preview")

        with patch("backend.app.student_runtime.db_learning_service.PREVIEW_ROOT", preview_root):
            with session_scope() as db:
                detail = get_section_detail(
                    db=db,
                    student_id="missing-student",
                    lesson_identifier=publish["lessonId"],
                    section_identifier=str(section_id),
                )

        assert detail is not None
        self.assertEqual(detail["audioStatus"], "published")
        self.assertEqual(detail["pages"][0]["imageUrl"], "/courseware-previews/parse-pdf/page-1.png")
        self.assertEqual(detail["pages"][0]["parsedContent"], "真实 PDF 页正文")

    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_student_runtime_falls_back_to_chapter_audio_asset(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        assert self.temp_dir is not None
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / "voice-cache"
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b"ID3demo-audio",
            duration_ms=2200,
            reqid="req-001",
            log_id="log-001",
            voice_type="volcano-voice",
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId="cw-course-001",
            title="demo",
            chapters=[
                CirChapter(
                    chapterId="course-001-chap-001",
                    chapterName="chapter",
                    nodes=[
                        LessonNode(nodeId="node-01-01", nodeName="node-1", pageRefs=[1], keyPoints=["k1"], summary="summary-1"),
                    ],
                )
            ],
        )
        parse_payload = ParseRequest(
            schoolId="school-001",
            userId="teacher-001",
            courseId="course-001",
            fileType="ppt",
            fileUrl="file:///tmp/demo.pptx",
            isExtractKeyPoint=True,
            enc="demo-signature",
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        script_summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle="standard",
                speechSpeed="normal",
                customOpening=None,
                enc="demo-signature",
            )
        )
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        script_detail.scriptStructure[0].content = "student runtime short section 1"

        with patch("backend.app.lesson.service.get_script", return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=script_summary.scriptId,
                    voiceType="female_standard",
                    audioFormat="mp3",
                    sectionIds=[script_detail.scriptStructure[0].sectionId],
                    enc="demo-signature",
                ),
                base_url="http://testserver/",
            )
            publish = publish_lesson(
                PublishRequest(
                    coursewareId="cw-course-001",
                    scriptId=script_summary.scriptId,
                    audioId=audio["audioId"],
                    publisherId="teacher-demo",
                    enc="demo-signature",
                )
            )

        with session_scope() as db:
            section = (
                db.query(LessonSection)
                .filter(LessonSection.lesson.has(lesson_no=publish["lessonId"]))
                .order_by(LessonSection.id.asc())
                .first()
            )
            assert section is not None
            assert section.audio_asset is not None
            section_id = section.id
            section.section_audio_asset_id = None
            section.audio_asset.audio_url = "http://testserver/cache/voice/legacy-fallback.mp3"
            section.audio_asset.status = "published"
            db.commit()

        with session_scope() as db:
            lessons = get_student_lessons_from_db(db=db, student_id=None)
            detail = get_section_detail(
                db=db,
                student_id="missing-student",
                lesson_identifier=publish["lessonId"],
                section_identifier=str(section_id),
            )

        lesson = next((item for item in lessons if item["lessonId"] == publish["lessonId"]), None)
        self.assertIsNotNone(lesson)
        self.assertIsNotNone(detail)
        assert lesson is not None
        assert detail is not None
        self.assertEqual(lesson["audioUrl"], "/cache/voice/legacy-fallback.mp3")
        self.assertEqual(lesson["audioStatus"], "published")
        self.assertEqual(detail["audioUrl"], "/cache/voice/legacy-fallback.mp3")
        self.assertEqual(detail["audioStatus"], "published")

    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_mark_page_read_falls_back_to_page_no_for_string_page_id(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        assert self.temp_dir is not None
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / "voice-cache"
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b"ID3demo-audio",
            duration_ms=2200,
            reqid="req-001",
            log_id="log-001",
            voice_type="volcano-voice",
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId="cw-course-001",
            title="demo",
            chapters=[
                CirChapter(
                    chapterId="course-001-chap-001",
                    chapterName="chapter",
                    nodes=[
                        LessonNode(nodeId="node-01-01", nodeName="node-1", pageRefs=[1], keyPoints=["k1"], summary="summary-1"),
                    ],
                )
            ],
        )
        parse_payload = ParseRequest(
            schoolId="school-001",
            userId="teacher-001",
            courseId="course-001",
            fileType="ppt",
            fileUrl="file:///tmp/demo.pptx",
            isExtractKeyPoint=True,
            enc="demo-signature",
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        script_summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle="standard",
                speechSpeed="normal",
                customOpening=None,
                enc="demo-signature",
            )
        )
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        script_detail.scriptStructure[0].content = "student runtime short section 1"

        with patch("backend.app.lesson.service.get_script", return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=script_summary.scriptId,
                    voiceType="female_standard",
                    audioFormat="mp3",
                    sectionIds=[script_detail.scriptStructure[0].sectionId],
                    enc="demo-signature",
                ),
                base_url="http://testserver/",
            )
            publish = publish_lesson(
                PublishRequest(
                    coursewareId="cw-course-001",
                    scriptId=script_summary.scriptId,
                    audioId=audio["audioId"],
                    publisherId="teacher-demo",
                    enc="demo-signature",
                )
            )

        with session_scope() as db:
            teacher = db.query(User).filter(User.user_no == "teacher-001").first()
            assert teacher is not None
            student = User(user_no="student-001", user_name="学生一", role="student", school_id=teacher.school_id)
            db.add(student)
            db.flush()
            section = (
                db.query(LessonSection)
                .filter(LessonSection.lesson.has(lesson_no=publish["lessonId"]))
                .order_by(LessonSection.id.asc())
                .first()
            )
            assert section is not None
            page = (
                db.query(LessonSectionPage)
                .filter(LessonSectionPage.section_id == section.id)
                .order_by(LessonSectionPage.page_no.asc(), LessonSectionPage.id.asc())
                .first()
            )
            assert page is not None
            student_no = student.user_no
            section_id = section.id
            page_id = page.id
            page_no = page.page_no
            db.commit()

        with session_scope() as db:
            result = mark_page_read(
                db=db,
                student_id=student_no,
                lesson_identifier=publish["lessonId"],
                section_identifier=str(section_id),
                lesson_page_id=f"{publish['lessonId']}-P{page_no}",
                page_no=page_no,
            )
            progress_row = (
                db.query(StudentPageProgress)
                .filter(StudentPageProgress.lesson_page_id == page_id)
                .order_by(StudentPageProgress.id.asc())
                .first()
            )
            progress_page_no = progress_row.page_no if progress_row is not None else None
            progress_is_completed = progress_row.is_completed if progress_row is not None else None

        self.assertIsNotNone(result)
        self.assertIsNotNone(progress_row)
        assert result is not None
        self.assertEqual(result["pageNo"], page_no)
        self.assertEqual(progress_page_no, page_no)
        self.assertTrue(progress_is_completed)
