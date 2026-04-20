from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.common.db import session_scope
from backend.chaoxing_db.models import ChapterParseTask, Lesson, LessonSection, LessonSectionPage

PREVIEW_ROOT = PROJECT_ROOT / "public" / "courseware-previews"


@dataclass
class RepairStats:
    lesson_no: str
    parse_results_checked: int = 0
    parse_result_rows_updated: int = 0
    lesson_pages_checked: int = 0
    lesson_page_rows_updated: int = 0
    missing_preview_files: int = 0


def _build_preview_path(parse_no: str, page_no: int) -> Path:
    return PREVIEW_ROOT / parse_no / f"page-{page_no}.png"


def _build_preview_url(parse_no: str, page_no: int) -> str:
    return f"/courseware-previews/{parse_no}/page-{page_no}.png"


def _resolve_parse_task(section: LessonSection) -> ChapterParseTask | None:
    if section.script_id and section.script and section.script.parse_task:
        return section.script.parse_task
    return None


def repair_lesson_page_previews(lesson_no: str, *, apply: bool) -> RepairStats:
    stats = RepairStats(lesson_no=lesson_no)
    with session_scope() as db:
        lesson = db.query(Lesson).filter(Lesson.lesson_no == lesson_no).first()
        if lesson is None:
            raise SystemExit(f"lesson not found: {lesson_no}")

        sections = (
            db.query(LessonSection)
            .filter(LessonSection.lesson_id == lesson.id)
            .order_by(LessonSection.sort_no.asc(), LessonSection.id.asc())
            .all()
        )
        if not sections:
            raise SystemExit(f"lesson has no sections: {lesson_no}")

        parse_result_ids_seen: set[int] = set()

        for section in sections:
            task = _resolve_parse_task(section)
            if task is None:
                print(f"[skip] section {section.id} {section.section_name}: parse task missing")
                continue

            parse_no = task.parse_no
            parse_result = task.parse_result
            if parse_result and parse_result.id not in parse_result_ids_seen:
                parse_result_ids_seen.add(parse_result.id)
                stats.parse_results_checked += 1
                page_mapping = list(parse_result.page_mapping or [])
                changed = False
                for item in page_mapping:
                    page_no = item.get("pageNo")
                    if not isinstance(page_no, int):
                        continue
                    preview_path = _build_preview_path(parse_no, page_no)
                    if not preview_path.exists():
                        stats.missing_preview_files += 1
                        print(f"[warn] parse {parse_no} page {page_no}: preview file missing -> {preview_path}")
                        continue
                    expected_url = _build_preview_url(parse_no, page_no)
                    current_url = item.get("previewUrl") or ""
                    if current_url != expected_url:
                        print(f"[fix] parse_result {parse_result.id} page {page_no}: {current_url or '<empty>'} -> {expected_url}")
                        item["previewUrl"] = expected_url
                        changed = True
                        stats.parse_result_rows_updated += 1
                if changed and apply:
                    parse_result.page_mapping = page_mapping

            pages = (
                db.query(LessonSectionPage)
                .filter(LessonSectionPage.section_id == section.id)
                .order_by(LessonSectionPage.sort_no.asc(), LessonSectionPage.id.asc())
                .all()
            )
            for page in pages:
                stats.lesson_pages_checked += 1
                page_no = page.source_page_no or page.page_no
                if not page_no:
                    print(f"[skip] lesson_page {page.id}: page number missing")
                    continue
                preview_path = _build_preview_path(parse_no, page_no)
                if not preview_path.exists():
                    stats.missing_preview_files += 1
                    print(f"[warn] lesson_page {page.id} page {page_no}: preview file missing -> {preview_path}")
                    continue
                expected_url = _build_preview_url(parse_no, page_no)
                current_url = page.ppt_page_url or ""
                if current_url != expected_url:
                    print(f"[fix] lesson_page {page.id} section {section.id} page {page_no}: {current_url or '<empty>'} -> {expected_url}")
                    if apply:
                        page.ppt_page_url = expected_url
                    stats.lesson_page_rows_updated += 1

        if not apply:
            db.rollback()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair preview URLs for one published lesson safely.")
    parser.add_argument("--lesson-no", required=True, help="Target lesson.lesson_no")
    parser.add_argument("--apply", action="store_true", help="Persist changes. Omit for dry run.")
    args = parser.parse_args()

    stats = repair_lesson_page_previews(args.lesson_no, apply=args.apply)
    print("--- summary ---")
    print(f"lesson_no={stats.lesson_no}")
    print(f"parse_results_checked={stats.parse_results_checked}")
    print(f"parse_result_rows_updated={stats.parse_result_rows_updated}")
    print(f"lesson_pages_checked={stats.lesson_pages_checked}")
    print(f"lesson_page_rows_updated={stats.lesson_page_rows_updated}")
    print(f"missing_preview_files={stats.missing_preview_files}")
    print(f"mode={'apply' if args.apply else 'dry-run'}")


if __name__ == "__main__":
    main()
