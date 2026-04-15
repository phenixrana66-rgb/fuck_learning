from __future__ import annotations

from datetime import UTC, datetime
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
from backend.chaoxing_db.models import ChapterAudioAsset, ChapterKnowledgeNode, ChapterParseTask, ChapterScript, ChapterScriptSection


def generate_script(payload: GenerateScriptRequest) -> ScriptSummary:
    parse_result = get_parse_task(payload.parseId)
    if parse_result.taskStatus != ParseTaskStatus.COMPLETED:
        raise ApiError(code=409, msg="解析任务尚未完成", status_code=409)

    script_id = _build_id("script")
    sections, section_nodes = _build_script_sections_with_nodes(parse_result, payload)
    with session_scope() as db:
        parse_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == payload.parseId).first()
        if parse_task is None:
            raise ApiError(code=404, msg="解析任务不存在", status_code=404)

        node_id_map = {node.node_code: node.id for node in parse_task.knowledge_nodes}
        script = ChapterScript(
            script_no=script_id,
            course_id=parse_task.course_id,
            chapter_id=parse_task.chapter_id,
            parse_task_id=parse_task.id,
            teacher_id=parse_task.teacher_id,
            teaching_style=payload.teachingStyle,
            speech_speed=payload.speechSpeed,
            custom_opening=payload.customOpening,
            script_status="generated",
            version_no=1,
        )
        db.add(script)
        db.flush()
        _replace_script_sections(db, script.id, sections, section_nodes, node_id_map)

    return ScriptSummary(
        scriptId=script_id,
        scriptStructure=sections,
        editUrl=f"/teacher/scripts/{script_id}/edit",
        audioGenerateUrl="/api/v1/lesson/generateAudio",
    )


def get_script(script_id: str) -> ScriptDetail:
    with session_scope() as db:
        script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
        if script is None:
            raise ApiError(code=404, msg="脚本不存在", status_code=404)
        return _build_script_detail(script)


def update_script(script_id: str, payload: UpdateScriptRequest) -> ScriptDetail:
    with session_scope() as db:
        script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
        if script is None:
            raise ApiError(code=404, msg="脚本不存在", status_code=404)

        parse_task = script.parse_task
        if parse_task is None:
            raise ApiError(code=404, msg="解析任务不存在", status_code=404)

        existing_node_map = {section.section_code: section.related_node_id for section in script.sections}
        parse_result = get_parse_task(parse_task.parse_no)
        section_nodes = _build_section_nodes_from_parse(parse_result)
        node_id_map = {node.node_code: node.id for node in parse_task.knowledge_nodes}

        script.teaching_style = script.teaching_style
        script.speech_speed = script.speech_speed
        script.script_status = "edited"
        script.version_no += 1

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
        raise ApiError(code=500, msg="解析结果缺少 CIR", status_code=500)

    sections: list[ScriptSection] = []
    section_nodes: dict[str, LessonNode] = {}
    section_index = 1
    opening = payload.customOpening

    for chapter in parse_result.cir.chapters:
        for node in chapter.nodes:
            section_id = f"sec{section_index:03d}"
            key_points = node.keyPoints[:3]
            summary = node.summary.strip()
            section_content = _build_section_content(
                node_name=node.nodeName,
                summary=summary,
                key_points=key_points,
                page_contents=node.pageContents,
                teaching_style=payload.teachingStyle,
                opening=openning_prefix(opening, section_index),
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
                sectionId="sec001",
                sectionName=parse_result.cir.title or "课件导入",
                content=(opening or "同学们好，下面我们进入本节内容的核心讲解。") + " 当前课件未抽取到可用节点，先围绕整体主题进行导学。",
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
        version=script.version_no,
    )


def _build_section_nodes_from_parse(parse_result: ParseQueryData) -> dict[str, LessonNode]:
    if parse_result.cir is None:
        return {}
    section_nodes: dict[str, LessonNode] = {}
    section_index = 1
    for chapter in parse_result.cir.chapters:
        for node in chapter.nodes:
            section_nodes[f"sec{section_index:03d}"] = node
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


def openning_prefix(opening: str | None, section_index: int) -> str:
    if opening and section_index == 1:
        return opening.strip()
    return ""


def _build_section_content(
    node_name: str,
    summary: str,
    key_points: list[str],
    page_contents: list[CirSlideContent],
    teaching_style: str,
    opening: str,
) -> str:
    style_prefix = {
        "standard": "先抓住核心概念，再顺着课堂理解路径展开。",
        "detailed": "我们会按知识背景、核心概念和应用理解三层展开。",
        "concise": "这一段只保留最关键的结论与记忆抓手。",
    }.get(teaching_style, "先抓住核心概念，再顺着课堂理解路径展开。")
    key_points_text = "；".join(key_points) if key_points else "本段以整体理解为主。"
    source_explanation = _build_page_grounded_explanation(page_contents)
    parts = [
        part
        for part in [
            opening,
            f"本节讲解《{node_name}》。",
            style_prefix,
            source_explanation or summary or "围绕当前节点做重点讲解。",
            f"重点包括：{key_points_text}",
        ]
        if part
    ]
    return " ".join(parts)


def _build_page_grounded_explanation(page_contents: list[CirSlideContent]) -> str:
    explanations: list[str] = []
    for page_content in page_contents[:3]:
        fragments: list[str] = []
        if page_content.title:
            fragments.append(f"第{page_content.slideNumber}页标题是《{_shorten_text(page_content.title, 40)}》")

        for body_text in page_content.bodyTexts[:2]:
            fragments.append(f"这一页重点提到：{_shorten_text(body_text, 90)}")

        for table_text in page_content.tableTexts[:1]:
            fragments.append(f"表格信息显示：{_shorten_text(table_text.replace(chr(10), '；'), 120)}")

        if page_content.notes:
            fragments.append(f"备注中补充了：{_shorten_text(page_content.notes, 80)}")

        if fragments:
            explanations.append("，".join(fragments) + "。")

    return " ".join(explanations)


def _shorten_text(text: str, limit: int) -> str:
    normalized = " ".join(part.strip() for part in text.splitlines() if part.strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _estimate_duration(speech_speed: str, key_points: list[str]) -> int:
    base_duration = 35 + len(key_points) * 8
    if speech_speed == "slow":
        return base_duration + 10
    if speech_speed == "fast":
        return max(20, base_duration - 8)
    return base_duration


def _format_page_refs(page_refs: list[int]) -> str | None:
    if not page_refs:
        return None
    if len(page_refs) == 1:
        return str(page_refs[0])
    return f"{min(page_refs)}-{max(page_refs)}"


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"
