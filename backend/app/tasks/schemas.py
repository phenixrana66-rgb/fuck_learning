from backend.app.common.schemas import AppBaseModel


class TaskRecord(AppBaseModel):
    taskId: str
    taskType: str
    status: str
    payload: dict
