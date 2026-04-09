from functools import lru_cache
from os import getenv

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    app_name: str = "AI互动智课后端服务"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = True
    signature_enabled: bool = False
    llm_api_base_url: str = "http://10.195.20.215:13010/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-5.1-codex-mini"
    llm_timeout_seconds: float = 60.0

    model_config = ConfigDict(extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    defaults = Settings()
    return Settings(
        app_name=getenv("A12_APP_NAME", defaults.app_name),
        app_version=getenv("A12_APP_VERSION", defaults.app_version),
        api_prefix=getenv("A12_API_PREFIX", defaults.api_prefix),
        debug=getenv("A12_DEBUG", "false").lower() == "true",
        signature_enabled=getenv("A12_SIGNATURE_ENABLED", "false").lower() == "true",
        llm_api_base_url=getenv("A12_LLM_API_BASE_URL", defaults.llm_api_base_url),
        llm_api_key=getenv("A12_LLM_API_KEY"),
        llm_model=getenv("A12_LLM_MODEL", defaults.llm_model),
        llm_timeout_seconds=float(getenv("A12_LLM_TIMEOUT_SECONDS", str(defaults.llm_timeout_seconds))),
    )
