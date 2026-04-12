import unittest
import tempfile
from pathlib import Path

from backend.app.common.db import configure_database_url, reset_database_url
from backend.app.common.exceptions import ApiError
from backend.app.tasks.repository import configure_task_storage, get_task_log_path, reset_task_storage
from backend.app.tasks.service import (
    clear_tasks,
    create_task,
    get_task,
    mark_task_completed,
    mark_task_failed,
    mark_task_processing,
    require_task,
)


class TaskServiceTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_task_storage(Path(self.temp_dir.name) / "logs")
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'tasks-service.db'}")
        clear_tasks()

    def tearDown(self) -> None:
        clear_tasks()
        reset_database_url()
        reset_task_storage()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    def test_create_task_uses_processing_as_initial_status(self) -> None:
        task = create_task("task-001", "lesson.parse", {"courseId": "course-001"}, request_id="req-001")

        self.assertEqual(task.status, "processing")
        self.assertEqual(task.progressPercent, 0)
        self.assertEqual(task.payload["courseId"], "course-001")
        self.assertEqual(task.requestId, "req-001")
        self.assertTrue(get_task_log_path("task-001").exists())

    def test_mark_task_processing_updates_progress(self) -> None:
        create_task("task-001", "lesson.parse", {})

        task = mark_task_processing("task-001", progress_percent=35)

        self.assertEqual(task.status, "processing")
        self.assertEqual(task.progressPercent, 35)

    def test_mark_task_completed_stores_result(self) -> None:
        create_task("task-001", "lesson.parse", {})

        task = mark_task_completed("task-001", result={"parseId": "task-001"})

        self.assertEqual(task.status, "completed")
        self.assertEqual(task.progressPercent, 100)
        self.assertEqual(task.result["parseId"], "task-001")
        self.assertIsNone(task.error)
        self.assertIsNotNone(task.finishedAt)

    def test_mark_task_failed_stores_error(self) -> None:
        create_task("task-001", "lesson.parse", {})

        task = mark_task_failed("task-001", code=400, msg="解析失败", data={"parseId": "task-001"})

        self.assertEqual(task.status, "failed")
        self.assertIsNotNone(task.error)
        assert task.error is not None
        self.assertEqual(task.error.code, 400)
        self.assertEqual(task.error.data["parseId"], "task-001")

    def test_require_task_raises_when_missing(self) -> None:
        with self.assertRaises(ApiError) as context:
            require_task("missing-task")

        self.assertEqual(context.exception.status_code, 404)

    def test_get_task_returns_stored_task(self) -> None:
        create_task("task-001", "lesson.parse", {})

        task = get_task("task-001")

        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(task.taskId, "task-001")

    def test_task_record_survives_repository_reload(self) -> None:
        assert self.temp_dir is not None
        create_task("task-001", "lesson.parse", {"courseId": "course-001"})

        reset_task_storage()
        configure_task_storage(Path(self.temp_dir.name) / "logs")
        task = get_task("task-001")

        self.assertIsNotNone(task)
        assert task is not None
        self.assertEqual(task.taskId, "task-001")
