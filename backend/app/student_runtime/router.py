from uuid import uuid4

import asyncio
import json

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.app.common.db import get_db
from backend.app.common.exceptions import ApiError
from backend.app.common.security import verify_signature_payload
from backend.app.student_runtime.adapter import ChaoxingAdapter
from backend.app.student_runtime.db_learning_service import (
    _find_latest_practice_attempt,
    _find_lesson,
    _find_section,
    _resolve_user_id,
    enhance_player_with_db,
    get_db_progress_state,
    get_db_resume_state,
    get_recent_chapter_visits,
    get_section_detail,
    get_student_lessons_from_db,
    get_student_profile_from_db,
    interact_with_section_context,
    mark_page_read,
    save_recent_chapter_visit,
)
from backend.app.student_runtime.pace_service import (
    apply_practice_checkpoint,
    apply_qa_checkpoint,
    ensure_section_progress,
    record_pace_skip,
)
from backend.app.student_runtime.db_qa_service import get_qa_sessions, save_qa_session
from backend.app.student_runtime.qa_image_storage import normalize_qa_image_attachments
from backend.app.student_runtime.learning_service import LearningService
from backend.app.student_runtime.qa_asr_service import AudioPayloadError, transcribe_audio_payload
from backend.app.student_runtime.qa_asr_realtime_service import handle_realtime_asr_message
from backend.app.student_runtime.qa_orchestrator import answer_question
from backend.app.student_runtime.qa_streaming import iter_answer_chunks
from backend.chaoxing_db.models import StudentPracticeAttempt, StudentSectionProgress

router = APIRouter()
adapter = ChaoxingAdapter()
learning_service = LearningService(adapter)


def build_response(code: int = 200, msg: str = "success", data=None, request_id: str | None = None):
    return {
        "code": code,
        "msg": msg,
        "data": data,
        "requestId": request_id or f"req-{uuid4().hex[:12]}",
    }


def response(code: int = 200, msg: str = "success", data=None, request_id: str | None = None):
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
        student_id = payload.get("studentId") or data.get("student", {}).get("studentId")
        data["lessons"] = get_student_lessons_from_db(db, student_id)
        return response(200, "success", data, getattr(request.state, "request_id", None))
    except PermissionError:
        raise ApiError(401, "免登 token 无效", status_code=401)


@router.post("/api/v1/getStudentLessonList")
async def get_student_lesson_list(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    student_id = payload.get("studentId")
    lessons = get_student_lessons_from_db(db, student_id)
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
async def qa_voice_to_text(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    try:
        data = transcribe_audio_payload(db, payload)
    except AudioPayloadError as exc:
        raise ApiError(400, str(exc), status_code=400)
    except Exception as exc:
        raise ApiError(500, f"语音识别失败：{exc}", status_code=500)
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.websocket("/ws/qa/asr")
async def qa_realtime_asr(websocket: WebSocket):
    await websocket.accept()
    state: dict[str, str] = {}
    try:
        while True:
            payload = await websocket.receive_json()
            await handle_realtime_asr_message(websocket, payload, state)
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover - websocket runtime guard
        try:
            await websocket.send_json({"type": "error", "message": f"实时语音识别链路异常：{exc}"})
        finally:
            await websocket.close()


@router.post("/api/v1/qa/interact")
async def qa_interact(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    section_id = payload.get("sectionId")
    question = (payload.get("question") or "").strip()
    page_no = payload.get("pageNo")
    lesson_id = payload.get("lessonId")
    student_db_id = _resolve_user_id(db, payload.get("studentId"))
    lesson = _find_lesson(db, lesson_id) if section_id and student_db_id else None
    section = _find_section(db, lesson.id, section_id) if lesson else None
    if section_id and question:
        data = answer_question(db, lesson_id=lesson_id, section_id=section_id, page_no=page_no, question=question)
        if data:
            pace_suggestion = None
            if student_db_id and lesson and section:
                section_progress = ensure_section_progress(db, student_db_id=student_db_id, lesson=lesson, section=section)
                pace_suggestion = apply_qa_checkpoint(
                    db,
                    student_db_id=student_db_id,
                    lesson=lesson,
                    section=section,
                    section_progress=section_progress,
                    checkpoint_result=data,
                    page_no=page_no,
                )
                db.commit()
            return response(200, "success", {**data, "paceSuggestion": pace_suggestion}, getattr(request.state, "request_id", None))
        data = interact_with_section_context(db, lesson_id, section_id, question, page_no)
        if data:
            pace_suggestion = None
            if student_db_id and lesson and section:
                section_progress = ensure_section_progress(db, student_db_id=student_db_id, lesson=lesson, section=section)
                pace_suggestion = apply_qa_checkpoint(
                    db,
                    student_db_id=student_db_id,
                    lesson=lesson,
                    section=section,
                    section_progress=section_progress,
                    checkpoint_result=data,
                    page_no=page_no,
                )
                db.commit()
            return response(200, "success", {**data, "paceSuggestion": pace_suggestion}, getattr(request.state, "request_id", None))
    data = learning_service.interact(lesson_id, question, payload.get("anchorId"), page_no)
    return response(200, "success", data, getattr(request.state, "request_id", None))


@router.post("/api/v1/qa/interact/stream")
async def qa_interact_stream(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    section_id = payload.get("sectionId")
    question = (payload.get("question") or "").strip()
    page_no = payload.get("pageNo")
    lesson_id = payload.get("lessonId")
    student_db_id = _resolve_user_id(db, payload.get("studentId"))
    lesson = _find_lesson(db, lesson_id) if section_id and student_db_id else None
    section = _find_section(db, lesson.id, section_id) if lesson else None
    attachments = normalize_qa_image_attachments(payload.get("attachments") or [])
    request_id = getattr(request.state, "request_id", None)
    if not question and not attachments:
        raise ApiError(400, "请输入问题或上传图片", status_code=400)

    async def event_stream():
        def emit(data: dict) -> str:
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        yield emit({"type": "start", "requestId": request_id})

        try:
            if section_id and (question or attachments):
                data = answer_question(
                    db,
                    lesson_id=lesson_id,
                    section_id=section_id,
                    page_no=page_no,
                    question=question,
                    attachments=attachments,
                )
                if not data:
                    data = interact_with_section_context(db, lesson_id, section_id, question, page_no)
            else:
                data = learning_service.interact(lesson_id, question, payload.get("anchorId"), page_no)

            pace_suggestion = None
            if data and student_db_id and lesson and section:
                section_progress = ensure_section_progress(db, student_db_id=student_db_id, lesson=lesson, section=section)
                pace_suggestion = apply_qa_checkpoint(
                    db,
                    student_db_id=student_db_id,
                    lesson=lesson,
                    section=section,
                    section_progress=section_progress,
                    checkpoint_result=data,
                    page_no=page_no,
                )
                db.commit()
                data = {**data, "paceSuggestion": pace_suggestion}

            answer = (data or {}).get("answer") or "当前内容暂无更多解读。"
            for chunk in iter_answer_chunks(answer):
                if await request.is_disconnected():
                    return
                yield emit({"type": "delta", "delta": chunk})
                await asyncio.sleep(0.03)
            yield emit({"type": "done", "data": {**(data or {}), "answer": answer}})
        except Exception as exc:
            yield emit({"type": "error", "message": str(exc) or "AI 问答失败"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/v1/progress/practice/checkpoint")
async def progress_practice_checkpoint(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    lesson = _find_lesson(db, payload.get("lessonId"))
    student_db_id = _resolve_user_id(db, payload.get("studentId"))
    if not lesson or not student_db_id:
        raise ApiError(404, "练习检查点关联的课程不存在", status_code=404)
    section = _find_section(db, lesson.id, payload.get("sectionId"))
    if not section:
        raise ApiError(404, "练习检查点关联的章节不存在", status_code=404)

    attempt_id = payload.get("attemptId")
    practice_attempt = None
    if attempt_id not in (None, ""):
        attempt_text = str(attempt_id).strip()
        if attempt_text.isdigit():
            practice_attempt = (
                db.query(StudentPracticeAttempt)
                .filter(
                    StudentPracticeAttempt.id == int(attempt_text),
                    StudentPracticeAttempt.student_id == student_db_id,
                    StudentPracticeAttempt.lesson_id == lesson.id,
                    StudentPracticeAttempt.section_id == section.id,
                    StudentPracticeAttempt.grading_status == "graded",
                )
                .first()
            )
    if practice_attempt is None:
        practice_attempt = _find_latest_practice_attempt(db, student_db_id, lesson.id, section.id)
    if not practice_attempt:
        raise ApiError(404, "暂无已批改的章节练习记录", status_code=404)

    section_progress = ensure_section_progress(db, student_db_id=student_db_id, lesson=lesson, section=section)
    pace_suggestion, practice_percent, mastery_percent, overall_progress, overall_mastery = apply_practice_checkpoint(
        db,
        student_db_id=student_db_id,
        lesson=lesson,
        section=section,
        section_progress=section_progress,
        practice_attempt=practice_attempt,
        page_no=payload.get("pageNo"),
    )
    db.commit()
    return response(
        200,
        "success",
        {
            "sectionId": str(section.id),
            "sectionTitle": section.section_name,
            "progressPercent": int(round(float(section_progress.progress_percent or 0))),
            "practicePercent": practice_percent,
            "masteryPercent": mastery_percent,
            "overallProgress": overall_progress,
            "overallMastery": overall_mastery,
            "paceSuggestion": pace_suggestion,
        },
        getattr(request.state, "request_id", None),
    )


@router.post("/api/v1/progress/pace/skip")
async def progress_pace_skip(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    lesson = _find_lesson(db, payload.get("lessonId"))
    student_db_id = _resolve_user_id(db, payload.get("studentId"))
    if not lesson or not student_db_id:
        raise ApiError(404, "学习节奏记录不存在", status_code=404)
    section = _find_section(db, lesson.id, payload.get("sectionId"))
    if not section:
        raise ApiError(404, "学习节奏记录不存在", status_code=404)
    section_progress = (
        db.query(StudentSectionProgress)
        .filter(
            StudentSectionProgress.student_id == student_db_id,
            StudentSectionProgress.lesson_id == lesson.id,
            StudentSectionProgress.section_id == section.id,
        )
        .first()
    )
    if not section_progress:
        return response(200, "success", {"paceSuggestion": None}, getattr(request.state, "request_id", None))
    suggestion = record_pace_skip(
        db,
        student_db_id=student_db_id,
        lesson=lesson,
        section=section,
        section_progress=section_progress,
        page_no=payload.get("pageNo"),
    )
    db.commit()
    return response(200, "success", {"paceSuggestion": suggestion}, getattr(request.state, "request_id", None))


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
async def lesson_resume(request: Request, db: Session = Depends(get_db)):
    payload = await require_signature(request)
    data = get_db_resume_state(db, payload.get("studentId"), payload.get("lessonId"))
    if data is None:
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
