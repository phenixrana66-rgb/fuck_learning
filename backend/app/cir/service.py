from backend.app.cir.schemas import CIR, CirChapter, KnowledgeAnchor, LessonNode
from backend.app.parser.schemas import StructurePreview


def build_cir(courseware_id: str, preview: StructurePreview) -> CIR:
    chapters: list[CirChapter] = []
    previous_node_id: str | None = None

    for chapter_index, preview_chapter in enumerate(preview.chapters, start=1):
        nodes: list[LessonNode] = []
        for node_index, subchapter in enumerate(preview_chapter.subChapters, start=1):
            node_id = f"node-{chapter_index:02d}-{node_index:02d}"
            page_start = int(subchapter.pageRange.split("-")[0])
            anchors = [
                KnowledgeAnchor(
                    anchorId=f"anchor-{chapter_index:02d}-{node_index:02d}",
                    label=subchapter.subChapterName,
                    pageRef=page_start,
                    nodeRef=node_id,
                    sourceSpan=f"第{page_start}页至第{_page_refs_from_range(subchapter.pageRange)[-1]}页涉及{subchapter.subChapterName}的课件内容",
                )
            ]
            nodes.append(
                LessonNode(
                    nodeId=node_id,
                    nodeName=subchapter.subChapterName,
                    pageRefs=_page_refs_from_range(subchapter.pageRange),
                    keyPoints=[
                        f"理解{subchapter.subChapterName}的核心内容",
                        f"掌握与{subchapter.subChapterName}相关的重点知识",
                        f"能够围绕{subchapter.subChapterName}进行课堂表达与复述",
                    ],
                    summary=f"本节点围绕{subchapter.subChapterName}展开，覆盖课件第{subchapter.pageRange}页的主要内容。",
                    anchors=anchors,
                    prerequisiteNodeIds=[previous_node_id] if previous_node_id else [],
                    nextNodeId=None,
                )
            )
            previous_node_id = node_id

        for index in range(len(nodes) - 1):
            nodes[index].nextNodeId = nodes[index + 1].nodeId

        chapters.append(
            CirChapter(
                chapterId=preview_chapter.chapterId,
                chapterName=preview_chapter.chapterName,
                nodes=nodes,
            )
        )

    return CIR(
        coursewareId=courseware_id,
        title="AI互动智课课程中间表示",
        chapters=chapters,
    )


def _page_refs_from_range(page_range: str) -> list[int]:
    start, end = page_range.split("-")
    return list(range(int(start), int(end) + 1))
