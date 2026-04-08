from datetime import UTC, datetime
from uuid import uuid4

from backend.app.common.exceptions import ApiError
from backend.app.courseware.service import get_parse_task
from backend.app.parser.schemas import ParseTaskStatus
from backend.app.script.schemas import GenerateScriptRequest, ScriptDetail, ScriptSection, ScriptSummary, UpdateScriptRequest

_SCRIPT_STORE: dict[str, ScriptDetail] = {}


def generate_script(payload: GenerateScriptRequest) -> ScriptSummary:
    parse_result = get_parse_task(payload.parseId)
    if parse_result.taskStatus != ParseTaskStatus.COMPLETED:
        raise ApiError(code=409, msg="解析任务尚未完成", status_code=409)

    script_id = _build_id("script")
    sections = _build_script_sections(parse_result, payload)
    detail = ScriptDetail(
        scriptId=script_id,
        parseId=payload.parseId,
        teachingStyle=payload.teachingStyle,
        speechSpeed=payload.speechSpeed,
        scriptStructure=sections,
    )
    _SCRIPT_STORE[script_id] = detail
    return ScriptSummary(
        scriptId=script_id,
        scriptStructure=sections,
        editUrl=f"/teacher/scripts/{script_id}/edit",
        audioGenerateUrl="/api/v1/lesson/generateAudio",
    )


def get_script(script_id: str) -> ScriptDetail:
    script = _SCRIPT_STORE.get(script_id)
    if not script:
        raise ApiError(code=404, msg="脚本不存在", status_code=404)
    return script


def update_script(script_id: str, payload: UpdateScriptRequest) -> ScriptDetail:
    script = get_script(script_id)
    script.scriptStructure = payload.scriptStructure
    script.version += 1
    return script


def clear_scripts() -> None:
    _SCRIPT_STORE.clear()


def _build_script_sections(parse_result, payload: GenerateScriptRequest) -> list[ScriptSection]:
    if parse_result.cir is None:
        raise ApiError(code=500, msg="解析结果缺少 CIR", status_code=500)

    sections: list[ScriptSection] = []
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

    return sections


def openning_prefix(opening: str | None, section_index: int) -> str:
    if opening and section_index == 1:
        return opening.strip()
    return ""


def _build_section_content(
    node_name: str,
    summary: str,
    key_points: list[str],
    teaching_style: str,
    opening: str,
) -> str:
    style_prefix = {
        "standard": "先抓住核心概念，再顺着课堂理解路径展开。",
        "detailed": "我们会按知识背景、核心概念和应用理解三层展开。",
        "concise": "这一段只保留最关键的结论与记忆抓手。",
    }.get(teaching_style, "先抓住核心概念，再顺着课堂理解路径展开。")
    key_points_text = "；".join(key_points) if key_points else "本段以整体理解为主。"
    parts = [part for part in [opening, f"本节进入《{node_name}》。", style_prefix, summary or "围绕当前节点做重点讲解。", f"重点包括：{key_points_text}"] if part]
    return " ".join(parts)


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
