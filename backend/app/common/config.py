from functools import lru_cache
from pathlib import Path
from runpy import run_path

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    app_name: str = "AI互动智课后端服务"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = True
    signature_enabled: bool = False
    db_url: str | None = None
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "Zenith"
    db_password: str = "123456"
    db_name: str = "chaoxing_ai_course"
    db_echo: bool = False
    static_key: str = "chaoxing-ai-static-key"
    mock_mode: bool = True
    teacher_test_platform_token: str = "test_token_001"
    default_audio_url: str = "https://www.w3schools.com/html/horse.mp3"
    APPID: str | None = None
    ACCESS_TOKEN: str | None = None
    TTS_URL: str | None = None
    TTS_CLUSTER: str | None = None
    TTS_VOICE_TYPE: str | None = None
    ASR_URL: str | None = None
    ASR_CLUSTER: str | None = None
    llm_api_base_url: str = "http://10.195.20.215:13010/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-5.1-codex-mini"
    llm_timeout_seconds: float = 60.0

    model_config = ConfigDict(extra="ignore")


_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_CONFIG_PATH = _REPO_ROOT / "config.local.py"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    defaults = Settings().model_dump()
    file_overrides = _load_local_config_values()
    return Settings(**{**defaults, **file_overrides})


def _load_local_config_values() -> dict[str, object]:
    if not _LOCAL_CONFIG_PATH.exists():
        return {}

    local_namespace = run_path(str(_LOCAL_CONFIG_PATH))
    declared_keys = set(Settings.model_fields)
    return {key: value for key, value in local_namespace.items() if key in declared_keys}
