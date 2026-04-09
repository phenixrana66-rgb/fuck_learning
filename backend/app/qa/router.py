from fastapi import APIRouter, Request

from backend.app.common.responses import success_response
from backend.app.common.security import verify_signature_placeholder
from backend.app.qa.schemas import QAInteractRequest, VoiceToTextRequest
from backend.app.qa.service import get_session, interact, voice_to_text

router = APIRouter(tags=["qa"])


@router.post("/qa/voiceToText")
def voice_to_text_endpoint(payload: VoiceToTextRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = voice_to_text(payload)
    return success_response(request, data, msg="语音识别成功")


@router.post("/qa/interact")
def qa_interact_endpoint(payload: QAInteractRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = interact(payload)
    return success_response(request, data, msg="问答交互成功")


@router.get("/qa/session/{sessionId}")
def get_qa_session_endpoint(sessionId: str, request: Request) -> dict:
    data = get_session(sessionId)
    return success_response(request, data, msg="问答会话查询成功")
