from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.common.db import get_db
from backend.app.common.exceptions import ApiError
from backend.app.teacher_runtime.status_service import (
    get_lesson_status,
    list_audios_by_script,
    list_courseware_assets,
    list_scripts_by_parse,
    publish_course_lesson,
    save_script,
)


router = APIRouter(tags=["teacher-runtime-extra"])


def teacher_response(request: Request, data=None, code: int = 200, msg: str = "success") -> dict:
    return {
        "code": code,
        "msg": msg,
        "data": data,
        "requestId": getattr(request.state, "request_id", "req-unknown"),
    }


async def request_payload(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return payload or {}


@router.post("/lesson/saveScript")
async def save_script_endpoint(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request_payload(request)
    script_id = str(payload.get("scriptId") or "").strip()
    script_content = str(payload.get("scriptContent") or "").strip()
    if not script_id:
        raise ApiError(400, "scriptId is required", status_code=400)
    if not script_content:
        raise ApiError(400, "scriptContent is required", status_code=400)

    try:
        data = save_script(db, script_id, script_content)
        return teacher_response(request, data)
    except LookupError as exc:
        raise ApiError(404, str(exc), status_code=404)


@router.post("/lesson/status")
async def lesson_status_endpoint(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request_payload(request)
    course_id = str(payload.get("courseId") or "").strip()
    if not course_id:
        raise ApiError(400, "courseId is required", status_code=400)

    try:
        data = get_lesson_status(db, course_id)
        return teacher_response(request, data)
    except LookupError as exc:
        raise ApiError(404, str(exc), status_code=404)


@router.get("/lesson/courseware/assets")
async def list_courseware_assets_endpoint(request: Request, db: Session = Depends(get_db)) -> dict:
    course_id = str(request.query_params.get("courseId") or "").strip()
    chapter_id = request.query_params.get("chapterId")
    if not course_id:
        raise ApiError(400, "courseId is required", status_code=400)

    try:
        data = list_courseware_assets(db, course_id, chapter_id)
        return teacher_response(request, data)
    except LookupError as exc:
        raise ApiError(404, str(exc), status_code=404)


@router.get("/lesson/parse/{parse_id}/scripts")
async def list_parse_scripts_endpoint(parse_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    try:
        data = list_scripts_by_parse(db, parse_id)
        return teacher_response(request, data)
    except LookupError as exc:
        raise ApiError(404, str(exc), status_code=404)


@router.get("/lesson/scripts/{script_id}/audios")
async def list_script_audios_endpoint(script_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    try:
        data = list_audios_by_script(db, script_id)
        return teacher_response(request, data)
    except LookupError as exc:
        raise ApiError(404, str(exc), status_code=404)


# @router.post("/lesson/publish")
# async def publish_lesson_endpoint(request: Request, db: Session = Depends(get_db)) -> dict:
#     payload = await request_payload(request)
#     course_id = str(payload.get("courseId") or "").strip()
#     chapter_id = payload.get("chapterId")
#     if not course_id:
#         raise ApiError(400, "courseId is required", status_code=400)

#     try:
#         data = publish_course_lesson(db, course_id, chapter_id)
#         return teacher_response(request, data)
#     except ValueError as exc:
#         raise ApiError(400, str(exc), status_code=400)
