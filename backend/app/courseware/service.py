from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.app.cir.schemas import CIR
from backend.app.cir.service import build_cir
from backend.app.common.db import session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseAcceptedData, ParseQueryData, ParseRequest
from backend.app.parser.schemas import ExtractedPresentation, FileInfo, ParseTaskStatus, StructurePreview
from backend.app.parser.service import parse_courseware
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
    CoursePlatformBinding,
    School,
    User,
    UserPlatformBinding,
)


def create_parse_task(payload: ParseRequest, request_id: str | None = None) -> ParseAcceptedData:
    del request_id
    parse_id = _build_id("parse")
    with session_scope() as db:
        school = _resolve_or_create_school(db, payload.schoolId)
        teacher = _resolve_or_create_teacher(db, payload.userId, school.id)
        course = _resolve_or_create_course(db, payload.courseId, school.id, teacher.id)
        chapter = _resolve_or_create_chapter(db, course.id, payload.courseId)
        asset = _create_parse_asset(db, payload, course.id, chapter.id, teacher.id)
        task = ChapterParseTask(
            parse_no=parse_id,
            course_id=course.id,
            chapter_id=chapter.id,
            ppt_asset_id=asset.id,
            teacher_id=teacher.id,
            task_status=ParseTaskStatus.PROCESSING.value,
            is_extract_key_point=payload.isExtractKeyPoint,
        )
        db.add(task)
    return ParseAcceptedData(parseId=parse_id, taskStatus=ParseTaskStatus.PROCESSING)


def run_parse_task(parse_id: str, payload: ParseRequest) -> None:
    with session_scope() as db:
        task = _require_parse_task_entity(db, parse_id)
        try:
            file_info, preview, extracted, cir = execute_parse_pipeline(
                course_id=payload.courseId,
                file_url=payload.fileUrl,
                file_type=payload.fileType,
                is_extract_key_point=payload.isExtractKeyPoint,
            )
        except ApiError as exc:
            _mark_parse_task_failed(db, task, exc.msg)
            return
        except Exception:  # noqa: BLE001
            _mark_parse_task_failed(db, task, "服务端错误")
            return

        _sync_parse_result(db, task, file_info, preview, extracted, cir)
        task.task_status = ParseTaskStatus.COMPLETED.value
        task.error_msg = None
        task.finished_at = datetime.now(UTC)
        task.ppt_asset.file_name = file_info.fileName
        task.ppt_asset.file_size = file_info.fileSize
        task.ppt_asset.page_count = file_info.pageCount
        task.ppt_asset.upload_status = "parsed"


def execute_parse_pipeline(
    course_id: str,
    file_url: str,
    file_type: str,
    is_extract_key_point: bool = True,
    courseware_id: str | None = None,
) -> tuple[FileInfo, StructurePreview, ExtractedPresentation, CIR]:
    parsed: tuple[FileInfo, StructurePreview] | tuple[FileInfo, StructurePreview, ExtractedPresentation] = parse_courseware(
        course_id=course_id,
        file_url=file_url,
        file_type=file_type,
        is_extract_key_point=is_extract_key_point,
    )
    if len(parsed) == 2:
        file_info, preview = parsed
        extracted = ExtractedPresentation(slides=[])
    else:
        file_info, preview, extracted = parsed
    cir = build_cir(courseware_id=courseware_id or f"cw-{course_id}", preview=preview, extracted=extracted)
    return file_info, preview, extracted, cir


def get_parse_task(parse_id: str) -> ParseQueryData:
    with session_scope() as db:
        task = _require_parse_task_entity(db, parse_id)
        return _build_parse_query_data(task)


def clear_parse_tasks() -> None:
    with session_scope() as db:
        _ = db.execute(delete(ChapterAudioAsset))
        _ = db.execute(delete(ChapterScriptSection))
        _ = db.execute(delete(ChapterScript))
        _ = db.execute(delete(ChapterKnowledgeNode))
        _ = db.execute(delete(ChapterParseResult))
        _ = db.execute(delete(ChapterParseTask))
        _ = db.execute(delete(ChapterPptAsset))


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"


def _resolve_or_create_school(db: Session, school_code: str) -> School:
    school = db.query(School).filter(School.school_code == school_code).first()
    if school:
        return school
    school = School(school_code=school_code, school_name=f"学校-{school_code}")
    db.add(school)
    db.flush()
    return school


def _resolve_or_create_teacher(db: Session, user_id: str, school_id: int) -> User:
    binding = db.query(UserPlatformBinding).filter(UserPlatformBinding.external_user_id == user_id).first()
    if binding:
        return binding.user
    teacher = db.query(User).filter(User.user_no == user_id).first()
    if teacher:
        return teacher
    teacher = User(user_no=user_id, user_name=f"教师-{user_id}", role="teacher", school_id=school_id)
    db.add(teacher)
    db.flush()
    return teacher


def _resolve_or_create_course(db: Session, course_id: str, school_id: int, teacher_id: int) -> Course:
    binding = db.query(CoursePlatformBinding).filter(CoursePlatformBinding.external_course_id == course_id).first()
    if binding:
        return binding.course
    course = db.query(Course).filter(Course.course_code == course_id).first()
    if course:
        return course
    course = Course(course_code=course_id, course_name=f"课程-{course_id}", school_id=school_id, created_by=teacher_id)
    db.add(course)
    db.flush()
    return course


def _resolve_or_create_chapter(db: Session, course_db_id: int, course_id: str) -> CourseChapter:
    chapter = (
        db.query(CourseChapter)
        .filter(CourseChapter.course_id == course_db_id, CourseChapter.chapter_type != "unit")
        .order_by(CourseChapter.sort_no.asc(), CourseChapter.id.asc())
        .first()
    )
    if chapter:
        return chapter
    chapter = CourseChapter(
        course_id=course_db_id,
        chapter_code=f"{course_id}-chap-001",
        chapter_name="默认章节",
        chapter_type="chapter",
        chapter_level=1,
        sort_no=1,
    )
    db.add(chapter)
    db.flush()
    return chapter


def _create_parse_asset(db: Session, payload: ParseRequest, course_id: int, chapter_id: int, teacher_id: int) -> ChapterPptAsset:
    latest_asset = (
        db.query(ChapterPptAsset)
        .filter(ChapterPptAsset.chapter_id == chapter_id)
        .order_by(ChapterPptAsset.version_no.desc(), ChapterPptAsset.id.desc())
        .first()
    )
    asset = ChapterPptAsset(
        course_id=course_id,
        chapter_id=chapter_id,
        uploader_id=teacher_id,
        file_name=_file_name_from_url(payload.fileUrl, payload.fileType),
        file_type=payload.fileType,
        file_url=payload.fileUrl,
        page_count=0,
        upload_status="parsing",
        version_no=(latest_asset.version_no + 1) if latest_asset else 1,
    )
    db.add(asset)
    db.flush()
    return asset


def _file_name_from_url(file_url: str, file_type: str) -> str:
    file_name = file_url.rstrip("/").split("/")[-1]
    if file_name:
        return file_name
    return f"courseware.{file_type}"


def _require_parse_task_entity(db: Session, parse_id: str) -> ChapterParseTask:
    task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == parse_id).first()
    if task is None:
        raise ApiError(code=404, msg="解析任务不存在", status_code=404)
    return task


def _mark_parse_task_failed(db: Session, task: ChapterParseTask, message: str) -> None:
    task.task_status = ParseTaskStatus.FAILED.value
    task.error_msg = message
    task.finished_at = datetime.now(UTC)
    task.ppt_asset.upload_status = "failed"
    db.flush()


def _sync_parse_result(
    db: Session,
    task: ChapterParseTask,
    file_info: FileInfo,
    preview: StructurePreview,
    extracted: ExtractedPresentation,
    cir: CIR,
) -> None:
    result = task.parse_result
    if result is None:
        result = ChapterParseResult(
            parse_task_id=task.id,
            course_id=task.course_id,
            chapter_id=task.chapter_id,
            ppt_asset_id=task.ppt_asset_id,
        )
        db.add(result)

    page_mapping = []
    for slide in extracted.slides:
        page_mapping.append(
            {
                "pageNo": slide.slideNumber,
                "title": slide.title or f"第 {slide.slideNumber} 页",
                "previewUrl": task.ppt_asset.file_url,
                "bodyTexts": slide.bodyTexts,
                "tableTexts": slide.tableTexts,
                "notes": slide.notes,
            }
        )

    result.chapter_summary = f"课件《{file_info.fileName}》解析完成，共 {file_info.pageCount} 页。"
    result.parsed_outline = preview.model_dump(mode="json")
    result.key_points = [key_point for chapter in cir.chapters for node in chapter.nodes for key_point in node.keyPoints]
    result.page_mapping = page_mapping
    result.raw_llm_output = cir.model_dump_json()
    result.normalized_content = "\n\n".join(
        node.summary for chapter in cir.chapters for node in chapter.nodes if node.summary
    )
    _replace_knowledge_nodes(db, task, cir)
    db.flush()


def _replace_knowledge_nodes(db: Session, task: ChapterParseTask, cir: CIR) -> None:
    if task.knowledge_nodes:
        for node in list(task.knowledge_nodes):
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


def _build_parse_query_data(task: ChapterParseTask) -> ParseQueryData:
    status = ParseTaskStatus(task.task_status)
    if status == ParseTaskStatus.COMPLETED:
        result = task.parse_result
        cir = CIR.model_validate_json(result.raw_llm_output) if result and result.raw_llm_output else None
        preview = StructurePreview.model_validate(result.parsed_outline) if result and result.parsed_outline else None
        return ParseQueryData(
            parseId=task.parse_no,
            fileInfo=FileInfo(
                fileName=task.ppt_asset.file_name,
                fileSize=task.ppt_asset.file_size or 0,
                pageCount=task.ppt_asset.page_count or 0,
            ),
            structurePreview=preview,
            taskStatus=status,
            cir=cir,
            progressPercent=100,
        )

    return ParseQueryData(
        parseId=task.parse_no,
        taskStatus=status,
        progressPercent=25 if status == ParseTaskStatus.PROCESSING else 100,
        errorMessage=task.error_msg,
    )
