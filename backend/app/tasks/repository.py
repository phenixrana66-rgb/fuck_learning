import json
import shutil
from pathlib import Path

from backend.app.tasks.schemas import TaskRecord

_DEFAULT_STORAGE_ROOT = Path(__file__).resolve().parents[3] / "temp" / "ai-generate" / "tasks"
_storage_root = _DEFAULT_STORAGE_ROOT


def configure_task_storage(root_path: str | Path) -> None:
    global _storage_root
    _storage_root = Path(root_path)


def reset_task_storage() -> None:
    global _storage_root
    _storage_root = _DEFAULT_STORAGE_ROOT


def get_tasks_file_path() -> Path:
    return _storage_root / "tasks.json"


def get_task_log_path(task_id: str) -> Path:
    return _storage_root / "logs" / f"{task_id}.log"


def save_task(task: TaskRecord) -> TaskRecord:
    tasks = load_all_tasks()
    tasks[task.taskId] = task
    _write_tasks(tasks)
    return task


def load_task(task_id: str) -> TaskRecord | None:
    return load_all_tasks().get(task_id)


def load_all_tasks() -> dict[str, TaskRecord]:
    file_path = get_tasks_file_path()
    if not file_path.exists():
        return {}

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return {task_id: TaskRecord.model_validate(task_data) for task_id, task_data in payload.items()}


def append_task_log(task_id: str, message: str) -> None:
    log_path = get_task_log_path(task_id)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(f"{message}\n")


def clear_task_storage_files() -> None:
    if _storage_root.exists():
        shutil.rmtree(_storage_root)


def _write_tasks(tasks: dict[str, TaskRecord]) -> None:
    file_path = get_tasks_file_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = {task_id: task.model_dump(mode="json") for task_id, task in tasks.items()}
    file_path.write_text(json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8")
