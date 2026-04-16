from __future__ import annotations

import logging
import math
import re
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete

from backend.app.cir.schemas import CIR, CirSlideContent, LessonNode
from backend.app.common.db import session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseQueryData
from backend.app.courseware.service import get_parse_task
from backend.app.parser.schemas import ParseTaskStatus
from backend.app.script.llm_client import generate_script_section_with_llm
from backend.app.script.schemas import GenerateScriptRequest, ScriptDetail, ScriptSection, ScriptSummary, UpdateScriptRequest
from backend.chaoxing_db.models import ChapterAudioAsset, ChapterParseTask, ChapterScript, ChapterScriptSection

logger = logging.getLogger(__name__)


@dataclass
class _ScriptGenerationTask:
    script_id: str
    parse_id: str
    status: str
    total_sections: int
    completed_sections: int = 0
    current_section_id: str | None = None
    current_section_name: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error_msg: str | None = None


_TASK_LOCK = threading.Lock()
_SCRIPT_TASKS: dict[str, _ScriptGenerationTask] = {}


def generate_script(payload: GenerateScriptRequest) -> ScriptSummary:
    parse_result = get_parse_task(payload.parseId)
    if parse_result.taskStatus != ParseTaskStatus.COMPLETED:
        raise ApiError(code=409, msg='parse task is not completed', status_code=409)

    script_id = _build_id('script')
    sections, section_nodes = _build_script_sections_skeleton_with_nodes(parse_result, payload)

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

    if section_nodes:
        _create_runtime_task(script_id, payload.parseId, total_sections=len(sections), status='running')
        worker = threading.Thread(
            target=_run_script_generation,
            args=(script_id, payload, sections, section_nodes),
            daemon=True,
            name=f'script-gen-{script_id}',
        )
        worker.start()
    else:
        _create_runtime_task(script_id, payload.parseId, total_sections=len(sections), status='completed')
        _mark_task_completed(script_id, len(sections))

    return ScriptSummary(
        scriptId=script_id,
        scriptStructure=sections,
        editUrl=f'/teacher/scripts/{script_id}/edit',
        audioGenerateUrl='/api/v1/lesson/generateAudio',
        **_build_runtime_payload(script_id, len(sections), _count_completed_sections(sections)),
    )


def get_script(script_id: str) -> ScriptDetail:
    with session_scope() as db:
        script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
        if script is None:
            raise ApiError(code=404, msg='script not found', status_code=404)
        detail = _build_script_detail(script)

    runtime_payload = _build_runtime_payload(
        script_id,
        total_sections=len(detail.scriptStructure),
        completed_sections=_count_completed_sections(detail.scriptStructure),
    )
    return detail.model_copy(update=runtime_payload)


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
        detail = _build_script_detail(script, parse_result=parse_result)

    runtime_payload = _build_runtime_payload(
        script_id,
        total_sections=len(detail.scriptStructure),
        completed_sections=_count_completed_sections(detail.scriptStructure),
    )
    return detail.model_copy(update=runtime_payload)


def clear_scripts() -> None:
    with session_scope() as db:
        db.execute(delete(ChapterAudioAsset))
        db.execute(delete(ChapterScriptSection))
        db.execute(delete(ChapterScript))
    with _TASK_LOCK:
        _SCRIPT_TASKS.clear()


def _run_script_generation(
    script_id: str,
    payload: GenerateScriptRequest,
    sections: list[ScriptSection],
    section_nodes: dict[str, LessonNode],
) -> None:
    previous_summary: str | None = None
    total_sections = len(sections)
    try:
        for index, section in enumerate(sections):
            node = section_nodes.get(section.sectionId)
            if node is None:
                _mark_task_progress(script_id, index + 1)
                continue

            next_section_name = sections[index + 1].sectionName if index + 1 < total_sections else None
            _mark_task_current(script_id, section.sectionId, section.sectionName)
            generated = generate_script_section_with_llm(
                payload,
                section_name=section.sectionName,
                section_key_points=section.keyPoints,
                page_contents=node.pageContents,
                previous_summary=previous_summary,
                next_section_name=next_section_name,
                is_first_section=index == 0,
                is_last_section=index == total_sections - 1,
            )
            content = generated['content'].strip()
            previous_summary = generated['summaryForNext'].strip() or _build_summary_for_next(content, section.sectionName, next_section_name)
            duration = _estimate_duration(payload.speechSpeed, content)
            _update_script_section_content(script_id, section.sectionId, content, duration)
            _mark_task_progress(script_id, index + 1)

        _mark_task_completed(script_id, total_sections)
    except Exception as exc:  # noqa: BLE001
        logger.exception('script generation failed for script_id=%s', script_id)
        message = exc.msg if isinstance(exc, ApiError) else str(exc) or '脚本生成失败'
        _mark_task_failed(script_id, message)


def _build_script_sections_skeleton(parse_result: ParseQueryData, payload: GenerateScriptRequest) -> list[ScriptSection]:
    sections, _ = _build_script_sections_skeleton_with_nodes(parse_result, payload)
    return sections


def _build_script_sections_skeleton_with_nodes(
    parse_result: ParseQueryData,
    payload: GenerateScriptRequest,
) -> tuple[list[ScriptSection], dict[str, LessonNode]]:
    if parse_result.cir is None:
        raise ApiError(code=500, msg='parse result is missing CIR', status_code=500)

    sections: list[ScriptSection] = []
    section_nodes: dict[str, LessonNode] = {}
    section_index = 1

    for chapter in parse_result.cir.chapters:
        for node in chapter.nodes:
            section_id = f'sec{section_index:03d}'
            key_points = node.keyPoints[:4]
            sections.append(
                ScriptSection(
                    sectionId=section_id,
                    sectionName=node.nodeName,
                    content='',
                    duration=0,
                    relatedChapterId=chapter.chapterId,
                    relatedPage=_format_page_refs(node.pageRefs),
                    keyPoints=key_points,
                )
            )
            section_nodes[section_id] = node
            section_index += 1

    if not sections:
        empty_content = _build_empty_script_content(parse_result.cir.title or '课件讲解', _normalize_opening(payload.customOpening))
        sections.append(
            ScriptSection(
                sectionId='sec001',
                sectionName=parse_result.cir.title or '课件导入',
                content=empty_content,
                duration=_estimate_duration(payload.speechSpeed, empty_content),
                keyPoints=[],
            )
        )

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


def _update_script_section_content(script_id: str, section_id: str, content: str, duration: int) -> None:
    with session_scope() as db:
        section = (
            db.query(ChapterScriptSection)
            .join(ChapterScript, ChapterScriptSection.script_id == ChapterScript.id)
            .filter(ChapterScript.script_no == script_id, ChapterScriptSection.section_code == section_id)
            .first()
        )
        if section is None:
            raise ApiError(code=404, msg='script section not found', status_code=404)
        section.section_content = content
        section.duration_sec = duration


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
        content=section.section_content or '',
        duration=section.duration_sec or 0,
        relatedChapterId=chapter_lookup.get(node_code) if node_code else None,
        relatedPage=section.related_page_range,
        keyPoints=node.keyPoints[:4] if node else [],
    )


def _normalize_opening(opening: str | None) -> str | None:
    if opening is None:
        return None
    normalized = opening.strip()
    return normalized or None


def _build_empty_script_content(courseware_title: str, opening: str | None) -> str:
    parts = [
        opening,
        f'这份课件暂时还没有抽取出可直接生成脚本的章节节点，我们先围绕“{courseware_title}”做一个简短导入。',
        '建议老师先补充清晰的章节划分，再重新生成讲稿，这样每一段会更贴近课堂讲解。',
    ]
    return ' '.join(part for part in parts if part)


def _build_summary_for_next(content: str, section_name: str, next_section_name: str | None) -> str:
    sentences = [part.strip() for part in re.split(r'[。！？!?]', content) if part.strip()]
    summary_parts = []
    if sentences:
        summary_parts.append(f'上一部分已经讲清了{section_name}。')
        summary_parts.append(_shorten_text(sentences[-1], 48))
    if next_section_name:
        summary_parts.append(f'接下来转到{next_section_name}。')
    return ' '.join(part for part in summary_parts if part)


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


def _count_completed_sections(sections: list[ScriptSection]) -> int:
    return sum(1 for section in sections if section.content and section.content.strip())


def _create_runtime_task(script_id: str, parse_id: str, total_sections: int, status: str) -> None:
    task = _ScriptGenerationTask(
        script_id=script_id,
        parse_id=parse_id,
        status=status,
        total_sections=total_sections,
        completed_sections=0 if status == 'running' else total_sections,
        started_at=_now_iso(),
        finished_at=_now_iso() if status == 'completed' else None,
    )
    with _TASK_LOCK:
        _SCRIPT_TASKS[script_id] = task


def _mark_task_current(script_id: str, section_id: str, section_name: str) -> None:
    with _TASK_LOCK:
        task = _SCRIPT_TASKS.get(script_id)
        if task is None:
            return
        task.current_section_id = section_id
        task.current_section_name = section_name


def _mark_task_progress(script_id: str, completed_sections: int) -> None:
    with _TASK_LOCK:
        task = _SCRIPT_TASKS.get(script_id)
        if task is None:
            return
        task.completed_sections = min(completed_sections, task.total_sections)


def _mark_task_completed(script_id: str, completed_sections: int) -> None:
    with _TASK_LOCK:
        task = _SCRIPT_TASKS.get(script_id)
        if task is None:
            return
        task.status = 'completed'
        task.completed_sections = min(completed_sections, task.total_sections)
        task.current_section_id = None
        task.current_section_name = None
        task.finished_at = _now_iso()
        task.error_msg = None


def _mark_task_failed(script_id: str, error_msg: str) -> None:
    with _TASK_LOCK:
        task = _SCRIPT_TASKS.get(script_id)
        if task is None:
            return
        task.status = 'failed'
        task.finished_at = _now_iso()
        task.error_msg = error_msg


def _build_runtime_payload(script_id: str, total_sections: int, completed_sections: int) -> dict[str, object]:
    with _TASK_LOCK:
        task = _SCRIPT_TASKS.get(script_id)
        if task is not None:
            return {
                'generationStatus': task.status,
                'completedSections': max(completed_sections, task.completed_sections),
                'totalSections': max(total_sections, task.total_sections),
                'currentSectionId': task.current_section_id,
                'currentSectionName': task.current_section_name,
                'startedAt': task.started_at,
                'finishedAt': task.finished_at,
                'errorMsg': task.error_msg,
            }

    derived_status = _derive_generation_status(total_sections, completed_sections)
    return {
        'generationStatus': derived_status,
        'completedSections': completed_sections,
        'totalSections': total_sections,
        'currentSectionId': None,
        'currentSectionName': None,
        'startedAt': None,
        'finishedAt': None,
        'errorMsg': None,
    }


def _derive_generation_status(total_sections: int, completed_sections: int) -> str:
    if total_sections == 0:
        return 'pending'
    if completed_sections >= total_sections:
        return 'completed'
    if completed_sections > 0:
        return 'interrupted'
    return 'pending'


def _shorten_text(text: str, limit: int) -> str:
    normalized = ' '.join(part.strip() for part in text.splitlines() if part.strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + '...'


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _build_id(prefix: str) -> str:
    return f'S{uuid4().hex[:12].upper()}'
