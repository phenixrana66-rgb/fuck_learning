from __future__ import annotations

from datetime import UTC, datetime
from math import ceil
import re
from uuid import uuid4

from backend.app.common.db import session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.service import get_parse_task
from backend.app.lesson.schemas import AudioInfo, GenerateAudioRequest, PlayRequest, PublishRequest, SectionAudio
from backend.app.lesson.tts_client import synthesize_speech
from backend.app.lesson.voice_storage import build_voice_public_url, save_audio_file
from backend.app.parser.schemas import ParseTaskStatus
from backend.app.script.service import get_script
from backend.chaoxing_db.models import (
    ChapterAudioAsset,
    ChapterKnowledgeNode,
    ChapterScript,
    ChapterScriptSection,
    ChapterSectionAudioAsset,
    Lesson,
    LessonSection,
    LessonSectionAnchor,
    LessonSectionKnowledgePoint,
    LessonSectionPage,
    LessonUnit,
)

_AUDIO_STORE: dict[str, dict] = {}
_LESSON_PACKAGES: dict[str, dict] = {}


def generate_audio(payload: GenerateAudioRequest, base_url: str | None = None) -> dict:
    script = get_script(payload.scriptId)
    section_map = {section.sectionId: section for section in script.scriptStructure}
    target_sections = payload.sectionIds or list(section_map.keys())
    if not target_sections:
        raise ApiError(code=400, msg="script has no available sections", status_code=400)

    missing_sections = [section_id for section_id in target_sections if section_id not in section_map]
    if missing_sections:
        raise ApiError(code=404, msg="script sections were not found", status_code=404, data={"sectionIds": missing_sections})

    selected_sections = [section_map[section_id] for section_id in target_sections]

    with session_scope() as db:
        script_entity = db.query(ChapterScript).filter(ChapterScript.script_no == payload.scriptId).first()
        if script_entity is None:
            raise ApiError(code=404, msg="script entity not found", status_code=404)

        section_entities = (
            db.query(ChapterScriptSection)
            .filter(ChapterScriptSection.script_id == script_entity.id, ChapterScriptSection.section_code.in_(target_sections))
            .order_by(ChapterScriptSection.sort_no.asc(), ChapterScriptSection.id.asc())
            .all()
        )
        section_entity_map = {section.section_code: section for section in section_entities}
        entity_missing_sections = [section_id for section_id in target_sections if section_id not in section_entity_map]
        if entity_missing_sections:
            raise ApiError(
                code=404,
                msg="script section entities were not found",
                status_code=404,
                data={"sectionIds": entity_missing_sections},
            )

        audio_asset = ChapterAudioAsset(
            course_id=script_entity.course_id,
            chapter_id=script_entity.chapter_id,
            script_id=script_entity.id,
            voice_type=payload.voiceType,
            audio_format=payload.audioFormat,
            audio_url="",
            total_duration_sec=0,
            file_size=0,
            bit_rate=0,
            status="generated",
        )
        db.add(audio_asset)
        db.flush()

        section_audios: list[dict] = []
        total_duration = 0
        total_file_size = 0
        preview_audio_url = ""

        for selected_section in selected_sections:
            section_entity = section_entity_map[selected_section.sectionId]
            synthesis = _synthesize_section_audio(
                selected_section,
                payload,
                base_url=base_url,
                filename_prefix=f"{payload.scriptId}-{selected_section.sectionId}",
            )
            section_audio_asset = ChapterSectionAudioAsset(
                audio_asset_id=audio_asset.id,
                course_id=script_entity.course_id,
                chapter_id=script_entity.chapter_id,
                script_id=script_entity.id,
                script_section_id=section_entity.id,
                voice_type=payload.voiceType,
                audio_format=payload.audioFormat,
                audio_url=synthesis["audioUrl"],
                duration_sec=synthesis["duration"],
                file_size=synthesis["fileSize"],
                bit_rate=synthesis["bitRate"],
                status="generated",
                sort_no=section_entity.sort_no,
            )
            db.add(section_audio_asset)
            db.flush()

            if not preview_audio_url:
                preview_audio_url = synthesis["audioUrl"]
            total_duration += synthesis["duration"]
            total_file_size += synthesis["fileSize"]
            section_audios.append(
                SectionAudio(
                    sectionAudioId=str(section_audio_asset.id),
                    sectionId=selected_section.sectionId,
                    audioUrl=synthesis["audioUrl"],
                    duration=synthesis["duration"],
                    status=section_audio_asset.status,
                ).model_dump()
            )

        audio_asset.audio_url = preview_audio_url
        audio_asset.total_duration_sec = total_duration
        audio_asset.file_size = total_file_size
        audio_asset.bit_rate = _resolve_bit_rate(total_file_size, total_duration)
        db.flush()
        audio_id = str(audio_asset.id)

    data = {
        "audioId": audio_id,
        "scriptId": payload.scriptId,
        "audioUrl": preview_audio_url,
        "audioInfo": AudioInfo(
            totalDuration=total_duration,
            fileSize=total_file_size,
            format=payload.audioFormat,
            bitRate=_resolve_bit_rate(total_file_size, total_duration),
        ).model_dump(),
        "sectionAudios": section_audios,
        "taskStatus": "completed",
        "status": "success",
    }
    _AUDIO_STORE[audio_id] = data
    return data


def publish_lesson(payload: PublishRequest) -> dict:
    audio = _load_audio_payload(payload.audioId, payload.scriptId)
    with session_scope() as db:
        script_entity = db.query(ChapterScript).filter(ChapterScript.script_no == payload.scriptId).first()
        if script_entity is None:
            raise ApiError(code=404, msg="script was not found", status_code=404)

        parse_result = get_parse_task(script_entity.parse_task.parse_no)
        if parse_result.taskStatus != ParseTaskStatus.COMPLETED or parse_result.cir is None:
            raise ApiError(code=409, msg="parse task is not completed", status_code=409)
        if parse_result.cir.coursewareId != payload.coursewareId:
            raise ApiError(code=409, msg="courseware and script do not match", status_code=409)

        try:
            audio_asset_id = int(payload.audioId)
        except ValueError as exc:
            raise ApiError(code=404, msg="audio was not found", status_code=404) from exc

        audio_asset = db.query(ChapterAudioAsset).filter(ChapterAudioAsset.id == audio_asset_id).first()
        if audio_asset is None or audio_asset.script_id != script_entity.id:
            raise ApiError(code=409, msg="audio and script do not match", status_code=409)

        section_audio_assets = (
            db.query(ChapterSectionAudioAsset)
            .filter(ChapterSectionAudioAsset.audio_asset_id == audio_asset.id)
            .order_by(ChapterSectionAudioAsset.sort_no.asc(), ChapterSectionAudioAsset.id.asc())
            .all()
        )
        if not section_audio_assets:
            raise ApiError(code=409, msg="audio has no section assets", status_code=409)

        section_audio_map = {asset.script_section_id: asset for asset in section_audio_assets}
        script_sections = (
            db.query(ChapterScriptSection)
            .filter(ChapterScriptSection.script_id == script_entity.id)
            .order_by(ChapterScriptSection.sort_no.asc(), ChapterScriptSection.id.asc())
            .all()
        )
        published_sections = [section for section in script_sections if section.id in section_audio_map]
        if not published_sections:
            raise ApiError(code=409, msg="audio has no matching script sections", status_code=409)

        chapter = script_entity.chapter
        unit_chapter = chapter.parent if chapter and chapter.parent is not None else chapter
        lesson = Lesson(
            lesson_no=_build_id("lesson"),
            course_id=script_entity.course_id,
            lesson_name=(chapter.chapter_name if chapter is not None else "Published Lesson"),
            teacher_id=script_entity.teacher_id,
            publish_version=1,
            publish_status="published",
            published_at=_utc_now_naive(),
        )
        db.add(lesson)
        db.flush()

        lesson_unit = LessonUnit(
            lesson_id=lesson.id,
            course_id=script_entity.course_id,
            source_chapter_id=unit_chapter.id if unit_chapter is not None else script_entity.chapter_id,
            unit_code=(unit_chapter.chapter_code if unit_chapter is not None else f"unit-{lesson.id}"),
            unit_title=(unit_chapter.chapter_name if unit_chapter is not None else lesson.lesson_name),
            sort_no=0,
        )
        db.add(lesson_unit)
        db.flush()

        page_mapping_lookup = _build_page_mapping_lookup(script_entity.parse_task.parse_result.page_mapping if script_entity.parse_task.parse_result else None)
        cumulative_start = 0
        script_refs: list[dict] = []
        audio_refs: list[dict] = []
        node_sequence: list[str] = []

        for sort_no, script_section in enumerate(published_sections):
            section_audio_asset = section_audio_map[script_section.id]
            lesson_section = LessonSection(
                lesson_id=lesson.id,
                course_id=script_entity.course_id,
                unit_id=lesson_unit.id,
                source_chapter_id=script_entity.chapter_id,
                parse_result_id=script_entity.parse_task.parse_result.id if script_entity.parse_task.parse_result else None,
                ppt_asset_id=script_entity.parse_task.ppt_asset_id,
                script_id=script_entity.id,
                audio_asset_id=audio_asset.id,
                section_audio_asset_id=section_audio_asset.id,
                section_code=script_section.section_code,
                section_name=script_section.section_name,
                section_summary=_build_section_summary(script_section.section_content),
                student_visible=True,
                sort_no=sort_no,
            )
            db.add(lesson_section)
            db.flush()

            page_numbers = _parse_page_numbers(script_section.related_page_range)
            created_page_numbers = _create_lesson_pages(
                db,
                lesson_id=lesson.id,
                lesson_section_id=lesson_section.id,
                source_ppt_asset_id=script_entity.parse_task.ppt_asset_id,
                page_numbers=page_numbers,
                page_mapping_lookup=page_mapping_lookup,
            )

            anchor_page_no = created_page_numbers[0] if created_page_numbers else (page_numbers[0] if page_numbers else None)
            db.add(
                LessonSectionAnchor(
                    lesson_id=lesson.id,
                    section_id=lesson_section.id,
                    lesson_page_id=None,
                    anchor_code=f"{lesson_section.section_code}-anchor",
                    anchor_title=lesson_section.section_name,
                    page_no=anchor_page_no,
                    start_time_sec=cumulative_start,
                    sort_no=0,
                )
            )

            node_code = _create_lesson_knowledge_point(db, lesson.id, lesson_section.id, script_section.related_node_id)
            if node_code:
                node_sequence.append(node_code)
            cumulative_start += section_audio_asset.duration_sec or 0

            script_refs.append({"sectionId": script_section.section_code, "scriptId": payload.scriptId})
            audio_refs.append(
                {
                    "sectionId": script_section.section_code,
                    "audioId": payload.audioId,
                    "sectionAudioId": str(section_audio_asset.id),
                    "audioUrl": section_audio_asset.audio_url,
                }
            )

        script_entity.script_status = "published"
        audio_asset.status = "published"
        for section_audio_asset in section_audio_assets:
            section_audio_asset.status = "published"
        db.flush()

        lesson_id = lesson.lesson_no
        parse_id = script_entity.parse_task.parse_no

    publish_id = _build_id("publish")
    data = {
        "publishId": publish_id,
        "lessonId": lesson_id,
        "publishStatus": "published",
        "snapshot": {
            "coursewareId": payload.coursewareId,
            "scriptId": payload.scriptId,
            "audioId": payload.audioId,
            "parseId": parse_id,
            "nodeSequence": node_sequence,
            "scriptRefs": script_refs,
            "audioRefs": audio_refs,
        },
    }
    _LESSON_PACKAGES[lesson_id] = data
    return data


def play_lesson(payload: PlayRequest) -> dict:
    package = _LESSON_PACKAGES.get(payload.lessonId)
    current_section_id = _extract_current_section(payload.resumeContext)
    if package is None:
        package = _load_lesson_package(payload.lessonId)
    snapshot = package["snapshot"]
    available_section_ids = [item["sectionId"] for item in snapshot.get("scriptRefs", [])]
    if current_section_id not in available_section_ids and available_section_ids:
        current_section_id = available_section_ids[0]
    return {
        "lessonId": package["lessonId"],
        "nodeSequence": snapshot.get("nodeSequence", []),
        "scriptRefs": snapshot.get("scriptRefs", []),
        "audioRefs": snapshot.get("audioRefs", []),
        "currentSectionId": current_section_id,
    }


def _load_audio_payload(audio_id: str, script_id: str) -> dict:
    cached = _AUDIO_STORE.get(audio_id)
    if cached is not None:
        if cached.get("scriptId") != script_id:
            raise ApiError(code=409, msg="audio and script do not match", status_code=409)
        return cached

    try:
        audio_asset_id = int(audio_id)
    except ValueError as exc:
        raise ApiError(code=404, msg="audio was not found", status_code=404) from exc

    with session_scope() as db:
        audio_asset = db.query(ChapterAudioAsset).filter(ChapterAudioAsset.id == audio_asset_id).first()
        if audio_asset is None:
            raise ApiError(code=404, msg="audio was not found", status_code=404)
        if audio_asset.script.script_no != script_id:
            raise ApiError(code=409, msg="audio and script do not match", status_code=409)

        section_audio_assets = (
            db.query(ChapterSectionAudioAsset)
            .join(ChapterScriptSection, ChapterSectionAudioAsset.script_section_id == ChapterScriptSection.id)
            .filter(ChapterSectionAudioAsset.audio_asset_id == audio_asset.id)
            .order_by(ChapterSectionAudioAsset.sort_no.asc(), ChapterSectionAudioAsset.id.asc())
            .all()
        )
        if section_audio_assets:
            section_audios = [
                SectionAudio(
                    sectionAudioId=str(section_audio_asset.id),
                    sectionId=section_audio_asset.script_section.section_code,
                    audioUrl=section_audio_asset.audio_url,
                    duration=section_audio_asset.duration_sec or 0,
                    status=section_audio_asset.status,
                ).model_dump()
                for section_audio_asset in section_audio_assets
            ]
            preview_audio_url = section_audios[0]["audioUrl"]
            total_duration = audio_asset.total_duration_sec or sum(section["duration"] for section in section_audios)
            total_file_size = audio_asset.file_size or sum((asset.file_size or 0) for asset in section_audio_assets)
            bit_rate = audio_asset.bit_rate or _resolve_bit_rate(total_file_size, total_duration)
        else:
            script_detail = get_script(script_id)
            section_audios = [
                SectionAudio(sectionId=section.sectionId, audioUrl=audio_asset.audio_url, duration=section.duration).model_dump()
                for section in script_detail.scriptStructure
            ]
            preview_audio_url = audio_asset.audio_url
            total_duration = audio_asset.total_duration_sec or sum(section["duration"] for section in section_audios)
            total_file_size = audio_asset.file_size or 0
            bit_rate = audio_asset.bit_rate or 0

        data = {
            "audioId": audio_id,
            "scriptId": script_id,
            "audioUrl": preview_audio_url,
            "audioInfo": AudioInfo(
                totalDuration=total_duration,
                fileSize=total_file_size,
                format=audio_asset.audio_format,
                bitRate=bit_rate,
            ).model_dump(),
            "sectionAudios": section_audios,
            "taskStatus": "completed",
            "status": "success",
        }
    _AUDIO_STORE[audio_id] = data
    return data


def _synthesize_section_audio(section, payload: GenerateAudioRequest, base_url: str | None = None, filename_prefix: str | None = None) -> dict:
    text = _build_synthesis_text(section.content)
    if not text:
        raise ApiError(code=400, msg="selected section has no content", status_code=400, data={"sectionId": section.sectionId})

    synthesis_result = synthesize_speech(text=text, voice_type=payload.voiceType, audio_format=payload.audioFormat)
    stored_audio = save_audio_file(synthesis_result.audio_bytes, payload.audioFormat, filename_prefix=filename_prefix)
    duration = _resolve_total_duration(synthesis_result.duration_ms, section.duration)
    audio_url = build_voice_public_url(stored_audio.filename, base_url=base_url)
    return {
        "audioUrl": audio_url,
        "duration": duration,
        "fileSize": stored_audio.file_size,
        "bitRate": _resolve_bit_rate(stored_audio.file_size, duration),
    }


def _build_synthesis_text(content: str | None) -> str:
    text = content.strip() if isinstance(content, str) else ""
    return text


def _resolve_total_duration(duration_ms: int | None, estimated_duration: int) -> int:
    if duration_ms and duration_ms > 0:
        return max(1, ceil(duration_ms / 1000))
    if estimated_duration > 0:
        return estimated_duration
    return 1


def _resolve_bit_rate(file_size: int, duration_seconds: int) -> int:
    if duration_seconds <= 0:
        return 0
    return max(1, int((file_size * 8) / duration_seconds))


def _extract_current_section(resume_context: dict | None) -> str:
    if not resume_context:
        return "sec001"
    current_section_id = resume_context.get("currentSectionId")
    return current_section_id if isinstance(current_section_id, str) and current_section_id else "sec001"


def clear_lessons() -> None:
    _AUDIO_STORE.clear()
    _LESSON_PACKAGES.clear()
    with session_scope() as db:
        db.query(LessonSectionKnowledgePoint).delete()
        db.query(LessonSectionAnchor).delete()
        db.query(LessonSectionPage).delete()
        db.query(LessonSection).delete()
        db.query(LessonUnit).delete()
        db.query(Lesson).delete()
        db.query(ChapterSectionAudioAsset).delete()
        db.query(ChapterAudioAsset).delete()


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _build_section_summary(content: str | None) -> str:
    text = re.sub(r"\s+", " ", content or "").strip()
    if not text:
        return ""
    return text[:120]


def _parse_page_numbers(page_range: str | None) -> list[int]:
    if not page_range:
        return []
    page_numbers: list[int] = []
    for token in re.split(r"[，,]", page_range):
        normalized = token.strip()
        if not normalized:
            continue
        if "-" in normalized:
            start_text, end_text = normalized.split("-", 1)
            if start_text.strip().isdigit() and end_text.strip().isdigit():
                start = int(start_text.strip())
                end = int(end_text.strip())
                if start <= end:
                    page_numbers.extend(range(start, end + 1))
            continue
        if normalized.isdigit():
            page_numbers.append(int(normalized))
    deduped: list[int] = []
    for page_no in page_numbers:
        if page_no not in deduped:
            deduped.append(page_no)
    return deduped


def _build_page_mapping_lookup(page_mapping: list[dict] | None) -> dict[int, dict]:
    lookup: dict[int, dict] = {}
    for item in page_mapping or []:
        page_no = item.get("pageNo")
        if isinstance(page_no, int):
            lookup[page_no] = item
    return lookup


def _create_lesson_pages(
    db,
    lesson_id: int,
    lesson_section_id: int,
    source_ppt_asset_id: int | None,
    page_numbers: list[int],
    page_mapping_lookup: dict[int, dict],
) -> list[int]:
    created_page_numbers: list[int] = []
    for sort_no, page_no in enumerate(page_numbers):
        page_mapping = page_mapping_lookup.get(page_no, {})
        row = LessonSectionPage(
            lesson_id=lesson_id,
            section_id=lesson_section_id,
            source_ppt_asset_id=source_ppt_asset_id,
            source_page_no=page_no,
            page_no=page_no,
            page_title=page_mapping.get("title") or f"Page {page_no}",
            page_summary=(page_mapping.get("title") or f"Page {page_no}"),
            ppt_page_url=page_mapping.get("previewUrl"),
            parsed_content="\n".join(page_mapping.get("bodyTexts") or []),
            sort_no=sort_no,
        )
        db.add(row)
        created_page_numbers.append(page_no)
    return created_page_numbers


def _create_lesson_knowledge_point(db, lesson_id: int, lesson_section_id: int, related_node_id: int | None) -> str | None:
    if related_node_id is None:
        return None
    node = db.query(ChapterKnowledgeNode).filter(ChapterKnowledgeNode.id == related_node_id).first()
    if node is None:
        return None
    db.add(
        LessonSectionKnowledgePoint(
            lesson_id=lesson_id,
            section_id=lesson_section_id,
            source_node_id=node.id,
            point_code=node.node_code,
            point_name=node.node_name,
            point_summary=None,
            sort_no=0,
        )
    )
    return node.node_code


def _load_lesson_package(lesson_id: str) -> dict:
    with session_scope() as db:
        lesson = db.query(Lesson).filter(Lesson.lesson_no == lesson_id).first()
        if lesson is None:
            raise ApiError(code=404, msg="lesson was not found", status_code=404)
        sections = db.query(LessonSection).filter(LessonSection.lesson_id == lesson.id).order_by(LessonSection.sort_no.asc(), LessonSection.id.asc()).all()
        script_refs = [
            {"sectionId": section.section_code, "scriptId": section.script.script_no if section.script_id and section.script else ""}
            for section in sections
        ]
        audio_refs = [
            {
                "sectionId": section.section_code,
                "audioId": str(section.audio_asset_id) if section.audio_asset_id is not None else "",
                "sectionAudioId": str(section.section_audio_asset_id) if section.section_audio_asset_id is not None else "",
                "audioUrl": section.section_audio_asset.audio_url if section.section_audio_asset_id and section.section_audio_asset else "",
            }
            for section in sections
        ]
        node_sequence = []
        for section in sections:
            for point in sorted(section.knowledge_points or [], key=lambda item: (item.sort_no, item.id)):
                node_sequence.append(point.point_code)
        snapshot = {
            "coursewareId": "",
            "scriptId": sections[0].script.script_no if sections and sections[0].script_id and sections[0].script else "",
            "audioId": str(sections[0].audio_asset_id) if sections and sections[0].audio_asset_id is not None else "",
            "parseId": sections[0].script.parse_task.parse_no if sections and sections[0].script_id and sections[0].script else "",
            "nodeSequence": node_sequence,
            "scriptRefs": script_refs,
            "audioRefs": audio_refs,
        }
        data = {
            "publishId": "",
            "lessonId": lesson.lesson_no,
            "publishStatus": lesson.publish_status,
            "snapshot": snapshot,
        }
        _LESSON_PACKAGES[lesson.lesson_no] = data
        return data
