from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from chaoxing_db.models import (
    ChapterKnowledgeNode,
    ChapterParseResult,
    ChapterParseTask,
    ChapterPptAsset,
    Course,
    CourseChapter,
    CoursePlatformBinding,
    User,
)


def _resolve_course(db: Session, external_course_id: str) -> Course | None:
    binding = (
        db.query(CoursePlatformBinding)
        .filter(CoursePlatformBinding.external_course_id == external_course_id)
        .first()
    )
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


def _build_outline(chapter_name: str) -> list[dict]:
    return [
        {"id": "1", "name": chapter_name, "children": [{"id": "1-1", "name": "稳定平衡条件"}, {"id": "1-2", "name": "临界载荷"}]},
        {"id": "2", "name": "压杆稳定分析", "children": [{"id": "2-1", "name": "欧拉公式"}, {"id": "2-2", "name": "工程应用"}]},
    ]


def _ensure_parse_result(db: Session, task: ChapterParseTask) -> ChapterParseResult:
    if task.parse_result:
        return task.parse_result

    outline = _build_outline(task.ppt_asset.file_name if task.ppt_asset else task.chapter.chapter_name)
    result = ChapterParseResult(
        parse_task_id=task.id,
        course_id=task.course_id,
        chapter_id=task.chapter_id,
        ppt_asset_id=task.ppt_asset_id,
        chapter_summary=f"围绕《{task.chapter.chapter_name}》生成的章节摘要与知识结构。",
        parsed_outline=outline,
        key_points=[child["name"] for node in outline for child in node["children"]],
        page_mapping=[{"pageNo": index + 1, "title": child["name"]} for index, node in enumerate(outline) for child in node["children"]],
        normalized_content=f"{task.chapter.chapter_name} 的解析内容已生成。",
    )
    db.add(result)
    db.flush()

    if not task.knowledge_nodes:
        sort_no = 0
        for node in outline:
            parent = ChapterKnowledgeNode(
                parse_task_id=task.id,
                chapter_id=task.chapter_id,
                node_code=f"{task.parse_no}-{node['id']}",
                node_name=node["name"],
                node_type="chapter",
                level_no=1,
                sort_no=sort_no,
            )
            db.add(parent)
            db.flush()
            sort_no += 1
            for child in node["children"]:
                db.add(
                    ChapterKnowledgeNode(
                        parse_task_id=task.id,
                        chapter_id=task.chapter_id,
                        parent_id=parent.id,
                        node_code=f"{task.parse_no}-{child['id']}",
                        node_name=child["name"],
                        node_type="knowledge",
                        level_no=2,
                        is_key_point=True,
                        sort_no=sort_no,
                    )
                )
                sort_no += 1

    task.task_status = "completed"
    task.finished_at = datetime.now()
    if task.ppt_asset:
        task.ppt_asset.upload_status = "parsed"
    db.commit()
    db.refresh(result)
    return result


def _build_tree(db: Session, task_id: int) -> list[dict]:
    nodes = (
        db.query(ChapterKnowledgeNode)
        .filter(ChapterKnowledgeNode.parse_task_id == task_id)
        .order_by(ChapterKnowledgeNode.level_no.asc(), ChapterKnowledgeNode.sort_no.asc(), ChapterKnowledgeNode.id.asc())
        .all()
    )
    children_map: dict[int | None, list[ChapterKnowledgeNode]] = {}
    for node in nodes:
        children_map.setdefault(node.parent_id, []).append(node)

    def transform(parent_id: int | None) -> list[dict]:
        return [
            {
                "id": node.node_code,
                "name": node.node_name,
                "children": transform(node.id),
            }
            for node in children_map.get(parent_id, [])
        ]

    return transform(None)


def upload_parse(db: Session, teacher: User, course_id: str, file_name: str, _file_content: str | None) -> dict:
    course = _resolve_course(db, course_id)
    if not course:
        raise ValueError("courseId 不能为空或课程不存在")
    chapter = _pick_chapter(db, course.id, file_name)
    ext = Path(file_name).suffix.lower().lstrip(".") or "ppt"
    asset = ChapterPptAsset(
        course_id=course.id,
        chapter_id=chapter.id,
        uploader_id=teacher.id,
        file_name=file_name,
        file_type="pdf" if ext == "pdf" else ("pptx" if ext == "pptx" else "ppt"),
        file_url=file_name,
        page_count=12,
        upload_status="parsing",
    )
    db.add(asset)
    db.flush()
    parse_no = f"P{uuid4().hex[:12].upper()}"
    task = ChapterParseTask(
        parse_no=parse_no,
        course_id=course.id,
        chapter_id=chapter.id,
        ppt_asset_id=asset.id,
        teacher_id=teacher.id,
        llm_model="gpt-5.4",
        task_status="processing",
    )
    db.add(task)
    db.commit()
    return {"parseId": parse_no, "status": "processing", "knowledgeTree": []}


def get_parse_status(db: Session, parse_id: str) -> dict:
    task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == parse_id).first()
    if not task:
        raise LookupError("parseId 不存在")
    if task.task_status != "completed":
        _ensure_parse_result(db, task)
        db.refresh(task)
    return {
        "parseId": task.parse_no,
        "status": "success" if task.task_status == "completed" else task.task_status,
        "knowledgeTree": _build_tree(db, task.id),
    }
