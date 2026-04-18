from __future__ import annotations

import base64
from typing import Any

from sqlalchemy.orm import Session

from backend.app.student_runtime.db_qa_service import save_voice_transcript
from backend.app.student_runtime.qa_dashscope_client import DashScopeClient


class AudioPayloadError(ValueError):
    pass


def _decode_audio_base64(audio_base64: str) -> bytes:
    if not audio_base64 or not isinstance(audio_base64, str):
        raise AudioPayloadError("未提供有效的音频数据。")
    normalized = audio_base64.strip()
    if "," in normalized and normalized.lower().startswith("data:"):
        normalized = normalized.split(",", 1)[1]
    try:
        return base64.b64decode(normalized, validate=True)
    except Exception as exc:
        raise AudioPayloadError("音频数据不是合法的 Base64 内容。") from exc


def transcribe_audio_payload(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    audio_bytes = _decode_audio_base64(payload.get("audioBase64", ""))
    file_name = payload.get("fileName") or "voice.webm"
    transcript_text = DashScopeClient().transcribe_audio(file_name=file_name, audio_bytes=audio_bytes)
    saved = save_voice_transcript(
        db,
        student_identifier=payload.get("studentId"),
        lesson_identifier=payload.get("lessonId"),
        section_identifier=payload.get("sectionId"),
        transcript_text=transcript_text,
        audio_url=None,
    )
    result = {"text": transcript_text}
    if saved and saved.get("transcriptId"):
        result["transcriptId"] = saved["transcriptId"]
    return result
