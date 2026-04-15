from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete

from backend.app.cir.schemas import CIR, CirSlideContent, LessonNode
from backend.app.common.db import session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseQueryData
from backend.app.courseware.service import get_parse_task
from backend.app.parser.schemas import ParseTaskStatus
from backend.app.script.llm_client import generate_script_sections_with_llm
from backend.app.script.schemas import GenerateScriptRequest, ScriptDetail, ScriptSection, ScriptSummary, UpdateScriptRequest
from backend.chaoxing_db.models import ChapterAudioAsset, ChapterParseTask, ChapterScript, ChapterScriptSection


def generate_script(payload: GenerateScriptRequest) -> ScriptSummary:
    parse_result = get_parse_task(payload.parseId)
    if parse_result.taskStatus != ParseTaskStatus.COMPLETED:
        raise ApiError(code=409, msg='parse task is not completed', status_code=409)

    script_id = _build_id('script')
    sections, section_nodes = _build_script_sections_with_nodes(parse_result, payload)

    with session_scope() as db:
        parse_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == payload.parseId).first()
        if parse_task is None:
            raise ApiError(code=404, msg='parse task not found', status_code=404)

        node_id_map = {node.node_code: node.id for node in parse_task.knowledge_nodes}
        script = ChapterScript(
            script_no=script_id,
            course_id=parse_task.course_id,
            chapter_id=parse_task.chapter_id,
            parse_task_id=parse_task.id,
            teacher_id=parse_task.teacher_id,
            teaching_style=payload.teachingStyle,
            speech_speed=payload.speechSpeed,
            custom_opening=_normalize_opening(payload.customOpening),
            script_status='generated',
            edit_url=f'/teacher/scripts/{script_id}/edit',
        )
        db.add(script)
        db.flush()
        _replace_script_sections(db, script.id, sections, section_nodes, node_id_map)

    return ScriptSummary(
        scriptId=script_id,
        scriptStructure=sections,
        editUrl=f'/teacher/scripts/{script_id}/edit',
        audioGenerateUrl='/api/v1/lesson/generateAudio',
    )


def get_script(script_id: str) -> ScriptDetail:
    with session_scope() as db:
        script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
        if script is None:
            raise ApiError(code=404, msg='script not found', status_code=404)
        return _build_script_detail(script)


def update_script(script_id: str, payload: UpdateScriptRequest) -> ScriptDetail:
    with session_scope() as db:
        script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
        if script is None:
            raise ApiError(code=404, msg='script not found', status_code=404)

        parse_task = script.parse_task
        if parse_task is None:
            raise ApiError(code=404, msg='parse task not found', status_code=404)

        existing_node_map = {section.section_code: section.related_node_id for section in script.sections}
        parse_result = get_parse_task(parse_task.parse_no)
        section_nodes = _build_section_nodes_from_parse(parse_result)
        node_id_map = {node.node_code: node.id for node in parse_task.knowledge_nodes}

        if script.script_status != 'published':
            script.script_status = 'edited'
        if not script.edit_url:
            script.edit_url = f'/teacher/scripts/{script_id}/edit'

        for section in list(script.sections):
            db.delete(section)
        db.flush()

        _replace_script_sections(
            db,
            script.id,
            payload.scriptStructure,
            section_nodes,
            node_id_map,
            existing_node_map=existing_node_map,
        )
        db.flush()
        db.refresh(script)
        return _build_script_detail(script, parse_result=parse_result)


def clear_scripts() -> None:
    with session_scope() as db:
        db.execute(delete(ChapterAudioAsset))
        db.execute(delete(ChapterScriptSection))
        db.execute(delete(ChapterScript))


def _build_script_sections(parse_result: ParseQueryData, payload: GenerateScriptRequest) -> list[ScriptSection]:
    sections, _ = _build_script_sections_with_nodes(parse_result, payload)
    return sections


def _build_script_sections_with_nodes(
    parse_result: ParseQueryData,
    payload: GenerateScriptRequest,
) -> tuple[list[ScriptSection], dict[str, LessonNode]]:
    if parse_result.cir is None:
        raise ApiError(code=500, msg='parse result is missing CIR', status_code=500)

    sections: list[ScriptSection] = []
    section_nodes: dict[str, LessonNode] = {}
    opening = _normalize_opening(payload.customOpening)
    section_index = 1

    for chapter in parse_result.cir.chapters:
        for node in chapter.nodes:
            section_id = f'sec{section_index:03d}'
            key_points = node.keyPoints[:3]
            section_content = _build_section_content(
                node_name=node.nodeName,
                summary=node.summary.strip(),
                key_points=key_points,
                page_contents=node.pageContents,
                teaching_style=payload.teachingStyle,
                opening=_opening_prefix(opening, section_index),
            )
            sections.append(
                ScriptSection(
                    sectionId=section_id,
                    sectionName=node.nodeName,
                    content=section_content,
                    duration=_estimate_duration(payload.speechSpeed, key_points),
                    relatedChapterId=chapter.chapterId,
                    relatedPage=_format_page_refs(node.pageRefs),
                    keyPoints=key_points,
                )
            )
            section_nodes[section_id] = node
            section_index += 1

    if not sections:
        sections.append(
            ScriptSection(
                sectionId='sec001',
                sectionName=parse_result.cir.title or 'Courseware Introduction',
                content=' '.join(
                    part
                    for part in [
                        opening,
                        '\u5f53\u524d\u8bfe\u4ef6\u672a\u62bd\u53d6\u5230\u53ef\u7528\u8282\u70b9\u3002',
                        '\u8bf7\u5148\u56f4\u7ed5\u7ae0\u8282\u4e3b\u9898\u5b8c\u6210\u5bfc\u5165\uff0c\u518d\u9010\u6b65\u5c55\u5f00\u5b8c\u6574\u8bb2\u89e3\u3002',
                    ]
                    if part
                ),
                duration=_estimate_duration(payload.speechSpeed, []),
                keyPoints=[],
            )
        )

    _try_fill_sections_with_llm(parse_result, payload, sections, section_nodes)
    return sections, section_nodes


def _replace_script_sections(
    db,
    script_db_id: int,
    sections: list[ScriptSection],
    section_nodes: dict[str, LessonNode],
    node_id_map: dict[str, int],
    existing_node_map: dict[str, int | None] | None = None,
) -> None:
    existing_node_map = existing_node_map or {}
    for sort_no, section in enumerate(sections):
        node = section_nodes.get(section.sectionId)
        related_node_id = existing_node_map.get(section.sectionId)
        if related_node_id is None and node is not None:
            related_node_id = node_id_map.get(node.nodeId)
        db.add(
            ChapterScriptSection(
                script_id=script_db_id,
                section_code=section.sectionId,
                section_name=section.sectionName,
                section_content=section.content,
                duration_sec=section.duration,
                related_node_id=related_node_id,
                related_page_range=section.relatedPage,
                sort_no=sort_no,
            )
        )


def _script_version(script: ChapterScript) -> int:
    return 2 if script.script_status == 'edited' else 1


def _build_script_detail(script: ChapterScript, parse_result: ParseQueryData | None = None) -> ScriptDetail:
    parse_result = parse_result or get_parse_task(script.parse_task.parse_no)
    node_lookup = _build_node_lookup(parse_result.cir)
    chapter_lookup = _build_chapter_lookup(parse_result.cir)
    knowledge_lookup = {node.id: node.node_code for node in script.parse_task.knowledge_nodes}
    sections = [
        _build_script_section(section, knowledge_lookup, node_lookup, chapter_lookup)
        for section in sorted(script.sections, key=lambda item: (item.sort_no, item.id))
    ]
    return ScriptDetail(
        scriptId=script.script_no,
        parseId=script.parse_task.parse_no,
        teachingStyle=script.teaching_style,
        speechSpeed=script.speech_speed,
        scriptStructure=sections,
        version=_script_version(script),
    )


def _build_section_nodes_from_parse(parse_result: ParseQueryData) -> dict[str, LessonNode]:
    if parse_result.cir is None:
        return {}

    section_nodes: dict[str, LessonNode] = {}
    section_index = 1
    for chapter in parse_result.cir.chapters:
        for node in chapter.nodes:
            section_nodes[f'sec{section_index:03d}'] = node
            section_index += 1
    return section_nodes


def _build_node_lookup(cir: CIR | None) -> dict[str, LessonNode]:
    if cir is None:
        return {}
    return {node.nodeId: node for chapter in cir.chapters for node in chapter.nodes}


def _build_chapter_lookup(cir: CIR | None) -> dict[str, str]:
    if cir is None:
        return {}

    chapter_lookup: dict[str, str] = {}
    for chapter in cir.chapters:
        for node in chapter.nodes:
            chapter_lookup[node.nodeId] = chapter.chapterId
    return chapter_lookup


def _build_script_section(
    section: ChapterScriptSection,
    knowledge_lookup: dict[int, str],
    node_lookup: dict[str, LessonNode],
    chapter_lookup: dict[str, str],
) -> ScriptSection:
    node_code = knowledge_lookup.get(section.related_node_id) if section.related_node_id is not None else None
    node = node_lookup.get(node_code) if node_code else None
    return ScriptSection(
        sectionId=section.section_code,
        sectionName=section.section_name,
        content=section.section_content,
        duration=section.duration_sec or 0,
        relatedChapterId=chapter_lookup.get(node_code) if node_code else None,
        relatedPage=section.related_page_range,
        keyPoints=node.keyPoints[:3] if node else [],
    )


def _try_fill_sections_with_llm(
    parse_result: ParseQueryData,
    payload: GenerateScriptRequest,
    sections: list[ScriptSection],
    section_nodes: dict[str, LessonNode],
) -> None:
    cir = parse_result.cir
    if cir is None or not sections:
        return

    try:
        generated_contents = generate_script_sections_with_llm(cir, payload, sections, section_nodes)
    except ApiError:
        return

    for section in sections:
        generated_content = generated_contents.get(section.sectionId)
        if isinstance(generated_content, str) and generated_content.strip():
            section.content = generated_content.strip()


def _normalize_opening(opening: str | None) -> str | None:
    if opening is None:
        return None
    normalized = opening.strip()
    return normalized or None


def _opening_prefix(opening: str | None, section_index: int) -> str:
    if opening and section_index == 1:
        return opening
    return ''


def openning_prefix(opening: str | None, section_index: int) -> str:
    return _opening_prefix(opening, section_index)


def _build_section_content(
    node_name: str,
    summary: str,
    key_points: list[str],
    page_contents: list[CirSlideContent],
    teaching_style: str,
    opening: str,
) -> str:
    style_prefix = {
        'standard': '\u5148\u6293\u4f4f\u6838\u5fc3\u6982\u5ff5\uff0c\u518d\u6309\u8bfe\u5802\u8bb2\u89e3\u987a\u5e8f\u5c55\u5f00\u3002',
        'detailed': '\u8fd9\u4e00\u6bb5\u4f1a\u6309\u80cc\u666f\u3001\u6982\u5ff5\u548c\u5e94\u7528\u4e09\u4e2a\u5c42\u6b21\u5b8c\u6574\u5c55\u5f00\u3002',
        'concise': '\u8fd9\u4e00\u6bb5\u53ea\u4fdd\u7559\u6700\u5173\u952e\u7684\u7ed3\u8bba\u548c\u8bb0\u5fc6\u6293\u624b\u3002',
    }.get(teaching_style, '\u5148\u6293\u4f4f\u6838\u5fc3\u6982\u5ff5\uff0c\u518d\u6309\u8bfe\u5802\u8bb2\u89e3\u987a\u5e8f\u5c55\u5f00\u3002')
    key_points_text = '\uff1b'.join(key_points) if key_points else '\u4ee5\u8282\u70b9\u6458\u8981\u4f5c\u4e3a\u672c\u6bb5\u4e3b\u7ebf\u3002'
    source_explanation = _build_page_grounded_explanation(page_contents)
    parts = [
        part
        for part in [
            opening,
            f'\u672c\u8282\u8bb2\u89e3\u300a{node_name}\u300b\u3002',
            style_prefix,
            source_explanation or summary or '\u56f4\u7ed5\u5f53\u524d\u8282\u70b9\u505a\u91cd\u70b9\u8bb2\u89e3\u3002',
            f'\u91cd\u70b9\u5305\u62ec\uff1a{key_points_text}',
        ]
        if part
    ]
    return ' '.join(parts)


def _build_page_grounded_explanation(page_contents: list[CirSlideContent]) -> str:
    explanations: list[str] = []
    for page_content in page_contents[:3]:
        fragments: list[str] = []
        if page_content.title:
            fragments.append(f"Page {page_content.slideNumber} is titled '{_shorten_text(page_content.title, 40)}'.")

        for body_text in page_content.bodyTexts[:2]:
            fragments.append(f"The slide highlights: {_shorten_text(body_text, 90)}")

        for table_text in page_content.tableTexts[:1]:
            fragments.append(f"The table content shows: {_shorten_text(table_text.replace(chr(10), '; '), 120)}")

        if page_content.notes:
            fragments.append(f"The speaker notes add: {_shorten_text(page_content.notes, 80)}")

        if fragments:
            explanations.append(' '.join(fragments))

    return ' '.join(explanations)


def _shorten_text(text: str, limit: int) -> str:
    normalized = ' '.join(part.strip() for part in text.splitlines() if part.strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + '...'


def _estimate_duration(speech_speed: str, key_points: list[str]) -> int:
    base_duration = 35 + len(key_points) * 8
    if speech_speed == 'slow':
        return base_duration + 10
    if speech_speed == 'fast':
        return max(20, base_duration - 8)
    return base_duration


def _format_page_refs(page_refs: list[int]) -> str | None:
    if not page_refs:
        return None
    if len(page_refs) == 1:
        return str(page_refs[0])
    return f'{min(page_refs)}-{max(page_refs)}'


def _build_id(prefix: str) -> str:
    return f'S{uuid4().hex[:12].upper()}'
