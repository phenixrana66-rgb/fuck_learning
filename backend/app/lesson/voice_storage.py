from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from uuid import uuid4

from backend.app.common.storage import get_storage_manager

VOICE_CACHE_ROUTE = "cache/voice"


@dataclass(slots=True)
class StoredAudioFile:
    filename: str
    path: Path | None
    file_size: int


def get_voice_cache_dir() -> Path:
    # 仅作为本地兼容保留
    project_root = Path(__file__).resolve().parents[3]
    voice_dir = project_root / "cache" / "voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    return voice_dir


def save_audio_file(audio_bytes: bytes, audio_format: str, filename_prefix: str | None = None) -> StoredAudioFile:
    if filename_prefix:
        safe_prefix = re.sub(r"[^A-Za-z0-9._-]+", "-", filename_prefix).strip("-")
    else:
        safe_prefix = ""
    filename = f"{safe_prefix + '-' if safe_prefix else ''}{uuid4().hex}.{audio_format.lower()}"
    
    storage_manager = get_storage_manager()
    storage_key = f"voice/{filename}"
    storage_manager.upload_bytes(audio_bytes, storage_key, content_type=f"audio/{audio_format.lower()}")
    
    return StoredAudioFile(filename=filename, path=None, file_size=len(audio_bytes))


def build_voice_public_url(filename: str, base_url: str | None = None) -> str:
    return get_storage_manager().get_public_url(f"voice/{filename}", base_url=base_url)
