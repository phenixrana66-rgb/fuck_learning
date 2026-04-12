import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from backend.app.common.db import session_scope
from backend.app.tasks.models import TaskEntity
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
    return _storage_root / "tasks.sqlite3"


def get_task_log_path(task_id: str) -> Path:
    return _storage_root / "logs" / f"{task_id}.log"


def save_task(task: TaskRecord) -> TaskRecord:
    created_at = _require_iso_datetime(task.createdAt)
    updated_at = _require_iso_datetime(task.updatedAt)
    with session_scope() as session:
        entity = session.get(TaskEntity, task.taskId)
        if entity is None:
            entity = TaskEntity(task_id=task.taskId)
            session.add(entity)

        entity.task_type = task.taskType
        entity.status = task.status
        entity.payload_json = task.payload
        entity.result_json = task.result
        entity.error_json = task.error.model_dump(mode="json") if task.error else None
        entity.progress_percent = task.progressPercent
        entity.request_id = task.requestId
        entity.created_at = created_at
        entity.updated_at = updated_at
        entity.finished_at = _parse_iso_datetime(task.finishedAt)
    return task


def load_task(task_id: str) -> TaskRecord | None:
    with session_scope() as session:
        entity = session.get(TaskEntity, task_id)
        return _entity_to_task(entity) if entity else None


def load_all_tasks() -> dict[str, TaskRecord]:
    with session_scope() as session:
        entities = session.scalars(select(TaskEntity)).all()
        tasks = [_entity_to_task(entity) for entity in entities]
        return {task.taskId: task for task in tasks}


def append_task_log(task_id: str, message: str) -> None:
    log_path = get_task_log_path(task_id)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(f"{message}\n")


def clear_task_storage_files() -> None:
    if _storage_root.exists():
        shutil.rmtree(_storage_root)
    _storage_root.mkdir(parents=True, exist_ok=True)


def clear_task_records() -> None:
    with session_scope() as session:
        session.execute(delete(TaskEntity))


def _entity_to_task(entity: TaskEntity) -> TaskRecord:
    payload: dict[str, Any] = {
        "taskId": entity.task_id,
        "taskType": entity.task_type,
        "status": entity.status,
        "payload": entity.payload_json or {},
        "result": entity.result_json or {},
        "error": entity.error_json,
        "progressPercent": entity.progress_percent,
        "requestId": entity.request_id,
        "createdAt": entity.created_at.isoformat(),
        "updatedAt": entity.updated_at.isoformat(),
        "finishedAt": entity.finished_at.isoformat() if entity.finished_at else None,
    }
    return TaskRecord.model_validate(payload)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _require_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
