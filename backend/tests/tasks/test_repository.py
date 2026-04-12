import tempfile
import unittest
from pathlib import Path

from backend.app.common.db import configure_database_url, reset_database_url
from backend.app.tasks.repository import (
    append_task_log,
    clear_task_records,
    clear_task_storage_files,
    configure_task_storage,
    get_task_log_path,
    get_tasks_file_path,
    load_task,
    reset_task_storage,
    save_task,
)
from backend.app.tasks.schemas import TaskRecord


class TaskRepositoryTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    log_root: Path | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_root = Path(self.temp_dir.name) / "logs"
        configure_task_storage(self.log_root)
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'tasks-test.db'}")
        clear_task_records()
        clear_task_storage_files()

    def tearDown(self) -> None:
        clear_task_records()
        clear_task_storage_files()
        reset_database_url()
        reset_task_storage()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    def test_save_task_persists_record_to_database(self) -> None:
        task = TaskRecord(
            taskId="task-001",
            taskType="lesson.parse",
            status="processing",
            payload={"courseId": "course-001"},
            requestId="req-001",
            createdAt="2026-04-08T12:00:00+00:00",
            updatedAt="2026-04-08T12:00:00+00:00",
        )

        save_task(task)
        reloaded = load_task("task-001")

        self.assertIsNotNone(reloaded)
        assert reloaded is not None
        self.assertEqual(reloaded.requestId, "req-001")

    def test_get_tasks_file_path_points_to_default_sqlite_artifact_name(self) -> None:
        self.assertEqual(get_tasks_file_path().name, "tasks.sqlite3")

    def test_append_task_log_creates_deterministic_log_file(self) -> None:
        append_task_log("task-001", "[2026-04-08T12:00:00+00:00] 任务已创建")

        log_path = get_task_log_path("task-001")

        self.assertTrue(log_path.exists())
        self.assertEqual(log_path.read_text(encoding="utf-8").strip(), "[2026-04-08T12:00:00+00:00] 任务已创建")

    def test_clear_task_storage_files_removes_saved_artifacts(self) -> None:
        task = TaskRecord(
            taskId="task-001",
            taskType="lesson.parse",
            status="processing",
            payload={},
            createdAt="2026-04-08T12:00:00+00:00",
            updatedAt="2026-04-08T12:00:00+00:00",
        )
        save_task(task)
        append_task_log("task-001", "[2026-04-08T12:00:00+00:00] 任务已创建")

        clear_task_storage_files()

        assert self.log_root is not None
        self.assertTrue(self.log_root.exists())
        self.assertFalse(get_task_log_path("task-001").exists())
