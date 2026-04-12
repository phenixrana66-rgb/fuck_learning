from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.common.db import get_db
from backend.app.common.exceptions import ApiError
from backend.app.common.security import verify_signature_payload
from backend.app.student_runtime.adapter import ChaoxingAdapter
from backend.app.student_runtime.db_learning_service import enhance_player_with_db, get_db_progress_state, get_recent_chapter_visits, get_section_detail, get_student_profile_from_db, interact_with_section_context, mark_page_read, save_recent_chapter_visit
from backend.app.student_runtime.db_qa_service import get_qa_sessions, save_qa_session
from backend.app.student_runtime.learning_service import LearningService

router = APIRouter()
adapter = ChaoxingAdapter()
learning_service = LearningService(adapter)


def build_response(code=200, msg="success", data=None, request_id=None):
    return {"code": code, "msg": msg, "data": data, "requestId": request_id or f"req-{uuid4().hex[:12]}"}


def response(code=200, msg="success", data=None, request_id=None):
    return JSONResponse(status_code=code, content=build_response(code=code, msg=msg, data=data, request_id=request_id))


async def request_payload(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return payload or {}


async def require_signature(request: Request):
    payload = await request_payload(request)
    verify_signature_payload(payload)
    return payload


@router.post("/auth/verify")
async def auth_verify(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    token = payload.get("token") or request.headers.get("X-Platform-Token", "")
    try:
        data = adapter.verify(token)
        db_student = get_student_profile_from_db(db, payload.get("studentId") or data.get("student", {}).get("studentId"))
        if db_student:
            data["student"] = {**data.get("student", {}), **db_student}
        return response(200, "success", data, getattr(request.state, "request_id", None))
    except PermissionError:
        raise ApiError(401, "免登 token 无效", status_code=401)


@router.post("/api/v1/getStudentLessonList")
async def get_student_lesson_list(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    student_id = payload.get("studentId")
    lessons = adapter.get_student_lessons(student_id)
    try:
        merged = [enhance_player_with_db(db, lesson, student_id) for lesson in lessons]
    except Exception:
        merged = lessons
    return response(200, "success", {"lessons": merged}, getattr(request.state, "request_id", None))


@router.post("/api/v1/recentChapters/list")
async def recent_chapter_list(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    items = get_recent_chapter_visits(db, payload.get("studentId"), payload.get("limit") or 3)
    return response(200, "success", {"items": items}, getattr(request.state, "request_id", None))


@router.post("/api/v1/recentChapters/save")
async def recent_chapter_save(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    data = save_recent_chapter_visit(db, payload.get("studentId"), payload.get("lessonId"), payload.get("sectionId"), payload.get("pageNo"))
    if not data:
        raise ApiError(404, "最近学习记录保存失败", status_code=404)
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/progress/get")
async def get_progress(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    db_progress = get_db_progress_state(db, payload.get("studentId"), payload.get("lessonId"))
    if db_progress:
        return response(200, "success", db_progress, getattr(request.state, "request_id", None))
    return response(200, "success", adapter.get_progress(payload.get("lessonId")), getattr(request.state, "request_id", None))


@router.post("/api/v1/progress/track")
async def track_progress(request: Request):
    payload = await require_signature(request)
    updated = adapter.update_progress(payload.get("lessonId"), {"anchorId": payload.get("anchorId"), "anchorTitle": payload.get("anchorTitle"), "pageNo": payload.get("pageNo"), "currentTime": payload.get("currentTime"), "progressPercent": payload.get("progressPercent"), "understandingLevel": payload.get("understandingLevel"), "weakPoints": payload.get("weakPoints", [])})
    return response(200, "success", updated, getattr(request.state, "request_id", None))


@router.post("/api/v1/progress/page/read")
async def progress_page_read(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    data = mark_page_read(db, payload.get("studentId"), payload.get("lessonId"), payload.get("sectionId"), payload.get("lessonPageId"), payload.get("pageNo"))
    if not data:
        raise ApiError(404, "章节页面不存在", status_code=404)
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/lesson/play")
async def lesson_play(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    player = adapter.play_lesson(payload.get("lessonId"))
    try:
        merged = enhance_player_with_db(db, player, payload.get("studentId"))
    except Exception:
        merged = player
    return response(200, "success", merged, getattr(request.state, "request_id", None))


@router.post("/api/v1/lesson/section/detail")
async def lesson_section_detail(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    data = get_section_detail(db, payload.get("studentId"), payload.get("lessonId"), payload.get("sectionId"))
    if not data:
        raise ApiError(404, "知识学习内容不存在", status_code=404)
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/qa/voiceToText")
async def qa_voice_to_text(request: Request):
    payload = await require_signature(request)
    data = {"text": learning_service.voice_to_text(payload.get("fileName", "voice.webm"))}
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/qa/interact")
async def qa_interact(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    section_id = payload.get("sectionId")
    if section_id:
        data = interact_with_section_context(db, payload.get("lessonId"), section_id, payload.get("question", ""), payload.get("pageNo"))
        if data:
            return response(200, "success", data, getattr(request.state, "request_id", None))
    data = learning_service.interact(payload.get("lessonId"), payload.get("question", ""), payload.get("anchorId"), payload.get("pageNo"))
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/qa/sessions/list")
async def qa_sessions_list(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    items = get_qa_sessions(db, payload.get("studentId"), payload.get("lessonId"))
    return response(200, "success", {"sessions": items}, getattr(request.state, "request_id", None))


@router.post("/api/v1/qa/sessions/save")
async def qa_sessions_save(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    data = save_qa_session(db, payload.get("studentId"), payload.get("lessonId"), payload.get("sectionId"), payload.get("session"))
    if not data:
        raise ApiError(404, "问答会话保存失败", status_code=404)
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/progress/adjust")
async def progress_adjust(request: Request):
    payload = await require_signature(request)
    data = learning_service.adjust_progress(payload.get("lessonId"), payload.get("anchorId"), payload.get("pageNo"), payload.get("understandingLevel"), payload.get("weakPoints", []))
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/lesson/resume")
async def lesson_resume(request: Request):
    payload = await require_signature(request)
    data = learning_service.resume(payload.get("lessonId"), payload.get("anchorId"))
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/notifications/list")
async def notification_list(request: Request):
    payload = await require_signature(request)
    data = {"notifications": adapter.list_notifications(payload.get("studentId"))}
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/notifications/detail")
async def notification_detail(request: Request):
    payload = await require_signature(request)
    data = adapter.get_notification_detail(payload.get("studentId"), payload.get("notificationId"))
    if data is None:
        raise ApiError(404, "通知不存在", status_code=404)
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/notifications/read")
async def notification_read(request: Request):
    payload = await require_signature(request)
    data = adapter.mark_notification_read(payload.get("studentId"), payload.get("notificationId"))
    if data is None:
        raise ApiError(404, "通知不存在", status_code=404)
    return response(200, "success", data, getattr(request.state, "request_id", None))
