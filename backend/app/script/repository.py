from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.cir.schemas import CIR, LessonNode
from backend.app.common.db import session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseQueryData
from backend.app.courseware.service import get_parse_task
from backend.app.parser.schemas import ParseTaskStatus
from backend.app.script.schemas import ScriptDetail, ScriptSection
from backend.chaoxing_db.models import ChapterAudioAsset, ChapterParseTask, ChapterScript, ChapterScriptSection


def save_script(script: ScriptDetail) -> ScriptDetail:
    parse_result = get_parse_task(script.parseId)
    if parse_result.taskStatus != ParseTaskStatus.COMPLETED:
        raise ApiError(code=409, msg='parse task is not completed', status_code=409)

    with session_scope() as session:
        parse_task = session.query(ChapterParseTask).filter(ChapterParseTask.parse_no == script.parseId).first()
        if parse_task is None:
            raise ApiError(code=404, msg='parse task not found', status_code=404)

        entity = session.query(ChapterScript).filter(ChapterScript.script_no == script.scriptId).first()
        if entity is None:
            entity = ChapterScript(
                script_no=script.scriptId,
                course_id=parse_task.course_id,
                chapter_id=parse_task.chapter_id,
                parse_task_id=parse_task.id,
                teacher_id=parse_task.teacher_id,
                script_status='edited' if script.version > 1 else 'generated',
                edit_url=f'/teacher/scripts/{script.scriptId}/edit',
            )
            session.add(entity)
            session.flush()
        elif entity.parse_task.parse_no != script.parseId:
            raise ApiError(code=409, msg='script and parse task do not match', status_code=409)

        entity.teaching_style = script.teachingStyle
        entity.speech_speed = script.speechSpeed
        if entity.script_status != 'published' and script.version > 1:
            entity.script_status = 'edited'
        if not entity.edit_url:
            entity.edit_url = f'/teacher/scripts/{script.scriptId}/edit'

        for section in list(entity.sections):
            session.delete(section)
        session.flush()

        _replace_script_sections(session, entity.id, parse_task, parse_result, script.scriptStructure)
    return script


def load_script(script_id: str) -> ScriptDetail | None:
    with session_scope() as session:
        entity = session.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
        return _entity_to_script(entity) if entity else None


def load_all_scripts() -> dict[str, ScriptDetail]:
    with session_scope() as session:
        entities = session.scalars(select(ChapterScript)).all()
        scripts = [_entity_to_script(entity) for entity in entities]
        return {script.scriptId: script for script in scripts}


def clear_script_records() -> None:
    with session_scope() as session:
        session.execute(delete(ChapterAudioAsset))
        session.execute(delete(ChapterScriptSection))
        session.execute(delete(ChapterScript))


def _script_version(entity: ChapterScript) -> int:
    return 2 if entity.script_status == 'edited' else 1


def _entity_to_script(entity: ChapterScript) -> ScriptDetail:
    parse_result = get_parse_task(entity.parse_task.parse_no)
    node_lookup = _build_node_lookup(parse_result.cir)
    chapter_lookup = _build_chapter_lookup(parse_result.cir)
    knowledge_lookup = {node.id: node.node_code for node in entity.parse_task.knowledge_nodes}
    return ScriptDetail.model_validate(
        {
            'scriptId': entity.script_no,
            'parseId': entity.parse_task.parse_no,
            'teachingStyle': entity.teaching_style,
            'speechSpeed': entity.speech_speed,
            'scriptStructure': [
                _build_script_section(section, knowledge_lookup, node_lookup, chapter_lookup)
                for section in sorted(entity.sections, key=lambda item: (item.sort_no, item.id))
            ],
            'version': _script_version(entity),
        }
    )


def _replace_script_sections(
    session: Session,
    script_db_id: int,
    parse_task: ChapterParseTask,
    parse_result: ParseQueryData,
    sections: list[ScriptSection],
) -> None:
    section_nodes = _build_section_nodes_from_parse(parse_result)
    node_id_map = {node.node_code: node.id for node in parse_task.knowledge_nodes}
    for sort_no, section in enumerate(sections):
        node = section_nodes.get(section.sectionId)
        related_node_id = node_id_map.get(node.nodeId) if node is not None else None
        session.add(
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
