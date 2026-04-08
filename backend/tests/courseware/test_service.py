import unittest
import tempfile
from unittest.mock import patch

from backend.app.cir.schemas import CIR
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import create_parse_task, get_parse_task
from backend.app.parser.schemas import FileInfo, ParseTaskStatus, StructurePreview
from backend.app.tasks.repository import configure_task_storage, get_task_log_path, reset_task_storage
from backend.app.tasks.service import clear_tasks, get_task


class CoursewareServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_task_storage(self.temp_dir.name)
        clear_tasks()
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
        clear_tasks()
        reset_task_storage()
        self.temp_dir.cleanup()

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_create_parse_task_stores_completed_result_in_tasks(self, mock_parse_courseware, mock_build_cir) -> None:
        file_info = FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8)
        preview = StructurePreview(chapters=[])
        cir = CIR(coursewareId="cw-course-001", title="demo", chapters=[])
        mock_parse_courseware.return_value = (file_info, preview)
        mock_build_cir.return_value = cir

        accepted = create_parse_task(self.payload, request_id="req-001")
        stored_task = get_task(accepted.parseId)
        queried = get_parse_task(accepted.parseId)

        self.assertIsNotNone(stored_task)
        self.assertEqual(accepted.taskStatus, ParseTaskStatus.COMPLETED)
        self.assertEqual(stored_task.status, ParseTaskStatus.COMPLETED.value)
        self.assertEqual(stored_task.result["parseId"], accepted.parseId)
        self.assertEqual(stored_task.requestId, "req-001")
        self.assertEqual(queried.taskStatus, ParseTaskStatus.COMPLETED)
        self.assertEqual(queried.cir.coursewareId, "cw-course-001")
        self.assertTrue(get_task_log_path(accepted.parseId).exists())

    @patch("backend.app.courseware.service.parse_courseware")
    def test_create_parse_task_records_failed_state(self, mock_parse_courseware) -> None:
        mock_parse_courseware.side_effect = ApiError(code=400, msg="当前 demo 仅支持 .pptx 文件解析", status_code=400)

        with self.assertRaises(ApiError) as context:
            create_parse_task(self.payload)

        parse_id = context.exception.data["parseId"]
        stored_task = get_task(parse_id)
        queried = get_parse_task(parse_id)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIsNotNone(stored_task)
        self.assertEqual(stored_task.status, ParseTaskStatus.FAILED.value)
        self.assertEqual(queried.taskStatus, ParseTaskStatus.FAILED)
        self.assertEqual(queried.errorMessage, "当前 demo 仅支持 .pptx 文件解析")
        self.assertTrue(get_task_log_path(parse_id).exists())

    def test_get_parse_task_raises_for_missing_task(self) -> None:
        with self.assertRaises(ApiError) as context:
            get_parse_task("parse-missing")

        self.assertEqual(context.exception.status_code, 404)
