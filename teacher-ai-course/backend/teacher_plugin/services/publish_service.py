from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from chaoxing_db.models import (
    ChapterAudioAsset,
    ChapterParseTask,
    ChapterScript,
    CourseChapter,
    Lesson,
    LessonSection,
    LessonSectionAnchor,
    LessonSectionKnowledgePoint,
    LessonSectionPage,
    LessonUnit,
)

from services.status_service import resolve_course


def _get_latest_publish_chain(db: Session, course_id: int, chapter_id: int | None = None):
    query = db.query(ChapterParseTask).filter(ChapterParseTask.course_id == course_id)
    if chapter_id:
        query = query.filter(ChapterParseTask.chapter_id == chapter_id)
    parse_task = query.order_by(ChapterParseTask.id.desc()).first()
    if not parse_task or not parse_task.parse_result:
        raise LookupError("当前课程还没有可发布的解析结果")

    script = (
        db.query(ChapterScript)
        .filter(ChapterScript.parse_task_id == parse_task.id)
        .order_by(ChapterScript.updated_at.desc(), ChapterScript.id.desc())
        .first()
    )
    if not script:
        raise LookupError("当前章节还没有生成讲稿")

    audio = (
        db.query(ChapterAudioAsset)
        .filter(ChapterAudioAsset.script_id == script.id)
        .order_by(ChapterAudioAsset.updated_at.desc(), ChapterAudioAsset.id.desc())
        .first()
    )
    if not audio:
        raise LookupError("当前章节还没有生成音频")

    return parse_task, script, audio


def _ensure_lesson(db: Session, parse_task: ChapterParseTask) -> Lesson:
    lesson = db.query(Lesson).filter(Lesson.course_id == parse_task.course_id).order_by(Lesson.id.asc()).first()
    if lesson:
        return lesson

    lesson = Lesson(
        lesson_no=f"L-{uuid4().hex[:10].upper()}",
        course_id=parse_task.course_id,
        lesson_name=parse_task.course.course_name if parse_task.course else parse_task.chapter.chapter_name,
        teacher_id=parse_task.teacher_id,
        publish_version=1,
        publish_status="draft",
    )
    db.add(lesson)
    db.flush()
    return lesson


def _ensure_unit(db: Session, lesson: Lesson, chapter: CourseChapter) -> LessonUnit:
    source_unit = chapter.parent if chapter.parent and chapter.parent.chapter_type == "unit" else None
    unit_source_id = source_unit.id if source_unit else chapter.id
    unit_title = source_unit.chapter_name if source_unit else chapter.chapter_name
    unit_code = f"LU-{source_unit.chapter_code if source_unit else chapter.chapter_code}"

    unit = (
        db.query(LessonUnit)
        .filter(LessonUnit.lesson_id == lesson.id, LessonUnit.source_chapter_id == unit_source_id)
        .first()
    )
    if unit:
        unit.unit_title = unit_title
        unit.unit_code = unit_code
        unit.sort_no = source_unit.sort_no if source_unit else chapter.sort_no
        return unit

    unit = LessonUnit(
        lesson_id=lesson.id,
        course_id=lesson.course_id,
        source_chapter_id=unit_source_id,
        unit_code=unit_code,
        unit_title=unit_title,
        sort_no=source_unit.sort_no if source_unit else chapter.sort_no,
    )
    db.add(unit)
    db.flush()
    return unit


def _rebuild_section_children(db: Session, section: LessonSection, parse_task: ChapterParseTask) -> None:
    parse_result = parse_task.parse_result

    db.query(LessonSectionAnchor).filter(LessonSectionAnchor.section_id == section.id).delete()
    db.query(LessonSectionPage).filter(LessonSectionPage.section_id == section.id).delete()
    db.query(LessonSectionKnowledgePoint).filter(LessonSectionKnowledgePoint.section_id == section.id).delete()

    page_mapping = parse_result.page_mapping or []
    if isinstance(page_mapping, dict):
        page_mapping = list(page_mapping.values())

    for index, page in enumerate(page_mapping, start=1):
        page_title = page.get("title") or f"第 {index} 页"
        preview_url = page.get("previewUrl") or ""
        page_summary = page.get("summary") or f"查看《{section.section_name}》课件第 {index} 页内容。"
        parsed_content = page.get("text") or page_summary

        lesson_page = LessonSectionPage(
            lesson_id=section.lesson_id,
            section_id=section.id,
            source_ppt_asset_id=parse_task.ppt_asset_id,
            source_page_no=index,
            page_no=index,
            page_title=page_title,
            page_summary=page_summary,
            ppt_page_url=preview_url,
            parsed_content=parsed_content,
            sort_no=index,
        )
        db.add(lesson_page)
        db.flush()

        db.add(
            LessonSectionAnchor(
                lesson_id=section.lesson_id,
                section_id=section.id,
                lesson_page_id=lesson_page.id,
                anchor_code=f"A-{section.section_code}-{index}",
                anchor_title=page_title,
                page_no=index,
                start_time_sec=(index - 1) * 90,
                sort_no=index,
            )
        )

    key_points = parse_result.key_points or []
    if isinstance(key_points, dict):
        key_points = list(key_points.values())

    for index, item in enumerate(key_points, start=1):
        point_name = item.get("name") if isinstance(item, dict) else str(item)
        point_summary = item.get("summary") if isinstance(item, dict) else ""
        db.add(
            LessonSectionKnowledgePoint(
                lesson_id=section.lesson_id,
                section_id=section.id,
                point_code=f"KP-{section.section_code}-{index}",
                point_name=point_name,
                point_summary=point_summary or f"围绕“{point_name}”展开讲解与互动问答。",
                sort_no=index,
            )
        )


def publish_lesson(db: Session, course_external_id: str | None, chapter_id: int | None) -> dict:
    course = resolve_course(db, course_external_id)
    if not course:
        raise LookupError("courseId 对应的课程不存在")

    parse_task, script, audio = _get_latest_publish_chain(db, course.id, chapter_id)
    lesson = _ensure_lesson(db, parse_task)
    unit = _ensure_unit(db, lesson, parse_task.chapter)

    section = (
        db.query(LessonSection)
        .filter(LessonSection.lesson_id == lesson.id, LessonSection.source_chapter_id == parse_task.chapter_id)
        .first()
    )
    if not section:
        section = LessonSection(
            lesson_id=lesson.id,
            course_id=lesson.course_id,
            unit_id=unit.id,
            source_chapter_id=parse_task.chapter_id,
            section_code=f"LS-{parse_task.chapter.chapter_code}",
            section_name=parse_task.chapter.chapter_name,
            sort_no=parse_task.chapter.sort_no,
        )
        db.add(section)
        db.flush()

    section.unit_id = unit.id
    section.parse_result_id = parse_task.parse_result.id
    section.ppt_asset_id = parse_task.ppt_asset_id
    section.script_id = script.id
    section.audio_asset_id = audio.id
    section.section_name = parse_task.chapter.chapter_name
    section.section_summary = parse_task.parse_result.chapter_summary or f"围绕《{parse_task.chapter.chapter_name}》开展课件学习。"
    section.student_visible = True
    section.sort_no = parse_task.chapter.sort_no

    _rebuild_section_children(db, section, parse_task)

    lesson.lesson_name = course.course_name
    lesson.publish_version = max(1, int(lesson.publish_version or 1))
    lesson.publish_status = "published"
    lesson.published_at = datetime.now()

    script.script_status = "published"
    audio.status = "published"
    parse_task.chapter.status = "published"
    course.course_status = "published"

    db.commit()
    db.refresh(lesson)
    db.refresh(section)

    return {
        "lessonNo": lesson.lesson_no,
        "sectionId": str(section.id),
        "chapterId": parse_task.chapter_id,
        "chapterName": parse_task.chapter.chapter_name,
        "publishStatus": lesson.publish_status,
        "publishedAt": lesson.published_at.isoformat() if lesson.published_at else "",
    }
