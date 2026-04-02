from datetime import datetime
from uuid import uuid4

from backend.app.lesson.schemas import AudioInfo, GenerateAudioRequest, PlayRequest, PublishRequest, SectionAudio
from backend.app.tasks.schemas import TaskRecord
from backend.app.tasks.service import upsert_task

_AUDIO_STORE: dict[str, dict] = {}
_LESSON_PACKAGES: dict[str, dict] = {}


def generate_audio(payload: GenerateAudioRequest) -> dict:
    audio_id = _build_id("audio")
    target_sections = payload.sectionIds or ["sec001", "sec002"]
    section_audios = [
        SectionAudio(
            sectionId=section_id,
            audioUrl=f"https://example.com/audio/{audio_id}/{section_id}.{payload.audioFormat}",
            duration=30 if section_id == "sec001" else 45,
        )
        for section_id in target_sections
    ]
    data = {
        "audioId": audio_id,
        "audioUrl": f"https://example.com/audio/{audio_id}.{payload.audioFormat}",
        "audioInfo": AudioInfo(
            totalDuration=sum(item.duration for item in section_audios),
            fileSize=9_600_000,
            format=payload.audioFormat,
            bitRate=128_000,
        ).model_dump(),
        "sectionAudios": [item.model_dump() for item in section_audios],
        "taskStatus": "processing",
    }
    _AUDIO_STORE[audio_id] = data
    upsert_task(
        TaskRecord(
            taskId=audio_id,
            taskType="lesson.generateAudio",
            status="processing",
            payload={"scriptId": payload.scriptId},
        )
    )
    return data


def publish_lesson(payload: PublishRequest) -> dict:
    lesson_id = _build_id("lesson")
    data = {
        "publishId": _build_id("publish"),
        "lessonId": lesson_id,
        "publishStatus": "processing",
        "snapshot": {
            "coursewareId": payload.coursewareId,
            "scriptId": payload.scriptId,
            "audioId": payload.audioId,
        },
    }
    _LESSON_PACKAGES[lesson_id] = data
    upsert_task(
        TaskRecord(
            taskId=data["publishId"],
            taskType="lesson.publish",
            status="processing",
            payload={"lessonId": lesson_id, "scriptId": payload.scriptId, "audioId": payload.audioId},
        )
    )
    return data


def play_lesson(payload: PlayRequest) -> dict:
    package = _LESSON_PACKAGES.get(payload.lessonId)
    current_section_id = _extract_current_section(payload.resumeContext)
    if package is None:
        package = {
            "lessonId": payload.lessonId,
            "snapshot": {},
        }
    return {
        "lessonId": package["lessonId"],
        "nodeSequence": ["node-01-01", "node-01-02"],
        "scriptRefs": [
            {"sectionId": "sec001", "scriptId": package.get("snapshot", {}).get("scriptId", "script-demo")},
            {"sectionId": "sec002", "scriptId": package.get("snapshot", {}).get("scriptId", "script-demo")},
        ],
        "audioRefs": [
            {"sectionId": "sec001", "audioId": package.get("snapshot", {}).get("audioId", "audio-demo")},
            {"sectionId": "sec002", "audioId": package.get("snapshot", {}).get("audioId", "audio-demo")},
        ],
        "currentSectionId": current_section_id,
    }


def _extract_current_section(resume_context: dict | None) -> str:
    if not resume_context:
        return "sec001"
    current_section_id = resume_context.get("currentSectionId")
    return current_section_id if isinstance(current_section_id, str) and current_section_id else "sec001"


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"
