from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.common.db import session_scope
from backend.app.lesson.voice_storage import build_voice_public_url, get_voice_cache_dir
from backend.chaoxing_db.models import (
    ChapterAudioAsset,
    ChapterKnowledgeNode,
    ChapterParseTask,
    ChapterScript,
    ChapterScriptSection,
    ChapterSectionAudioAsset,
)


@dataclass
class SeedStats:
    parse_id: str
    script_id: str
    audio_id: str = ""
    sections_synced: int = 0
    section_audio_synced: int = 0
    audio_reused: bool = False


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _build_page_content(page_mapping: dict) -> str:
    parts: list[str] = []
    title = _normalize_text(page_mapping.get("title"))
    if title:
        parts.append(f"页面主题：{title}")
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
        parts.append(f"备注：{notes}")
    return "\n".join(parts)


def _page_range_text(start_page: int | None, end_page: int | None) -> str | None:
    if not start_page and not end_page:
        return None
    if start_page and end_page and start_page != end_page:
        return f"{start_page}-{end_page}"
    return str(start_page or end_page)


def _pick_voice_files() -> list[Path]:
    voice_files = sorted(path for path in get_voice_cache_dir().glob("*.mp3") if path.is_file())
    if not voice_files:
        raise SystemExit("no voice files found under cache/voice")
    return voice_files


def seed_publish_ready_chain(*, parse_id: str, script_id: str, voice_type: str) -> SeedStats:
    stats = SeedStats(parse_id=parse_id, script_id=script_id)
    voice_files = _pick_voice_files()

    with session_scope() as db:
        parse_task = db.query(ChapterParseTask).filter(ChapterParseTask.parse_no == parse_id).first()
        if parse_task is None or parse_task.parse_result is None:
            raise SystemExit(f"parse task not found or incomplete: {parse_id}")

        script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
        if script is None:
            raise SystemExit(f"script not found: {script_id}")

        page_mapping_lookup = {
            item.get("pageNo"): item
            for item in (parse_task.parse_result.page_mapping or [])
            if isinstance(item.get("pageNo"), int)
        }
        nodes = (
            db.query(ChapterKnowledgeNode)
            .filter(ChapterKnowledgeNode.parse_task_id == parse_task.id)
            .order_by(ChapterKnowledgeNode.sort_no.asc(), ChapterKnowledgeNode.id.asc())
            .all()
        )
        if not nodes:
            raise SystemExit(f"no knowledge nodes found for parse: {parse_id}")

        script.course_id = parse_task.course_id
        script.chapter_id = parse_task.chapter_id
        script.parse_task_id = parse_task.id
        script.teacher_id = parse_task.teacher_id
        script.teaching_style = "standard"
        script.speech_speed = "normal"
        script.script_status = "generated"
        script.edit_url = f"/teacher/scripts/{script.script_no}/edit"

        existing_audios = (
            db.query(ChapterAudioAsset)
            .filter(ChapterAudioAsset.script_id == script.id)
            .order_by(ChapterAudioAsset.id.desc())
            .all()
        )
        existing_audio = existing_audios[0] if existing_audios else None
        old_audio_ids = [audio.id for audio in existing_audios]
        if old_audio_ids:
            db.query(ChapterSectionAudioAsset).filter(ChapterSectionAudioAsset.audio_asset_id.in_(old_audio_ids)).delete(
                synchronize_session=False
            )

        db.query(ChapterScriptSection).filter(ChapterScriptSection.script_id == script.id).delete(synchronize_session=False)
        db.flush()

        script_sections: list[ChapterScriptSection] = []
        for sort_no, node in enumerate(nodes):
            start_page = node.page_start or (sort_no + 1)
            end_page = node.page_end or start_page
            content_parts: list[str] = [f"下面学习：{node.node_name}。"]
            for page_no in range(start_page, end_page + 1):
                page_mapping = page_mapping_lookup.get(page_no, {})
                page_content = _build_page_content(page_mapping)
                if page_content:
                    content_parts.append(page_content)
            section = ChapterScriptSection(
                script_id=script.id,
                section_code=f"sec{sort_no + 1:03d}",
                section_name=node.node_name,
                section_content="\n".join(part for part in content_parts if part).strip() or f"下面学习：{node.node_name}。",
                duration_sec=max(20, 35 * max(1, end_page - start_page + 1)),
                related_node_id=node.id,
                related_page_range=_page_range_text(start_page, end_page),
                sort_no=sort_no,
            )
            db.add(section)
            script_sections.append(section)
        db.flush()
        stats.sections_synced = len(script_sections)

        seed_audio_file = voice_files[0]
        total_duration = 0
        total_file_size = 0
        if existing_audio is None:
            audio_asset = ChapterAudioAsset(
                course_id=parse_task.course_id,
                chapter_id=parse_task.chapter_id,
                script_id=script.id,
                voice_type=voice_type,
                audio_format="mp3",
                audio_url=build_voice_public_url(seed_audio_file.name),
                total_duration_sec=0,
                file_size=0,
                bit_rate=128,
                status="generated",
            )
            db.add(audio_asset)
            db.flush()
        else:
            audio_asset = existing_audio
            stats.audio_reused = True
            audio_asset.course_id = parse_task.course_id
            audio_asset.chapter_id = parse_task.chapter_id
            audio_asset.script_id = script.id
            audio_asset.voice_type = voice_type
            audio_asset.audio_format = "mp3"
            audio_asset.audio_url = build_voice_public_url(seed_audio_file.name)
            audio_asset.bit_rate = 128
            audio_asset.status = "generated"

        for index, section in enumerate(script_sections):
            voice_file = voice_files[index % len(voice_files)]
            file_size = voice_file.stat().st_size
            duration_sec = max(20, round(file_size / 16000))
            total_duration += duration_sec
            total_file_size += file_size
            row = ChapterSectionAudioAsset(
                audio_asset_id=audio_asset.id,
                course_id=parse_task.course_id,
                chapter_id=parse_task.chapter_id,
                script_id=script.id,
                script_section_id=section.id,
                voice_type=voice_type,
                audio_format="mp3",
                audio_url=build_voice_public_url(voice_file.name),
                duration_sec=duration_sec,
                file_size=file_size,
                bit_rate=128,
                status="generated",
                sort_no=section.sort_no,
            )
            db.add(row)
            stats.section_audio_synced += 1

        audio_asset.total_duration_sec = total_duration
        audio_asset.file_size = total_file_size
        stats.audio_id = str(audio_asset.id)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a publish-ready parse -> script -> audio chain for the teacher page.")
    parser.add_argument("--parse-id", default="P4787CCFD3395")
    parser.add_argument("--script-id", default="S24EDF31FAE82")
    parser.add_argument("--voice-type", default="female_standard")
    args = parser.parse_args()

    stats = seed_publish_ready_chain(parse_id=args.parse_id, script_id=args.script_id, voice_type=args.voice_type)
    print("--- summary ---")
    print(f"parse_id={stats.parse_id}")
    print(f"script_id={stats.script_id}")
    print(f"audio_id={stats.audio_id}")
    print(f"sections_synced={stats.sections_synced}")
    print(f"section_audio_synced={stats.section_audio_synced}")
    print(f"audio_reused={stats.audio_reused}")


if __name__ == "__main__":
    main()
