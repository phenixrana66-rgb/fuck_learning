from __future__ import annotations

import json
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from backend.app.common.config import get_settings
from backend.app.common.db import session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.service import get_parse_task
from backend.app.lesson.schemas import AudioInfo, GenerateAudioRequest, PlayRequest, PublishRequest, SectionAudio
from backend.app.parser.schemas import ParseTaskStatus
from backend.app.script.service import get_script
from backend.app.tasks.service import create_task, mark_task_completed
from backend.chaoxing_db.models import ChapterAudioAsset, ChapterScript

_AUDIO_STORE: dict[str, dict] = {}
_LESSON_PACKAGES: dict[str, dict] = {}


def generate_audio(payload: GenerateAudioRequest) -> dict:
    script = get_script(payload.scriptId)
    section_map = {section.sectionId: section for section in script.scriptStructure}
    target_sections = payload.sectionIds or list(section_map.keys())
    if not target_sections:
        raise ApiError(code=400, msg='script has no available sections', status_code=400)

    missing_sections = [section_id for section_id in target_sections if section_id not in section_map]
    if missing_sections:
        raise ApiError(code=404, msg='script sections were not found', status_code=404, data={'sectionIds': missing_sections})

    selected_sections = [section_map[section_id] for section_id in target_sections]
    synthesis = _synthesize_audio(selected_sections, payload)

    with session_scope() as db:
        script_entity = db.query(ChapterScript).filter(ChapterScript.script_no == payload.scriptId).first()
        if script_entity is None:
            raise ApiError(code=404, msg='script entity not found', status_code=404)

        audio_asset = ChapterAudioAsset(
            course_id=script_entity.course_id,
            chapter_id=script_entity.chapter_id,
            script_id=script_entity.id,
            voice_type=payload.voiceType,
            audio_format=payload.audioFormat,
            audio_url=synthesis['audioUrl'],
            total_duration_sec=synthesis['totalDuration'],
            file_size=synthesis['fileSize'],
            bit_rate=synthesis['bitRate'],
            status='generated',
        )
        db.add(audio_asset)
        db.flush()
        audio_id = str(audio_asset.id)

    create_task(audio_id, 'lesson.generateAudio', {'scriptId': payload.scriptId})
    section_audios = [
        SectionAudio(
            sectionId=section.sectionId,
            audioUrl=_section_audio_url(synthesis['sectionAudioUrlTemplate'], audio_id, section.sectionId),
            duration=section.duration,
        )
        for section in selected_sections
    ]
    data = {
        'audioId': audio_id,
        'scriptId': payload.scriptId,
        'audioUrl': synthesis['audioUrl'],
        'audioInfo': AudioInfo(
            totalDuration=synthesis['totalDuration'],
            fileSize=synthesis['fileSize'],
            format=payload.audioFormat,
            bitRate=synthesis['bitRate'],
        ).model_dump(),
        'sectionAudios': [item.model_dump() for item in section_audios],
        'taskStatus': 'completed',
        'status': 'success',
    }
    _AUDIO_STORE[audio_id] = data
    mark_task_completed(audio_id, result=data)
    return data


def publish_lesson(payload: PublishRequest) -> dict:
    script = get_script(payload.scriptId)
    parse_result = get_parse_task(script.parseId)
    if parse_result.taskStatus != ParseTaskStatus.COMPLETED or parse_result.cir is None:
        raise ApiError(code=409, msg='parse task is not completed', status_code=409)

    audio = _load_audio_payload(payload.audioId, payload.scriptId)
    if parse_result.cir.coursewareId != payload.coursewareId:
        raise ApiError(code=409, msg='courseware and script do not match', status_code=409)

    lesson_id = _build_id('lesson')
    publish_id = _build_id('publish')
    create_task(publish_id, 'lesson.publish', {'lessonId': lesson_id, 'scriptId': payload.scriptId, 'audioId': payload.audioId})
    script_refs = [{'sectionId': section.sectionId, 'scriptId': payload.scriptId} for section in script.scriptStructure]
    audio_ref_map = {item['sectionId']: payload.audioId for item in audio['sectionAudios']}
    audio_refs = [
        {'sectionId': section.sectionId, 'audioId': audio_ref_map[section.sectionId]}
        for section in script.scriptStructure
        if section.sectionId in audio_ref_map
    ]
    node_sequence = [node.nodeId for chapter in parse_result.cir.chapters for node in chapter.nodes]
    data = {
        'publishId': publish_id,
        'lessonId': lesson_id,
        'publishStatus': 'published',
        'snapshot': {
            'coursewareId': payload.coursewareId,
            'scriptId': payload.scriptId,
            'audioId': payload.audioId,
            'parseId': script.parseId,
            'nodeSequence': node_sequence,
            'scriptRefs': script_refs,
            'audioRefs': audio_refs,
        },
    }
    _LESSON_PACKAGES[lesson_id] = data
    mark_task_completed(publish_id, result=data)
    return data


def play_lesson(payload: PlayRequest) -> dict:
    package = _LESSON_PACKAGES.get(payload.lessonId)
    current_section_id = _extract_current_section(payload.resumeContext)
    if package is None:
        raise ApiError(code=404, msg='lesson was not found', status_code=404)

    snapshot = package['snapshot']
    available_section_ids = [item['sectionId'] for item in snapshot.get('scriptRefs', [])]
    if current_section_id not in available_section_ids and available_section_ids:
        current_section_id = available_section_ids[0]
    return {
        'lessonId': package['lessonId'],
        'nodeSequence': snapshot.get('nodeSequence', []),
        'scriptRefs': snapshot.get('scriptRefs', []),
        'audioRefs': snapshot.get('audioRefs', []),
        'currentSectionId': current_section_id,
    }


def _load_audio_payload(audio_id: str, script_id: str) -> dict:
    cached = _AUDIO_STORE.get(audio_id)
    if cached is not None:
        if cached.get('scriptId') != script_id:
            raise ApiError(code=409, msg='audio and script do not match', status_code=409)
        return cached

    try:
        audio_asset_id = int(audio_id)
    except ValueError as exc:
        raise ApiError(code=404, msg='audio was not found', status_code=404) from exc

    with session_scope() as db:
        audio_asset = db.query(ChapterAudioAsset).join(ChapterScript).filter(ChapterAudioAsset.id == audio_asset_id).first()
        if audio_asset is None:
            raise ApiError(code=404, msg='audio was not found', status_code=404)
        if audio_asset.script.script_no != script_id:
            raise ApiError(code=409, msg='audio and script do not match', status_code=409)

    script_detail = get_script(script_id)
    section_audios = [
        SectionAudio(sectionId=section.sectionId, audioUrl=audio_asset.audio_url, duration=section.duration).model_dump()
        for section in script_detail.scriptStructure
    ]
    data = {
        'audioId': audio_id,
        'scriptId': script_id,
        'audioUrl': audio_asset.audio_url,
        'audioInfo': AudioInfo(
            totalDuration=audio_asset.total_duration_sec or sum(section['duration'] for section in section_audios),
            fileSize=audio_asset.file_size or 0,
            format=audio_asset.audio_format,
            bitRate=audio_asset.bit_rate or 0,
        ).model_dump(),
        'sectionAudios': section_audios,
        'taskStatus': 'completed',
        'status': 'success',
    }
    _AUDIO_STORE[audio_id] = data
    return data


def _synthesize_audio(selected_sections: list, payload: GenerateAudioRequest) -> dict:
    settings = get_settings()
    text = '\n\n'.join(section.content.strip() for section in selected_sections if isinstance(section.content, str) and section.content.strip())
    estimated_duration = sum(section.duration for section in selected_sections)
    fallback = {
        'audioUrl': settings.default_audio_url,
        'totalDuration': estimated_duration,
        'fileSize': 4_800_000 + len(selected_sections) * 320_000,
        'bitRate': 128_000,
        'sectionAudioUrlTemplate': settings.default_audio_url,
    }
    if not settings.tts_api_url:
        return fallback

    request_body = json.dumps(
        {
            'text': text,
            'voiceType': payload.voiceType,
            'audioFormat': payload.audioFormat,
        }
    ).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if settings.tts_api_key:
        headers['Authorization'] = f'Bearer {settings.tts_api_key}'

    request = Request(settings.tts_api_url, data=request_body, headers=headers, method='POST')
    try:
        with urlopen(request, timeout=settings.tts_timeout_seconds) as response:
            raw = response.read().decode('utf-8')
    except (HTTPError, URLError, TimeoutError, OSError):
        return fallback

    try:
        payload_data = json.loads(raw)
    except json.JSONDecodeError:
        return fallback

    audio_url = payload_data.get('audioUrl') or payload_data.get('url') or settings.default_audio_url
    if not isinstance(audio_url, str) or not audio_url:
        audio_url = settings.default_audio_url

    return {
        'audioUrl': audio_url,
        'totalDuration': int(payload_data.get('durationSec') or payload_data.get('totalDuration') or estimated_duration),
        'fileSize': int(payload_data.get('fileSize') or fallback['fileSize']),
        'bitRate': int(payload_data.get('bitRate') or fallback['bitRate']),
        'sectionAudioUrlTemplate': payload_data.get('sectionAudioUrlTemplate') or audio_url,
    }


def _section_audio_url(template: str, audio_id: str, section_id: str) -> str:
    if '{section_id}' in template or '{audio_id}' in template:
        return template.format(section_id=section_id, audio_id=audio_id)
    return template


def _extract_current_section(resume_context: dict | None) -> str:
    if not resume_context:
        return 'sec001'
    current_section_id = resume_context.get('currentSectionId')
    return current_section_id if isinstance(current_section_id, str) and current_section_id else 'sec001'


def clear_lessons() -> None:
    _AUDIO_STORE.clear()
    _LESSON_PACKAGES.clear()
    with session_scope() as db:
        db.query(ChapterAudioAsset).delete()


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"
