from __future__ import annotations

from sqlalchemy.orm import Session

from chaoxing_db.models import ChapterAudioAsset, ChapterParseTask, ChapterScript, Course, CoursePlatformBinding, Lesson, LessonSection


def resolve_course(db: Session, external_course_id: str | None) -> Course | None:
    if not external_course_id:
        return None

    binding = (
        db.query(CoursePlatformBinding)
        .filter(CoursePlatformBinding.external_course_id == str(external_course_id))
        .first()
    )
    if binding:
        return binding.course

    return db.query(Course).filter(Course.course_code == str(external_course_id)).first()


def get_course_status(db: Session, external_course_id: str | None) -> dict:
    course = resolve_course(db, external_course_id)
    if not course:
        raise LookupError("courseId 对应的课程不存在")

    parse_task = (
        db.query(ChapterParseTask)
        .filter(ChapterParseTask.course_id == course.id)
        .order_by(ChapterParseTask.id.desc())
        .first()
    )

    script = None
    audio = None
    if parse_task:
        script = (
            db.query(ChapterScript)
            .filter(ChapterScript.parse_task_id == parse_task.id)
            .order_by(ChapterScript.updated_at.desc(), ChapterScript.id.desc())
            .first()
        )
    if script:
        audio = (
            db.query(ChapterAudioAsset)
            .filter(ChapterAudioAsset.script_id == script.id)
            .order_by(ChapterAudioAsset.updated_at.desc(), ChapterAudioAsset.id.desc())
            .first()
        )

    lesson = db.query(Lesson).filter(Lesson.course_id == course.id).order_by(Lesson.updated_at.desc(), Lesson.id.desc()).first()
    published_section = None
    if parse_task:
        published_section = (
            db.query(LessonSection)
            .filter(LessonSection.course_id == course.id, LessonSection.source_chapter_id == parse_task.chapter_id)
            .order_by(LessonSection.updated_at.desc(), LessonSection.id.desc())
            .first()
        )

    primary_section = None
    if script and script.sections:
        primary_section = sorted(script.sections, key=lambda item: (item.sort_no, item.id))[0]

    chapter_name = parse_task.chapter.chapter_name if parse_task and parse_task.chapter else ""
    return {
        "courseId": external_course_id,
        "chapterId": parse_task.chapter_id if parse_task else None,
        "chapterName": chapter_name,
        "parse": {
            "parseId": parse_task.parse_no if parse_task else "",
            "status": parse_task.task_status if parse_task else "idle",
            "fileName": parse_task.ppt_asset.file_name if parse_task and parse_task.ppt_asset else "",
        },
        "script": {
            "scriptId": script.script_no if script else "",
            "status": script.script_status if script else "idle",
            "scriptType": script.teaching_style if script else "",
            "scriptContent": primary_section.section_content if primary_section else "",
            "updatedAt": script.updated_at.isoformat() if script and script.updated_at else "",
        },
        "audio": {
            "audioId": str(audio.id) if audio else "",
            "status": audio.status if audio else "idle",
            "voiceType": audio.voice_type if audio else "",
            "audioUrl": audio.audio_url if audio else "",
            "updatedAt": audio.updated_at.isoformat() if audio and audio.updated_at else "",
        },
        "publish": {
            "lessonNo": lesson.lesson_no if lesson else "",
            "sectionId": str(published_section.id) if published_section else "",
            "status": lesson.publish_status if lesson else "draft",
            "publishedAt": lesson.published_at.isoformat() if lesson and lesson.published_at else "",
        },
    }
