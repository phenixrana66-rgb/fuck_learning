from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from backend.chaoxing_db.models import ChapterPptAsset, ChapterParseResult, ChapterScript, ChapterScriptSection, Lesson, LessonSection, LessonSectionAnchor, LessonSectionPage, LessonUnit, ProgressTrackLog, ResumeRecord, StudentLessonProgress, StudentPageProgress, StudentPracticeAttempt, StudentSectionMasteryLog, StudentSectionProgress, User

UNDERSTANDING_LABELS = {"weak": "未理解", "partial": "部分理解", "complete": "完全理解"}
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PREVIEW_ROOT = PROJECT_ROOT / "public" / "lesson-previews"
JsonDict = dict[str, Any]


def _round_int(value) -> int:
    if value is None:
        return 0
    return int(round(float(value)))


def _normalize_asset_url(url: str | None) -> str:
    if not url:
        return ""
    if url.startswith(("http://", "https://", "/")):
        return url
    return f"/{url.lstrip('/')}"


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _is_placeholder_page_text(section_name: str | None, text: str | None) -> bool:
    normalized = _clean_text(text)
    if not normalized:
        return True
    section_name = _clean_text(section_name)
    if section_name and normalized.startswith(f"本页为《{section_name}》课件第 ") and normalized.endswith(" 页。"):
        return True
    if section_name and normalized.startswith(f"查看《{section_name}》课件第 ") and normalized.endswith(" 页内容。"):
        return True
    return False


def _load_primary_script_content(db: Session, section: LessonSection) -> str:
    if not section.script_id:
        return ""
    row = (
        db.query(ChapterScriptSection)
        .join(ChapterScript, ChapterScript.id == ChapterScriptSection.script_id)
        .filter(ChapterScript.id == section.script_id)
        .order_by(ChapterScriptSection.sort_no.asc(), ChapterScriptSection.id.asc())
        .first()
    )
    return _clean_text(row.section_content if row else None)


def _build_section_chapter_context(db: Session, section: LessonSection) -> dict[str, str]:
    parse_result = db.query(ChapterParseResult).filter(ChapterParseResult.id == section.parse_result_id).first() if section.parse_result_id else None
    summary = _clean_text(section.section_summary)
    parse_summary = _clean_text(parse_result.chapter_summary if parse_result else None)
    normalized_content = _clean_text(parse_result.normalized_content if parse_result else None)
    script_content = _load_primary_script_content(db, section)
    knowledge_lines = [
        f"{(point.point_name or '').strip()}：{(point.point_summary or '').strip()}"
        for point in sorted(section.knowledge_points or [], key=lambda item: (item.sort_no, item.id))
        if _clean_text(point.point_name)
    ]

    parts: list[str] = []
    if summary:
        parts.append(f"章节摘要：{summary}")
    if parse_summary and parse_summary != summary:
        parts.append(f"解析摘要：{parse_summary}")
    if normalized_content:
        parts.append(f"章节导读：{normalized_content}")
    if script_content:
        parts.append(f"教师讲稿：{script_content}")
    if knowledge_lines:
        parts.append("核心知识点：" + "；".join(knowledge_lines))

    return {
        "summary": summary,
        "parseSummary": parse_summary,
        "normalizedContent": normalized_content,
        "scriptContent": script_content,
        "chapterContextText": "\n".join(parts).strip(),
    }


def _resolve_user_id(db: Session, student_identifier: str | int | None) -> int | None:
    if student_identifier in (None, ""):
        return None
    if isinstance(student_identifier, int):
        return student_identifier
    text = str(student_identifier).strip()
    if not text:
        return None
    if text.isdigit():
        user_by_id = db.query(User.id).filter(User.id == int(text)).first()
        if user_by_id:
            return int(text)
    user = db.query(User.id).filter(User.user_no == text).first()
    return user.id if user else None


def _find_lesson(db: Session, lesson_identifier: str | int | None) -> Lesson | None:
    if lesson_identifier in (None, ""):
        return None
    filters = [Lesson.lesson_no == str(lesson_identifier)]
    lesson_text = str(lesson_identifier).strip()
    if lesson_text.isdigit():
        filters.append(Lesson.id == int(lesson_text))
    return db.query(Lesson).options(joinedload(Lesson.course), joinedload(Lesson.units).joinedload(LessonUnit.sections).joinedload(LessonSection.pages), joinedload(Lesson.units).joinedload(LessonUnit.sections).joinedload(LessonSection.anchors), joinedload(Lesson.units).joinedload(LessonUnit.sections).joinedload(LessonSection.knowledge_points)).filter(or_(*filters)).first()


def _find_teacher_name(db: Session, lesson: Lesson) -> str:
    teacher = db.query(User).filter(User.id == lesson.teacher_id).first()
    return teacher.user_name if teacher else ""


def get_student_profile_from_db(db: Session, student_identifier: str | int | None) -> JsonDict | None:
    student_db_id = _resolve_user_id(db, student_identifier)
    if not student_db_id:
        return None
    student = db.query(User).options(joinedload(User.school)).filter(User.id == student_db_id, User.role == "student").first()
    if not student:
        return None
    return {"studentId": student.user_no, "userName": student.user_name, "studentName": student.user_name, "schoolName": student.school.school_name if student.school else "", "collegeName": (student.school.school_name if student.school else "") or ""}


def _find_section(db: Session, lesson_db_id: int, section_identifier: str | int | None) -> LessonSection | None:
    if section_identifier in (None, ""):
        return None
    query = db.query(LessonSection).options(joinedload(LessonSection.pages), joinedload(LessonSection.anchors), joinedload(LessonSection.knowledge_points), joinedload(LessonSection.unit)).filter(LessonSection.lesson_id == lesson_db_id)
    text = str(section_identifier).strip()
    filters = [LessonSection.section_code == text]
    if text.isdigit():
        filters.append(LessonSection.id == int(text))
    return query.filter(or_(*filters)).first()


def _preview_folder_name(section: LessonSection) -> str:
    if "压杆稳定" in (section.section_name or ""):
        return "pressure-stability"
    return f"chapter-{section.source_chapter_id}"


def _ensure_real_preview_pages(db: Session, section: LessonSection) -> bool:
    if not section.ppt_asset_id:
        return False
    preview_dir = PREVIEW_ROOT / _preview_folder_name(section)
    if not preview_dir.exists():
        return False
    image_files = sorted(preview_dir.glob("page-*.png"), key=lambda file: int(file.stem.split("-")[-1]))
    if not image_files:
        return False
    changed = False
    existing_pages = {page.page_no: page for page in db.query(LessonSectionPage).filter(LessonSectionPage.section_id == section.id).all()}
    for page_no, _image in enumerate(image_files, start=1):
        row = existing_pages.get(page_no)
        if not row:
            row = LessonSectionPage(lesson_id=section.lesson_id, section_id=section.id, source_ppt_asset_id=section.ppt_asset_id, source_page_no=page_no, page_no=page_no, sort_no=page_no)
            db.add(row)
            changed = True
        target_url = f"/lesson-previews/{_preview_folder_name(section)}/page-{page_no}.png"
        if row.ppt_page_url != target_url:
            row.ppt_page_url = target_url
            changed = True
        if row.page_title != f"第 {page_no} 页":
            row.page_title = f"第 {page_no} 页"
            changed = True
        if row.page_summary != f"查看《{section.section_name}》课件第 {page_no} 页内容。":
            row.page_summary = f"查看《{section.section_name}》课件第 {page_no} 页内容。"
            changed = True
        if row.parsed_content != f"本页为《{section.section_name}》课件第 {page_no} 页。":
            row.parsed_content = f"本页为《{section.section_name}》课件第 {page_no} 页。"
            changed = True
        row.source_ppt_asset_id = section.ppt_asset_id
        row.source_page_no = page_no
        row.sort_no = page_no
    asset = db.query(ChapterPptAsset).filter(ChapterPptAsset.id == section.ppt_asset_id).first()
    if asset and asset.page_count != len(image_files):
        asset.page_count = len(image_files)
        changed = True
    if changed:
        db.commit()
    return changed


def _get_section_progress_map(db: Session, student_db_id: int | None, lesson_db_id: int) -> dict[int, StudentSectionProgress]:
    if not student_db_id:
        return {}
    rows = db.query(StudentSectionProgress).filter(StudentSectionProgress.student_id == student_db_id, StudentSectionProgress.lesson_id == lesson_db_id).all()
    return {row.section_id: row for row in rows}


def _find_latest_practice_attempt(db: Session, student_db_id: int | None, lesson_db_id: int, section_db_id: int) -> StudentPracticeAttempt | None:
    if not student_db_id:
        return None
    return db.query(StudentPracticeAttempt).filter(StudentPracticeAttempt.student_id == student_db_id, StudentPracticeAttempt.lesson_id == lesson_db_id, StudentPracticeAttempt.section_id == section_db_id, StudentPracticeAttempt.grading_status == "graded").order_by(StudentPracticeAttempt.submitted_at.desc(), StudentPracticeAttempt.id.desc()).first()


def _find_section_anchor(section: LessonSection, page_no: int | None = None) -> LessonSectionAnchor | None:
    anchors = sorted(section.anchors or [], key=lambda item: ((item.page_no or 0), item.sort_no, item.id))
    if not anchors:
        return None
    if page_no is None:
        return anchors[0]
    eligible = [anchor for anchor in anchors if (anchor.page_no or 0) <= page_no]
    return eligible[-1] if eligible else anchors[0]


def _build_db_chapter(section: LessonSection, unit_title: str, progress: StudentSectionProgress | None, fallback_page_no: int) -> JsonDict:
    knowledge_points = [point.point_name for point in sorted(section.knowledge_points or [], key=lambda item: (item.sort_no, item.id))]
    return {"chapterId": f"db-section-{section.id}", "sectionId": str(section.id), "chapterTitle": section.section_name, "progressPercent": _round_int(progress.progress_percent if progress else 0), "masteryPercent": _round_int(progress.mastery_percent if progress else 0), "pageNo": fallback_page_no, "summary": section.section_summary or f"围绕“{section.section_name}”展开课件学习、知识导读与章节练习。", "knowledgePoints": knowledge_points[:3] or [section.section_name, unit_title, "核心概念"]}


def enhance_player_with_db(db: Session, player: JsonDict, student_id: str | int | None) -> JsonDict:
    player_copy = cast(JsonDict, deepcopy(player or {}))
    if not player_copy.get("lessonId"):
        return player_copy
    lesson = _find_lesson(db, player_copy.get("lessonId"))
    if not lesson:
        return player_copy
    student_db_id = _resolve_user_id(db, student_id)
    progress_map = _get_section_progress_map(db, student_db_id, lesson.id)
    units = cast(list[JsonDict], player_copy.get("units", []))
    max_page_no = 0
    for unit in units:
        for chapter in unit.get("chapters", []):
            max_page_no = max(max_page_no, int(chapter.get("pageNo") or 0))
    unit_by_title = {cast(str, unit.get("unitTitle", "")): unit for unit in units if isinstance(unit, dict)}
    for unit in sorted(lesson.units or [], key=lambda item: (item.sort_no, item.id)):
        unit_payload = unit_by_title.get(unit.unit_title)
        if not unit_payload:
            unit_payload = {"unitId": f"db-unit-{unit.id}", "unitTitle": unit.unit_title, "chapters": []}
            units.append(unit_payload)
            unit_by_title[unit.unit_title] = unit_payload
        chapters = cast(list[JsonDict], unit_payload.setdefault("chapters", []))
        chapters_by_title = {cast(str, chapter.get("chapterTitle", "")): chapter for chapter in chapters if isinstance(chapter, dict)}
        for section in sorted(unit.sections or [], key=lambda item: (item.sort_no, item.id)):
            max_page_no += 1
            progress = progress_map.get(section.id)
            db_chapter = _build_db_chapter(section, unit.unit_title, progress, max_page_no)
            existing = chapters_by_title.get(section.section_name)
            if existing:
                existing.update(db_chapter)
            else:
                chapters.append(db_chapter)
    chapters = [chapter for unit in units for chapter in unit.get("chapters", [])]
    player_copy["units"] = units
    player_copy["teacherName"] = _find_teacher_name(db, lesson) or player_copy.get("teacherName", "")
    if chapters:
        player_copy["progressPercent"] = _round_int(sum(int(chapter.get("progressPercent") or 0) for chapter in chapters) / len(chapters))
        player_copy["masteryPercent"] = _round_int(sum(int(chapter.get("masteryPercent") or 0) for chapter in chapters) / len(chapters))
    return player_copy


def get_db_progress_state(db: Session, student_id: str | int | None, lesson_identifier: str | int | None) -> JsonDict | None:
    lesson = _find_lesson(db, lesson_identifier)
    student_db_id = _resolve_user_id(db, student_id)
    if not lesson or not student_db_id:
        return None
    lesson_progress = db.query(StudentLessonProgress).filter(StudentLessonProgress.student_id == student_db_id, StudentLessonProgress.lesson_id == lesson.id).first()
    if not lesson_progress:
        return None
    anchor = None
    if lesson_progress.current_anchor_id:
        anchor = db.query(LessonSectionAnchor).filter(LessonSectionAnchor.id == lesson_progress.current_anchor_id).first()
    if not anchor and lesson_progress.current_section_id:
        section = db.query(LessonSection).filter(LessonSection.id == lesson_progress.current_section_id).first()
        if section:
            anchor = _find_section_anchor(section, lesson_progress.last_page_no)
    return {"sectionId": str(lesson_progress.current_section_id) if lesson_progress.current_section_id else "", "anchorId": str(anchor.id) if anchor else "", "anchorTitle": anchor.anchor_title if anchor else "", "pageNo": lesson_progress.last_page_no or (anchor.page_no if anchor else 1) or 1, "currentTime": (anchor.start_time_sec if anchor else 0) or 0, "progressPercent": _round_int(lesson_progress.total_progress), "understandingLevel": "partial", "weakPoints": []}


def get_section_detail(db: Session, student_id: str | int | None, lesson_identifier: str | int | None, section_identifier: str | int | None) -> JsonDict | None:
    lesson = _find_lesson(db, lesson_identifier)
    if not lesson:
        return None
    section = _find_section(db, lesson.id, section_identifier)
    if not section:
        return None
    if _ensure_real_preview_pages(db, section):
        section = _find_section(db, lesson.id, section_identifier)
        if not section:
            return None
    student_db_id = _resolve_user_id(db, student_id)
    progress = None
    if student_db_id:
        progress = db.query(StudentSectionProgress).filter(StudentSectionProgress.student_id == student_db_id, StudentSectionProgress.lesson_id == lesson.id, StudentSectionProgress.section_id == section.id).first()
    practice_attempt = _find_latest_practice_attempt(db, student_db_id, lesson.id, section.id)
    parse_result = db.query(ChapterParseResult).filter(ChapterParseResult.id == section.parse_result_id).first() if section.parse_result_id else None
    page_progress_rows = {}
    if student_db_id:
        rows = db.query(StudentPageProgress).filter(StudentPageProgress.student_id == student_db_id, StudentPageProgress.section_id == section.id).all()
        page_progress_rows = {row.lesson_page_id: row for row in rows}
    anchors_by_page = {}
    for anchor in sorted(section.anchors or [], key=lambda item: ((item.page_no or 0), item.sort_no, item.id)):
        if anchor.page_no and anchor.page_no not in anchors_by_page:
            anchors_by_page[anchor.page_no] = anchor
    pages = []
    for page in sorted(section.pages or [], key=lambda item: (item.sort_no, item.page_no, item.id)):
        row = page_progress_rows.get(page.id)
        anchor = anchors_by_page.get(page.page_no)
        pages.append({"lessonPageId": page.id, "pageNo": page.page_no, "pageTitle": page.page_title or f"第 {page.page_no} 页", "pageSummary": page.page_summary or "", "imageUrl": _normalize_asset_url(page.ppt_page_url), "parsedContent": page.parsed_content or page.page_summary or "", "anchorId": str(anchor.id) if anchor else "", "anchorTitle": anchor.anchor_title if anchor else "", "isRead": bool(row and row.is_completed)})
    current_page_no = progress.last_page_no if progress and progress.last_page_no else (pages[0]["pageNo"] if pages else 1)
    teacher_name = _find_teacher_name(db, lesson)
    return {"lessonId": lesson.lesson_no, "lessonDbId": lesson.id, "courseName": lesson.course.course_name if lesson.course else lesson.lesson_name, "teacherName": teacher_name, "unitTitle": section.unit.unit_title if section.unit else "", "sectionId": str(section.id), "sectionTitle": section.section_name, "progressPercent": _round_int(progress.progress_percent if progress else 0), "masteryPercent": _round_int(progress.mastery_percent if progress else 0), "practicePercent": _round_int(practice_attempt.accuracy_percent if practice_attempt and practice_attempt.accuracy_percent is not None else 0), "currentPageNo": current_page_no, "aiGuideContent": ((parse_result.normalized_content if parse_result else None) or (parse_result.chapter_summary if parse_result else None) or section.section_summary or ""), "knowledgePoints": [point.point_name for point in sorted(section.knowledge_points or [], key=lambda item: (item.sort_no, item.id))], "pages": pages}


def get_section_context_for_qa(db: Session, lesson_identifier: str | int | None, section_identifier: str | int | None) -> JsonDict | None:
    lesson = _find_lesson(db, lesson_identifier)
    if not lesson:
        return None
    section = _find_section(db, lesson.id, section_identifier)
    if not section:
        return None
    chapter_context = _build_section_chapter_context(db, section)
    return {
        "lessonDbId": lesson.id,
        "lessonNo": lesson.lesson_no,
        "courseName": lesson.course.course_name if lesson.course else lesson.lesson_name,
        "sectionDbId": section.id,
        "sectionCode": section.section_code,
        "sectionName": section.section_name,
        "summary": chapter_context["summary"],
        "parseSummary": chapter_context["parseSummary"],
        "normalizedContent": chapter_context["normalizedContent"],
        "scriptContent": chapter_context["scriptContent"],
        "chapterContextText": chapter_context["chapterContextText"],
    }


def get_page_context_for_qa(db: Session, lesson_identifier: str | int | None, section_identifier: str | int | None, page_no: int | None) -> JsonDict | None:
    lesson = _find_lesson(db, lesson_identifier)
    if not lesson:
        return None
    section = _find_section(db, lesson.id, section_identifier)
    if not section:
        return None
    pages = sorted(section.pages or [], key=lambda item: (item.sort_no, item.page_no, item.id))
    current_page = next((item for item in pages if item.page_no == page_no), None) if page_no else None
    if not current_page and pages:
        current_page = pages[0]
    if not current_page:
        return None
    anchor = _find_section_anchor(section, current_page.page_no)
    return {
        "lessonDbId": lesson.id,
        "sectionDbId": section.id,
        "pageDbId": current_page.id,
        "pageNo": current_page.page_no,
        "pageTitle": current_page.page_title or "",
        "pageSummary": current_page.page_summary or "",
        "parsedContent": current_page.parsed_content or current_page.page_summary or "",
        "hasMeaningfulContent": not _is_placeholder_page_text(section.section_name, current_page.parsed_content or current_page.page_summary or ""),
        "anchorId": str(anchor.id) if anchor else "",
        "anchorTitle": anchor.anchor_title if anchor else section.section_name,
    }


def get_section_knowledge_points_for_qa(db: Session, lesson_identifier: str | int | None, section_identifier: str | int | None) -> list[JsonDict]:
    lesson = _find_lesson(db, lesson_identifier)
    if not lesson:
        return []
    section = _find_section(db, lesson.id, section_identifier)
    if not section:
        return []
    return [
        {
            "id": point.id,
            "pointCode": point.point_code,
            "pointName": point.point_name,
            "pointSummary": point.point_summary or "",
        }
        for point in sorted(section.knowledge_points or [], key=lambda item: (item.sort_no, item.id))
    ]


def save_recent_chapter_visit(db: Session, student_id: str | int | None, lesson_identifier: str | int | None, section_identifier: str | int | None, page_no: int | None) -> JsonDict | None:
    lesson = _find_lesson(db, lesson_identifier)
    student_db_id = _resolve_user_id(db, student_id)
    if not lesson or not student_db_id:
        return None
    section = _find_section(db, lesson.id, section_identifier)
    if not section:
        return None
    safe_page_no = int(page_no or 1)
    anchor = _find_section_anchor(section, safe_page_no)
    resume_record = ResumeRecord(student_id=student_db_id, course_id=lesson.course_id, lesson_id=lesson.id, section_id=section.id, anchor_id=anchor.id if anchor else None, page_no=safe_page_no, resume_time_sec=anchor.start_time_sec if anchor else 0, resume_type="manual")
    db.add(resume_record)
    db.commit()
    return {"lessonId": lesson.lesson_no, "sectionId": str(section.id), "pageNo": safe_page_no, "savedAt": resume_record.created_at.strftime("%Y-%m-%d %H:%M") if resume_record.created_at else ""}


def get_recent_chapter_visits(db: Session, student_id: str | int | None, limit: int = 3) -> list[JsonDict]:
    student_db_id = _resolve_user_id(db, student_id)
    if not student_db_id:
        return []
    rows = db.query(ResumeRecord).filter(ResumeRecord.student_id == student_db_id, ResumeRecord.section_id.isnot(None), ResumeRecord.page_no.isnot(None)).order_by(ResumeRecord.created_at.desc(), ResumeRecord.id.desc()).all()
    if not rows:
        return []
    lesson_ids = {row.lesson_id for row in rows if row.lesson_id}
    section_ids = {row.section_id for row in rows if row.section_id}
    lessons = {lesson.id: lesson for lesson in db.query(Lesson).options(joinedload(Lesson.course)).filter(Lesson.id.in_(lesson_ids)).all()}
    sections = {section.id: section for section in db.query(LessonSection).filter(LessonSection.id.in_(section_ids)).all()}
    result = []
    seen = set()
    for row in rows:
        if not row.lesson_id or not row.section_id:
            continue
        dedupe_key = (row.lesson_id, row.section_id)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        lesson = lessons.get(row.lesson_id)
        section = sections.get(row.section_id)
        if not lesson or not section:
            continue
        result.append({"lessonId": lesson.lesson_no, "courseName": lesson.course.course_name if lesson.course else lesson.lesson_name, "chapterId": str(section.source_chapter_id or section.id), "chapterTitle": section.section_name, "sectionId": str(section.id), "pageNo": row.page_no or 1, "lastExitedAt": row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else "", "exitedAt": int(row.created_at.timestamp() * 1000) if row.created_at else 0})
        if len(result) >= limit:
            break
    return result


def mark_page_read(db: Session, student_id: str | int | None, lesson_identifier: str | int | None, section_identifier: str | int | None, lesson_page_id: str | int | None, page_no: int | None) -> JsonDict | None:
    lesson = _find_lesson(db, lesson_identifier)
    student_db_id = _resolve_user_id(db, student_id)
    if not lesson or not student_db_id or section_identifier in (None, "") or lesson_page_id in (None, ""):
        return None
    section = _find_section(db, lesson.id, section_identifier)
    if not section:
        return None
    if _ensure_real_preview_pages(db, section):
        section = _find_section(db, lesson.id, section_identifier)
        if not section:
            return None
    page = db.query(LessonSectionPage).filter(LessonSectionPage.id == int(lesson_page_id), LessonSectionPage.section_id == section.id).first()
    if not page:
        return None
    now = datetime.now()
    progress_row = db.query(StudentPageProgress).filter(StudentPageProgress.student_id == student_db_id, StudentPageProgress.lesson_page_id == page.id).first()
    if not progress_row:
        progress_row = StudentPageProgress(student_id=student_db_id, course_id=lesson.course_id, lesson_id=lesson.id, section_id=section.id, lesson_page_id=page.id, page_no=page.page_no, read_percent=100.0, is_completed=True, stay_seconds=0, first_read_at=now, last_read_at=now, completed_at=now)
        db.add(progress_row)
    else:
        progress_row.read_percent = 100.0
        progress_row.is_completed = True
        progress_row.last_read_at = now
        progress_row.completed_at = progress_row.completed_at or now
    db.flush()
    total_pages = len(section.pages or [])
    completed_pages = db.query(StudentPageProgress).filter(StudentPageProgress.student_id == student_db_id, StudentPageProgress.section_id == section.id, StudentPageProgress.is_completed == True).count()  # noqa: E712
    progress_percent = _round_int((completed_pages / total_pages) * 100) if total_pages else 0
    practice_attempt = _find_latest_practice_attempt(db, student_db_id, lesson.id, section.id)
    practice_percent = _round_int(practice_attempt.accuracy_percent if practice_attempt and practice_attempt.accuracy_percent is not None else 0)
    mastery_percent = _round_int(progress_percent * 0.4 + practice_percent * 0.6)
    anchor = _find_section_anchor(section, page_no or page.page_no)
    section_progress = db.query(StudentSectionProgress).filter(StudentSectionProgress.student_id == student_db_id, StudentSectionProgress.lesson_id == lesson.id, StudentSectionProgress.section_id == section.id).first()
    if not section_progress:
        section_progress = StudentSectionProgress(student_id=student_db_id, course_id=lesson.course_id, lesson_id=lesson.id, unit_id=section.unit_id, section_id=section.id)
        db.add(section_progress)
    section_progress.current_anchor_id = anchor.id if anchor else None
    section_progress.last_page_no = page.page_no
    section_progress.progress_percent = progress_percent
    section_progress.mastery_percent = mastery_percent
    section_progress.last_practice_attempt_id = practice_attempt.id if practice_attempt else None
    section_progress.last_operate_time = now
    lesson_progress = db.query(StudentLessonProgress).filter(StudentLessonProgress.student_id == student_db_id, StudentLessonProgress.lesson_id == lesson.id).first()
    if not lesson_progress:
        lesson_progress = StudentLessonProgress(student_id=student_db_id, course_id=lesson.course_id, lesson_id=lesson.id)
        db.add(lesson_progress)
    db.flush()
    all_section_rows = db.query(StudentSectionProgress).filter(StudentSectionProgress.student_id == student_db_id, StudentSectionProgress.lesson_id == lesson.id).all()
    if all_section_rows:
        total_progress = _round_int(sum(_round_int(row.progress_percent) for row in all_section_rows) / len(all_section_rows))
        overall_mastery = _round_int(sum(_round_int(row.mastery_percent) for row in all_section_rows) / len(all_section_rows))
    else:
        total_progress = progress_percent
        overall_mastery = mastery_percent
    lesson_progress.total_progress = total_progress
    lesson_progress.overall_mastery_percent = overall_mastery
    lesson_progress.current_unit_id = section.unit_id
    lesson_progress.current_section_id = section.id
    lesson_progress.current_anchor_id = anchor.id if anchor else None
    lesson_progress.last_page_no = page.page_no
    lesson_progress.last_operate_time = now
    db.add(ProgressTrackLog(student_id=student_db_id, course_id=lesson.course_id, lesson_id=lesson.id, section_id=section.id, anchor_id=anchor.id if anchor else None, page_no=page.page_no, track_source="page_read", progress_percent=progress_percent, last_operate_time=now))
    db.add(ResumeRecord(student_id=student_db_id, course_id=lesson.course_id, lesson_id=lesson.id, section_id=section.id, anchor_id=anchor.id if anchor else None, page_no=page.page_no, resume_time_sec=anchor.start_time_sec if anchor else 0, resume_type="manual"))
    db.add(StudentSectionMasteryLog(student_id=student_db_id, course_id=lesson.course_id, lesson_id=lesson.id, section_id=section.id, practice_attempt_id=practice_attempt.id if practice_attempt else None, source_type="progress_sync", page_progress_contribution=round(progress_percent * 0.4, 2), practice_contribution=round(practice_percent * 0.6, 2), qa_contribution=0, final_mastery_percent=mastery_percent, detail_json={"progressPercent": progress_percent, "practicePercent": practice_percent}))
    db.commit()
    return {"sectionId": str(section.id), "sectionTitle": section.section_name, "pageNo": page.page_no, "anchorId": str(anchor.id) if anchor else "", "anchorTitle": anchor.anchor_title if anchor else "", "progressPercent": progress_percent, "masteryPercent": mastery_percent, "overallProgress": total_progress, "overallMastery": overall_mastery}


def interact_with_section_context(db: Session, lesson_identifier: str | int | None, section_identifier: str | int | None, question: str, page_no: int | None) -> JsonDict | None:
    lesson = _find_lesson(db, lesson_identifier)
    if not lesson:
        return None
    section = _find_section(db, lesson.id, section_identifier)
    if not section:
        return None
    pages = sorted(section.pages or [], key=lambda item: (item.sort_no, item.page_no, item.id))
    current_page = next((item for item in pages if item.page_no == page_no), None) if page_no is not None else None
    text = question or ""
    if any(keyword in text for keyword in ["不会", "不懂", "没明白", "不理解"]):
        understanding = "weak"
    elif any(keyword in text for keyword in ["区别", "关系", "为什么", "如何", "怎么"]):
        understanding = "partial"
    else:
        understanding = "complete"
    anchor = _find_section_anchor(section, current_page.page_no if current_page else None)
    related_points = [point.point_name for point in sorted(section.knowledge_points or [], key=lambda item: (item.sort_no, item.id))][:3]
    chapter_context = _build_section_chapter_context(db, section)
    if current_page and not _is_placeholder_page_text(section.section_name, current_page.parsed_content or current_page.page_summary or ""):
        answer = f"当前学习章节是《{section.section_name}》，你现在看到的是第 {current_page.page_no} 页。建议先围绕 {', '.join(related_points[:2]) or '本章核心知识点'} 理解本页内容。{current_page.parsed_content or section.section_summary or ''}"
    else:
        answer = f"当前学习章节是《{section.section_name}》。这次回答将围绕整章内容展开，建议重点关注 {', '.join(related_points[:3]) or '本章核心知识点'}。{chapter_context['chapterContextText'] or section.section_summary or ''}"
    return {"answer": answer, "relatedKnowledgePoints": related_points, "understandingLevel": understanding, "understandingLabel": UNDERSTANDING_LABELS[understanding], "resumeAnchor": {"anchorId": str(anchor.id) if anchor else "", "anchorTitle": anchor.anchor_title if anchor else section.section_name, "pageNo": current_page.page_no if current_page else (pages[0].page_no if pages else 1)}, "weakPoints": related_points[:2] if understanding != "complete" else []}
