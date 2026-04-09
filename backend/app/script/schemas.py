from typing import Literal

from pydantic import Field

from backend.app.common.schemas import AppBaseModel


class GenerateScriptRequest(AppBaseModel):
    parseId: str
    teachingStyle: Literal["standard", "detailed", "concise"] = "standard"
    speechSpeed: Literal["slow", "normal", "fast"] = "normal"
    customOpening: str | None = None
    enc: str
    time: str | None = None


class ScriptSection(AppBaseModel):
    sectionId: str
    sectionName: str
    content: str
    duration: int
    relatedChapterId: str | None = None
    relatedPage: str | None = None
    keyPoints: list[str] = Field(default_factory=list)


class ScriptSummary(AppBaseModel):
    scriptId: str
    scriptStructure: list[ScriptSection] = Field(default_factory=list)
    editUrl: str
    audioGenerateUrl: str


class ScriptDetail(AppBaseModel):
    scriptId: str
    parseId: str
    teachingStyle: str
    speechSpeed: str
    scriptStructure: list[ScriptSection] = Field(default_factory=list)
    version: int = 1


class UpdateScriptRequest(AppBaseModel):
    scriptStructure: list[ScriptSection]
    versionRemark: str | None = None
    enc: str
    time: str | None = None
