from pydantic import Field

from backend.app.common.schemas import AppBaseModel


class TaskError(AppBaseModel):
    code: int | None = None
    msg: str
    data: dict = Field(default_factory=dict)


class TaskRecord(AppBaseModel):
    taskId: str
    taskType: str
    status: str
    payload: dict = Field(default_factory=dict)
    progressPercent: int = Field(default=0, ge=0, le=100)
    result: dict = Field(default_factory=dict)
    error: TaskError | None = None
    requestId: str | None = None
    createdAt: str
    updatedAt: str
    finishedAt: str | None = None
