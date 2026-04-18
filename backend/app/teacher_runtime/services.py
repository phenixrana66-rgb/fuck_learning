from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.app.common.config import get_settings
from backend.app.common.exceptions import ApiError
from backend.app.courseware.teacher_service import get_parse_status, run_teacher_parse_task, upload_parse
from backend.app.platform.teacher_service import require_teacher, sync_courses, sync_user
from backend.app.script.schemas import GenerateScriptRequest
from backend.app.script.service import generate_script as generate_main_script
from backend.chaoxing_db.models import ChapterAudioAsset, ChapterScript

SCRIPT_TYPE_MAPPING = {
    "standard": "standard",
    "detail": "detailed",
    "simple": "concise",
    "detailed": "detailed",
    "concise": "concise",
}
JsonDict = dict[str, Any]


def _map_script_type(script_type: str | None) -> str:
    normalized = (script_type or "standard").strip()
    mapped = SCRIPT_TYPE_MAPPING.get(normalized)
    if mapped is None:
        raise ApiError(400, f"scriptType is not supported: {normalized}", status_code=400)
    return mapped


def _build_teacher_script_response(parse_id: str, script_type: str | None, summary) -> JsonDict:
    script_content = "\n\n".join(
        section.content.strip()
        for section in summary.scriptStructure
        if isinstance(section.content, str) and section.content.strip()
    )
    return {
        "scriptId": summary.scriptId,
        "parseId": parse_id,
        "scriptType": script_type or "standard",
        "scriptContent": script_content,
        "scriptStructure": [section.model_dump() for section in summary.scriptStructure],
        "status": "success",
    }


def generate_script(db: Session, parse_id: str, script_type: str) -> JsonDict:
    _ = db
    summary = generate_main_script(
        GenerateScriptRequest(
            parseId=parse_id,
            teachingStyle=_map_script_type(script_type),
            speechSpeed="normal",
            customOpening=None,
            enc="teacher-compat",
        )
    )
    return _build_teacher_script_response(parse_id, script_type, summary)


def generate_audio(db: Session, script_id: str, voice_type: str) -> JsonDict:
    script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
    if not script:
        raise LookupError("scriptId 不存在")
    settings = get_settings()
    audio = ChapterAudioAsset(
        course_id=script.course_id,
        chapter_id=script.chapter_id,
        script_id=script.id,
        voice_type=voice_type,
        audio_format="mp3",
        audio_url=settings.default_audio_url,
        total_duration_sec=180,
        status="generated",
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return {
        "audioId": str(audio.id),
        "scriptId": script_id,
        "voiceType": voice_type,
        "audioUrl": audio.audio_url,
        "status": "success",
    }


__all__ = [
    "generate_audio",
    "generate_script",
    "get_parse_status",
    "require_teacher",
    "run_teacher_parse_task",
    "sync_courses",
    "sync_user",
    "upload_parse",
]
