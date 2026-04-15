import re

from backend.app.cir.schemas import CIR, CirChapter, CirSlideContent, KnowledgeAnchor, LessonNode
from backend.app.parser.schemas import ExtractedPresentation, ExtractedSlide, StructurePreview

_GENERIC_FACTS = {
    '知识目标',
    '知识目标——',
    '重点',
    '本节小结',
    'END',
}
_KEY_POINT_KEYWORDS = (
    '定义',
    '分类',
    '用途',
    '内容',
    '组成',
    '结构',
    '原理',
    '规则',
    '条件',
    '系统',
    '设备',
    '步骤',
    '参数',
    '编码',
    '代号',
    '阻力',
    '附着',
)


def build_cir(courseware_id: str, preview: StructurePreview, extracted: ExtractedPresentation) -> CIR:
    chapters: list[CirChapter] = []
    previous_node_id: str | None = None
    slide_lookup = {slide.slideNumber: slide for slide in extracted.slides}

    for chapter_index, preview_chapter in enumerate(preview.chapters, start=1):
        nodes: list[LessonNode] = []
        for node_index, subchapter in enumerate(preview_chapter.subChapters, start=1):
            node_id = f'node-{chapter_index:02d}-{node_index:02d}'
            page_start = int(subchapter.pageRange.split('-')[0])
            page_refs = _page_refs_from_range(subchapter.pageRange)
            page_contents = _collect_page_contents(page_refs, slide_lookup)
            anchors = [
                KnowledgeAnchor(
                    anchorId=f'anchor-{chapter_index:02d}-{node_index:02d}',
                    label=subchapter.subChapterName,
                    pageRef=page_start,
                    nodeRef=node_id,
                    sourceSpan=f'第{page_start}页至第{page_refs[-1]}页涉及{subchapter.subChapterName}的课件内容',
                )
            ]
            nodes.append(
                LessonNode(
                    nodeId=node_id,
                    nodeName=subchapter.subChapterName,
                    pageRefs=page_refs,
                    pageContents=page_contents,
                    keyPoints=_extract_key_points(subchapter.subChapterName, page_contents),
                    summary=_build_node_summary(subchapter.subChapterName, subchapter.pageRange, page_contents),
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
        title=_build_cir_title(courseware_id, extracted),
        chapters=chapters,
    )


def _page_refs_from_range(page_range: str) -> list[int]:
    start, end = page_range.split('-')
    return list(range(int(start), int(end) + 1))


def _collect_page_contents(page_refs: list[int], slide_lookup: dict[int, ExtractedSlide]) -> list[CirSlideContent]:
    page_contents: list[CirSlideContent] = []
    for page_ref in page_refs:
        slide = slide_lookup.get(page_ref)
        if slide is None:
            continue
        page_contents.append(
            CirSlideContent(
                slideNumber=slide.slideNumber,
                title=slide.title,
                bodyTexts=slide.bodyTexts,
                tableTexts=slide.tableTexts,
                notes=slide.notes,
            )
        )
    return page_contents


def _build_cir_title(courseware_id: str, extracted: ExtractedPresentation) -> str:
    for slide in extracted.slides:
        title = _clean_fact_text(slide.title)
        if title:
            return title
    return courseware_id


def _build_node_summary(node_name: str, page_range: str, page_contents: list[CirSlideContent]) -> str:
    facts = _extract_key_points(node_name, page_contents)[:2]
    if facts:
        return f'本节围绕“{node_name}”展开，重点讲解{"、".join(facts)}。'
    return f'本节围绕“{node_name}”展开，覆盖课件第{page_range}页的主要内容。'


def _extract_key_points(node_name: str, page_contents: list[CirSlideContent]) -> list[str]:
    scored_candidates: list[tuple[int, str]] = []
    fallback_candidates: list[str] = []
    seen: set[str] = set()

    for page_content in page_contents:
        title = _clean_fact_text(page_content.title)
        if title and title not in seen:
            fallback_candidates.append(title)
            seen.add(title)
            scored_candidates.append((_score_fact(title, from_title=True), title))

        for raw_text in [*page_content.bodyTexts[:4], *page_content.tableTexts[:2], page_content.notes or '']:
            for segment in _split_fact_segments(raw_text):
                candidate = _clean_fact_text(segment)
                if not candidate or candidate in seen:
                    continue
                seen.add(candidate)
                fallback_candidates.append(candidate)
                scored_candidates.append((_score_fact(candidate, from_title=False), candidate))

    ranked = [
        text
        for _, text in sorted(scored_candidates, key=lambda item: (-item[0], len(item[1])))
        if text != node_name
    ]

    if ranked:
        return ranked[:4]
    if fallback_candidates:
        return fallback_candidates[:4]
    return [node_name]


def _split_fact_segments(text: str | None) -> list[str]:
    if not text:
        return []
    normalized = text.replace('\r', '\n')
    parts = re.split(r'[\n；;。！？]', normalized)
    return [part.strip() for part in parts if part and part.strip()]


def _clean_fact_text(text: str | None) -> str | None:
    if not text:
        return None
    normalized = ' '.join(part.strip() for part in text.splitlines() if part.strip())
    normalized = re.sub(r'^[◇•·●]+', '', normalized).strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip('，。；;：:、 ') 
    if not normalized:
        return None
    if normalized in _GENERIC_FACTS:
        return None
    if re.fullmatch(r'第?\d+页', normalized):
        return None
    if len(normalized) < 2:
        return None
    return normalized[:80]


def _score_fact(text: str, *, from_title: bool) -> int:
    score = 1
    if from_title:
        score += 2
    if any(keyword in text for keyword in _KEY_POINT_KEYWORDS):
        score += 3
    if any(char.isdigit() for char in text):
        score += 1
    if len(text) <= 32:
        score += 1
    if '理解' in text or '掌握' in text or '复述' in text:
        score -= 2
    return score

