from datetime import UTC, datetime
from uuid import uuid4

from backend.app.common.exceptions import ApiError
from backend.app.courseware.service import get_parse_task
from backend.app.lesson.schemas import AudioInfo, GenerateAudioRequest, PlayRequest, PublishRequest, SectionAudio
from backend.app.parser.schemas import ParseTaskStatus
from backend.app.script.service import get_script
from backend.app.tasks.service import create_task, mark_task_completed

_AUDIO_STORE: dict[str, dict] = {}
_LESSON_PACKAGES: dict[str, dict] = {}


def generate_audio(payload: GenerateAudioRequest) -> dict:
    script = get_script(payload.scriptId)
    audio_id = _build_id("audio")
    section_map = {section.sectionId: section for section in script.scriptStructure}
    target_sections = payload.sectionIds or list(section_map.keys())
    if not target_sections:
        raise ApiError(code=400, msg="脚本缺少可用章节", status_code=400)

    missing_sections = [section_id for section_id in target_sections if section_id not in section_map]
    if missing_sections:
        raise ApiError(code=404, msg="脚本章节不存在", status_code=404, data={"sectionIds": missing_sections})

    create_task(audio_id, "lesson.generateAudio", {"scriptId": payload.scriptId})
    section_audios = [
        SectionAudio(
            sectionId=section_id,
            audioUrl=f"https://example.com/audio/{audio_id}/{section_id}.{payload.audioFormat}",
            duration=section_map[section_id].duration,
        )
        for section_id in target_sections
    ]
    data = {
        "audioId": audio_id,
        "scriptId": payload.scriptId,
        "audioUrl": f"https://example.com/audio/{audio_id}.{payload.audioFormat}",
        "audioInfo": AudioInfo(
            totalDuration=sum(item.duration for item in section_audios),
            fileSize=4_800_000 + len(section_audios) * 320_000,
            format=payload.audioFormat,
            bitRate=128_000,
        ).model_dump(),
        "sectionAudios": [item.model_dump() for item in section_audios],
        "taskStatus": "completed",
    }
    _AUDIO_STORE[audio_id] = data
    mark_task_completed(audio_id, result=data)
    return data


def publish_lesson(payload: PublishRequest) -> dict:
    script = get_script(payload.scriptId)
    parse_result = get_parse_task(script.parseId)
    if parse_result.taskStatus != ParseTaskStatus.COMPLETED or parse_result.cir is None:
        raise ApiError(code=409, msg="解析任务尚未完成", status_code=409)

    audio = _AUDIO_STORE.get(payload.audioId)
    if audio is None:
        raise ApiError(code=404, msg="音频不存在", status_code=404)
    if audio.get("scriptId") != payload.scriptId:
        raise ApiError(code=409, msg="音频与脚本不匹配", status_code=409)
    if parse_result.cir.coursewareId != payload.coursewareId:
        raise ApiError(code=409, msg="课件与脚本不匹配", status_code=409)

    lesson_id = _build_id("lesson")
    publish_id = _build_id("publish")
    create_task(publish_id, "lesson.publish", {"lessonId": lesson_id, "scriptId": payload.scriptId, "audioId": payload.audioId})
    script_refs = [{"sectionId": section.sectionId, "scriptId": payload.scriptId} for section in script.scriptStructure]
    audio_ref_map = {item["sectionId"]: payload.audioId for item in audio["sectionAudios"]}
    audio_refs = [{"sectionId": section.sectionId, "audioId": audio_ref_map[section.sectionId]} for section in script.scriptStructure if section.sectionId in audio_ref_map]
    node_sequence = [node.nodeId for chapter in parse_result.cir.chapters for node in chapter.nodes]
    data = {
        "publishId": publish_id,
        "lessonId": lesson_id,
        "publishStatus": "published",
        "snapshot": {
            "coursewareId": payload.coursewareId,
            "scriptId": payload.scriptId,
            "audioId": payload.audioId,
            "parseId": script.parseId,
            "nodeSequence": node_sequence,
            "scriptRefs": script_refs,
            "audioRefs": audio_refs,
        },
    }
    _LESSON_PACKAGES[lesson_id] = data
    mark_task_completed(publish_id, result=data)
    return data


def play_lesson(payload: PlayRequest) -> dict:
    package = _LESSON_PACKAGES.get(payload.lessonId)
    current_section_id = _extract_current_section(payload.resumeContext)
    if package is None:
        raise ApiError(code=404, msg="智课不存在", status_code=404)

    snapshot = package["snapshot"]
    available_section_ids = [item["sectionId"] for item in snapshot.get("scriptRefs", [])]
    if current_section_id not in available_section_ids and available_section_ids:
        current_section_id = available_section_ids[0]
    return {
        "lessonId": package["lessonId"],
        "nodeSequence": snapshot.get("nodeSequence", []),
        "scriptRefs": snapshot.get("scriptRefs", []),
        "audioRefs": snapshot.get("audioRefs", []),
        "currentSectionId": current_section_id,
    }


def _extract_current_section(resume_context: dict | None) -> str:
    if not resume_context:
        return "sec001"
    current_section_id = resume_context.get("currentSectionId")
    return current_section_id if isinstance(current_section_id, str) and current_section_id else "sec001"


def clear_lessons() -> None:
    _AUDIO_STORE.clear()
    _LESSON_PACKAGES.clear()


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"
