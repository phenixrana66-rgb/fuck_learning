from __future__ import annotations

import logging
import math
import re
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

logger = logging.getLogger(__name__)


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
    flattened_nodes = [
        (chapter.chapterId, node)
        for chapter in parse_result.cir.chapters
        for node in chapter.nodes
    ]

    for section_index, (chapter_id, node) in enumerate(flattened_nodes, start=1):
        section_id = f'sec{section_index:03d}'
        key_points = node.keyPoints[:4]
        next_node_name = flattened_nodes[section_index][1].nodeName if section_index < len(flattened_nodes) else None
        section_content = _build_section_content(
            node_name=node.nodeName,
            summary=node.summary.strip(),
            key_points=key_points,
            page_contents=node.pageContents,
            teaching_style=payload.teachingStyle,
            opening=_opening_prefix(opening, section_index),
            section_index=section_index,
            total_sections=len(flattened_nodes),
            next_node_name=next_node_name,
        )
        sections.append(
            ScriptSection(
                sectionId=section_id,
                sectionName=node.nodeName,
                content=section_content,
                duration=_estimate_duration(payload.speechSpeed, section_content),
                relatedChapterId=chapter_id,
                relatedPage=_format_page_refs(node.pageRefs),
                keyPoints=key_points,
            )
        )
        section_nodes[section_id] = node

    if not sections:
        empty_content = _build_empty_script_content(parse_result.cir.title or '课件讲解', opening)
        sections.append(
            ScriptSection(
                sectionId='sec001',
                sectionName=parse_result.cir.title or '课件导入',
                content=empty_content,
                duration=_estimate_duration(payload.speechSpeed, empty_content),
                keyPoints=[],
            )
        )

    _try_fill_sections_with_llm(parse_result, payload, sections, section_nodes)
    _refresh_section_durations(sections, payload.speechSpeed)
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
        keyPoints=node.keyPoints[:4] if node else [],
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
    except ApiError as exc:
        logger.warning('script generation LLM failed for parse_id=%s: %s', payload.parseId, exc.msg)
        return

    for section in sections:
        generated_content = generated_contents.get(section.sectionId)
        if isinstance(generated_content, str) and generated_content.strip():
            section.content = generated_content.strip()


def _refresh_section_durations(sections: list[ScriptSection], speech_speed: str) -> None:
    for section in sections:
        section.duration = _estimate_duration(speech_speed, section.content)


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
    section_index: int,
    total_sections: int,
    next_node_name: str | None,
) -> str:
    parts = [
        opening,
        f'这一部分我们重点讲“{node_name}”。',
        _style_guidance(teaching_style),
        _build_page_grounded_explanation(page_contents, summary),
        _build_key_points_sentence(key_points),
        _build_transition_sentence(node_name, section_index, total_sections, next_node_name),
    ]
    return ' '.join(part for part in parts if part)


def _build_empty_script_content(courseware_title: str, opening: str | None) -> str:
    parts = [
        opening,
        f'这份课件当前还没有抽取出可直接生成脚本的章节节点，我们先围绕“{courseware_title}”做一个简短导入。',
        '建议老师先补充章节划分，明确每一部分要讲的概念、案例或步骤，再生成完整讲稿。',
        '如果需要先行授课，可以从课程目标、核心概念和应用场景三个层次展开，最后做一个简短总结。',
    ]
    return ' '.join(part for part in parts if part)


def _style_guidance(teaching_style: str) -> str:
    return {
        'standard': '讲解时先把概念说清，再把重点事实串起来。',
        'detailed': '这一段可以按背景、概念、细节和应用的顺序展开，适当多解释一步。',
        'concise': '这一段尽量短句表达，只保留最关键的概念、结论和记忆抓手。',
    }.get(teaching_style, '讲解时先把概念说清，再把重点事实串起来。')


def _build_page_grounded_explanation(page_contents: list[CirSlideContent], summary: str) -> str:
    facts = _collect_grounded_facts(page_contents)
    if facts:
        if len(facts) == 1:
            return f'结合课件内容，需要重点讲清：{facts[0]}。'
        return f'结合课件内容，这里至少要讲清以下事实：{'；'.join(facts)}。'
    return summary or '这一部分需要围绕课件中的核心事实做具体讲解。'


def _collect_grounded_facts(page_contents: list[CirSlideContent]) -> list[str]:
    facts: list[str] = []
    seen: set[str] = set()

    for page_content in page_contents[:3]:
        title = _clean_fact_text(page_content.title)
        if title:
            _push_fact(facts, seen, f'课件标题聚焦“{title}”')

        for body_text in page_content.bodyTexts[:3]:
            for segment in _split_fact_segments(body_text):
                candidate = _clean_fact_text(segment)
                if candidate:
                    _push_fact(facts, seen, candidate)

        for table_text in page_content.tableTexts[:1]:
            cleaned_table = _clean_fact_text(table_text.replace(chr(10), '； '))
            if cleaned_table:
                _push_fact(facts, seen, cleaned_table)

        notes = _clean_fact_text(page_content.notes)
        if notes:
            _push_fact(facts, seen, notes)

    return facts[:4]


def _push_fact(facts: list[str], seen: set[str], candidate: str) -> None:
    normalized = candidate.strip()
    if not normalized or normalized in seen:
        return
    seen.add(normalized)
    facts.append(normalized)


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
    if re.fullmatch(r'第?\d+页', normalized):
        return None
    if normalized.upper() == 'END':
        return None
    return _shorten_text(normalized, 120)


def _build_key_points_sentence(key_points: list[str]) -> str:
    if not key_points:
        return '讲解时要把课件中最关键的概念和事实讲透。'
    return f'课堂上可以把重点收束为：{'；'.join(key_points[:4])}。'


def _build_transition_sentence(
    node_name: str,
    section_index: int,
    total_sections: int,
    next_node_name: str | None,
) -> str:
    if total_sections <= 1:
        return f'把“{node_name}”讲清之后，可以顺势带学生回顾整节课的主线。'
    if section_index < total_sections and next_node_name:
        return f'把这一部分理解清楚后，我们就可以自然过渡到“{next_node_name}”。'
    return '到这里，本节的关键内容就串起来了，最后可以带学生做一个简短回顾。'


def _shorten_text(text: str, limit: int) -> str:
    normalized = ' '.join(part.strip() for part in text.splitlines() if part.strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + '...'


def _estimate_duration(speech_speed: str, content: str) -> int:
    char_count = max(1, len(re.sub(r'\s+', '', content)))
    chars_per_second = {
        'slow': 3.8,
        'normal': 4.6,
        'fast': 5.3,
    }.get(speech_speed, 4.6)
    seconds = math.ceil(char_count / chars_per_second)
    return max(20, min(240, seconds))


def _format_page_refs(page_refs: list[int]) -> str | None:
    if not page_refs:
        return None
    if len(page_refs) == 1:
        return str(page_refs[0])
    return f'{min(page_refs)}-{max(page_refs)}'


def _build_id(prefix: str) -> str:
    return f'S{uuid4().hex[:12].upper()}'
