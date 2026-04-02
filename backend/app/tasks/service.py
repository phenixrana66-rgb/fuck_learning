from backend.app.tasks.schemas import TaskRecord

_TASKS: dict[str, TaskRecord] = {}


def upsert_task(task: TaskRecord) -> TaskRecord:
    _TASKS[task.taskId] = task
    return task


def get_task(task_id: str) -> TaskRecord | None:
    return _TASKS.get(task_id)
