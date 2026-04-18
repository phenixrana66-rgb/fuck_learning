from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.chaoxing_db.models import (
    ChapterAudioAsset,
    ChapterParseTask,
    ChapterScript,
    ChapterScriptSection,
    Course,
    CourseChapter,
    CoursePlatformBinding,
    Lesson,
)


JsonDict = dict[str, object]


def resolve_course(db: Session, external_course_id: str) -> Course | None:
    binding = (
        db.query(CoursePlatformBinding)
        .filter(CoursePlatformBinding.external_course_id == external_course_id)
        .first()
    )
    if binding:
        return binding.course
    return db.query(Course).filter(Course.course_code == external_course_id).first()


def save_script(db: Session, script_id: str, script_content: str) -> JsonDict:
    script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
    if not script:
        raise LookupError("scriptId not found")

    first_section = (
        db.query(ChapterScriptSection)
        .filter(ChapterScriptSection.script_id == script.id)
        .order_by(ChapterScriptSection.sort_no.asc(), ChapterScriptSection.id.asc())
        .first()
    )
    if first_section is None:
        first_section = ChapterScriptSection(
            script_id=script.id,
            section_code=f"{script.script_no}-01",
            section_name=script.chapter.chapter_name,
            section_content=script_content,
            sort_no=0,
        )
        db.add(first_section)
    else:
        first_section.section_content = script_content

    script.script_status = "edited"
    db.commit()
    db.refresh(script)
    return {
        "scriptId": script.script_no,
        "status": script.script_status,
        "scriptType": script.teaching_style,
        "scriptContent": first_section.section_content,
        "updatedAt": script.updated_at.isoformat() if script.updated_at else "",
    }


def get_lesson_status(db: Session, course_id: str) -> JsonDict:
    course = resolve_course(db, course_id)
    if not course:
        raise LookupError("courseId not found")

    parse_task = (
        db.query(ChapterParseTask)
        .filter(ChapterParseTask.course_id == course.id)
        .order_by(ChapterParseTask.id.desc())
        .first()
    )
    script = (
        db.query(ChapterScript)
        .filter(ChapterScript.course_id == course.id)
        .order_by(ChapterScript.id.desc())
        .first()
    )
    audio = (
        db.query(ChapterAudioAsset)
        .filter(ChapterAudioAsset.course_id == course.id)
        .order_by(ChapterAudioAsset.id.desc())
        .first()
    )
    lesson = (
        db.query(Lesson)
        .filter(Lesson.course_id == course.id)
        .order_by(Lesson.id.desc())
        .first()
    )

    active_chapter = None
    for candidate in (
        parse_task.chapter if parse_task else None,
        script.chapter if script else None,
        audio.script.chapter if audio and audio.script else None,
    ):
        if candidate is not None:
            active_chapter = candidate
            break

    script_section = None
    if script:
        script_section = (
            db.query(ChapterScriptSection)
            .filter(ChapterScriptSection.script_id == script.id)
            .order_by(ChapterScriptSection.sort_no.asc(), ChapterScriptSection.id.asc())
            .first()
        )

    return {
        "courseId": course_id,
        "chapterId": str(active_chapter.id) if active_chapter else "",
        "chapterName": active_chapter.chapter_name if active_chapter else "",
        "parse": {
            "parseId": parse_task.parse_no if parse_task else "",
            "status": parse_task.task_status if parse_task else "idle",
            "fileName": parse_task.ppt_asset.file_name if parse_task and parse_task.ppt_asset else "",
        },
        "script": {
            "scriptId": script.script_no if script else "",
            "status": script.script_status if script else "idle",
            "scriptType": script.teaching_style if script else "",
            "scriptContent": script_section.section_content if script_section else "",
            "updatedAt": script.updated_at.isoformat() if script and script.updated_at else "",
        },
        "audio": {
            "audioId": str(audio.id) if audio else "",
            "status": audio.status if audio else "idle",
            "voiceType": audio.voice_type if audio else "",
            "audioUrl": audio.audio_url if audio else "",
        },
        "publish": {
            "status": lesson.publish_status if lesson else "draft",
            "lessonNo": lesson.lesson_no if lesson else "",
            "sectionId": str(active_chapter.id) if active_chapter else "",
            "publishedAt": lesson.published_at.isoformat() if lesson and lesson.published_at else "",
        },
    }


def publish_course_lesson(db: Session, course_id: str, chapter_id: str | int | None) -> JsonDict:
    course = resolve_course(db, course_id)
    if not course:
        raise ValueError("courseId not found")

    chapter = None
    if chapter_id not in (None, ""):
        chapter = (
            db.query(CourseChapter)
            .filter(CourseChapter.id == int(chapter_id), CourseChapter.course_id == course.id)
            .first()
        )
    if chapter is None:
        latest_parse = (
            db.query(ChapterParseTask)
            .filter(ChapterParseTask.course_id == course.id)
            .order_by(ChapterParseTask.id.desc())
            .first()
        )
        chapter = latest_parse.chapter if latest_parse else None
    if chapter is None:
        raise ValueError("no chapter available to publish")

    script = (
        db.query(ChapterScript)
        .filter(ChapterScript.course_id == course.id, ChapterScript.chapter_id == chapter.id)
        .order_by(ChapterScript.id.desc())
        .first()
    )
    if script is None:
        raise ValueError("generate script before publish")

    audio = (
        db.query(ChapterAudioAsset)
        .filter(
            ChapterAudioAsset.course_id == course.id,
            ChapterAudioAsset.chapter_id == chapter.id,
            ChapterAudioAsset.script_id == script.id,
        )
        .order_by(ChapterAudioAsset.id.desc())
        .first()
    )
    if audio is None:
        raise ValueError("generate audio before publish")

    lesson = db.query(Lesson).filter(Lesson.course_id == course.id).order_by(Lesson.id.desc()).first()
    now = datetime.now()
    if lesson is None:
        lesson = Lesson(
            lesson_no=f"L{uuid4().hex[:12].upper()}",
            course_id=course.id,
            lesson_name=f"{course.course_name}-智能课",
            teacher_id=script.teacher_id,
            publish_version=1,
            publish_status="published",
            published_at=now,
        )
        db.add(lesson)
    else:
        lesson.publish_status = "published"
        lesson.publish_version = (lesson.publish_version or 0) + 1
        lesson.published_at = now

    script.script_status = "published"
    audio.status = "published"
    db.commit()
    db.refresh(lesson)
    return {
        "publishStatus": "published",
        "chapterName": chapter.chapter_name,
        "publishedAt": lesson.published_at.isoformat() if lesson.published_at else "",
        "lessonNo": lesson.lesson_no,
    }
