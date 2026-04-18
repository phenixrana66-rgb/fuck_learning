from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload

from backend.app.student_runtime.db_learning_service import (
    _find_lesson,
    _find_section,
    _find_section_anchor,
    _resolve_user_id,
)
from backend.chaoxing_db.models import (
    QAAnswer,
    QAAnswerTrace,
    QAMessage,
    QAMessageKnowledgeRef,
    QASession,
    VoiceTranscript,
)

QA_UNDERSTANDING_LEVEL_MAP = {
    "未理解": "none",
    "部分理解": "partial",
    "完全理解": "full",
    "none": "none",
    "partial": "partial",
    "full": "full",
}
QA_UNDERSTANDING_LABEL_MAP = {
    "none": "未理解",
    "partial": "部分理解",
    "full": "完全理解",
}
JsonDict = dict[str, Any]


def _timestamp_ms(value: datetime | None) -> int:
    if not value:
        return 0
    return int(value.timestamp() * 1000)


def _datetime_from_maybe_ms(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if value in (None, ""):
        return datetime.now()
    try:
        number = float(value)
        if number > 10_000_000_000:
            number /= 1000
        return datetime.fromtimestamp(number)
    except Exception:
        return datetime.now()


def _create_session_title(question: str = "") -> str:
    normalized = " ".join((question or "").split()).strip()
    if not normalized:
        return "未命名问答"
    return f"{normalized[:24]}..." if len(normalized) > 24 else normalized


def _resolve_answer_anchor_title(db: Session, answer: QAAnswer | None, section_name: str) -> str:
    if not answer:
        return section_name
    if answer.recommended_anchor_id:
        from backend.chaoxing_db.models import LessonSectionAnchor

        anchor = db.query(LessonSectionAnchor).filter(LessonSectionAnchor.id == answer.recommended_anchor_id).first()
        if anchor and anchor.anchor_title:
            return anchor.anchor_title
    return section_name


def get_qa_sessions(db: Session, student_identifier: str | int | None, lesson_identifier: str | int | None) -> list[JsonDict]:
    lesson = _find_lesson(db, lesson_identifier)
    student_db_id = _resolve_user_id(db, student_identifier)
    if not lesson or not student_db_id:
        return []
    sessions = (
        db.query(QASession)
        .options(
            joinedload(QASession.messages),
            joinedload(QASession.answers).joinedload(QAAnswer.knowledge_refs),
        )
        .filter(QASession.student_id == student_db_id, QASession.lesson_id == lesson.id)
        .order_by(QASession.updated_at.desc(), QASession.id.desc())
        .all()
    )
    result: list[JsonDict] = []
    for session in sessions:
        current_section = _find_section(db, lesson.id, session.current_section_id) if session.current_section_id else None
        section_name = current_section.section_name if current_section else (lesson.course.course_name if lesson.course else "")
        messages = sorted(session.messages or [], key=lambda item: (item.created_at or datetime.min, item.id))
        answers_by_message_id = {answer.assistant_message_id: answer for answer in (session.answers or [])}
        first_question = next((item.message_content for item in messages if item.role == "user"), "")
        payload_messages: list[JsonDict] = []
        for message in messages:
            item: JsonDict = {
                "id": f"db-msg-{message.id}",
                "role": message.role,
                "content": message.message_content,
                "createdAt": _timestamp_ms(message.created_at),
            }
            if message.role == "assistant":
                answer = answers_by_message_id.get(message.id)
                item["relatedPoints"] = [
                    ref.knowledge_name
                    for ref in sorted(answer.knowledge_refs or [], key=lambda row: (row.sort_no, row.id))
                ] if answer else []
                item["understandingLevel"] = answer.understanding_level if answer else None
                item["understandingLabel"] = (
                    QA_UNDERSTANDING_LABEL_MAP.get(answer.understanding_level, "")
                    if answer and answer.understanding_level
                    else None
                )
                item["anchorTitle"] = _resolve_answer_anchor_title(db, answer, section_name)
                item["resumePageNo"] = answer.recommended_page_no if answer else None
            payload_messages.append(item)
        result.append(
            {
                "sessionId": session.session_no,
                "title": session.session_title or _create_session_title(first_question),
                "messages": payload_messages,
                "createdAt": _timestamp_ms(session.created_at),
                "updatedAt": _timestamp_ms(session.updated_at),
            }
        )
    return result


def save_qa_session(
    db: Session,
    student_identifier: str | int | None,
    lesson_identifier: str | int | None,
    section_identifier: str | int | None,
    session_payload: JsonDict,
) -> JsonDict | None:
    lesson = _find_lesson(db, lesson_identifier)
    student_db_id = _resolve_user_id(db, student_identifier)
    if not lesson or not student_db_id or not isinstance(session_payload, dict):
        return None
    section = _find_section(db, lesson.id, section_identifier)
    if not section:
        section = next(
            (
                item
                for unit in sorted(lesson.units or [], key=lambda row: (row.sort_no, row.id))
                for item in sorted(unit.sections or [], key=lambda row: (row.sort_no, row.id))
            ),
            None,
        )
    if not section:
        return None

    session_no = session_payload.get("sessionId") or f"session-{uuid4().hex[:16]}"
    messages_payload = session_payload.get("messages") or []
    first_question = next((item.get("content", "") for item in messages_payload if item.get("role") == "user"), "")
    now = datetime.now()

    session = (
        db.query(QASession)
        .filter(
            QASession.session_no == session_no,
            QASession.student_id == student_db_id,
            QASession.lesson_id == lesson.id,
        )
        .first()
    )
    if not session:
        session = QASession(
            session_no=session_no,
            student_id=student_db_id,
            course_id=lesson.course_id,
            lesson_id=lesson.id,
            current_section_id=section.id,
            created_at=_datetime_from_maybe_ms(session_payload.get("createdAt")),
        )
        db.add(session)
        db.flush()
    else:
        answer_ids = [row.id for row in db.query(QAAnswer.id).filter(QAAnswer.session_id == session.id).all()]
        if answer_ids:
            db.query(QAMessageKnowledgeRef).filter(QAMessageKnowledgeRef.answer_id.in_(answer_ids)).delete(synchronize_session=False)
            db.query(QAAnswer).filter(QAAnswer.id.in_(answer_ids)).delete(synchronize_session=False)
        db.query(QAMessage).filter(QAMessage.session_id == session.id).delete(synchronize_session=False)

    session.current_section_id = section.id
    session.session_title = session_payload.get("title") or _create_session_title(first_question)
    session.status = "active"
    session.updated_at = now
    db.flush()

    pending_question = None
    for item in messages_payload:
        role = "assistant" if item.get("role") == "assistant" else "user"
        created_at = _datetime_from_maybe_ms(item.get("createdAt"))
        message = QAMessage(
            session_id=session.id,
            lesson_id=lesson.id,
            section_id=section.id,
            role=role,
            question_type=(item.get("questionType") or "text") if role == "user" else None,
            message_content=item.get("content") or "",
            created_at=created_at,
        )
        db.add(message)
        db.flush()
        if role == "user":
            pending_question = message
            continue
        if not pending_question:
            continue
        understanding_level = QA_UNDERSTANDING_LEVEL_MAP.get(item.get("understandingLevel") or item.get("understandingLabel"))
        anchor = _find_section_anchor(section, item.get("resumePageNo"))
        answer = QAAnswer(
            answer_no=f"ans-{uuid4().hex[:16]}",
            session_id=session.id,
            question_message_id=pending_question.id,
            assistant_message_id=message.id,
            related_section_id=section.id,
            answer_type="text",
            understanding_level=understanding_level,
            recommended_section_id=section.id if item.get("resumePageNo") else None,
            recommended_page_no=item.get("resumePageNo"),
            recommended_anchor_id=anchor.id if anchor else None,
            next_sections_json=None,
            suggestions_json=None,
            created_at=created_at,
        )
        db.add(answer)
        db.flush()
        for point_index, point in enumerate(item.get("relatedPoints") or []):
            if not point:
                continue
            db.add(QAMessageKnowledgeRef(answer_id=answer.id, knowledge_name=point, sort_no=point_index))
        pending_question = None
    db.commit()
    return {"sessionId": session.session_no, "title": session.session_title or _create_session_title(first_question)}


def save_voice_transcript(
    db: Session,
    *,
    student_identifier: str | int | None,
    lesson_identifier: str | int | None,
    section_identifier: str | int | None,
    transcript_text: str,
    audio_url: str | None = None,
    session_id: int | None = None,
    question_message_id: int | None = None,
    language: str = "zh-CN",
    duration_seconds: int | None = None,
    confidence_score: float | None = None,
) -> JsonDict | None:
    lesson = _find_lesson(db, lesson_identifier)
    student_db_id = _resolve_user_id(db, student_identifier)
    if not lesson or not student_db_id or not transcript_text.strip():
        return None
    section = _find_section(db, lesson.id, section_identifier) if section_identifier not in (None, "") else None
    row = VoiceTranscript(
        student_id=student_db_id,
        session_id=session_id,
        question_message_id=question_message_id,
        lesson_id=lesson.id,
        section_id=section.id if section else None,
        audio_url=audio_url,
        duration_seconds=duration_seconds,
        language=language,
        transcript_text=transcript_text.strip(),
        confidence_score=confidence_score,
    )
    db.add(row)
    db.commit()
    return {"transcriptId": row.id, "text": row.transcript_text}


def record_qa_answer_trace(db: Session, trace_payload: JsonDict) -> JsonDict:
    trace = QAAnswerTrace(
        session_id=trace_payload.get("session_id"),
        question_message_id=trace_payload.get("question_message_id"),
        answer_message_id=trace_payload.get("answer_message_id"),
        lesson_id=trace_payload.get("lesson_id"),
        section_id=trace_payload.get("section_id"),
        page_no=trace_payload.get("page_no"),
        model_provider=trace_payload.get("model_provider") or "unknown",
        model_name=trace_payload.get("model_name") or "unknown",
        embedding_model=trace_payload.get("embedding_model"),
        faq_hit_ids_json=trace_payload.get("faq_hit_ids_json"),
        context_chunk_ids_json=trace_payload.get("context_chunk_ids_json"),
        prompt_version=trace_payload.get("prompt_version"),
        latency_ms=trace_payload.get("latency_ms"),
        confidence_score=trace_payload.get("confidence_score"),
    )
    db.add(trace)
    db.commit()
    return {"traceId": trace.id}
