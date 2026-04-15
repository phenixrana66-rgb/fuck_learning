from threading import Thread

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.common.db import get_db
from backend.app.common.exceptions import ApiError
from backend.app.common.responses import success_response
from backend.app.common.security import verify_signature_placeholder
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import create_parse_task, get_parse_task, run_parse_task
from backend.app.lesson.schemas import GenerateAudioRequest, PlayRequest, PublishRequest
from backend.app.lesson.service import generate_audio as generate_main_audio
from backend.app.lesson.service import play_lesson, publish_lesson
from backend.app.platform.schemas import SyncCourseRequest, SyncUserRequest
from backend.app.platform.service import sync_course as sync_main_course
from backend.app.platform.service import sync_user as sync_main_user
from backend.app.script.schemas import GenerateScriptRequest, UpdateScriptRequest
from backend.app.script.service import generate_script as generate_main_script
from backend.app.script.service import get_script, update_script
from backend.app.teacher_runtime.services import (
    get_parse_status,
    require_teacher,
    run_teacher_parse_task,
    sync_courses,
    sync_user,
    upload_parse,
)

router = APIRouter(tags=["compat"])


async def request_payload(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return payload or {}


def teacher_response(request: Request, data=None, code: int = 200, msg: str = "success") -> dict:
    return {
        "code": code,
        "msg": msg,
        "data": data,
        "requestId": getattr(request.state, "request_id", "req-unknown"),
    }


def _extract_token(request: Request, payload: dict) -> str | None:
    header_token = request.headers.get("X-Platform-Token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    return payload.get("token") or header_token


def _is_teacher_compat_platform_payload(payload: dict) -> bool:
    return "userInfo" not in payload and "courseInfo" not in payload


def _is_teacher_parse_payload(payload: dict) -> bool:
    return "action" in payload


@router.post("/platform/syncUser")
async def sync_user_endpoint(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request_payload(request)
    if _is_teacher_compat_platform_payload(payload):
        try:
            data = sync_user(db, _extract_token(request, payload))
            return teacher_response(request, data)
        except PermissionError:
            raise ApiError(401, "token 无效", status_code=401)

    typed_payload = SyncUserRequest.model_validate(payload)
    verify_signature_placeholder(typed_payload.enc, typed_payload.time)
    data = sync_main_user(typed_payload)
    return success_response(request, data, msg="用户同步成功")


@router.post("/platform/syncCourse")
async def sync_course_endpoint(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request_payload(request)
    if _is_teacher_compat_platform_payload(payload):
        try:
            teacher = require_teacher(db, _extract_token(request, payload))
            data = sync_courses(db, teacher)
            return teacher_response(request, data)
        except PermissionError:
            raise ApiError(401, "token 无效", status_code=401)

    typed_payload = SyncCourseRequest.model_validate(payload)
    verify_signature_placeholder(typed_payload.enc, typed_payload.time)
    data = sync_main_course(typed_payload)
    return success_response(request, data, msg="课程同步成功")


@router.post("/lesson/parse")
async def lesson_parse_endpoint(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request_payload(request)
    try:
        teacher = require_teacher(db, _extract_token(request, payload))
    except PermissionError:
        raise ApiError(401, "token 无效", status_code=401)

    try:
        data = upload_parse(
            db,
            teacher,
            payload.get("courseId"),
            payload.get("fileName"),
            payload.get("fileContent"),
            str(request.base_url),
        )
        Thread(target=run_teacher_parse_task, args=(data["parseId"],), daemon=True).start()
        return teacher_response(request, data)
    except ValueError as exc:
        raise ApiError(400, str(exc), status_code=400)
    except LookupError as exc:
        raise ApiError(404, str(exc), status_code=404)

    # typed_payload = ParseRequest.model_validate(payload)
    # verify_signature_placeholder(typed_payload.enc, typed_payload.time)
    # data = create_parse_task(typed_payload, request_id=getattr(request.state, "request_id", None))
    # Thread(target=run_parse_task, args=(data.parseId, typed_payload.model_copy(deep=True)), daemon=True).start()
    # return success_response(request, data.model_dump(), msg="课件解析任务已创建")


@router.get("/lesson/parse/{parseId}")
def get_parse_task_endpoint(parseId: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """
    统一的解析状态查询接口。
    """
    # 1. 尝试从老师的 ChapterParseTask 表查询
    try:
        # 注意：这里调用你之前的 get_parse_status
        teacher_data = get_parse_status(db, parseId)
        return teacher_response(request, teacher_data)
    except Exception as exc:
        raise ApiError(404, f"未找到任务或查询失败: {parseId}", status_code=404)


@router.post("/lesson/generateScript")
async def generate_script_endpoint(request: Request, db: Session = Depends(get_db)) -> dict:
    _ = db
    payload = await request_payload(request)
    try:
        typed_payload = GenerateScriptRequest.model_validate(payload)
    except ValidationError as exc:
        raise ApiError(400, "generateScript payload is invalid", status_code=400, data={"errors": exc.errors()})

    verify_signature_placeholder(typed_payload.enc, typed_payload.time)
    data = generate_main_script(typed_payload)
    return success_response(request, data.model_dump(), msg="script generated successfully")

@router.put("/scripts/{scriptId}")
async def update_script_endpoint(scriptId: str, request: Request) -> dict:
    payload = await request_payload(request)
    typed_payload = UpdateScriptRequest.model_validate(payload)
    verify_signature_placeholder(typed_payload.enc, typed_payload.time)
    data = update_script(scriptId, typed_payload)
    return success_response(
        request,
        {
            "scriptId": data.scriptId,
            "version": data.version,
            "savedAt": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        },
        msg="脚本保存成功",
    )


@router.post("/lesson/generateAudio")
async def generate_audio_endpoint(request: Request, db: Session = Depends(get_db)) -> dict:
    _ = db
    payload = await request_payload(request)
    try:
        typed_payload = GenerateAudioRequest.model_validate(payload)
    except ValidationError as exc:
        raise ApiError(400, "generateAudio payload is invalid", status_code=400, data={"errors": exc.errors()})

    verify_signature_placeholder(typed_payload.enc, typed_payload.time)
    data = generate_main_audio(typed_payload)
    return success_response(request, data, msg="audio generated successfully")


@router.post("/lesson/publish")
async def publish_lesson_endpoint(request: Request) -> dict:
    payload = await request_payload(request)
    typed_payload = PublishRequest.model_validate(payload)
    verify_signature_placeholder(typed_payload.enc, typed_payload.time)
    data = publish_lesson(typed_payload)
    return success_response(request, data, msg="智课发布任务已创建")


@router.post("/lesson/play")
async def play_lesson_endpoint(request: Request) -> dict:
    payload = await request_payload(request)
    typed_payload = PlayRequest.model_validate(payload)
    verify_signature_placeholder(typed_payload.enc, typed_payload.time)
    data = play_lesson(typed_payload)
    return success_response(request, data, msg="智课播放装配成功")
