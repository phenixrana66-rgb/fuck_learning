from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from config import Config
from db import get_db
from services.chaoxing_adapter import ChaoxingAdapter
from services.db_learning_service import (
    enhance_player_with_db,
    get_db_progress_state,
    get_recent_chapter_visits,
    get_section_detail,
    get_student_profile_from_db,
    interact_with_section_context,
    mark_page_read,
    save_recent_chapter_visit,
)
from services.db_qa_service import get_qa_sessions, save_qa_session
from services.learning_service import LearningService
from services.signing import verify_signature


class ApiError(Exception):
    def __init__(self, status_code, msg, data=None, request_id=None):
        super().__init__(msg)
        self.status_code = status_code
        self.msg = msg
        self.data = data
        self.request_id = request_id


app = FastAPI(title="Student Plugin Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

adapter = ChaoxingAdapter()
learning_service = LearningService(adapter)


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


async def require_signature(request: Request):
    payload = await request_payload(request)
    if not verify_signature(payload, Config.STATIC_KEY):
        raise ApiError(401, "签名校验失败")
    return payload


@app.exception_handler(ApiError)
async def handle_api_error(_request: Request, exc: ApiError):
    return response(exc.status_code, exc.msg, exc.data, exc.request_id)


@app.exception_handler(Exception)
async def handle_unexpected_error(_request: Request, _exc: Exception):
    return response(500, "学生端服务异常")


@app.post("/auth/verify")
async def auth_verify(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    token = payload.get("token") or request.headers.get("X-Platform-Token", "")
    try:
        data = adapter.verify(token)
        db_student = get_student_profile_from_db(
            db,
            payload.get("studentId") or data.get("student", {}).get("studentId"),
        )
        if db_student:
            data["student"] = {**data.get("student", {}), **db_student}
        return response(200, "success", data)
    except PermissionError:
        raise ApiError(401, "免登 token 无效")


@app.post("/api/v1/getStudentLessonList")
async def get_student_lesson_list(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    student_id = payload.get("studentId")
    lessons = adapter.get_student_lessons(student_id)
    try:
        merged = [enhance_player_with_db(db, lesson, student_id) for lesson in lessons]
    except Exception:
        merged = lessons
    return response(200, "success", {"lessons": merged})


@app.post("/api/v1/recentChapters/list")
async def recent_chapter_list(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    items = get_recent_chapter_visits(db, payload.get("studentId"), payload.get("limit") or 3)
    return response(200, "success", {"items": items})


@app.post("/api/v1/recentChapters/save")
async def recent_chapter_save(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    data = save_recent_chapter_visit(
        db,
        payload.get("studentId"),
        payload.get("lessonId"),
        payload.get("sectionId"),
        payload.get("pageNo"),
    )
    if not data:
        raise ApiError(404, "最近学习记录保存失败")
    return response(200, "success", data)


@app.post("/api/v1/progress/get")
async def get_progress(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    student_id = payload.get("studentId")
    lesson_id = payload.get("lessonId")
    db_progress = get_db_progress_state(db, student_id, lesson_id)
    if db_progress:
        return response(200, "success", db_progress)
    return response(200, "success", adapter.get_progress(lesson_id))


@app.post("/api/v1/progress/track")
async def track_progress(request: Request):
    payload = await require_signature(request)
    updated = adapter.update_progress(
        payload.get("lessonId"),
        {
            "anchorId": payload.get("anchorId"),
            "anchorTitle": payload.get("anchorTitle"),
            "pageNo": payload.get("pageNo"),
            "currentTime": payload.get("currentTime"),
            "progressPercent": payload.get("progressPercent"),
            "understandingLevel": payload.get("understandingLevel"),
            "weakPoints": payload.get("weakPoints", []),
        },
    )
    return response(200, "success", updated)


@app.post("/api/v1/progress/page/read")
async def progress_page_read(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    data = mark_page_read(
        db,
        payload.get("studentId"),
        payload.get("lessonId"),
        payload.get("sectionId"),
        payload.get("lessonPageId"),
        payload.get("pageNo"),
    )
    if not data:
        raise ApiError(404, "章节页面不存在")
    return response(200, "success", data)


@app.post("/api/v1/lesson/play")
async def lesson_play(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    lesson_id = payload.get("lessonId")
    student_id = payload.get("studentId")
    player = adapter.play_lesson(lesson_id)
    try:
        merged = enhance_player_with_db(db, player, student_id)
    except Exception:
        merged = player
    return response(200, "success", merged)


@app.post("/api/v1/lesson/section/detail")
async def lesson_section_detail(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    data = get_section_detail(
        db,
        payload.get("studentId"),
        payload.get("lessonId"),
        payload.get("sectionId"),
    )
    if not data:
        raise ApiError(404, "知识学习内容不存在")
    return response(200, "success", data)


@app.post("/api/v1/qa/voiceToText")
async def qa_voice_to_text(request: Request):
    payload = await require_signature(request)
    data = {"text": learning_service.voice_to_text(payload.get("fileName", "voice.webm"))}
    return response(200, "success", data)


@app.post("/api/v1/qa/interact")
async def qa_interact(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    section_id = payload.get("sectionId")
    if section_id:
        data = interact_with_section_context(
            db,
            payload.get("lessonId"),
            section_id,
            payload.get("question", ""),
            payload.get("pageNo"),
        )
        if data:
            return response(200, "success", data)

    data = learning_service.interact(
        payload.get("lessonId"),
        payload.get("question", ""),
        payload.get("anchorId"),
        payload.get("pageNo"),
    )
    return response(200, "success", data)


@app.post("/api/v1/qa/sessions/list")
async def qa_sessions_list(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    items = get_qa_sessions(db, payload.get("studentId"), payload.get("lessonId"))
    return response(200, "success", {"sessions": items})


@app.post("/api/v1/qa/sessions/save")
async def qa_sessions_save(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    data = save_qa_session(
        db,
        payload.get("studentId"),
        payload.get("lessonId"),
        payload.get("sectionId"),
        payload.get("session"),
    )
    if not data:
        raise ApiError(404, "问答会话保存失败")
    return response(200, "success", data)


@app.post("/api/v1/progress/adjust")
async def progress_adjust(request: Request):
    payload = await require_signature(request)
    data = learning_service.adjust_progress(
        payload.get("lessonId"),
        payload.get("anchorId"),
        payload.get("pageNo"),
        payload.get("understandingLevel"),
        payload.get("weakPoints", []),
    )
    return response(200, "success", data)


@app.post("/api/v1/lesson/resume")
async def lesson_resume(request: Request):
    payload = await require_signature(request)
    data = learning_service.resume(payload.get("lessonId"), payload.get("anchorId"))
    return response(200, "success", data)


@app.post("/api/v1/notifications/list")
async def notification_list(request: Request):
    payload = await require_signature(request)
    data = {"notifications": adapter.list_notifications(payload.get("studentId"))}
    return response(200, "success", data)


@app.post("/api/v1/notifications/detail")
async def notification_detail(request: Request):
    payload = await require_signature(request)
    data = adapter.get_notification_detail(payload.get("studentId"), payload.get("notificationId"))
    if data is None:
        raise ApiError(404, "通知不存在")
    return response(200, "success", data)


@app.post("/api/v1/notifications/read")
async def notification_read(request: Request):
    payload = await require_signature(request)
    data = adapter.mark_notification_read(payload.get("studentId"), payload.get("notificationId"))
    if data is None:
        raise ApiError(404, "通知不存在")
    return response(200, "success", data)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
