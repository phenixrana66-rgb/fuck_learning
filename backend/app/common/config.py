from functools import lru_cache
from os import getenv

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    app_name: str = "AI互动智课后端服务"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = False
    signature_enabled: bool = False

    model_config = ConfigDict(extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=getenv("A12_APP_NAME", "AI互动智课后端服务"),
        app_version=getenv("A12_APP_VERSION", "0.1.0"),
        api_prefix=getenv("A12_API_PREFIX", "/api/v1"),
        debug=getenv("A12_DEBUG", "false").lower() == "true",
        signature_enabled=getenv("A12_SIGNATURE_ENABLED", "false").lower() == "true",
    )
