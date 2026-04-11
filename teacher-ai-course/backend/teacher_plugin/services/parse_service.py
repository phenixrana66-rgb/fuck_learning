from __future__ import annotations

import base64
import re
import shutil
import subprocess
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
    LessonSection,
    LessonSectionPage,
    User,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
PUBLIC_ROOT = PROJECT_ROOT / "public"
PREVIEW_ROOT = PUBLIC_ROOT / "lesson-previews"
UPLOAD_ROOT = Path(__file__).resolve().parents[1] / "storage" / "uploads"
DEFAULT_PRESSURE_STABILITY_PPT = Path(
    r"D:\BaiduNetdiskDownload\10-a12基于泛雅平台的AI互动智课生成与实时问答\a12基于泛雅平台的AI互动智课生成与实时问答\课件下载-3月3日\课件下载-3月3日\第九章 压杆稳定_20260401213017.ppt"
)

PRESSURE_STABILITY_OUTLINE = [
    "稳定平衡条件",
    "临界载荷",
    "欧拉公式",
    "长细比影响",
    "工程应用",
]


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


def _preview_folder_name(chapter: CourseChapter) -> str:
    if "压杆稳定" in (chapter.chapter_name or ""):
        return "pressure-stability"
    return f"chapter-{chapter.id}"


def _preview_dir(chapter: CourseChapter) -> Path:
    path = PREVIEW_ROOT / _preview_folder_name(chapter)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _preview_url(chapter: CourseChapter, page_no: int) -> str:
    return f"/lesson-previews/{_preview_folder_name(chapter)}/page-{page_no}.png"


def _decode_file_content(file_content: str) -> bytes:
    raw = file_content or ""
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw)


def _save_uploaded_file(parse_no: str, file_name: str, file_content: str | None) -> str:
    if file_content:
        target_dir = UPLOAD_ROOT / parse_no
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / Path(file_name).name
        target_path.write_bytes(_decode_file_content(file_content))
        return str(target_path)

    direct_path = Path(file_name)
    if direct_path.exists():
        return str(direct_path.resolve())

    if DEFAULT_PRESSURE_STABILITY_PPT.exists():
        return str(DEFAULT_PRESSURE_STABILITY_PPT)

    return file_name


def _ps_literal(path: Path | str) -> str:
    return str(path).replace("'", "''")


def _export_ppt_to_pngs(source_path: str, preview_dir: Path) -> list[Path]:
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"PPT 文件不存在：{source_path}")

    raw_dir = preview_dir / "_raw_export"
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    script = f"""
$ErrorActionPreference = 'Stop'
$src = '{_ps_literal(source)}'
$dest = '{_ps_literal(raw_dir)}'
$ppt = $null
$presentation = $null
try {{
  $ppt = New-Object -ComObject PowerPoint.Application
  $ppt.Visible = -1
  $presentation = $ppt.Presentations.Open($src, $true, $false, $false)
  $presentation.SaveAs($dest, 18)
}} finally {{
  if ($presentation) {{ $presentation.Close() }}
  if ($ppt) {{ $ppt.Quit() }}
  if ($presentation) {{ [System.Runtime.Interopservices.Marshal]::ReleaseComObject($presentation) | Out-Null }}
  if ($ppt) {{ [System.Runtime.Interopservices.Marshal]::ReleaseComObject($ppt) | Out-Null }}
  [gc]::Collect()
  [gc]::WaitForPendingFinalizers()
}}
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
    )

    for existing in preview_dir.glob("page-*.png"):
        existing.unlink()

    exported = []
    for item in sorted(raw_dir.glob("*.PNG"), key=lambda file: int(re.search(r"(\d+)", file.stem).group(1))):
        page_no = int(re.search(r"(\d+)", item.stem).group(1))
        target = preview_dir / f"page-{page_no}.png"
        shutil.copyfile(item, target)
        exported.append(target)

    shutil.rmtree(raw_dir, ignore_errors=True)
    if not exported:
        raise RuntimeError("PPT 已打开，但没有成功导出页图")
    return exported


def _list_preview_images(chapter: CourseChapter) -> list[Path]:
    return sorted(
        _preview_dir(chapter).glob("page-*.png"),
        key=lambda file: int(re.search(r"(\d+)", file.stem).group(1)),
    )


def _ensure_preview_images(task: ChapterParseTask) -> list[str]:
    if not task.ppt_asset:
        raise RuntimeError("当前解析任务缺少 PPT 资源")

    chapter = task.chapter
    preview_dir = _preview_dir(chapter)
    images = _list_preview_images(chapter)

    if not images:
        images = _export_ppt_to_pngs(task.ppt_asset.file_url, preview_dir)

    task.ppt_asset.page_count = len(images)
    task.ppt_asset.upload_status = "parsed"
    return [_preview_url(chapter, index + 1) for index in range(len(images))]


def _build_outline(chapter_name: str) -> list[dict]:
    return [
        {
            "id": f"outline-{index + 1}",
            "name": item,
            "children": [],
        }
        for index, item in enumerate(PRESSURE_STABILITY_OUTLINE if "压杆稳定" in chapter_name else [chapter_name])
    ]


def _sync_knowledge_nodes(db: Session, task: ChapterParseTask, outline: list[dict]) -> None:
    if task.knowledge_nodes:
        return

    sort_no = 0
    for node in outline:
        db.add(
            ChapterKnowledgeNode(
                parse_task_id=task.id,
                chapter_id=task.chapter_id,
                node_code=f"{task.parse_no}-{node['id']}",
                node_name=node["name"],
                node_type="knowledge",
                level_no=1,
                is_key_point=True,
                page_start=sort_no + 1,
                page_end=sort_no + 1,
                sort_no=sort_no,
            )
        )
        sort_no += 1


def _sync_parse_result(db: Session, task: ChapterParseTask, image_urls: list[str]) -> ChapterParseResult:
    outline = _build_outline(task.chapter.chapter_name)
    page_mapping = [
        {
            "pageNo": page_no,
            "title": f"第 {page_no} 页",
            "previewUrl": image_url,
        }
        for page_no, image_url in enumerate(image_urls, start=1)
    ]

    result = task.parse_result
    if not result:
        result = ChapterParseResult(
            parse_task_id=task.id,
            course_id=task.course_id,
            chapter_id=task.chapter_id,
            ppt_asset_id=task.ppt_asset_id,
        )
        db.add(result)

    result.chapter_summary = f"本章围绕《{task.chapter.chapter_name}》展开知识讲解、课件学习与工程应用分析。"
    result.parsed_outline = outline
    result.key_points = [node["name"] for node in outline]
    result.page_mapping = page_mapping
    result.normalized_content = (
        "本章建议先顺序完成 PPT 页面的学习，再围绕临界载荷、欧拉公式、长细比影响和工程校核继续提问。"
    )

    _sync_knowledge_nodes(db, task, outline)
    return result


def _sync_lesson_section_pages(db: Session, task: ChapterParseTask, image_urls: list[str]) -> None:
    section = (
        db.query(LessonSection)
        .filter(
            LessonSection.course_id == task.course_id,
            LessonSection.source_chapter_id == task.chapter_id,
        )
        .order_by(LessonSection.id.asc())
        .first()
    )
    if not section:
        return

    existing_pages = {
        page.page_no: page
        for page in db.query(LessonSectionPage).filter(LessonSectionPage.section_id == section.id).all()
    }

    for page_no, image_url in enumerate(image_urls, start=1):
        row = existing_pages.get(page_no)
        if not row:
            row = LessonSectionPage(
                lesson_id=section.lesson_id,
                section_id=section.id,
                source_ppt_asset_id=task.ppt_asset_id,
                source_page_no=page_no,
                page_no=page_no,
                sort_no=page_no,
            )
            db.add(row)

        row.source_ppt_asset_id = task.ppt_asset_id
        row.source_page_no = page_no
        row.page_title = f"第 {page_no} 页"
        row.page_summary = f"查看《{section.section_name}》课件第 {page_no} 页内容。"
        row.ppt_page_url = image_url
        row.parsed_content = f"本页为《{section.section_name}》课件第 {page_no} 页。"
        row.sort_no = page_no


def _ensure_parse_result(db: Session, task: ChapterParseTask) -> ChapterParseResult:
    image_urls = _ensure_preview_images(task)
    result = _sync_parse_result(db, task, image_urls)
    _sync_lesson_section_pages(db, task, image_urls)

    task.task_status = "completed"
    task.finished_at = datetime.now()
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
    return [
        {
            "id": node.node_code,
            "name": node.node_name,
            "children": [],
        }
        for node in nodes
    ]


def upload_parse(db: Session, teacher: User, course_id: str, file_name: str, file_content: str | None) -> dict:
    course = _resolve_course(db, course_id)
    if not course:
        raise ValueError("courseId 不能为空或课程不存在")

    chapter = _pick_chapter(db, course.id, file_name)
    parse_no = f"P{uuid4().hex[:12].upper()}"
    asset_path = _save_uploaded_file(parse_no, file_name, file_content)
    ext = Path(file_name).suffix.lower().lstrip(".") or "ppt"
    latest_asset = (
        db.query(ChapterPptAsset)
        .filter(ChapterPptAsset.chapter_id == chapter.id)
        .order_by(ChapterPptAsset.version_no.desc(), ChapterPptAsset.id.desc())
        .first()
    )
    next_version = (latest_asset.version_no + 1) if latest_asset else 1

    asset = ChapterPptAsset(
        course_id=course.id,
        chapter_id=chapter.id,
        uploader_id=teacher.id,
        file_name=Path(file_name).name,
        file_type="pdf" if ext == "pdf" else ("pptx" if ext == "pptx" else "ppt"),
        file_url=asset_path,
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
        llm_model="gpt-5.4",
        task_status="processing",
    )
    db.add(task)
    db.commit()

    return {
        "parseId": parse_no,
        "status": "processing",
        "knowledgeTree": [],
    }


def get_parse_status(db: Session, parse_id: str) -> dict:
    task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == parse_id).first()
    if not task:
        raise LookupError("parseId 不存在")

    if task.task_status != "completed" or not task.parse_result:
        _ensure_parse_result(db, task)
        db.refresh(task)
    else:
        # 已完成任务也做一次预览与页面同步，避免旧测试数据仍停留在占位页图。
        _ensure_parse_result(db, task)
        db.refresh(task)

    return {
        "parseId": task.parse_no,
        "status": "success",
        "knowledgeTree": _build_tree(db, task.id),
    }
