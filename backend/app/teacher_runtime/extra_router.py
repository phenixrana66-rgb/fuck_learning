from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.common.db import get_db
from backend.app.common.exceptions import ApiError
from backend.app.platform.teacher_service import require_teacher
from backend.app.student_runtime.qa_lab_service import get_course_outline, run_compare
from backend.app.student_runtime.qa_runtime_config_service import (
    build_student_qa_runtime_config_payload,
    reset_student_qa_runtime_config,
    update_student_qa_runtime_config,
)
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


def _extract_token(request: Request, payload: dict) -> str | None:
    header_token = request.headers.get("X-Platform-Token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    return payload.get("token") or header_token


def _require_teacher_auth(db: Session, request: Request, payload: dict) -> None:
    try:
        require_teacher(db, _extract_token(request, payload))
    except PermissionError:
        raise ApiError(401, "token invalid", status_code=401)


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


@router.get("/qa-lab/runtime-config")
async def qa_lab_runtime_config_get(request: Request, db: Session = Depends(get_db)) -> dict:
    _require_teacher_auth(db, request, {})
    return teacher_response(request, build_student_qa_runtime_config_payload(db))


@router.put("/qa-lab/runtime-config")
async def qa_lab_runtime_config_update(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request_payload(request)
    _require_teacher_auth(db, request, payload)
    data = update_student_qa_runtime_config(db, payload)
    return teacher_response(request, data)


@router.post("/qa-lab/runtime-config/reset")
async def qa_lab_runtime_config_reset(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request_payload(request)
    _require_teacher_auth(db, request, payload)
    data = reset_student_qa_runtime_config(db)
    return teacher_response(request, data)


@router.post("/qa-lab/course-outline")
async def qa_lab_course_outline(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request_payload(request)
    _require_teacher_auth(db, request, payload)
    try:
        data = get_course_outline(db, str(payload.get("courseId") or ""))
        return teacher_response(request, data)
    except ValueError as exc:
        raise ApiError(400, str(exc), status_code=400)
    except LookupError as exc:
        raise ApiError(404, str(exc), status_code=404)


@router.post("/qa-lab/compare")
async def qa_lab_compare(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request_payload(request)
    _require_teacher_auth(db, request, payload)
    try:
        data = run_compare(db, payload)
        return teacher_response(request, data)
    except ValueError as exc:
        raise ApiError(400, str(exc), status_code=400)


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
