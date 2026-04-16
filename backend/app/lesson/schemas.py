from typing import Literal

from pydantic import Field

from backend.app.common.schemas import AppBaseModel


class GenerateAudioRequest(AppBaseModel):
    scriptId: str
    voiceType: str = "female_standard"
    audioFormat: Literal["mp3", "wav"] = "mp3"
    sectionIds: list[str] = Field(default_factory=list)
    enc: str
    time: str | None = None


class SectionAudio(AppBaseModel):
    sectionAudioId: str | None = None
    sectionId: str
    audioUrl: str
    duration: int
    status: str = "generated"


class AudioInfo(AppBaseModel):
    totalDuration: int
    fileSize: int
    format: str
    bitRate: int


class PublishRequest(AppBaseModel):
    coursewareId: str
    scriptId: str
    audioId: str
    publisherId: str | None = None
    enc: str
    time: str | None = None


class PlayRequest(AppBaseModel):
    lessonId: str
    userId: str
    resumeContext: dict | None = None
    enc: str
    time: str | None = None
