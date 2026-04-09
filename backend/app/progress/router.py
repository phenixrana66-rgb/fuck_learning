from fastapi import APIRouter, Request

from backend.app.common.responses import success_response
from backend.app.common.security import verify_signature_placeholder
from backend.app.progress.schemas import AdjustProgressRequest, TrackProgressRequest
from backend.app.progress.service import adjust_progress, track_progress

router = APIRouter(tags=["progress"])


@router.post("/progress/track")
def track_progress_endpoint(payload: TrackProgressRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = track_progress(payload)
    return success_response(request, data, msg="进度追踪成功")


@router.post("/progress/adjust")
def adjust_progress_endpoint(payload: AdjustProgressRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = adjust_progress(payload)
    return success_response(request, data, msg="节奏调整成功")
