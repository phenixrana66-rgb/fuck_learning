from datetime import UTC, datetime

from backend.app.common.exceptions import ApiError
from backend.app.tasks.repository import append_task_log, clear_task_storage_files, load_task, save_task
from backend.app.tasks.schemas import TaskError, TaskRecord


def create_task(
    task_id: str,
    task_type: str,
    payload: dict,
    progress_percent: int = 0,
    request_id: str | None = None,
) -> TaskRecord:
    now = _now_iso()
    task = TaskRecord(
        taskId=task_id,
        taskType=task_type,
        status="processing",
        payload=payload,
        progressPercent=progress_percent,
        requestId=request_id,
        createdAt=now,
        updatedAt=now,
    )
    saved_task = save_task(task)
    append_task_log(task_id, f"[{now}] 任务已创建 status=processing requestId={request_id or 'unknown'}")
    return saved_task


def upsert_task(task: TaskRecord) -> TaskRecord:
    return save_task(task)


def mark_task_processing(task_id: str, progress_percent: int) -> TaskRecord:
    task = require_task(task_id)
    task.status = "processing"
    task.progressPercent = progress_percent
    task.error = None
    task.updatedAt = _now_iso()
    task.finishedAt = None
    append_task_log(task_id, f"[{task.updatedAt}] 任务处理中 progressPercent={progress_percent}")
    return upsert_task(task)


def mark_task_completed(task_id: str, result: dict, progress_percent: int = 100) -> TaskRecord:
    task = require_task(task_id)
    task.status = "completed"
    task.progressPercent = progress_percent
    task.result = result
    task.error = None
    task.updatedAt = _now_iso()
    task.finishedAt = task.updatedAt
    append_task_log(task_id, f"[{task.updatedAt}] 任务已完成 progressPercent={progress_percent}")
    return upsert_task(task)


def mark_task_failed(task_id: str, code: int | None, msg: str, data: dict | None = None) -> TaskRecord:
    task = require_task(task_id)
    task.status = "failed"
    task.error = TaskError(code=code, msg=msg, data=data or {})
    task.updatedAt = _now_iso()
    task.finishedAt = task.updatedAt
    append_task_log(task_id, f"[{task.updatedAt}] 任务失败 code={code} msg={msg}")
    return upsert_task(task)


def get_task(task_id: str) -> TaskRecord | None:
    return load_task(task_id)


def require_task(task_id: str) -> TaskRecord:
    task = get_task(task_id)
    if task is None:
        raise ApiError(code=404, msg="任务不存在", status_code=404)
    return task


def clear_tasks() -> None:
    clear_task_storage_files()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
