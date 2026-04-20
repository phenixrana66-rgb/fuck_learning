from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.common.config import get_settings
from backend.app.common.db import session_scope
from backend.chaoxing_db.models import (
    ChapterAudioAsset,
    ChapterKnowledgeNode,
    ChapterParseTask,
    ChapterScript,
    ChapterScriptSection,
    ChapterSectionAudioAsset,
    Course,
    Lesson,
    LessonSection,
    LessonSectionAnchor,
    LessonSectionKnowledgePoint,
    LessonSectionPage,
    LessonUnit,
)

PREVIEW_ROOT = PROJECT_ROOT / "public" / "courseware-previews"


@dataclass
class BootstrapStats:
    course_code: str
    parse_no: str
    lesson_no: str
    script_no: str
    preview_files_copied: int = 0
    preview_urls_updated: int = 0
    script_sections_synced: int = 0
    section_audio_synced: int = 0
    lesson_sections_synced: int = 0
    lesson_pages_synced: int = 0


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _build_page_content(page_mapping: dict) -> str:
    parts: list[str] = []
    for item in page_mapping.get("bodyTexts") or []:
        text = _normalize_text(item)
        if text:
            parts.append(text)
    for item in page_mapping.get("tableTexts") or []:
        text = _normalize_text(item)
        if text:
            parts.append(text)
    notes = _normalize_text(page_mapping.get("notes"))
    if notes:
        parts.append(notes)
    return "\n".join(parts)


def _page_range_text(start_page: int | None, end_page: int | None) -> str | None:
    if not start_page and not end_page:
        return None
    if start_page and end_page and start_page != end_page:
        return f"{start_page}-{end_page}"
    return str(start_page or end_page)


def _copy_preview_files(parse_no: str, source_parse_no: str) -> int:
    target_dir = PREVIEW_ROOT / parse_no
    source_dir = PREVIEW_ROOT / source_parse_no
    if not source_dir.exists():
        raise SystemExit(f"source preview dir not found: {source_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for image in sorted(source_dir.glob("page-*.png")):
        target_path = target_dir / image.name
        if not target_path.exists():
            shutil.copy2(image, target_path)
            copied += 1
    return copied


def bootstrap_fake_publish(course_code: str, source_preview_parse_no: str) -> BootstrapStats:
    settings = get_settings()
    with session_scope() as db:
        course = db.query(Course).filter(Course.course_code == course_code).first()
        if course is None:
            raise SystemExit(f"course not found: {course_code}")

        parse_task = (
            db.query(ChapterParseTask)
            .filter(ChapterParseTask.course_id == course.id, ChapterParseTask.task_status == "completed")
            .order_by(ChapterParseTask.id.asc())
            .first()
        )
        if parse_task is None or parse_task.parse_result is None:
            raise SystemExit(f"completed parse task not found for course: {course_code}")

        parse_result = parse_task.parse_result
        parse_no = parse_task.parse_no
        stats = BootstrapStats(
            course_code=course_code,
            parse_no=parse_no,
            lesson_no=f"mockpub-{course_code}",
            script_no=f"mock-script-{course_code}",
        )

        stats.preview_files_copied = _copy_preview_files(parse_no, source_preview_parse_no)
        page_mapping_lookup = {item.get("pageNo"): item for item in (parse_result.page_mapping or []) if isinstance(item.get("pageNo"), int)}

        for page_no, item in sorted(page_mapping_lookup.items()):
            preview_path = PREVIEW_ROOT / parse_no / f"page-{page_no}.png"
            if not preview_path.exists():
                raise SystemExit(f"preview image missing for page {page_no}: {preview_path}")
            expected_url = f"/courseware-previews/{parse_no}/page-{page_no}.png"
            if item.get("previewUrl") != expected_url:
                item["previewUrl"] = expected_url
                stats.preview_urls_updated += 1
        parse_result.page_mapping = list(page_mapping_lookup.values())

        script = db.query(ChapterScript).filter(ChapterScript.script_no == stats.script_no).first()
        if script is None:
            script = ChapterScript(
                script_no=stats.script_no,
                course_id=course.id,
                chapter_id=parse_task.chapter_id,
                parse_task_id=parse_task.id,
                teacher_id=parse_task.teacher_id,
                teaching_style="standard",
                speech_speed="normal",
                custom_opening="",
                script_status="published",
                edit_url=f"/teacher/scripts/{stats.script_no}/edit",
            )
            db.add(script)
            db.flush()
        else:
            script.course_id = course.id
            script.chapter_id = parse_task.chapter_id
            script.parse_task_id = parse_task.id
            script.teacher_id = parse_task.teacher_id
            script.script_status = "published"
            script.edit_url = f"/teacher/scripts/{stats.script_no}/edit"

        nodes = (
            db.query(ChapterKnowledgeNode)
            .filter(ChapterKnowledgeNode.parse_task_id == parse_task.id)
            .order_by(ChapterKnowledgeNode.sort_no.asc(), ChapterKnowledgeNode.id.asc())
            .all()
        )
        if not nodes:
            raise SystemExit(f"knowledge nodes missing for parse task: {parse_task.parse_no}")

        existing_script_sections = {row.section_code: row for row in db.query(ChapterScriptSection).filter(ChapterScriptSection.script_id == script.id).all()}
        for sort_no, node in enumerate(nodes, start=1):
            section_code = f"sec{sort_no:03d}"
            content_parts: list[str] = [f"下面学习：{node.node_name}。"]
            for page_no in range(node.page_start or sort_no, (node.page_end or node.page_start or sort_no) + 1):
                page_mapping = page_mapping_lookup.get(page_no, {})
                page_title = _normalize_text(page_mapping.get("title"))
                page_content = _build_page_content(page_mapping)
                if page_title:
                    content_parts.append(f"第 {page_no} 页主题：{page_title}。")
                if page_content:
                    content_parts.append(page_content)
            row = existing_script_sections.get(section_code)
            if row is None:
                row = ChapterScriptSection(
                    script_id=script.id,
                    section_code=section_code,
                    section_name=node.node_name,
                    section_content="",
                    sort_no=sort_no - 1,
                )
                db.add(row)
                db.flush()
            row.script_id = script.id
            row.section_code = section_code
            row.section_name = node.node_name
            row.section_content = "\n".join(part for part in content_parts if part).strip()
            row.duration_sec = max(20, 35 * max(1, (node.page_end or node.page_start or 1) - (node.page_start or 1) + 1))
            row.related_node_id = node.id
            row.related_page_range = _page_range_text(node.page_start, node.page_end)
            row.sort_no = sort_no - 1
            stats.script_sections_synced += 1

        audio_asset = db.query(ChapterAudioAsset).filter(ChapterAudioAsset.script_id == script.id).order_by(ChapterAudioAsset.id.asc()).first()
        if audio_asset is None:
            audio_asset = ChapterAudioAsset(
                course_id=course.id,
                chapter_id=parse_task.chapter_id,
                script_id=script.id,
                voice_type="mock",
                audio_format="mp3",
                audio_url=settings.default_audio_url,
                total_duration_sec=0,
                file_size=0,
                bit_rate=0,
                status="published",
            )
            db.add(audio_asset)
            db.flush()
        else:
            audio_asset.course_id = course.id
            audio_asset.chapter_id = parse_task.chapter_id
            audio_asset.script_id = script.id
            audio_asset.voice_type = "mock"
            audio_asset.audio_format = "mp3"
            audio_asset.audio_url = settings.default_audio_url
            audio_asset.status = "published"

        script_sections = (
            db.query(ChapterScriptSection)
            .filter(ChapterScriptSection.script_id == script.id)
            .order_by(ChapterScriptSection.sort_no.asc(), ChapterScriptSection.id.asc())
            .all()
        )
        existing_section_audio = {row.script_section_id: row for row in db.query(ChapterSectionAudioAsset).filter(ChapterSectionAudioAsset.script_id == script.id).all()}
        total_duration = 0
        for section in script_sections:
            row = existing_section_audio.get(section.id)
            if row is None:
                row = ChapterSectionAudioAsset(
                    audio_asset_id=audio_asset.id,
                    course_id=course.id,
                    chapter_id=parse_task.chapter_id,
                    script_id=script.id,
                    script_section_id=section.id,
                    voice_type="mock",
                    audio_format="mp3",
                    audio_url=settings.default_audio_url,
                    duration_sec=section.duration_sec or 30,
                    file_size=0,
                    bit_rate=0,
                    status="published",
                    sort_no=section.sort_no,
                )
                db.add(row)
                db.flush()
            row.audio_asset_id = audio_asset.id
            row.course_id = course.id
            row.chapter_id = parse_task.chapter_id
            row.script_id = script.id
            row.script_section_id = section.id
            row.voice_type = "mock"
            row.audio_format = "mp3"
            row.audio_url = settings.default_audio_url
            row.duration_sec = section.duration_sec or 30
            row.file_size = 0
            row.bit_rate = 0
            row.status = "published"
            row.sort_no = section.sort_no
            total_duration += row.duration_sec or 0
            stats.section_audio_synced += 1
        audio_asset.total_duration_sec = total_duration

        lesson = db.query(Lesson).filter(Lesson.lesson_no == stats.lesson_no).first()
        if lesson is None:
            lesson = Lesson(
                lesson_no=stats.lesson_no,
                course_id=course.id,
                lesson_name=course.course_name,
                teacher_id=parse_task.teacher_id,
                publish_version=1,
                publish_status="published",
                published_at=_utc_now_naive(),
            )
            db.add(lesson)
            db.flush()
        else:
            lesson.course_id = course.id
            lesson.lesson_name = course.course_name
            lesson.teacher_id = parse_task.teacher_id
            lesson.publish_status = "published"
            lesson.publish_version = max(1, int(lesson.publish_version or 0) + 1)
            lesson.published_at = _utc_now_naive()

        unit = db.query(LessonUnit).filter(LessonUnit.lesson_id == lesson.id).order_by(LessonUnit.id.asc()).first()
        if unit is None:
            unit = LessonUnit(
                lesson_id=lesson.id,
                course_id=course.id,
                source_chapter_id=parse_task.chapter_id,
                unit_code=f"mock-unit-{course_code}",
                unit_title=parse_task.chapter.chapter_name if parse_task.chapter else course.course_name,
                sort_no=0,
            )
            db.add(unit)
            db.flush()
        else:
            unit.course_id = course.id
            unit.source_chapter_id = parse_task.chapter_id
            unit.unit_code = f"mock-unit-{course_code}"
            unit.unit_title = parse_task.chapter.chapter_name if parse_task.chapter else course.course_name
            unit.sort_no = 0

        existing_lesson_sections = {row.section_code: row for row in db.query(LessonSection).filter(LessonSection.lesson_id == lesson.id).all()}
        for script_section in script_sections:
            section_audio = next((item for item in audio_asset.section_audio_assets if item.script_section_id == script_section.id), None)
            node = next((item for item in nodes if item.id == script_section.related_node_id), None)
            row = existing_lesson_sections.get(script_section.section_code)
            if row is None:
                row = LessonSection(
                    lesson_id=lesson.id,
                    course_id=course.id,
                    unit_id=unit.id,
                    source_chapter_id=parse_task.chapter_id,
                    section_code=script_section.section_code,
                    section_name=script_section.section_name,
                    student_visible=True,
                    sort_no=script_section.sort_no,
                )
                db.add(row)
                db.flush()
            row.lesson_id = lesson.id
            row.course_id = course.id
            row.unit_id = unit.id
            row.source_chapter_id = parse_task.chapter_id
            row.parse_result_id = parse_result.id
            row.ppt_asset_id = parse_task.ppt_asset_id
            row.script_id = script.id
            row.audio_asset_id = audio_asset.id
            row.section_audio_asset_id = section_audio.id if section_audio else None
            row.section_code = script_section.section_code
            row.section_name = script_section.section_name
            row.section_summary = _normalize_text(script_section.section_content)[:180]
            row.student_visible = True
            row.sort_no = script_section.sort_no
            stats.lesson_sections_synced += 1

            existing_pages = {page.page_no: page for page in db.query(LessonSectionPage).filter(LessonSectionPage.section_id == row.id).all()}
            page_start = node.page_start if node and node.page_start else 1
            page_end = node.page_end if node and node.page_end else page_start
            for relative_sort, page_no in enumerate(range(page_start, page_end + 1)):
                page_mapping = page_mapping_lookup.get(page_no, {})
                page = existing_pages.get(page_no)
                if page is None:
                    page = LessonSectionPage(
                        lesson_id=lesson.id,
                        section_id=row.id,
                        source_ppt_asset_id=parse_task.ppt_asset_id,
                        source_page_no=page_no,
                        page_no=page_no,
                        page_title=_normalize_text(page_mapping.get("title")) or f"第 {page_no} 页",
                        page_summary=f"查看《{row.section_name}》课件第 {page_no} 页内容。",
                        ppt_page_url=f"/courseware-previews/{parse_no}/page-{page_no}.png",
                        parsed_content=_build_page_content(page_mapping),
                        sort_no=relative_sort,
                    )
                    db.add(page)
                page.lesson_id = lesson.id
                page.section_id = row.id
                page.source_ppt_asset_id = parse_task.ppt_asset_id
                page.source_page_no = page_no
                page.page_no = page_no
                page.page_title = _normalize_text(page_mapping.get("title")) or f"第 {page_no} 页"
                page.page_summary = f"查看《{row.section_name}》课件第 {page_no} 页内容。"
                page.ppt_page_url = f"/courseware-previews/{parse_no}/page-{page_no}.png"
                page.parsed_content = _build_page_content(page_mapping)
                page.sort_no = relative_sort
                stats.lesson_pages_synced += 1

            anchor = db.query(LessonSectionAnchor).filter(LessonSectionAnchor.section_id == row.id).order_by(LessonSectionAnchor.id.asc()).first()
            first_page = (
                db.query(LessonSectionPage)
                .filter(LessonSectionPage.section_id == row.id)
                .order_by(LessonSectionPage.sort_no.asc(), LessonSectionPage.page_no.asc(), LessonSectionPage.id.asc())
                .first()
            )
            if anchor is None:
                anchor = LessonSectionAnchor(lesson_id=lesson.id, section_id=row.id)
                db.add(anchor)
            anchor.lesson_id = lesson.id
            anchor.section_id = row.id
            anchor.lesson_page_id = first_page.id if first_page else None
            anchor.anchor_code = f"{row.section_code}-anchor"
            anchor.anchor_title = row.section_name
            anchor.page_no = first_page.page_no if first_page else 1
            anchor.start_time_sec = sum(item.duration_sec or 0 for item in audio_asset.section_audio_assets if item.sort_no < row.sort_no)
            anchor.sort_no = 0

            point = db.query(LessonSectionKnowledgePoint).filter(LessonSectionKnowledgePoint.section_id == row.id).order_by(LessonSectionKnowledgePoint.id.asc()).first()
            if point is None:
                point = LessonSectionKnowledgePoint(lesson_id=lesson.id, section_id=row.id)
                db.add(point)
            point.lesson_id = lesson.id
            point.section_id = row.id
            point.source_node_id = node.id if node else None
            point.point_code = node.node_code if node else row.section_code
            point.point_name = node.node_name if node else row.section_name
            point.point_summary = None
            point.sort_no = 0

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a fake published lesson from existing parse data.")
    parser.add_argument("--course-code", default="course-ai-001")
    parser.add_argument("--source-preview-parse-no", default="P49178FA7B0E3")
    args = parser.parse_args()

    stats = bootstrap_fake_publish(args.course_code, args.source_preview_parse_no)
    print("--- summary ---")
    print(f"course_code={stats.course_code}")
    print(f"parse_no={stats.parse_no}")
    print(f"lesson_no={stats.lesson_no}")
    print(f"script_no={stats.script_no}")
    print(f"preview_files_copied={stats.preview_files_copied}")
    print(f"preview_urls_updated={stats.preview_urls_updated}")
    print(f"script_sections_synced={stats.script_sections_synced}")
    print(f"section_audio_synced={stats.section_audio_synced}")
    print(f"lesson_sections_synced={stats.lesson_sections_synced}")
    print(f"lesson_pages_synced={stats.lesson_pages_synced}")


if __name__ == "__main__":
    main()
