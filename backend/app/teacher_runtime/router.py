from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.common.db import get_db
from backend.app.common.exceptions import ApiError
from backend.app.teacher_runtime.services import generate_audio, generate_script, get_parse_status, require_teacher, sync_courses, sync_user, upload_parse

router = APIRouter()


def build_response(code: int = 200, msg: str = "success", data=None, request_id: str | None = None) -> dict:
    return {"code": code, "msg": msg, "data": data, "requestId": request_id or f"req-{uuid4().hex[:12]}"}


def response(code: int = 200, msg: str = "success", data=None, request_id: str | None = None) -> JSONResponse:
    return JSONResponse(status_code=code, content=build_response(code=code, msg=msg, data=data, request_id=request_id))


async def request_payload(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return payload or {}


def _extract_token(request: Request, payload: dict) -> str | None:
    header_token = request.headers.get("X-Platform-Token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    return payload.get("token") or header_token


@router.post("/api/v1/platform/syncUser")
async def sync_user_api(request: Request, db: Session = Depends(get_db)):
    payload = await request_payload(request)
    try:
        data = sync_user(db, _extract_token(request, payload))
        return response(200, "success", data, getattr(request.state, "request_id", None))
    except PermissionError:
        raise ApiError(401, "token 无效", status_code=401)


@router.post("/api/v1/platform/syncCourse")
async def sync_course_api(request: Request, db: Session = Depends(get_db)):
    payload = await request_payload(request)
    try:
        teacher = require_teacher(db, _extract_token(request, payload))
        data = sync_courses(db, teacher)
        return response(200, "success", data, getattr(request.state, "request_id", None))
    except PermissionError:
        raise ApiError(401, "token 无效", status_code=401)


@router.post("/api/v1/lesson/parse")
async def lesson_parse_api(request: Request, db: Session = Depends(get_db)):
    payload = await request_payload(request)
    try:
        teacher = require_teacher(db, _extract_token(request, payload))
    except PermissionError:
        raise ApiError(401, "token 无效", status_code=401)

    action = payload.get("action")
    try:
        if action == "upload":
            data = upload_parse(db, teacher, payload.get("courseId"), payload.get("fileName"), payload.get("fileContent"))
            return response(200, "success", data, getattr(request.state, "request_id", None))
        if action == "status":
            data = get_parse_status(db, payload.get("parseId"))
            return response(200, "success", data, getattr(request.state, "request_id", None))
        raise ApiError(400, "action 无效，仅支持 upload/status", status_code=400)
    except ValueError as exc:
        raise ApiError(400, str(exc), status_code=400)
    except LookupError as exc:
        raise ApiError(404, str(exc), status_code=404)


@router.post("/api/v1/lesson/generateScript")
async def generate_script_api(request: Request, db: Session = Depends(get_db)):
    payload = await request_payload(request)
    try:
        data = generate_script(db, payload.get("parseId"), payload.get("scriptType", "standard"))
        return response(200, "success", data, getattr(request.state, "request_id", None))
    except LookupError as exc:
        raise ApiError(404, str(exc), status_code=404)


@router.post("/api/v1/lesson/generateAudio")
async def generate_audio_api(request: Request, db: Session = Depends(get_db)):
    payload = await request_payload(request)
    try:
        data = generate_audio(db, payload.get("scriptId"), payload.get("voiceType", "female_standard"))
        return response(200, "success", data, getattr(request.state, "request_id", None))
    except LookupError as exc:
        raise ApiError(404, str(exc), status_code=404)
