from typing import Literal

from pydantic import Field

from backend.app.common.schemas import AppBaseModel


class QAHistoryItem(AppBaseModel):
    question: str
    answer: str
    timestamp: str


class QAInteractRequest(AppBaseModel):
    schoolId: str
    userId: str
    courseId: str
    lessonId: str
    sessionId: str
    questionType: Literal["text", "voice"]
    questionContent: str
    currentSectionId: str
    historyQa: list[QAHistoryItem] = Field(default_factory=list)
    enc: str
    time: str | None = None


class VoiceToTextRequest(AppBaseModel):
    voiceUrl: str
    voiceDuration: int | None = None
    language: str = "zh-CN"
    enc: str
    time: str | None = None
