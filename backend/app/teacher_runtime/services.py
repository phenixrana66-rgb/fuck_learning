from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.common.db import session_scope
from backend.app.common.config import get_settings
from backend.app.common.exceptions import ApiError
from backend.chaoxing_db.models import (
    ChapterAudioAsset,
    ChapterKnowledgeNode,
    ChapterParseResult,
    ChapterParseTask,
    ChapterPptAsset,
    ChapterScript,
    ChapterScriptSection,
    Course,
    CourseChapter,
    CourseClass,
    CourseMember,
    CoursePlatformBinding,
    LessonSection,
    LessonSectionPage,
    School,
    User,
    UserPlatformBinding,
)
from backend.app.courseware.service import execute_parse_pipeline
from backend.app.script.schemas import GenerateScriptRequest
from backend.app.script.service import generate_script as generate_main_script

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
MOCK_REMOTE_PREFIX = "/mock-remote/examples"
SCRIPT_TYPE_MAPPING = {
    "standard": "standard",
    "detail": "detailed",
    "simple": "concise",
    "detailed": "detailed",
    "concise": "concise",
}
JsonDict = dict[str, Any]


def _get_teacher_by_token(db: Session, token: str | None) -> User:
    settings = get_settings()
    teacher = (
        db.query(User)
        .filter(User.role == "teacher", User.auth_token == (token or settings.teacher_test_platform_token))
        .first()
    )
    if teacher:
        return teacher
    raise PermissionError("token 无效")


def sync_user(db: Session, token: str | None) -> JsonDict:
    teacher = _get_teacher_by_token(db, token)
    school = db.query(School).filter(School.id == teacher.school_id).first()
    binding = (
        db.query(UserPlatformBinding)
        .filter(UserPlatformBinding.user_id == teacher.id, UserPlatformBinding.external_role == "teacher")
        .first()
    )
    return {
        "teacherId": binding.external_user_id if binding else teacher.user_no,
        "userId": teacher.user_no,
        "teacherName": teacher.user_name,
        "userName": teacher.user_name,
        "schoolId": school.school_code if school else "",
        "schoolName": school.school_name if school else "",
    }


def require_teacher(db: Session, token: str | None) -> User:
    return _get_teacher_by_token(db, token)


def sync_courses(db: Session, teacher: User) -> JsonDict:
    memberships = (
        db.query(CourseMember)
        .filter(CourseMember.user_id == teacher.id, CourseMember.member_role == "teacher")
        .all()
    )
    course_list = []
    for membership in memberships:
        course = membership.course
        if not course:
            continue
        binding = db.query(CoursePlatformBinding).filter(CoursePlatformBinding.course_id == course.id).first()
        school = db.query(School).filter(School.id == course.school_id).first()
        class_obj = None
        if membership.class_id:
            class_obj = db.query(CourseClass).filter(CourseClass.id == membership.class_id).first()
        course_list.append(
            {
                "courseId": binding.external_course_id if binding else course.course_code,
                "courseName": course.course_name,
                "classId": class_obj.class_code if class_obj else "",
                "schoolId": school.school_code if school else "",
            }
        )
    return {"courseList": course_list}


def _resolve_course(db: Session, external_course_id: str) -> Course | None:
    binding = db.query(CoursePlatformBinding).filter(CoursePlatformBinding.external_course_id == external_course_id).first()
    if binding:
        return binding.course
    return db.query(Course).filter(Course.course_code == external_course_id).first()


def _pick_chapter(db: Session, course_id: int, file_name: str) -> CourseChapter:
    chapters = (
        db.query(CourseChapter)
        .filter(CourseChapter.course_id == course_id, CourseChapter.chapter_type != "unit")
        .order_by(CourseChapter.sort_no.asc(), CourseChapter.id.asc())
        .all()
    )
    normalized = file_name.replace(" ", "")
    for chapter in chapters:
        if chapter.chapter_name.replace(" ", "") in normalized:
            return chapter
    if chapters:
        return chapters[0]
    raise ValueError("当前课程未配置章节")


def _decode_file_content(file_content: str) -> bytes:
    raw = file_content or ""
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw)


def _save_uploaded_file(parse_no: str, file_name: str, file_content: str | None) -> Path:
    if not file_content:
        raise ValueError("请先选择课件文件")
    EXAMPLES_ROOT.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file_name or "courseware.pptx").name
    target_path = EXAMPLES_ROOT / f"{parse_no}-{safe_name}"
    target_path.write_bytes(_decode_file_content(file_content))
    return target_path


def _build_mock_remote_url(base_url: str, file_path: Path) -> str:
    base = (base_url or "").rstrip("/")
    return f"{base}{MOCK_REMOTE_PREFIX}/{file_path.name}"


def _sync_knowledge_nodes(db: Session, task: ChapterParseTask, cir) -> None:
    if task.knowledge_nodes:
        for node in task.knowledge_nodes:
            db.delete(node)
        db.flush()

    sort_no = 0
    for chapter in cir.chapters:
        for node in chapter.nodes:
            page_refs = sorted(node.pageRefs)
            db.add(
                ChapterKnowledgeNode(
                    parse_task_id=task.id,
                    chapter_id=task.chapter_id,
                    node_code=node.nodeId,
                    node_name=node.nodeName,
                    node_type="knowledge",
                    level_no=1,
                    is_key_point=bool(node.keyPoints),
                    page_start=page_refs[0] if page_refs else None,
                    page_end=page_refs[-1] if page_refs else None,
                    sort_no=sort_no,
                )
            )
            sort_no += 1


def _sync_parse_result(db: Session, task: ChapterParseTask, file_info, preview, extracted, cir) -> ChapterParseResult:
    page_mapping = []
    for slide in extracted.slides:
        page_mapping.append(
            {
                "pageNo": slide.slideNumber,
                "title": slide.title or f"第 {slide.slideNumber } 页",
                "previewUrl": task.ppt_asset.file_url,
                "bodyTexts": slide.bodyTexts,
                "tableTexts": slide.tableTexts,
                "notes": slide.notes,
            }
        )

    key_points = []
    for chapter in cir.chapters:
        for node in chapter.nodes:
            key_points.extend(node.keyPoints)

    result = task.parse_result
    if not result:
        result = ChapterParseResult(parse_task_id=task.id, course_id=task.course_id, chapter_id=task.chapter_id, ppt_asset_id=task.ppt_asset_id)
        db.add(result)

    result.chapter_summary = f"本章《{task.chapter.chapter_name}》已按 CIR 链路完成解析，共 {file_info.pageCount} 页。"
    result.parsed_outline = preview.model_dump(mode="json")
    result.key_points = key_points
    result.page_mapping = page_mapping
    result.raw_llm_output = cir.model_dump_json()
    result.normalized_content = "\n\n".join(node.summary for chapter in cir.chapters for node in chapter.nodes if node.summary)
    _sync_knowledge_nodes(db, task, cir)
    return result


def _sync_lesson_section_pages(db: Session, task: ChapterParseTask, parse_result: ChapterParseResult, extracted) -> None:
    section = (
        db.query(LessonSection)
        .filter(LessonSection.course_id == task.course_id, LessonSection.source_chapter_id == task.chapter_id)
        .order_by(LessonSection.id.asc())
        .first()
    )
    if not section:
        return
    section.parse_result_id = parse_result.id
    section.ppt_asset_id = task.ppt_asset_id
    existing_pages = {page.page_no: page for page in db.query(LessonSectionPage).filter(LessonSectionPage.section_id == section.id).all()}
    for slide in extracted.slides:
        row = existing_pages.get(slide.slideNumber)
        if not row:
            row = LessonSectionPage(
                lesson_id=section.lesson_id,
                section_id=section.id,
                source_ppt_asset_id=task.ppt_asset_id,
                source_page_no=slide.slideNumber,
                page_no=slide.slideNumber,
                sort_no=slide.slideNumber,
            )
            db.add(row)
        row.source_ppt_asset_id = task.ppt_asset_id
        row.source_page_no = slide.slideNumber
        row.page_title = slide.title or f"第 {slide.slideNumber} 页"
        row.page_summary = f"查看《{section.section_name}》课件第 {slide.slideNumber} 页内容。"
        row.ppt_page_url = task.ppt_asset.file_url
        row.parsed_content = "\n".join([*slide.bodyTexts, *slide.tableTexts, *( [slide.notes] if slide.notes else [])])
        row.sort_no = slide.slideNumber


def _ensure_parse_result(db: Session, task: ChapterParseTask, file_info, preview, extracted, cir) -> ChapterParseResult:
    result = _sync_parse_result(db, task, file_info, preview, extracted, cir)
    db.flush()
    _sync_lesson_section_pages(db, task, result, extracted)
    task.ppt_asset.page_count = file_info.pageCount
    task.ppt_asset.upload_status = "parsed"
    task.task_status = "completed"
    task.finished_at = datetime.now()
    db.commit()
    db.refresh(result)
    return result


def _build_tree(db: Session, task_id: int) -> list[JsonDict]:
    nodes = (
        db.query(ChapterKnowledgeNode)
        .filter(ChapterKnowledgeNode.parse_task_id == task_id)
        .order_by(ChapterKnowledgeNode.level_no.asc(), ChapterKnowledgeNode.sort_no.asc(), ChapterKnowledgeNode.id.asc())
        .all()
    )
    return [{"id": node.node_code, "name": node.node_name, "children": []} for node in nodes]


def upload_parse(db: Session, teacher: User, course_id: str, file_name: str, file_content: str | None, base_url: str) -> JsonDict:
    settings = get_settings()
    course = _resolve_course(db, course_id)
    if not course:
        raise ValueError("courseId 不能为空或课程不存在")
    chapter = _pick_chapter(db, course.id, file_name)
    parse_no = f"P{uuid4().hex[:12].upper()}"
    asset_path = _save_uploaded_file(parse_no, file_name, file_content)
    file_url = _build_mock_remote_url(base_url, asset_path)
    ext = Path(file_name).suffix.lower().lstrip(".") or "ppt"
    latest_asset = db.query(ChapterPptAsset).filter(ChapterPptAsset.chapter_id == chapter.id).order_by(ChapterPptAsset.version_no.desc(), ChapterPptAsset.id.desc()).first()
    next_version = (latest_asset.version_no + 1) if latest_asset else 1
    asset = ChapterPptAsset(
        course_id=course.id,
        chapter_id=chapter.id,
        uploader_id=teacher.id,
        file_name=Path(file_name).name,
        file_type="pdf" if ext == "pdf" else ("pptx" if ext == "pptx" else "ppt"),
        file_url=file_url,
        file_size=asset_path.stat().st_size,
        page_count=0,
        upload_status="parsing",
        version_no=next_version,
    )
    db.add(asset)
    db.flush()
    task = ChapterParseTask(
        parse_no=parse_no,
        course_id=course.id,
        chapter_id=chapter.id,
        ppt_asset_id=asset.id,
        teacher_id=teacher.id,
        llm_model=settings.llm_model,
        task_status="processing",
    )
    db.add(task)
    db.commit()
    return {"parseId": parse_no, "status": "processing", "knowledgeTree": []}


def run_teacher_parse_task(parse_id: str) -> None:
    with session_scope() as db:
        task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == parse_id).first()
        if not task:
            return
        try:
            file_info, preview, extracted, cir = execute_parse_pipeline(
                course_id=str(task.chapter.course.course_code),
                file_url=task.ppt_asset.file_url,
                file_type=task.ppt_asset.file_type,
                is_extract_key_point=task.is_extract_key_point,
                courseware_id=f"cw-{task.chapter.course.course_code}",
            )
            _ensure_parse_result(db, task, file_info, preview, extracted, cir)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            failed_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == parse_id).first()
            if not failed_task:
                return
            failed_task.task_status = "failed"
            failed_task.error_msg = str(exc)[:500]
            failed_task.finished_at = datetime.now()
            if failed_task.ppt_asset:
                failed_task.ppt_asset.upload_status = "failed"
            db.commit()


def get_parse_status(db: Session, parse_id: str) -> JsonDict:
    task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == parse_id).first()
    if not task:
        raise LookupError("parseId 不存在")
    if task.task_status == "completed":
        return {"parseId": task.parse_no, "status": "success", "knowledgeTree": _build_tree(db, task.id)}
    if task.task_status == "failed":
        return {"parseId": task.parse_no, "status": "failed", "knowledgeTree": [], "msg": task.error_msg or "解析失败"}
    return {"parseId": task.parse_no, "status": "processing", "knowledgeTree": []}


def _map_script_type(script_type: str | None) -> str:
    normalized = (script_type or "standard").strip()
    mapped = SCRIPT_TYPE_MAPPING.get(normalized)
    if mapped is None:
        raise ApiError(400, f"scriptType is not supported: {normalized}", status_code=400)
    return mapped


def _build_teacher_script_response(parse_id: str, script_type: str | None, summary) -> JsonDict:
    script_content = "\n\n".join(
        section.content.strip() for section in summary.scriptStructure if isinstance(section.content, str) and section.content.strip()
    )
    return {
        "scriptId": summary.scriptId,
        "parseId": parse_id,
        "scriptType": script_type or "standard",
        "scriptContent": script_content,
        "scriptStructure": [section.model_dump() for section in summary.scriptStructure],
        "status": "success",
    }


def generate_script(db: Session, parse_id: str, script_type: str) -> JsonDict:
    _ = db
    summary = generate_main_script(
        GenerateScriptRequest(
            parseId=parse_id,
            teachingStyle=_map_script_type(script_type),
            speechSpeed="normal",
            customOpening=None,
            enc="teacher-compat",
        )
    )
    return _build_teacher_script_response(parse_id, script_type, summary)


def generate_audio(db: Session, script_id: str, voice_type: str) -> JsonDict:
    script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
    if not script:
        raise LookupError("scriptId 不存在")
    settings = get_settings()
    audio = ChapterAudioAsset(
        course_id=script.course_id,
        chapter_id=script.chapter_id,
        script_id=script.id,
        voice_type=voice_type,
        audio_format="mp3",
        audio_url=settings.default_audio_url,
        total_duration_sec=180,
        status="generated",
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return {"audioId": str(audio.id), "scriptId": script_id, "voiceType": voice_type, "audioUrl": audio.audio_url, "status": "success"}
