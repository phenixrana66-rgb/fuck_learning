from uuid import uuid4

import bootstrap  # noqa: F401
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db import get_db
from services.audio_service import generate_audio
from services.auth_service import require_teacher, sync_user
from services.course_service import sync_courses
from services.parse_service import get_parse_status, upload_parse
from services.script_service import generate_script


class ApiError(Exception):
    def __init__(self, status_code: int, msg: str, data=None, request_id: str | None = None):
        super().__init__(msg)
        self.status_code = status_code
        self.msg = msg
        self.data = data
        self.request_id = request_id


app = FastAPI(title="Teacher Plugin Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_response(code=200, msg="success", data=None, request_id=None):
    return {
        "code": code,
        "msg": msg,
        "data": data,
        "requestId": request_id or f"req-{uuid4().hex[:12]}",
    }


def response(code=200, msg="success", data=None, request_id=None):
    return JSONResponse(
        status_code=code,
        content=build_response(code=code, msg=msg, data=data, request_id=request_id),
    )


async def request_payload(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return payload or {}


@app.exception_handler(ApiError)
async def handle_api_error(_request: Request, exc: ApiError):
    return response(exc.status_code, exc.msg, exc.data, exc.request_id)


@app.exception_handler(Exception)
async def handle_unexpected_error(_request: Request, _exc: Exception):
    return response(500, "教师端服务异常", None)


def _extract_token(request: Request, payload: dict) -> str | None:
    header_token = request.headers.get("X-Platform-Token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    return payload.get("token") or header_token


@app.post("/api/v1/platform/syncUser")
async def sync_user_api(request: Request, db: Session = Depends(get_db)):
    payload = await request_payload(request)
    try:
        data = sync_user(db, _extract_token(request, payload))
        return response(200, "success", data)
    except PermissionError:
        raise ApiError(401, "token 无效")


@app.post("/api/v1/platform/syncCourse")
async def sync_course_api(request: Request, db: Session = Depends(get_db)):
    payload = await request_payload(request)
    try:
        teacher = require_teacher(db, _extract_token(request, payload))
        data = sync_courses(db, teacher)
        return response(200, "success", data)
    except PermissionError:
        raise ApiError(401, "token 无效")


@app.post("/api/v1/lesson/parse")
async def lesson_parse_api(request: Request, db: Session = Depends(get_db)):
    payload = await request_payload(request)
    try:
        teacher = require_teacher(db, _extract_token(request, payload))
    except PermissionError:
        raise ApiError(401, "token 无效")
    action = payload.get("action")
    try:
        if action == "upload":
            data = upload_parse(
                db,
                teacher,
                payload.get("courseId"),
                payload.get("fileName"),
                payload.get("fileContent"),
            )
            return response(200, "success", data)
        if action == "status":
            data = get_parse_status(db, payload.get("parseId"))
            return response(200, "success", data)
        raise ApiError(400, "action 无效，仅支持 upload/status")
    except ValueError as exc:
        raise ApiError(400, str(exc))
    except LookupError as exc:
        raise ApiError(404, str(exc))


@app.post("/api/v1/lesson/generateScript")
async def generate_script_api(request: Request, db: Session = Depends(get_db)):
    payload = await request_payload(request)
    try:
        data = generate_script(db, payload.get("parseId"), payload.get("scriptType", "standard"))
        return response(200, "success", data)
    except LookupError as exc:
        raise ApiError(404, str(exc))


@app.post("/api/v1/lesson/generateAudio")
async def generate_audio_api(request: Request, db: Session = Depends(get_db)):
    payload = await request_payload(request)
    try:
        data = generate_audio(db, payload.get("scriptId"), payload.get("voiceType", "female_standard"))
        return response(200, "success", data)
    except LookupError as exc:
        raise ApiError(404, str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=3001, reload=True)
