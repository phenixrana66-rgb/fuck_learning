from __future__ import annotations

from typing import Any

from anyio import to_thread
from fastapi import WebSocket

from backend.app.common.db import session_scope
from backend.app.student_runtime.db_qa_service import save_voice_transcript
from backend.app.student_runtime.qa_asr_service import AudioPayloadError, _decode_audio_base64
from backend.app.student_runtime.qa_dashscope_client import DashScopeClient


async def transcribe_stream_payload(payload: dict[str, Any]) -> dict[str, Any]:
    audio_bytes = _decode_audio_base64(payload.get("audioBase64", ""))
    file_name = payload.get("fileName") or "voice-stream.webm"
    transcript_text = await to_thread.run_sync(
        lambda: DashScopeClient().transcribe_audio(file_name=file_name, audio_bytes=audio_bytes)
    )
    return {"text": transcript_text.strip(), "final": bool(payload.get("final"))}


async def handle_realtime_asr_message(websocket: WebSocket, payload: dict[str, Any], state: dict[str, Any]) -> None:
    message_type = payload.get("type")
    if message_type == "start":
        state.update(
            {
                "studentId": payload.get("studentId"),
                "lessonId": payload.get("lessonId"),
                "sectionId": payload.get("sectionId"),
                "lastText": "",
            }
        )
        await websocket.send_json({"type": "ready"})
        return

    if message_type != "audio":
        await websocket.send_json({"type": "error", "message": "不支持的语音消息类型。"})
        return

    try:
        result = await transcribe_stream_payload(payload)
    except AudioPayloadError as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        return
    except Exception as exc:  # pragma: no cover - network/service failures
        await websocket.send_json({"type": "error", "message": f"语音识别失败：{exc}"})
        return

    transcript_text = result["text"]
    state["lastText"] = transcript_text
    await websocket.send_json(
        {
            "type": "transcript",
            "text": transcript_text,
            "final": result["final"],
            "seq": payload.get("seq"),
        }
    )

    if result["final"] and transcript_text:
        with session_scope() as db:
            saved = save_voice_transcript(
                db,
                student_identifier=state.get("studentId"),
                lesson_identifier=state.get("lessonId"),
                section_identifier=state.get("sectionId"),
                transcript_text=transcript_text,
                audio_url=None,
            )
        if saved and saved.get("transcriptId"):
            await websocket.send_json({"type": "saved", "transcriptId": saved["transcriptId"], "text": transcript_text})
