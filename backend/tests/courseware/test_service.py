import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.cir.schemas import CIR
from backend.app.common.db import configure_database_url, reset_database_url, session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import clear_parse_tasks, create_parse_task, get_parse_task, run_parse_task
from backend.app.parser.schemas import FileInfo, ParseTaskStatus, StructurePreview
from backend.chaoxing_db.models import ChapterParseResult, ChapterParseTask


class CoursewareServiceTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    payload: ParseRequest | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'courseware-test.db'}")
        clear_parse_tasks()
        self.payload = ParseRequest(
            schoolId="school-001",
            userId="teacher-001",
            courseId="course-001",
            fileType="ppt",
            fileUrl="file:///tmp/demo.pptx",
            isExtractKeyPoint=True,
            enc="demo-signature",
        )

    def tearDown(self) -> None:
        clear_parse_tasks()
        reset_database_url()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_create_parse_task_returns_processing_before_runner_executes(self, mock_parse_courseware, mock_build_cir) -> None:
        payload = self.payload
        assert payload is not None
        file_info = FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8)
        preview = StructurePreview(chapters=[])
        cir = CIR(coursewareId="cw-course-001", title="demo", chapters=[])
        mock_parse_courseware.return_value = (file_info, preview)
        mock_build_cir.return_value = cir

        accepted = create_parse_task(payload, request_id="req-001")
        with session_scope() as db:
            stored_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == accepted.parseId).first()
            stored_task_status = stored_task.task_status if stored_task else None

        self.assertIsNotNone(stored_task)
        self.assertEqual(accepted.taskStatus, ParseTaskStatus.PROCESSING)
        self.assertEqual(stored_task_status, ParseTaskStatus.PROCESSING.value)

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_run_parse_task_completes_task_and_query(self, mock_parse_courseware, mock_build_cir) -> None:
        payload = self.payload
        assert payload is not None
        file_info = FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8)
        preview = StructurePreview(chapters=[])
        cir = CIR(coursewareId="cw-course-001", title="demo", chapters=[])
        mock_parse_courseware.return_value = (file_info, preview)
        mock_build_cir.return_value = cir

        accepted = create_parse_task(payload, request_id="req-001")

        run_parse_task(accepted.parseId, payload)

        with session_scope() as db:
            stored_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == accepted.parseId).first()
            stored_result = (
                db.query(ChapterParseResult)
                .join(ChapterParseTask, ChapterParseResult.parse_task_id == ChapterParseTask.id)
                .filter(ChapterParseTask.parse_no == accepted.parseId)
                .first()
            )
            stored_task_status = stored_task.task_status if stored_task else None
        queried = get_parse_task(accepted.parseId)

        self.assertIsNotNone(stored_task)
        self.assertIsNotNone(stored_result)
        self.assertEqual(stored_task_status, ParseTaskStatus.COMPLETED.value)
        self.assertEqual(queried.parseId, accepted.parseId)
        self.assertEqual(queried.taskStatus, ParseTaskStatus.COMPLETED)
        self.assertIsNotNone(queried.cir)
        assert queried.cir is not None
        self.assertEqual(queried.cir.coursewareId, "cw-course-001")

    @patch("backend.app.courseware.service.parse_courseware")
    def test_create_parse_task_records_failed_state(self, mock_parse_courseware) -> None:
        payload = self.payload
        assert payload is not None
        mock_parse_courseware.side_effect = ApiError(code=400, msg="当前 demo 仅支持 .pptx 文件解析", status_code=400)

        accepted = create_parse_task(payload)

        run_parse_task(accepted.parseId, payload)

        with session_scope() as db:
            stored_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == accepted.parseId).first()
            stored_task_status = stored_task.task_status if stored_task else None
        queried = get_parse_task(accepted.parseId)

        self.assertIsNotNone(stored_task)
        self.assertEqual(stored_task_status, ParseTaskStatus.FAILED.value)
        self.assertEqual(queried.taskStatus, ParseTaskStatus.FAILED)
        self.assertEqual(queried.errorMessage, "当前 demo 仅支持 .pptx 文件解析")

    def test_get_parse_task_raises_for_missing_task(self) -> None:
        with self.assertRaises(ApiError) as context:
            get_parse_task("parse-missing")

        self.assertEqual(context.exception.status_code, 404)
