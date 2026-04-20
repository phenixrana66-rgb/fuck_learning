from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.chaoxing_db.models import (
    ChapterAudioAsset,
    ChapterParseResult,
    ChapterParseTask,
    ChapterPptAsset,
    ChapterScript,
    ChapterScriptSection,
    ChapterSectionAudioAsset,
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


def _normalize_audio_asset_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlsplit(url)
    if parsed.scheme in {"http", "https"} and parsed.hostname in {"localhost", "testserver"} and parsed.path:
        if parsed.query:
            return f"{parsed.path}?{parsed.query}"
        return parsed.path
    return url


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
            "assetId": str(parse_task.ppt_asset.id) if parse_task and parse_task.ppt_asset else "",
            "versionNo": parse_task.ppt_asset.version_no if parse_task and parse_task.ppt_asset else None,
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
            "audioUrl": _normalize_audio_asset_url(audio.audio_url) if audio else "",
        },
        "publish": {
            "status": lesson.publish_status if lesson else "draft",
            "lessonNo": lesson.lesson_no if lesson else "",
            "sectionId": str(active_chapter.id) if active_chapter else "",
            "publishedAt": lesson.published_at.isoformat() if lesson and lesson.published_at else "",
        },
    }


def list_courseware_assets(db: Session, course_id: str, chapter_id: str | int | None = None) -> JsonDict:
    course = resolve_course(db, course_id)
    if not course:
        raise LookupError("courseId not found")

    chapter = _resolve_target_chapter(db, course.id, chapter_id)
    if chapter is None:
        return {
            "courseId": course_id,
            "chapterId": "",
            "chapterName": "",
            "assets": [],
        }

    assets = (
        db.query(ChapterPptAsset)
        .filter(ChapterPptAsset.course_id == course.id, ChapterPptAsset.chapter_id == chapter.id)
        .order_by(ChapterPptAsset.version_no.desc(), ChapterPptAsset.id.desc())
        .all()
    )
    asset_ids = [asset.id for asset in assets]
    parse_tasks = (
        db.query(ChapterParseTask)
        .filter(ChapterParseTask.ppt_asset_id.in_(asset_ids))
        .order_by(ChapterParseTask.id.desc())
        .all()
        if asset_ids
        else []
    )
    parse_task_ids = [task.id for task in parse_tasks]
    parse_results = (
        db.query(ChapterParseResult)
        .filter(ChapterParseResult.parse_task_id.in_(parse_task_ids))
        .all()
        if parse_task_ids
        else []
    )
    scripts = (
        db.query(ChapterScript)
        .filter(ChapterScript.parse_task_id.in_(parse_task_ids))
        .order_by(ChapterScript.id.desc())
        .all()
        if parse_task_ids
        else []
    )
    script_ids = [script.id for script in scripts]
    audios = (
        db.query(ChapterAudioAsset)
        .filter(ChapterAudioAsset.script_id.in_(script_ids))
        .order_by(ChapterAudioAsset.id.desc())
        .all()
        if script_ids
        else []
    )

    parse_result_by_task_id = {row.parse_task_id: row for row in parse_results}
    scripts_by_parse_task_id: dict[int, list[ChapterScript]] = {}
    for script in scripts:
        scripts_by_parse_task_id.setdefault(script.parse_task_id, []).append(script)

    audios_by_script_id: dict[int, list[ChapterAudioAsset]] = {}
    for audio in audios:
        audios_by_script_id.setdefault(audio.script_id, []).append(audio)

    parse_tasks_by_asset_id: dict[int, list[ChapterParseTask]] = {}
    for task in parse_tasks:
        parse_tasks_by_asset_id.setdefault(task.ppt_asset_id, []).append(task)

    serialized_assets = []
    latest_asset_id = assets[0].id if assets else None
    for asset in assets:
        serialized_parse_tasks = []
        for task in parse_tasks_by_asset_id.get(asset.id, []):
            task_scripts = scripts_by_parse_task_id.get(task.id, [])
            audio_count = sum(len(audios_by_script_id.get(script.id, [])) for script in task_scripts)
            latest_script = task_scripts[0] if task_scripts else None
            latest_audio = audios_by_script_id.get(latest_script.id, [None])[0] if latest_script else None
            is_published = any(script.script_status == "published" for script in task_scripts)
            if latest_script is not None:
                is_published = is_published or any(
                    audio.status == "published" for audio in audios_by_script_id.get(latest_script.id, [])
                )
            serialized_parse_tasks.append(
                {
                    "parseId": task.parse_no,
                    "taskStatus": task.task_status,
                    "createdAt": _iso(task.created_at),
                    "finishedAt": _iso(task.finished_at),
                    "errorMsg": task.error_msg or "",
                    "hasParseResult": task.id in parse_result_by_task_id,
                    "scriptCount": len(task_scripts),
                    "audioCount": audio_count,
                    "latestScriptId": latest_script.script_no if latest_script else "",
                    "latestAudioId": str(latest_audio.id) if latest_audio else "",
                    "isPublished": is_published,
                }
            )

        serialized_assets.append(
            {
                "assetId": str(asset.id),
                "versionNo": asset.version_no,
                "fileName": asset.file_name,
                "fileType": asset.file_type,
                "fileUrl": asset.file_url,
                "fileSize": asset.file_size or 0,
                "pageCount": asset.page_count or 0,
                "uploadStatus": asset.upload_status,
                "uploadedAt": _iso(asset.created_at),
                "updatedAt": _iso(asset.updated_at),
                "isLatest": asset.id == latest_asset_id,
                "parseTasks": serialized_parse_tasks,
            }
        )

    return {
        "courseId": course_id,
        "chapterId": str(chapter.id),
        "chapterName": chapter.chapter_name,
        "assets": serialized_assets,
    }


def list_scripts_by_parse(db: Session, parse_id: str) -> JsonDict:
    parse_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == parse_id).first()
    if not parse_task:
        raise LookupError("parseId not found")

    scripts = (
        db.query(ChapterScript)
        .filter(ChapterScript.parse_task_id == parse_task.id)
        .order_by(ChapterScript.updated_at.desc(), ChapterScript.id.desc())
        .all()
    )
    script_ids = [script.id for script in scripts]
    audios = (
        db.query(ChapterAudioAsset)
        .filter(ChapterAudioAsset.script_id.in_(script_ids))
        .order_by(ChapterAudioAsset.updated_at.desc(), ChapterAudioAsset.id.desc())
        .all()
        if script_ids
        else []
    )
    audios_by_script_id: dict[int, list[ChapterAudioAsset]] = {}
    for audio in audios:
        audios_by_script_id.setdefault(audio.script_id, []).append(audio)

    return {
        "parseId": parse_id,
        "courseId": str(parse_task.course_id),
        "chapterId": str(parse_task.chapter_id),
        "chapterName": parse_task.chapter.chapter_name if parse_task.chapter else "",
        "fileName": parse_task.ppt_asset.file_name if parse_task.ppt_asset else "",
        "fileType": parse_task.ppt_asset.file_type if parse_task.ppt_asset else "",
        "assetId": str(parse_task.ppt_asset.id) if parse_task.ppt_asset else "",
        "versionNo": parse_task.ppt_asset.version_no if parse_task.ppt_asset else None,
        "scripts": [
            {
                "scriptId": script.script_no,
                "parseId": parse_id,
                "scriptStatus": script.script_status,
                "teachingStyle": script.teaching_style,
                "speechSpeed": script.speech_speed,
                "createdAt": _iso(script.created_at),
                "updatedAt": _iso(script.updated_at),
                "audioCount": len(audios_by_script_id.get(script.id, [])),
                "latestAudioId": str(audios_by_script_id.get(script.id, [None])[0].id) if audios_by_script_id.get(script.id) else "",
                "isPublished": script.script_status == "published" or any(audio.status == "published" for audio in audios_by_script_id.get(script.id, [])),
            }
            for script in scripts
        ],
    }


def list_audios_by_script(db: Session, script_id: str) -> JsonDict:
    script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
    if not script:
        raise LookupError("scriptId not found")

    audios = (
        db.query(ChapterAudioAsset)
        .filter(ChapterAudioAsset.script_id == script.id)
        .order_by(ChapterAudioAsset.updated_at.desc(), ChapterAudioAsset.id.desc())
        .all()
    )
    audio_ids = [audio.id for audio in audios]
    section_audio_assets = (
        db.query(ChapterSectionAudioAsset)
        .filter(ChapterSectionAudioAsset.audio_asset_id.in_(audio_ids))
        .all()
        if audio_ids
        else []
    )
    section_count_by_audio_id: dict[int, int] = {}
    for row in section_audio_assets:
        section_count_by_audio_id[row.audio_asset_id] = section_count_by_audio_id.get(row.audio_asset_id, 0) + 1

    return {
        "scriptId": script_id,
        "parseId": script.parse_task.parse_no if script.parse_task else "",
        "audios": [
            {
                "audioId": str(audio.id),
                "voiceType": audio.voice_type,
                "audioFormat": audio.audio_format,
                "audioUrl": _normalize_audio_asset_url(audio.audio_url),
                "status": audio.status,
                "createdAt": _iso(audio.created_at),
                "updatedAt": _iso(audio.updated_at),
                "totalDurationSec": audio.total_duration_sec or 0,
                "fileSize": audio.file_size or 0,
                "sectionCount": section_count_by_audio_id.get(audio.id, 0),
                "isPublished": audio.status == "published",
            }
            for audio in audios
        ],
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


def _resolve_target_chapter(db: Session, course_db_id: int, chapter_id: str | int | None) -> CourseChapter | None:
    if chapter_id not in (None, ""):
        return (
            db.query(CourseChapter)
            .filter(CourseChapter.id == int(chapter_id), CourseChapter.course_id == course_db_id)
            .first()
        )

    latest_parse = (
        db.query(ChapterParseTask)
        .filter(ChapterParseTask.course_id == course_db_id)
        .order_by(ChapterParseTask.id.desc())
        .first()
    )
    if latest_parse and latest_parse.chapter is not None:
        return latest_parse.chapter

    latest_script = (
        db.query(ChapterScript)
        .filter(ChapterScript.course_id == course_db_id)
        .order_by(ChapterScript.id.desc())
        .first()
    )
    if latest_script and latest_script.chapter is not None:
        return latest_script.chapter

    return (
        db.query(CourseChapter)
        .filter(CourseChapter.course_id == course_db_id)
        .order_by(CourseChapter.sort_no.asc(), CourseChapter.id.asc())
        .first()
    )


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""
