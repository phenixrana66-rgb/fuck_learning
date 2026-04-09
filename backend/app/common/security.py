from backend.app.common.config import get_settings
from backend.app.common.exceptions import ApiError


def ensure_signature_present(enc: str | None) -> None:
    if not enc:
        raise ApiError(code=400, msg="缺少 enc 签名信息", status_code=400)


def verify_signature_placeholder(enc: str | None, time: str | None = None) -> None:
    ensure_signature_present(enc)

    settings = get_settings()
    if settings.signature_enabled and not time:
        raise ApiError(code=400, msg="签名校验启用时必须提供 time", status_code=400)
