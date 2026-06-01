from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.student_runtime.qa_image_storage import normalize_qa_image_attachments
from backend.app.student_runtime.qa_orchestrator import answer_question
from backend.app.student_runtime.qa_runtime_config_service import get_student_qa_runtime_config
from backend.app.teacher_runtime.status_service import resolve_course
from backend.chaoxing_db.models import Lesson, LessonSection, LessonSectionPage


def get_course_outline(db: Session, course_id: str) -> dict[str, object]:
    normalized_course_id = str(course_id or "").strip()
    if not normalized_course_id:
        raise ValueError("courseId is required")
    course = resolve_course(db, normalized_course_id)
    if course is None:
        raise LookupError("courseId not found")

    lessons = (
        db.query(Lesson)
        .filter(Lesson.course_id == course.id, Lesson.publish_status == "published")
        .order_by(Lesson.published_at.desc(), Lesson.id.desc())
        .all()
    )
    lesson_ids = [lesson.id for lesson in lessons]
    sections = (
        db.query(LessonSection)
        .filter(LessonSection.lesson_id.in_(lesson_ids))
        .order_by(LessonSection.lesson_id.asc(), LessonSection.sort_no.asc(), LessonSection.id.asc())
        .all()
        if lesson_ids
        else []
    )
    section_ids = [section.id for section in sections]
    pages = (
        db.query(LessonSectionPage)
        .filter(LessonSectionPage.section_id.in_(section_ids))
        .order_by(LessonSectionPage.section_id.asc(), LessonSectionPage.page_no.asc(), LessonSectionPage.id.asc())
        .all()
        if section_ids
        else []
    )

    pages_by_section_id: dict[int, list[dict[str, object]]] = {}
    for page in pages:
        pages_by_section_id.setdefault(page.section_id, []).append(
            {
                "pageNo": page.page_no,
                "pageTitle": page.page_title or "",
                "hasMeaningfulContent": bool((page.parsed_content or "").strip()),
            }
        )

    sections_by_lesson_id: dict[int, list[dict[str, object]]] = {}
    for section in sections:
        section_pages = pages_by_section_id.get(section.id, [])
        sections_by_lesson_id.setdefault(section.lesson_id, []).append(
            {
                "sectionId": section.section_code,
                "sectionName": section.section_name,
                "pageCount": len(section_pages),
                "pages": section_pages,
            }
        )

    return {
        "courseId": normalized_course_id,
        "courseName": course.course_name,
        "lessons": [
            {
                "lessonId": lesson.lesson_no,
                "lessonName": lesson.lesson_name,
                "publishStatus": lesson.publish_status,
                "publishedAt": lesson.published_at.isoformat() if lesson.published_at else "",
                "sections": sections_by_lesson_id.get(lesson.id, []),
            }
            for lesson in lessons
        ],
    }


def run_compare(db: Session, payload: dict[str, object]) -> dict[str, object]:
    lesson_id = str(payload.get("lessonId") or "").strip()
    section_id = str(payload.get("sectionId") or "").strip()
    question = str(payload.get("question") or "").strip()
    page_no = _normalize_page_no(payload.get("pageNo"))
    attachments = normalize_qa_image_attachments(payload.get("attachments") or [])
    if not lesson_id:
        raise ValueError("lessonId is required")
    if not section_id:
        raise ValueError("sectionId is required")
    if not question and not attachments:
        raise ValueError("question or attachments is required")

    base_config = get_student_qa_runtime_config(db)
    variants = [
        ("retrieval_on", "检索开启", base_config.with_retrieval_enabled(True)),
        ("retrieval_off", "检索关闭", base_config.with_retrieval_enabled(False)),
    ]
    results: list[dict[str, object]] = []
    for variant_key, label, runtime_config in variants:
        answer = answer_question(
            db,
            lesson_id=lesson_id,
            section_id=section_id,
            page_no=page_no,
            question=question,
            attachments=attachments,
            runtime_config=runtime_config,
            include_debug=True,
            record_trace=False,
        )
        results.append(
            {
                "variantKey": variant_key,
                "label": label,
                "result": answer or {},
            }
        )

    return {
        "question": question,
        "lessonId": lesson_id,
        "sectionId": section_id,
        "pageNo": page_no,
        "results": results,
    }


def _normalize_page_no(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        page_no = int(value)
    except Exception:
        return None
    return page_no if page_no > 0 else None
