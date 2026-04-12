import hashlib
import json

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


def _normalize_signature_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def sort_and_join_signature_payload(payload: dict[str, object]) -> str:
    return "&".join(
        f"{key}={_normalize_signature_value(payload[key])}"
        for key in sorted(payload.keys())
        if payload[key] not in ("", None)
    )


def generate_signature(payload: dict[str, object], static_key: str, timestamp: str) -> str:
    raw = f"{sort_and_join_signature_payload(payload)}{static_key}{timestamp}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def verify_signature_payload(payload: dict[str, object]) -> dict[str, object]:
    normalized_payload = dict(payload or {})
    enc = str(normalized_payload.pop("enc", "") or "")
    timestamp = str(normalized_payload.pop("time", "") or "")
    if not enc or not timestamp:
        raise ApiError(code=401, msg="签名校验失败", status_code=401)

    settings = get_settings()
    expected = generate_signature(normalized_payload, settings.static_key, timestamp)
    if expected != enc:
        raise ApiError(code=401, msg="签名校验失败", status_code=401)

    return dict(payload or {})
