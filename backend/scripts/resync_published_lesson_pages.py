from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.common.db import session_scope
from backend.app.lesson.service import _parse_page_numbers, _sync_lesson_anchor, _sync_lesson_pages
from backend.chaoxing_db.models import ChapterScriptSection, Lesson, LessonSection

PREVIEW_ROOT = PROJECT_ROOT / "public" / "courseware-previews"


@dataclass
class RepairStats:
    lessons_checked: int = 0
    lessons_repaired: int = 0
    sections_checked: int = 0
    sections_repaired: int = 0
    pages_synced: int = 0
    preview_urls_filled: int = 0
    skipped_sections: int = 0


def _preview_file(parse_no: str, page_no: int) -> Path:
    return PREVIEW_ROOT / parse_no / f"page-{page_no}.png"


def _preview_url(parse_no: str, page_no: int) -> str:
    return f"/courseware-previews/{parse_no}/page-{page_no}.png"


def _build_page_mapping_lookup(page_mapping: list[dict] | None, parse_no: str, stats: RepairStats) -> dict[int, dict]:
    lookup: dict[int, dict] = {}
    for item in page_mapping or []:
        page_no = item.get("pageNo")
        if not isinstance(page_no, int):
            continue
        preview_path = _preview_file(parse_no, page_no)
        expected_url = _preview_url(parse_no, page_no)
        current_url = (item.get("previewUrl") or "").strip()
        if preview_path.exists() and current_url != expected_url:
            item["previewUrl"] = expected_url
            stats.preview_urls_filled += 1
        lookup[page_no] = item
    return lookup


def resync_published_lesson_pages(*, lesson_no: str | None = None, apply: bool) -> RepairStats:
    stats = RepairStats()

    with session_scope() as db:
        lessons_query = db.query(Lesson).filter(Lesson.publish_status == "published").order_by(Lesson.id.asc())
        if lesson_no:
            lessons_query = lessons_query.filter(Lesson.lesson_no == lesson_no)
        lessons = lessons_query.all()

        if lesson_no and not lessons:
            raise SystemExit(f"published lesson not found: {lesson_no}")

        for lesson in lessons:
            stats.lessons_checked += 1
            lesson_repaired = False
            sections = (
                db.query(LessonSection)
                .filter(LessonSection.lesson_id == lesson.id)
                .order_by(LessonSection.sort_no.asc(), LessonSection.id.asc())
                .all()
            )
            for section in sections:
                stats.sections_checked += 1
                script = section.script
                parse_task = script.parse_task if script is not None else None
                parse_result = parse_task.parse_result if parse_task is not None else None
                if script is None or parse_task is None or parse_result is None:
                    stats.skipped_sections += 1
                    print(f"[skip] lesson={lesson.lesson_no} section={section.id} missing script/parse_result")
                    continue

                script_section = (
                    db.query(ChapterScriptSection)
                    .filter(
                        ChapterScriptSection.script_id == script.id,
                        ChapterScriptSection.section_code == section.section_code,
                    )
                    .first()
                )
                if script_section is None:
                    stats.skipped_sections += 1
                    print(f"[skip] lesson={lesson.lesson_no} section={section.id} missing script_section for {section.section_code}")
                    continue

                page_numbers = _parse_page_numbers(script_section.related_page_range)
                if not page_numbers:
                    stats.skipped_sections += 1
                    print(f"[skip] lesson={lesson.lesson_no} section={section.id} empty page range")
                    continue

                page_mapping_lookup = _build_page_mapping_lookup(parse_result.page_mapping, parse_task.parse_no, stats)
                created_page_numbers = _sync_lesson_pages(
                    db,
                    lesson_id=lesson.id,
                    lesson_section=section,
                    source_ppt_asset_id=parse_task.ppt_asset_id,
                    page_numbers=page_numbers,
                    page_mapping_lookup=page_mapping_lookup,
                )
                anchor_page_no = created_page_numbers[0] if created_page_numbers else page_numbers[0]
                existing_start_time_sec = 0
                if section.anchors:
                    existing_start_time_sec = int(section.anchors[0].start_time_sec or 0)

                _sync_lesson_anchor(
                    db,
                    lesson_id=lesson.id,
                    lesson_section=section,
                    anchor_page_no=anchor_page_no,
                    start_time_sec=existing_start_time_sec,
                )
                stats.pages_synced += len(created_page_numbers)
                stats.sections_repaired += 1
                lesson_repaired = True

            if lesson_repaired:
                stats.lessons_repaired += 1

        if not apply:
            db.rollback()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Resync lesson_section_pages for published lessons from current script/parse data.")
    parser.add_argument("--lesson-no", help="Only repair a specific published lesson.lesson_no")
    parser.add_argument("--apply", action="store_true", help="Persist changes. Omit for dry run.")
    args = parser.parse_args()

    stats = resync_published_lesson_pages(lesson_no=args.lesson_no, apply=args.apply)
    print("--- summary ---")
    print(f"lessons_checked={stats.lessons_checked}")
    print(f"lessons_repaired={stats.lessons_repaired}")
    print(f"sections_checked={stats.sections_checked}")
    print(f"sections_repaired={stats.sections_repaired}")
    print(f"pages_synced={stats.pages_synced}")
    print(f"preview_urls_filled={stats.preview_urls_filled}")
    print(f"skipped_sections={stats.skipped_sections}")
    print(f"mode={'apply' if args.apply else 'dry-run'}")


if __name__ == "__main__":
    main()
