from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import or_

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.common.db import session_scope
from backend.chaoxing_db.models import Lesson, LessonSection, LessonSectionAnchor, LessonSectionPage, StudentPageProgress


@dataclass
class CleanupStats:
    valid_lessons: int = 0
    valid_sections: int = 0
    stale_pages: int = 0
    stale_pages_missing_lesson: int = 0
    stale_pages_missing_section: int = 0
    stale_pages_mismatched_lesson: int = 0
    affected_student_page_progress: int = 0
    affected_anchors: int = 0
    deleted_student_page_progress: int = 0
    nulled_anchors: int = 0
    deleted_lesson_section_pages: int = 0


def cleanup_stale_lesson_pages(*, apply: bool) -> CleanupStats:
    stats = CleanupStats()

    with session_scope() as db:
        valid_lesson_ids = {lesson_id for (lesson_id,) in db.query(Lesson.id).all()}
        valid_section_ids = {section_id for (section_id,) in db.query(LessonSection.id).all()}
        section_lesson_pairs = {
            section_id: lesson_id for section_id, lesson_id in db.query(LessonSection.id, LessonSection.lesson_id).all()
        }

        stats.valid_lessons = len(valid_lesson_ids)
        stats.valid_sections = len(valid_section_ids)

        stale_pages = db.query(LessonSectionPage).filter(
            or_(
                ~LessonSectionPage.lesson_id.in_(valid_lesson_ids),
                ~LessonSectionPage.section_id.in_(valid_section_ids),
            )
        ).all()

        stale_page_ids: list[int] = []
        for page in stale_pages:
            section_lesson_id = section_lesson_pairs.get(page.section_id)
            missing_lesson = page.lesson_id not in valid_lesson_ids
            missing_section = page.section_id not in valid_section_ids
            mismatched_lesson = section_lesson_id is not None and section_lesson_id != page.lesson_id

            if missing_lesson:
                stats.stale_pages_missing_lesson += 1
            if missing_section:
                stats.stale_pages_missing_section += 1
            if mismatched_lesson:
                stats.stale_pages_mismatched_lesson += 1

            if missing_lesson or missing_section or mismatched_lesson:
                stale_page_ids.append(page.id)

        stats.stale_pages = len(stale_page_ids)

        if stale_page_ids:
            stats.affected_student_page_progress = (
                db.query(StudentPageProgress)
                .filter(StudentPageProgress.lesson_page_id.in_(stale_page_ids))
                .count()
            )
            stats.affected_anchors = (
                db.query(LessonSectionAnchor)
                .filter(LessonSectionAnchor.lesson_page_id.in_(stale_page_ids))
                .count()
            )

            if apply:
                stats.deleted_student_page_progress = (
                    db.query(StudentPageProgress)
                    .filter(StudentPageProgress.lesson_page_id.in_(stale_page_ids))
                    .delete(synchronize_session=False)
                )
                stats.nulled_anchors = (
                    db.query(LessonSectionAnchor)
                    .filter(LessonSectionAnchor.lesson_page_id.in_(stale_page_ids))
                    .update({LessonSectionAnchor.lesson_page_id: None}, synchronize_session=False)
                )
                stats.deleted_lesson_section_pages = (
                    db.query(LessonSectionPage)
                    .filter(LessonSectionPage.id.in_(stale_page_ids))
                    .delete(synchronize_session=False)
                )
            else:
                db.rollback()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Safely clean stale lesson_section_pages and dependent references. Defaults to dry-run."
    )
    parser.add_argument("--apply", action="store_true", help="Persist changes. Omit for dry run.")
    args = parser.parse_args()

    stats = cleanup_stale_lesson_pages(apply=args.apply)
    print("--- summary ---")
    print(f"valid_lessons={stats.valid_lessons}")
    print(f"valid_sections={stats.valid_sections}")
    print(f"stale_pages={stats.stale_pages}")
    print(f"stale_pages_missing_lesson={stats.stale_pages_missing_lesson}")
    print(f"stale_pages_missing_section={stats.stale_pages_missing_section}")
    print(f"stale_pages_mismatched_lesson={stats.stale_pages_mismatched_lesson}")
    print(f"affected_student_page_progress={stats.affected_student_page_progress}")
    print(f"affected_anchors={stats.affected_anchors}")
    print(f"deleted_student_page_progress={stats.deleted_student_page_progress}")
    print(f"nulled_anchors={stats.nulled_anchors}")
    print(f"deleted_lesson_section_pages={stats.deleted_lesson_section_pages}")
    print(f"mode={'apply' if args.apply else 'dry-run'}")


if __name__ == "__main__":
    main()
