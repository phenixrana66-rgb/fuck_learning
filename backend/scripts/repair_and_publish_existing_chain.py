from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.common.db import session_scope
from backend.app.courseware.service import get_parse_task
from backend.app.lesson.schemas import PublishRequest
from backend.app.lesson.service import publish_lesson
from backend.chaoxing_db.models import ChapterAudioAsset, ChapterScript, Lesson, LessonSection, LessonSectionAnchor


@dataclass
class RepairStats:
    sections_scanned: int = 0
    sections_updated: int = 0
    anchors_updated: int = 0


@dataclass
class PublishTarget:
    script_id: str
    audio_id: str
    parse_id: str
    courseware_id: str
    chapter_name: str


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _build_scoped_section_code(source_chapter_id: int | None, section_code: str | None) -> str:
    normalized_section_code = _normalize_text(section_code) or "sec"
    if source_chapter_id is None:
        return normalized_section_code
    prefix = f"ch{source_chapter_id}-"
    if normalized_section_code.startswith(prefix):
        return normalized_section_code
    return f"{prefix}{normalized_section_code}"


def _build_unique_section_code(base_code: str, used_codes: set[str]) -> str:
    candidate = base_code
    suffix = 2
    while candidate in used_codes:
        candidate = f"{base_code}-{suffix}"
        suffix += 1
    return candidate


def repair_lesson_section_codes(*, lesson_no: str | None = None) -> RepairStats:
    stats = RepairStats()
    with session_scope() as db:
        query = db.query(Lesson).order_by(Lesson.id.asc())
        if lesson_no:
            query = query.filter(Lesson.lesson_no == lesson_no)
        lessons = query.all()

        for lesson in lessons:
            used_codes: set[str] = set()
            sections = (
                db.query(LessonSection)
                .filter(LessonSection.lesson_id == lesson.id)
                .order_by(LessonSection.sort_no.asc(), LessonSection.id.asc())
                .all()
            )
            for section in sections:
                stats.sections_scanned += 1
                desired_code = _build_unique_section_code(
                    _build_scoped_section_code(section.source_chapter_id, section.section_code),
                    used_codes,
                )
                used_codes.add(desired_code)
                if section.section_code != desired_code:
                    section.section_code = desired_code
                    stats.sections_updated += 1

                anchors = (
                    db.query(LessonSectionAnchor)
                    .filter(LessonSectionAnchor.section_id == section.id)
                    .order_by(LessonSectionAnchor.sort_no.asc(), LessonSectionAnchor.id.asc())
                    .all()
                )
                for index, anchor in enumerate(anchors, start=1):
                    expected_anchor_code = f"{desired_code}-anchor" if index == 1 else f"{desired_code}-anchor-{index}"
                    if anchor.anchor_code != expected_anchor_code:
                        anchor.anchor_code = expected_anchor_code
                        stats.anchors_updated += 1

    return stats


def _resolve_publish_target(*, script_id: str | None, audio_id: str | None) -> PublishTarget:
    with session_scope() as db:
        script = None
        audio = None

        if script_id:
            script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
            if script is None:
                raise SystemExit(f"script not found: {script_id}")

        if audio_id:
            if not str(audio_id).isdigit():
                raise SystemExit(f"audio id must be numeric: {audio_id}")
            audio = db.query(ChapterAudioAsset).filter(ChapterAudioAsset.id == int(audio_id)).first()
            if audio is None:
                raise SystemExit(f"audio not found: {audio_id}")

        if script is None and audio is not None:
            script = audio.script
        if audio is None and script is not None:
            audio = (
                db.query(ChapterAudioAsset)
                .filter(ChapterAudioAsset.script_id == script.id)
                .order_by(ChapterAudioAsset.id.desc())
                .first()
            )

        if script is None or audio is None:
            audio = (
                db.query(ChapterAudioAsset)
                .filter(ChapterAudioAsset.script_id.isnot(None))
                .order_by(ChapterAudioAsset.id.desc())
                .first()
            )
            if audio is None:
                raise SystemExit("no publish-ready audio record found")
            script = audio.script

        if script is None or script.parse_task is None:
            raise SystemExit("script parse task missing")

        parse_task = script.parse_task
        parse_detail = get_parse_task(parse_task.parse_no)
        if parse_detail.cir is None:
            raise SystemExit(f"parse result missing CIR payload: {parse_task.parse_no}")

        return PublishTarget(
            script_id=script.script_no,
            audio_id=str(audio.id),
            parse_id=parse_task.parse_no,
            courseware_id=parse_detail.cir.coursewareId,
            chapter_name=script.chapter.chapter_name if script.chapter is not None else "",
        )


def repair_and_publish(*, script_id: str | None, audio_id: str | None, lesson_no: str | None) -> None:
    repair_stats = repair_lesson_section_codes(lesson_no=lesson_no)
    target = _resolve_publish_target(script_id=script_id, audio_id=audio_id)
    result = publish_lesson(
        PublishRequest(
            coursewareId=target.courseware_id,
            scriptId=target.script_id,
            audioId=target.audio_id,
            publisherId="repair-script",
            chapterName=target.chapter_name,
            enc="repair-script",
        )
    )

    print("--- repair summary ---")
    print(f"sections_scanned={repair_stats.sections_scanned}")
    print(f"sections_updated={repair_stats.sections_updated}")
    print(f"anchors_updated={repair_stats.anchors_updated}")
    print("--- publish target ---")
    print(f"parse_id={target.parse_id}")
    print(f"script_id={target.script_id}")
    print(f"audio_id={target.audio_id}")
    print(f"courseware_id={target.courseware_id}")
    print(f"chapter_name={target.chapter_name}")
    print("--- publish result ---")
    print(f"lesson_id={result.get('lessonId')}")
    print(f"publish_status={result.get('publishStatus')}")
    print(f"publish_id={result.get('publishId')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair legacy lesson section codes and publish an existing script/audio chain.")
    parser.add_argument("--script-id", default="")
    parser.add_argument("--audio-id", default="")
    parser.add_argument("--lesson-no", default="")
    args = parser.parse_args()

    repair_and_publish(
        script_id=_normalize_text(args.script_id) or None,
        audio_id=_normalize_text(args.audio_id) or None,
        lesson_no=_normalize_text(args.lesson_no) or None,
    )


if __name__ == "__main__":
    main()
