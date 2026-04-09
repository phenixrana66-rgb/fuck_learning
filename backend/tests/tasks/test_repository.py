import tempfile
import unittest
from pathlib import Path

from backend.app.tasks.repository import (
    append_task_log,
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
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_task_storage(self.temp_dir.name)
        clear_task_storage_files()

    def tearDown(self) -> None:
        clear_task_storage_files()
        reset_task_storage()
        self.temp_dir.cleanup()

    def test_save_task_persists_record_to_disk(self) -> None:
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

        self.assertTrue(get_tasks_file_path().exists())
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.requestId, "req-001")

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

        self.assertFalse(Path(self.temp_dir.name).exists())
