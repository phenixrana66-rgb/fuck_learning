from fastapi import APIRouter, Request

from backend.app.common.responses import success_response
from backend.app.common.security import verify_signature_placeholder
from backend.app.lesson.schemas import GenerateAudioRequest, PlayRequest, PublishRequest
from backend.app.lesson.service import generate_audio, play_lesson, publish_lesson

router = APIRouter(tags=["lesson"])


@router.post("/lesson/generateAudio")
def generate_audio_endpoint(payload: GenerateAudioRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = generate_audio(payload, base_url=str(request.base_url))
    return success_response(request, data, msg="语音合成任务已创建")


@router.post("/lesson/publish")
def publish_lesson_endpoint(payload: PublishRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = publish_lesson(payload)
    return success_response(request, data, msg="智课发布任务已创建")


@router.post("/lesson/play")
def play_lesson_endpoint(payload: PlayRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = play_lesson(payload)
    return success_response(request, data, msg="智课播放装配成功")
