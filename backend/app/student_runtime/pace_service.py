from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.chaoxing_db.models import (
    Lesson,
    LessonSection,
    LessonSectionAnchor,
    LessonSectionPage,
    ProgressAdjustRecord,
    StudentLessonProgress,
    StudentPracticeAttempt,
    StudentSectionMasteryLog,
    StudentSectionProgress,
)

JsonDict = dict[str, Any]

PACE_MODE_CONTINUE = "continue"
PACE_MODE_SUPPLEMENT = "supplement"
PACE_MODE_REINFORCE = "reinforce"

PACE_TRIGGER_QA = "qa"
PACE_TRIGGER_PRACTICE = "practice"

PRACTICE_WEAK_THRESHOLD = 60
PRACTICE_PARTIAL_THRESHOLD = 80
SECTION_COMPLETION_MASTERY_THRESHOLD = 60

UNDERSTANDING_TO_MODEL = {
    "weak": "none",
    "partial": "partial",
    "complete": "full",
}

PACE_REASON_SUMMARY_MAP = {
    (PACE_MODE_CONTINUE, PACE_TRIGGER_QA): "这轮问答显示理解比较稳定，可以继续推进当前章节。",
    (PACE_MODE_CONTINUE, PACE_TRIGGER_PRACTICE): "这次练习结果较稳定，可以继续推进当前章节。",
    (PACE_MODE_SUPPLEMENT, PACE_TRIGGER_QA): "这轮问答显示你还处于部分理解，建议先补一段过渡讲解再继续。",
    (PACE_MODE_SUPPLEMENT, PACE_TRIGGER_PRACTICE): "这次练习结果说明还需要补一段过渡讲解，再继续会更稳。",
    (PACE_MODE_REINFORCE, PACE_TRIGGER_QA): "这轮问答显示当前理解偏弱，建议先回看关键内容并强化一轮。",
    (PACE_MODE_REINFORCE, PACE_TRIGGER_PRACTICE): "这次练习结果偏弱，建议先回看关键内容并强化一轮。",
}


def _round_int(value: Any) -> int:
    if value is None:
        return 0
    return int(round(float(value)))


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat(timespec="seconds")


def compute_mastery_percent(progress_percent: int | float, practice_percent: int | float) -> int:
    return _round_int(float(progress_percent) * 0.4 + float(practice_percent) * 0.6)


def _normalize_understanding_level(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"weak", "partial", "complete"}:
        return normalized
    return "partial"


def _practice_understanding_level(practice_percent: int) -> str:
    if practice_percent < PRACTICE_WEAK_THRESHOLD:
        return "weak"
    if practice_percent < PRACTICE_PARTIAL_THRESHOLD:
        return "partial"
    return "complete"


def _resolve_pace_mode(understanding_level: str) -> str:
    if understanding_level == "weak":
        return PACE_MODE_REINFORCE
    if understanding_level == "partial":
        return PACE_MODE_SUPPLEMENT
    return PACE_MODE_CONTINUE


def _pace_reason_summary(mode: str, trigger_source: str) -> str:
    return PACE_REASON_SUMMARY_MAP.get((mode, trigger_source), "继续推进当前章节学习。")


def _sorted_pages(section: LessonSection) -> list[LessonSectionPage]:
    return sorted(section.pages or [], key=lambda item: (item.sort_no, item.page_no, item.id))


def _sorted_anchors(section: LessonSection) -> list[LessonSectionAnchor]:
    return sorted(section.anchors or [], key=lambda item: ((item.page_no or 0), item.sort_no, item.id))


def _find_anchor(section: LessonSection, page_no: int | None) -> LessonSectionAnchor | None:
    anchors = _sorted_anchors(section)
    if not anchors:
        return None
    if page_no is None:
        return anchors[0]
    eligible = [anchor for anchor in anchors if (anchor.page_no or 0) <= page_no]
    return eligible[-1] if eligible else anchors[0]


def _find_target_page(section: LessonSection, page_no: int | None, mode: str) -> LessonSectionPage | None:
    pages = _sorted_pages(section)
    if not pages:
        return None
    if page_no is None:
        return pages[0]
    page_map = {page.page_no: page for page in pages}
    if mode == PACE_MODE_REINFORCE:
        return page_map.get(max(1, int(page_no) - 1)) or page_map.get(int(page_no)) or pages[0]
    return page_map.get(int(page_no)) or pages[0]


def _build_block_payload(
    section: LessonSection,
    mode: str,
    page_no: int | None,
    weak_points: list[str] | None = None,
    intensity: str = "normal",
) -> JsonDict:
    target_page = _find_target_page(section, page_no, mode)
    target_anchor = _find_anchor(section, target_page.page_no if target_page else page_no)
    focus_points = [point for point in (weak_points or []) if point][:2]
    if not focus_points:
        focus_points = [
            point.point_name
            for point in sorted(section.knowledge_points or [], key=lambda item: (item.sort_no, item.id))
            if point.point_name
        ][:2]

    if mode == PACE_MODE_SUPPLEMENT:
        return {
            "title": "补充一段过渡讲解",
            "description": "先用一小段补充说明把当前知识点串起来，再继续往后学。",
            "actionLabel": "先看补充再继续",
            "focusPoints": focus_points,
            "targetPageNo": target_page.page_no if target_page else 1,
            "targetPageTitle": target_page.page_title if target_page else "",
            "targetAnchorId": str(target_anchor.id) if target_anchor else "",
            "targetAnchorTitle": target_anchor.anchor_title if target_anchor else section.section_name,
            "intensity": intensity,
        }
    if mode == PACE_MODE_REINFORCE:
        return {
            "title": "先强化关键内容",
            "description": "建议先回看关键页，再带着问题继续问答或进入练习。",
            "actionLabel": "先回看关键页",
            "focusPoints": focus_points,
            "targetPageNo": target_page.page_no if target_page else 1,
            "targetPageTitle": target_page.page_title if target_page else "",
            "targetAnchorId": str(target_anchor.id) if target_anchor else "",
            "targetAnchorTitle": target_anchor.anchor_title if target_anchor else section.section_name,
            "intensity": intensity,
        }
    return {}


def build_pace_suggestion(
    section_progress: StudentSectionProgress | None,
    section: LessonSection,
    *,
    mode: str | None = None,
    trigger_source: str | None = None,
    weak_points: list[str] | None = None,
    updated_at: datetime | None = None,
) -> JsonDict | None:
    resolved_mode = (mode or (section_progress.pace_mode if section_progress else "") or "").strip()
    if not resolved_mode:
        return None

    resolved_trigger = (trigger_source or (section_progress.pace_trigger_source if section_progress else "") or "").strip()
    resolved_updated_at = updated_at or (section_progress.pace_updated_at if section_progress else None)
    last_page_no = section_progress.last_page_no if section_progress else None
    repeated_reinforce = (
        resolved_mode == PACE_MODE_REINFORCE
        and section_progress is not None
        and section_progress.pace_mode == PACE_MODE_REINFORCE
    )
    intensity = "high" if repeated_reinforce else "normal"
    reason_summary = (
        section_progress.pace_reason_summary
        if section_progress and section_progress.pace_reason_summary and mode is None and trigger_source is None
        else _pace_reason_summary(resolved_mode, resolved_trigger)
    )

    block_payload = _build_block_payload(
        section,
        resolved_mode,
        last_page_no,
        weak_points=weak_points,
        intensity=intensity,
    )
    block_type = (
        "supplement_card"
        if resolved_mode == PACE_MODE_SUPPLEMENT
        else "reinforce_card"
        if resolved_mode == PACE_MODE_REINFORCE
        else "continue_hint"
    )
    suggested_action = (
        "continue_learning"
        if resolved_mode == PACE_MODE_CONTINUE
        else "read_supplement"
        if resolved_mode == PACE_MODE_SUPPLEMENT
        else "review_key_content"
    )

    return {
        "paceMode": resolved_mode,
        "reasonSummary": reason_summary,
        "triggerSource": resolved_trigger,
        "updatedAt": _format_datetime(resolved_updated_at),
        "suggestedAction": suggested_action,
        "suggestedBlockType": block_type,
        "suggestedBlockPayload": block_payload,
        "allowSkip": resolved_mode != PACE_MODE_CONTINUE,
    }


def get_active_pace_suggestion(
    section_progress: StudentSectionProgress | None,
    section: LessonSection,
) -> JsonDict | None:
    if not section_progress or section_progress.pace_mode not in {PACE_MODE_SUPPLEMENT, PACE_MODE_REINFORCE}:
        return None
    return build_pace_suggestion(section_progress, section)


def clear_pace_state(section_progress: StudentSectionProgress | None) -> None:
    if section_progress is None:
        return
    section_progress.pace_mode = None
    section_progress.pace_reason_summary = None
    section_progress.pace_trigger_source = None
    section_progress.pace_updated_at = None


def should_clear_pace_on_completion(
    section_progress: StudentSectionProgress | None,
    understanding_level: str | None = None,
) -> bool:
    if section_progress is None:
        return False
    if _round_int(section_progress.progress_percent) < 100:
        return False
    if _round_int(section_progress.mastery_percent) < SECTION_COMPLETION_MASTERY_THRESHOLD:
        return False
    if understanding_level and _normalize_understanding_level(understanding_level) == "weak":
        return False
    return True


def ensure_section_progress(
    db: Session,
    *,
    student_db_id: int,
    lesson: Lesson,
    section: LessonSection,
) -> StudentSectionProgress:
    section_progress = (
        db.query(StudentSectionProgress)
        .filter(
            StudentSectionProgress.student_id == student_db_id,
            StudentSectionProgress.lesson_id == lesson.id,
            StudentSectionProgress.section_id == section.id,
        )
        .first()
    )
    if section_progress is None:
        section_progress = StudentSectionProgress(
            student_id=student_db_id,
            course_id=lesson.course_id,
            lesson_id=lesson.id,
            unit_id=section.unit_id,
            section_id=section.id,
        )
        db.add(section_progress)
        db.flush()
    return section_progress


def ensure_lesson_progress(
    db: Session,
    *,
    student_db_id: int,
    lesson: Lesson,
) -> StudentLessonProgress:
    lesson_progress = (
        db.query(StudentLessonProgress)
        .filter(StudentLessonProgress.student_id == student_db_id, StudentLessonProgress.lesson_id == lesson.id)
        .first()
    )
    if lesson_progress is None:
        lesson_progress = StudentLessonProgress(
            student_id=student_db_id,
            course_id=lesson.course_id,
            lesson_id=lesson.id,
        )
        db.add(lesson_progress)
        db.flush()
    return lesson_progress


def refresh_lesson_progress_rollup(
    db: Session,
    *,
    student_db_id: int,
    lesson: Lesson,
    section: LessonSection,
    section_progress: StudentSectionProgress,
) -> tuple[StudentLessonProgress, int, int]:
    lesson_progress = ensure_lesson_progress(db, student_db_id=student_db_id, lesson=lesson)
    all_section_rows = (
        db.query(StudentSectionProgress)
        .filter(StudentSectionProgress.student_id == student_db_id, StudentSectionProgress.lesson_id == lesson.id)
        .all()
    )
    if all_section_rows:
        total_progress = _round_int(sum(_round_int(row.progress_percent) for row in all_section_rows) / len(all_section_rows))
        overall_mastery = _round_int(sum(_round_int(row.mastery_percent) for row in all_section_rows) / len(all_section_rows))
    else:
        total_progress = _round_int(section_progress.progress_percent)
        overall_mastery = _round_int(section_progress.mastery_percent)
    lesson_progress.total_progress = total_progress
    lesson_progress.overall_mastery_percent = overall_mastery
    lesson_progress.current_unit_id = section.unit_id
    lesson_progress.current_section_id = section.id
    lesson_progress.current_anchor_id = section_progress.current_anchor_id
    lesson_progress.last_page_no = section_progress.last_page_no
    lesson_progress.last_operate_time = section_progress.last_operate_time
    return lesson_progress, total_progress, overall_mastery


def apply_qa_checkpoint(
    db: Session,
    *,
    student_db_id: int,
    lesson: Lesson,
    section: LessonSection,
    section_progress: StudentSectionProgress,
    checkpoint_result: JsonDict,
    page_no: int | None,
    now: datetime | None = None,
) -> JsonDict | None:
    resolved_now = now or datetime.now()
    understanding_level = _normalize_understanding_level(checkpoint_result.get("understandingLevel"))
    weak_points = [str(item).strip() for item in (checkpoint_result.get("weakPoints") or []) if str(item).strip()][:3]
    next_mode = _resolve_pace_mode(understanding_level)
    anchor = _find_anchor(section, page_no or section_progress.last_page_no)

    section_progress.understanding_level = UNDERSTANDING_TO_MODEL[understanding_level]
    section_progress.current_anchor_id = anchor.id if anchor else section_progress.current_anchor_id
    if page_no:
        section_progress.last_page_no = int(page_no)
    section_progress.last_operate_time = resolved_now

    if should_clear_pace_on_completion(section_progress, understanding_level=understanding_level) or next_mode == PACE_MODE_CONTINUE:
        clear_pace_state(section_progress)
    else:
        section_progress.pace_mode = next_mode
        section_progress.pace_reason_summary = _pace_reason_summary(next_mode, PACE_TRIGGER_QA)
        section_progress.pace_trigger_source = PACE_TRIGGER_QA
        section_progress.pace_updated_at = resolved_now

    db.add(
        ProgressAdjustRecord(
            student_id=student_db_id,
            course_id=lesson.course_id,
            lesson_id=lesson.id,
            section_id=section.id,
            understanding_level=UNDERSTANDING_TO_MODEL[understanding_level],
            adjust_type="advance" if next_mode == PACE_MODE_CONTINUE else "supplement" if next_mode == PACE_MODE_SUPPLEMENT else "review",
            continue_section_id=section.id,
            recommended_page_no=int(page_no or section_progress.last_page_no or 1),
            recommended_anchor_id=anchor.id if anchor else None,
            adjust_payload={
                "triggerSource": PACE_TRIGGER_QA,
                "paceMode": next_mode,
                "weakPoints": weak_points,
            },
        )
    )
    refresh_lesson_progress_rollup(
        db,
        student_db_id=student_db_id,
        lesson=lesson,
        section=section,
        section_progress=section_progress,
    )
    db.flush()
    return None if next_mode == PACE_MODE_CONTINUE else build_pace_suggestion(
        section_progress,
        section,
        mode=next_mode,
        trigger_source=PACE_TRIGGER_QA,
        weak_points=weak_points,
        updated_at=resolved_now,
    )


def apply_practice_checkpoint(
    db: Session,
    *,
    student_db_id: int,
    lesson: Lesson,
    section: LessonSection,
    section_progress: StudentSectionProgress,
    practice_attempt: StudentPracticeAttempt,
    page_no: int | None = None,
    now: datetime | None = None,
) -> tuple[JsonDict | None, int, int, int, int]:
    resolved_now = now or datetime.now()
    practice_percent = _round_int(practice_attempt.accuracy_percent if practice_attempt.accuracy_percent is not None else 0)
    progress_percent = _round_int(section_progress.progress_percent)
    mastery_percent = compute_mastery_percent(progress_percent, practice_percent)
    understanding_level = _practice_understanding_level(practice_percent)
    next_mode = _resolve_pace_mode(understanding_level)
    anchor = _find_anchor(section, page_no or section_progress.last_page_no)

    section_progress.last_practice_attempt_id = practice_attempt.id
    section_progress.mastery_percent = mastery_percent
    section_progress.understanding_level = UNDERSTANDING_TO_MODEL[understanding_level]
    section_progress.current_anchor_id = anchor.id if anchor else section_progress.current_anchor_id
    if page_no:
        section_progress.last_page_no = int(page_no)
    section_progress.last_operate_time = resolved_now

    if should_clear_pace_on_completion(section_progress, understanding_level=understanding_level) or next_mode == PACE_MODE_CONTINUE:
        clear_pace_state(section_progress)
    else:
        section_progress.pace_mode = next_mode
        section_progress.pace_reason_summary = _pace_reason_summary(next_mode, PACE_TRIGGER_PRACTICE)
        section_progress.pace_trigger_source = PACE_TRIGGER_PRACTICE
        section_progress.pace_updated_at = resolved_now

    lesson_progress, total_progress, overall_mastery = refresh_lesson_progress_rollup(
        db,
        student_db_id=student_db_id,
        lesson=lesson,
        section=section,
        section_progress=section_progress,
    )
    lesson_progress.last_operate_time = resolved_now

    db.add(
        StudentSectionMasteryLog(
            student_id=student_db_id,
            course_id=lesson.course_id,
            lesson_id=lesson.id,
            section_id=section.id,
            practice_attempt_id=practice_attempt.id,
            source_type="practice_submit",
            page_progress_contribution=round(progress_percent * 0.4, 2),
            practice_contribution=round(practice_percent * 0.6, 2),
            qa_contribution=0,
            final_mastery_percent=mastery_percent,
            detail_json={
                "progressPercent": progress_percent,
                "practicePercent": practice_percent,
                "paceMode": next_mode,
            },
        )
    )
    db.add(
        ProgressAdjustRecord(
            student_id=student_db_id,
            course_id=lesson.course_id,
            lesson_id=lesson.id,
            section_id=section.id,
            understanding_level=UNDERSTANDING_TO_MODEL[understanding_level],
            adjust_type="advance" if next_mode == PACE_MODE_CONTINUE else "supplement" if next_mode == PACE_MODE_SUPPLEMENT else "review",
            continue_section_id=section.id,
            recommended_page_no=int(section_progress.last_page_no or 1),
            recommended_anchor_id=anchor.id if anchor else None,
            adjust_payload={
                "triggerSource": PACE_TRIGGER_PRACTICE,
                "paceMode": next_mode,
                "practicePercent": practice_percent,
            },
        )
    )
    db.flush()

    suggestion = None if next_mode == PACE_MODE_CONTINUE else build_pace_suggestion(
        section_progress,
        section,
        mode=next_mode,
        trigger_source=PACE_TRIGGER_PRACTICE,
        updated_at=resolved_now,
    )
    return suggestion, practice_percent, mastery_percent, total_progress, overall_mastery


def record_pace_skip(
    db: Session,
    *,
    student_db_id: int,
    lesson: Lesson,
    section: LessonSection,
    section_progress: StudentSectionProgress,
    page_no: int | None = None,
) -> JsonDict | None:
    suggestion = get_active_pace_suggestion(section_progress, section)
    if suggestion is None:
        return None
    db.add(
        ProgressAdjustRecord(
            student_id=student_db_id,
            course_id=lesson.course_id,
            lesson_id=lesson.id,
            section_id=section.id,
            understanding_level=section_progress.understanding_level,
            adjust_type="keep",
            continue_section_id=section.id,
            recommended_page_no=int(page_no or section_progress.last_page_no or 1),
            recommended_anchor_id=section_progress.current_anchor_id,
            adjust_payload={
                "event": "pace_skip",
                "paceMode": suggestion["paceMode"],
                "triggerSource": suggestion["triggerSource"],
            },
        )
    )
    db.flush()
    return suggestion
