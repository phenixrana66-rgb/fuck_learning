from enum import Enum
from typing import Literal

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


class ExtractedSlide(AppBaseModel):
    slideNumber: int = Field(ge=1)
    title: str | None = None
    bodyTexts: list[str] = Field(default_factory=list)
    tableTexts: list[str] = Field(default_factory=list)
    notes: str | None = None


class ExtractedPresentation(AppBaseModel):
    sourceType: Literal["pptx"] = "pptx"
    slides: list[ExtractedSlide] = Field(default_factory=list)


class OutlineSubChapter(AppBaseModel):
    name: str
    pageStart: int = Field(ge=1)
    pageEnd: int = Field(ge=1)
    isKeyPoint: bool = True


class OutlineChapter(AppBaseModel):
    name: str
    subChapters: list[OutlineSubChapter] = Field(default_factory=list)


class OutlineResult(AppBaseModel):
    title: str | None = None
    chapters: list[OutlineChapter] = Field(default_factory=list)
