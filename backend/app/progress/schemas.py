from typing import Literal

from backend.app.common.schemas import AppBaseModel


class TrackProgressRequest(AppBaseModel):
    schoolId: str
    userId: str
    courseId: str
    lessonId: str
    currentSectionId: str
    progressPercent: float
    lastOperateTime: str
    qaRecordId: str | None = None
    enc: str
    time: str | None = None


class AdjustProgressRequest(AppBaseModel):
    userId: str
    lessonId: str
    currentSectionId: str
    understandingLevel: Literal["none", "partial", "full"]
    qaRecordId: str
    enc: str
    time: str | None = None
