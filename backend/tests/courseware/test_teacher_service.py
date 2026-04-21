import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.cir.schemas import CIR
from backend.app.common.db import configure_database_url, reset_database_url, session_scope
from backend.app.courseware.teacher_service import EXAMPLES_ROOT, run_teacher_parse_task, upload_parse
from backend.app.parser.schemas import ExtractedPresentation, ExtractedSlide, FileInfo, StructurePreview
from backend.chaoxing_db.models import ChapterParseResult, ChapterParseTask, ChapterPptAsset, Course, CourseChapter, Lesson, LessonSection, LessonSectionPage, LessonUnit, School, User


class TeacherServiceTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    uploaded_files: list[Path]

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.uploaded_files = []
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'teacher-service-test.db'}")
        self._seed_course_and_lesson()

    def tearDown(self) -> None:
        for file_path in self.uploaded_files:
            if file_path.exists():
                file_path.unlink()
        reset_database_url()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    @patch("backend.app.courseware.teacher_service.execute_parse_pipeline")
    def test_run_teacher_parse_task_writes_preview_urls_to_parse_result_and_lesson_pages(self, mock_execute_parse_pipeline) -> None:
        mock_execute_parse_pipeline.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=2048, pageCount=2),
            StructurePreview(chapters=[]),
            ExtractedPresentation(
                sourceType="pptx",
                slides=[
                    ExtractedSlide(
                        slideNumber=1,
                        title="第一页",
                        bodyTexts=["第一页正文"],
                        tableTexts=[],
                        notes=None,
                        previewUrl="/courseware-previews/parse-demo/page-1.png",
                    ),
                    ExtractedSlide(
                        slideNumber=2,
                        title="第二页",
                        bodyTexts=["第二页正文"],
                        tableTexts=[],
                        notes=None,
                        previewUrl="/courseware-previews/parse-demo/page-2.png",
                    ),
                ],
            ),
            CIR(coursewareId="cw-course-001", title="demo", chapters=[]),
        )

        file_content = base64.b64encode(b"fake pptx content").decode()
        with session_scope() as db:
            teacher = db.query(User).filter(User.user_no == "teacher-001").first()
            chapter = db.query(CourseChapter).filter(CourseChapter.chapter_name == "压杆稳定").order_by(CourseChapter.id.asc()).first()
            assert teacher is not None
            assert chapter is not None
            accepted = upload_parse(
                db,
                teacher,
                "course-001",
                "demo.pptx",
                file_content,
                chapter_name="压杆稳定",
                base_url="http://testserver/",
                target_chapter_id=chapter.id,
            )

        parse_id = accepted["parseId"]
        uploaded_file = EXAMPLES_ROOT / f"{parse_id}-demo.pptx"
        self.uploaded_files.append(uploaded_file)

        self.assertTrue(uploaded_file.exists())

        run_teacher_parse_task(parse_id)

        with session_scope() as db:
            parse_result = (
                db.query(ChapterParseResult)
                .join(ChapterParseTask, ChapterParseResult.parse_task_id == ChapterParseTask.id)
                .filter(ChapterParseTask.parse_no == parse_id)
                .first()
            )
            task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == parse_id).first()
            asset = db.query(ChapterPptAsset).join(ChapterParseTask, ChapterParseTask.ppt_asset_id == ChapterPptAsset.id).filter(ChapterParseTask.parse_no == parse_id).first()
            pages = db.query(LessonSectionPage).order_by(LessonSectionPage.page_no.asc(), LessonSectionPage.id.asc()).all()
            section = db.query(LessonSection).filter(LessonSection.section_code == "section-001").first()
            page_mapping = list(parse_result.page_mapping or []) if parse_result else []
            parse_result_id = parse_result.id if parse_result else None
            task_status = task.task_status if task else None
            asset_page_count = asset.page_count if asset else None
            asset_status = asset.upload_status if asset else None
            asset_id = asset.id if asset else None
            section_parse_result_id = section.parse_result_id if section else None
            section_ppt_asset_id = section.ppt_asset_id if section else None
            page_payloads = [(page.ppt_page_url, page.parsed_content) for page in pages]

        self.assertIsNotNone(parse_result)
        self.assertEqual(page_mapping[0]["previewUrl"], "/courseware-previews/parse-demo/page-1.png")
        self.assertIsNotNone(section)
        self.assertEqual(task_status, "completed")
        self.assertEqual(asset_page_count, 2)
        self.assertEqual(asset_status, "parsed")
        self.assertEqual(section_parse_result_id, parse_result_id)
        self.assertEqual(section_ppt_asset_id, asset_id)
        self.assertEqual(len(page_payloads), 2)
        self.assertEqual(page_payloads[0][0], "/courseware-previews/parse-demo/page-1.png")
        self.assertEqual(page_payloads[0][1], "第一页正文")
        self.assertEqual(page_payloads[1][0], "/courseware-previews/parse-demo/page-2.png")

    def test_upload_parse_uses_custom_chapter_name_and_creates_missing_chapter(self) -> None:
        file_content = base64.b64encode(b"fake pptx content").decode()
        with session_scope() as db:
            teacher = db.query(User).filter(User.user_no == "teacher-001").first()
            assert teacher is not None
            accepted = upload_parse(
                db,
                teacher,
                "course-001",
                "01总论.pptx",
                file_content,
                chapter_name="课程导学",
                base_url="http://testserver/",
            )
            task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == accepted["parseId"]).first()
            self.assertIsNotNone(task)
            self.assertEqual(accepted["chapterName"], "课程导学")
            self.assertIsNotNone(task.chapter)
            self.assertEqual(task.chapter.chapter_name, "课程导学")
            self.assertEqual(task.chapter.chapter_code.startswith("chapter-"), True)

    def test_upload_parse_with_same_chapter_name_creates_new_course_chapter_by_default(self) -> None:
        file_content = base64.b64encode(b"fake pptx content").decode()
        with session_scope() as db:
            teacher = db.query(User).filter(User.user_no == "teacher-001").first()
            assert teacher is not None
            first = upload_parse(
                db,
                teacher,
                "course-001",
                "01总论.pptx",
                file_content,
                chapter_name="课程导学",
                base_url="http://testserver/",
            )
            second = upload_parse(
                db,
                teacher,
                "course-001",
                "02绪论.pptx",
                file_content,
                chapter_name="课程导学",
                base_url="http://testserver/",
            )
            first_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == first["parseId"]).first()
            second_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == second["parseId"]).first()
            first_task_id = first_task.chapter_id if first_task is not None else None
            second_task_id = second_task.chapter_id if second_task is not None else None
            chapter_names = [
                chapter.chapter_name
                for chapter in db.query(CourseChapter)
                .filter(CourseChapter.course_id == first_task.course_id)
                .order_by(CourseChapter.id.asc())
                .all()
            ]

        self.assertIsNotNone(first_task)
        self.assertIsNotNone(second_task)
        self.assertNotEqual(first_task_id, second_task_id)
        self.assertEqual(chapter_names.count("课程导学"), 2)

    def _seed_course_and_lesson(self) -> None:
        with session_scope() as db:
            school = School(school_code="school-001", school_name="测试学校")
            db.add(school)
            db.flush()

            teacher = User(user_no="teacher-001", user_name="测试教师", role="teacher", school_id=school.id, auth_token="token-001")
            db.add(teacher)
            db.flush()

            course = Course(course_code="course-001", course_name="材料力学智慧课程", school_id=school.id, created_by=teacher.id)
            db.add(course)
            db.flush()

            chapter = CourseChapter(
                course_id=course.id,
                chapter_code="chapter-001",
                chapter_name="压杆稳定",
                chapter_type="chapter",
                chapter_level=1,
                sort_no=1,
            )
            db.add(chapter)
            db.flush()

            lesson = Lesson(
                lesson_no="lesson-001",
                course_id=course.id,
                lesson_name="材料力学智慧课程",
                teacher_id=teacher.id,
                publish_version=1,
                publish_status="published",
            )
            db.add(lesson)
            db.flush()

            unit = LessonUnit(
                lesson_id=lesson.id,
                course_id=course.id,
                source_chapter_id=chapter.id,
                unit_code="unit-001",
                unit_title="第一单元",
                sort_no=1,
            )
            db.add(unit)
            db.flush()

            section = LessonSection(
                lesson_id=lesson.id,
                course_id=course.id,
                unit_id=unit.id,
                source_chapter_id=chapter.id,
                section_code="section-001",
                section_name="压杆稳定",
                sort_no=1,
            )
            db.add(section)
