from enum import Enum

from pydantic import Field

from backend.app.common.schemas import AppBaseModel


class ParseTaskStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileInfo(AppBaseModel):
    fileName: str
    fileSize: int
    pageCount: int


class PreviewSubChapter(AppBaseModel):
    subChapterId: str
    subChapterName: str
    isKeyPoint: bool = True
    pageRange: str


class PreviewChapter(AppBaseModel):
    chapterId: str
    chapterName: str
    subChapters: list[PreviewSubChapter] = Field(default_factory=list)


class StructurePreview(AppBaseModel):
    chapters: list[PreviewChapter] = Field(default_factory=list)
