from __future__ import annotations

from sqlalchemy.orm import Session

from chaoxing_db.models import ChapterAudioAsset, ChapterScript

from config import Config


def generate_audio(db: Session, script_id: str, voice_type: str) -> dict:
    script = db.query(ChapterScript).filter(ChapterScript.script_no == script_id).first()
    if not script:
        raise LookupError("scriptId 不存在")
    audio = ChapterAudioAsset(
        course_id=script.course_id,
        chapter_id=script.chapter_id,
        script_id=script.id,
        voice_type=voice_type,
        audio_format="mp3",
        audio_url=Config.DEFAULT_AUDIO_URL,
        total_duration_sec=180,
        status="generated",
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return {
        "audioId": str(audio.id),
        "scriptId": script_id,
        "voiceType": voice_type,
        "audioUrl": audio.audio_url,
        "status": "success",
    }
