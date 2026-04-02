from typing import Literal

from pydantic import Field

from backend.app.cir.schemas import CIR
from backend.app.common.schemas import AppBaseModel
from backend.app.parser.schemas import FileInfo, ParseTaskStatus, StructurePreview


class ParseRequest(AppBaseModel):
    schoolId: str
    userId: str
    courseId: str
    fileType: Literal["ppt", "pdf"]
    fileUrl: str
    isExtractKeyPoint: bool = True
    enc: str
    time: str | None = None


class ParseAcceptedData(AppBaseModel):
    parseId: str
    fileInfo: FileInfo
    structurePreview: StructurePreview
    taskStatus: ParseTaskStatus


class ParseQueryData(ParseAcceptedData):
    cir: CIR | None = None
    progressPercent: int = Field(default=25, ge=0, le=100)
