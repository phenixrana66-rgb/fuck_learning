from functools import lru_cache
from os import getenv
from pathlib import Path
from runpy import run_path

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    app_name: str = "AI互动智课后端服务"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = False
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
    llm_api_base_url: str = "http://10.195.20.215:13010/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-5.1-codex-mini"
    llm_timeout_seconds: float = 60.0
    qa_llm_provider: str = "dashscope"
    qa_llm_model: str = "qwen-max"
    qa_embedding_model: str = "text-embedding-v4"
    qa_embedding_dimensions: int = 1024
    qa_asr_model: str = "qwen3-asr-flash"
    qa_asr_timeout_seconds: float = 180.0
    qa_asr_poll_interval_seconds: float = 2.0
    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com"
    vector_db_url: str | None = None

    model_config = ConfigDict(extra="ignore")


_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_CONFIG_PATH = _REPO_ROOT / "config.local.py"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    defaults = Settings()
    file_overrides = _load_local_config_values()
    merged_defaults = {**defaults.model_dump(), **file_overrides}
    return Settings(
        app_name=getenv("A12_APP_NAME", str(merged_defaults["app_name"])),
        app_version=getenv("A12_APP_VERSION", str(merged_defaults["app_version"])),
        api_prefix=getenv("A12_API_PREFIX", str(merged_defaults["api_prefix"])),
        debug=_getenv_bool("A12_DEBUG", bool(merged_defaults["debug"])),
        signature_enabled=_getenv_bool("A12_SIGNATURE_ENABLED", bool(merged_defaults["signature_enabled"])),
        db_url=getenv("A12_DB_URL", _get_optional_str(merged_defaults["db_url"])),
        db_host=getenv("A12_DB_HOST", str(merged_defaults["db_host"])),
        db_port=int(getenv("A12_DB_PORT", str(merged_defaults["db_port"]))),
        db_user=getenv("A12_DB_USER", str(merged_defaults["db_user"])),
        db_password=getenv("A12_DB_PASSWORD", str(merged_defaults["db_password"])),
        db_name=getenv("A12_DB_NAME", str(merged_defaults["db_name"])),
        db_echo=_getenv_bool("A12_DB_ECHO", bool(merged_defaults["db_echo"])),
        static_key=getenv("A12_STATIC_KEY", str(merged_defaults["static_key"])),
        mock_mode=_getenv_bool("A12_MOCK_MODE", bool(merged_defaults["mock_mode"])),
        teacher_test_platform_token=getenv("A12_TEACHER_TEST_PLATFORM_TOKEN", str(merged_defaults["teacher_test_platform_token"])),
        default_audio_url=getenv("A12_DEFAULT_AUDIO_URL", str(merged_defaults["default_audio_url"])),
        llm_api_base_url=getenv("A12_LLM_API_BASE_URL", str(merged_defaults["llm_api_base_url"])),
        llm_api_key=getenv("A12_LLM_API_KEY", _get_optional_str(merged_defaults["llm_api_key"])),
        llm_model=getenv("A12_LLM_MODEL", str(merged_defaults["llm_model"])),
        llm_timeout_seconds=float(getenv("A12_LLM_TIMEOUT_SECONDS", str(merged_defaults["llm_timeout_seconds"]))),
        qa_llm_provider=getenv("A12_QA_LLM_PROVIDER", str(merged_defaults["qa_llm_provider"])),
        qa_llm_model=getenv("A12_QA_LLM_MODEL", str(merged_defaults["qa_llm_model"])),
        qa_embedding_model=getenv("A12_QA_EMBEDDING_MODEL", str(merged_defaults["qa_embedding_model"])),
        qa_embedding_dimensions=int(getenv("A12_QA_EMBEDDING_DIMENSIONS", str(merged_defaults["qa_embedding_dimensions"]))),
        qa_asr_model=getenv("A12_QA_ASR_MODEL", str(merged_defaults["qa_asr_model"])),
        qa_asr_timeout_seconds=float(getenv("A12_QA_ASR_TIMEOUT_SECONDS", str(merged_defaults["qa_asr_timeout_seconds"]))),
        qa_asr_poll_interval_seconds=float(getenv("A12_QA_ASR_POLL_INTERVAL_SECONDS", str(merged_defaults["qa_asr_poll_interval_seconds"]))),
        dashscope_api_key=getenv("A12_DASHSCOPE_API_KEY", _get_optional_str(merged_defaults["dashscope_api_key"])),
        dashscope_base_url=getenv("A12_DASHSCOPE_BASE_URL", str(merged_defaults["dashscope_base_url"])),
        vector_db_url=getenv("A12_VECTOR_DB_URL", _get_optional_str(merged_defaults["vector_db_url"])),
    )


def _load_local_config_values() -> dict[str, object]:
    if not _LOCAL_CONFIG_PATH.exists():
        return {}
    local_namespace = run_path(str(_LOCAL_CONFIG_PATH))
    declared_keys = set(Settings.model_fields)
    return {key: value for key, value in local_namespace.items() if key in declared_keys}


def _getenv_bool(name: str, default: bool) -> bool:
    return getenv(name, str(default)).lower() == "true"


def _get_optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
