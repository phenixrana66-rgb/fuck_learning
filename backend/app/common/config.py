from functools import lru_cache
from pathlib import Path
from runpy import run_path

from pydantic import BaseModel, ConfigDict


_SETTING_ALIASES = {
    "appid": "APPID",
    "access_token": "ACCESS_TOKEN",
    "tts_url": "TTS_URL",
    "tts_cluster": "TTS_CLUSTER",
    "tts_voice_type": "TTS_VOICE_TYPE",
    "tts_insecure_skip_verify": "tts_insecure_skip_verify",
    "asr_url": "ASR_URL",
    "asr_cluster": "ASR_CLUSTER",
}


class Settings(BaseModel):
    app_name: str = "AI Lesson Backend Service"
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
    tts_timeout_seconds: float = 60.0
    tts_insecure_skip_verify: bool = False
    tts_retry_attempts: int = 4
    tts_retry_backoff_seconds: float = 1.0
    ASR_URL: str | None = None
    ASR_CLUSTER: str | None = None
    llm_api_base_url: str = "http://10.195.20.215:13010/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-5.1-codex-mini"
    llm_timeout_seconds: float = 60.0
    qa_llm_provider: str = "dashscope"
    qa_llm_model: str = "qwen-max"
    qa_multimodal_model: str = "qwen3.5-plus"
    qa_embedding_model: str = "text-embedding-v4"
    qa_embedding_dimensions: int = 1024
    qa_image_generation_model: str = "wanx2.1-t2i-turbo"
    qa_image_generation_size: str = "1024*1024"
    qa_image_generation_count: int = 1
    qa_image_generation_timeout_seconds: float = 60.0
    qa_image_generation_poll_interval_seconds: float = 2.0
    qa_asr_model: str = "qwen3-asr-flash"
    qa_asr_timeout_seconds: float = 180.0
    qa_asr_poll_interval_seconds: float = 2.0
    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com"
    openai_compat_api_key: str | None = None
    vector_db_url: str | None = None

    # S3 / MinIO 存储配置
    s3_enabled: bool = False
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_secure: bool = False
    s3_bucket: str = "chaoxing"
    s3_public_url: str = ""

    model_config = ConfigDict(extra="allow")


_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_CONFIG_PATH = _REPO_ROOT / "config.local.py"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    defaults = Settings().model_dump()
    file_overrides = _load_local_config_values()
    settings = Settings(**{**defaults, **file_overrides})
    
    # 自动识别单元测试环境，若在测试中则强制关闭 S3
    import sys
    is_testing = "unittest" in sys.modules or any("unittest" in arg for arg in sys.argv)
    if is_testing:
        settings.s3_enabled = False
        
    return settings


def get_setting(name: str, default=None):
    settings = get_settings()
    resolved_name = _SETTING_ALIASES.get(name, _SETTING_ALIASES.get(name.lower(), name))
    return getattr(settings, resolved_name, default)


def _load_local_config_values() -> dict[str, object]:
    if not _LOCAL_CONFIG_PATH.exists():
        return {}

    local_namespace = run_path(str(_LOCAL_CONFIG_PATH))
    declared_keys = set(Settings.model_fields)
    loaded_values: dict[str, object] = {}
    for key, value in local_namespace.items():
        resolved_key = _SETTING_ALIASES.get(key, _SETTING_ALIASES.get(key.lower(), key))
        if resolved_key in declared_keys or _is_runtime_secret_key(resolved_key):
            loaded_values[resolved_key] = value
    return loaded_values


def _is_runtime_secret_key(key: str) -> bool:
    normalized = str(key or "").lower()
    return "_api_key" in normalized or "_api_token" in normalized
