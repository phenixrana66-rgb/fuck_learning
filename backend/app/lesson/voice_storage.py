from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import quote, urljoin
from uuid import uuid4


VOICE_CACHE_ROUTE = "cache/voice"
_REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(slots=True)
class StoredAudioFile:
    filename: str
    path: Path
    file_size: int


def get_voice_cache_dir() -> Path:
    voice_dir = _REPO_ROOT / "cache" / "voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    return voice_dir


def save_audio_file(audio_bytes: bytes, audio_format: str, filename_prefix: str | None = None) -> StoredAudioFile:
    voice_dir = get_voice_cache_dir()
    voice_dir.mkdir(parents=True, exist_ok=True)
    if filename_prefix:
        safe_prefix = re.sub(r"[^A-Za-z0-9._-]+", "-", filename_prefix).strip("-")
    else:
        safe_prefix = ""
    filename = f"{safe_prefix + '-' if safe_prefix else ''}{uuid4().hex}.{audio_format.lower()}"
    path = voice_dir / filename
    path.write_bytes(audio_bytes)
    return StoredAudioFile(filename=filename, path=path, file_size=path.stat().st_size)


def build_voice_public_url(filename: str, base_url: str | None = None) -> str:
    if not base_url:
        return f"/{VOICE_CACHE_ROUTE}/{quote(filename)}"
    normalized_base_url = base_url.rstrip("/") + "/"
    return urljoin(normalized_base_url, f"{VOICE_CACHE_ROUTE}/{quote(filename)}")
