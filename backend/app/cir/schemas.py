from pydantic import Field

from backend.app.common.schemas import AppBaseModel


class KnowledgeAnchor(AppBaseModel):
    anchorId: str
    label: str
    pageRef: int
    nodeRef: str
    sourceSpan: str


class LessonNode(AppBaseModel):
    nodeId: str
    nodeName: str
    pageRefs: list[int] = Field(default_factory=list)
    keyPoints: list[str] = Field(default_factory=list)
    summary: str
    anchors: list[KnowledgeAnchor] = Field(default_factory=list)
    prerequisiteNodeIds: list[str] = Field(default_factory=list)
    nextNodeId: str | None = None


class CirChapter(AppBaseModel):
    chapterId: str
    chapterName: str
    nodes: list[LessonNode] = Field(default_factory=list)


class CIR(AppBaseModel):
    coursewareId: str
    title: str
    chapters: list[CirChapter] = Field(default_factory=list)
