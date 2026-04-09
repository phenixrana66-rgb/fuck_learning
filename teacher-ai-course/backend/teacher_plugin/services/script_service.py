from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from chaoxing_db.models import ChapterParseTask, ChapterScript, ChapterScriptSection


SCRIPT_LABELS = {
    "standard": "标准",
    "detail": "详细",
    "simple": "简洁",
}


def _build_script_content(script_type: str, chapter_name: str, parse_no: str) -> str:
    label = SCRIPT_LABELS.get(script_type, "标准")
    return (
        f"《{label}讲稿》\n"
        f"parseId：{parse_no}\n\n"
        f"本节内容围绕《{chapter_name}》展开。\n"
        f"先介绍核心背景与学习目标，再讲解关键概念、典型问题和课堂总结。"
    )


def generate_script(db: Session, parse_id: str, script_type: str) -> dict:
    task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == parse_id).first()
    if not task:
        raise LookupError("parseId 不存在")
    content = _build_script_content(script_type, task.chapter.chapter_name, task.parse_no)
    script_no = f"S{uuid4().hex[:12].upper()}"
    script = ChapterScript(
        script_no=script_no,
        course_id=task.course_id,
        chapter_id=task.chapter_id,
        parse_task_id=task.id,
        teacher_id=task.teacher_id,
        teaching_style=script_type,
        speech_speed="normal",
        script_status="generated",
    )
    db.add(script)
    db.flush()
    db.add(
        ChapterScriptSection(
            script_id=script.id,
            section_code=f"{script_no}-01",
            section_name=task.chapter.chapter_name,
            section_content=content,
            sort_no=0,
        )
    )
    db.commit()
    return {
        "scriptId": script.script_no,
        "parseId": parse_id,
        "scriptType": script_type,
        "scriptContent": content,
        "status": "success",
    }
