from __future__ import annotations

import base64
import binascii
import json
import ssl
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from backend.app.common.config import get_setting
from backend.app.common.exceptions import ApiError


@dataclass(slots=True)
class TtsSynthesisResult:
    audio_bytes: bytes
    duration_ms: int | None
    reqid: str | None
    log_id: str | None
    voice_type: str


def synthesize_speech(text: str, voice_type: str, audio_format: str) -> TtsSynthesisResult:
    appid = _required_setting("appid")
    access_token = _required_setting("access_token")
    tts_url = _required_setting("tts_url")
    tts_cluster = _required_setting("tts_cluster")
    resolved_voice_type = _resolve_voice_type(voice_type)
    timeout_seconds = float(get_setting("tts_timeout_seconds", 60.0))
    insecure_skip_verify = bool(get_setting("tts_insecure_skip_verify", False))
    retry_attempts = max(1, int(get_setting("tts_retry_attempts", 4)))
    retry_backoff_seconds = max(0.1, float(get_setting("tts_retry_backoff_seconds", 1.0)))
    request_id = str(uuid4())

    request_body = json.dumps(
        {
            "app": {
                "appid": appid,
                "token": access_token,
                "cluster": tts_cluster,
            },
            "user": {
                "uid": f"lesson-audio-{request_id[:12]}",
            },
            "audio": {
                "voice_type": resolved_voice_type,
                "encoding": audio_format,
                "speed_ratio": 1.0,
            },
            "request": {
                "reqid": request_id,
                "text": text,
                "operation": "query",
            },
        }
    ).encode("utf-8")
    request = Request(
        tts_url,
        data=request_body,
        headers={
            "Authorization": f"Bearer;{access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    ssl_context = _build_ssl_context(insecure_skip_verify)
    last_exc: Exception | None = None
    raw_body = ""
    log_id = None
    for attempt in range(retry_attempts):
        try:
            with urlopen(request, timeout=timeout_seconds, context=ssl_context) as response:
                raw_body = response.read().decode("utf-8")
                log_id = response.headers.get("X-Tt-Logid")
            break
        except HTTPError as exc:
            last_exc = exc
            # 429 限流时做指数退避重试，降低长任务失败率
            if exc.code == 429 and attempt < retry_attempts - 1:
                time.sleep(retry_backoff_seconds * (2**attempt))
                continue
            _raise_tts_error("volcengine tts http error", status_code=502, data={"status": exc.code, "attempt": attempt + 1})
        except (URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt < retry_attempts - 1:
                time.sleep(retry_backoff_seconds * (2**attempt))
                continue
            _raise_tts_error(
                "volcengine tts request failed",
                status_code=502,
                data={
                    "detail": str(exc),
                    "insecureSkipVerify": insecure_skip_verify,
                    "attempt": attempt + 1,
                },
            )
    else:
        _raise_tts_error("volcengine tts request failed", status_code=502, data={"detail": str(last_exc) if last_exc else "unknown"})

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        _raise_tts_error("volcengine tts returned invalid json", status_code=502, data={"detail": str(exc)})

    if payload.get("code") != 3000:
        _raise_tts_error(
            "volcengine tts synthesis failed",
            status_code=502,
            data={
                "ttsCode": payload.get("code"),
                "ttsMessage": payload.get("message"),
                "reqid": payload.get("reqid") or request_id,
                "logId": log_id,
            },
        )

    audio_base64 = payload.get("data")
    if not isinstance(audio_base64, str) or not audio_base64:
        _raise_tts_error(
            "volcengine tts returned empty audio",
            status_code=502,
            data={"reqid": payload.get("reqid") or request_id, "logId": log_id},
        )

    try:
        audio_bytes = base64.b64decode(audio_base64)
    except (ValueError, binascii.Error) as exc:
        _raise_tts_error(
            "volcengine tts returned invalid audio payload",
            status_code=502,
            data={"detail": str(exc), "reqid": payload.get("reqid") or request_id, "logId": log_id},
        )

    addition = payload.get("addition")
    duration_ms = _parse_duration_ms(addition)
    return TtsSynthesisResult(
        audio_bytes=audio_bytes,
        duration_ms=duration_ms,
        reqid=payload.get("reqid") or request_id,
        log_id=log_id,
        voice_type=resolved_voice_type,
    )


def _required_setting(name: str) -> str:
    value = get_setting(name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    _raise_tts_error(f"missing tts setting: {name}", status_code=503)


def _resolve_voice_type(request_voice_type: str) -> str:
    configured_voice_type = get_setting("tts_voice_type")
    if request_voice_type and request_voice_type not in {"female_standard", "male_standard"}:
        return request_voice_type
    if isinstance(configured_voice_type, str) and configured_voice_type.strip():
        return configured_voice_type.strip()
    _raise_tts_error("missing tts setting: tts_voice_type", status_code=503)


def _parse_duration_ms(addition: Any) -> int | None:
    if not isinstance(addition, dict):
        return None

    duration_value = addition.get("duration")
    if duration_value is None:
        return None

    try:
        return max(0, int(duration_value))
    except (TypeError, ValueError):
        return None


def _build_ssl_context(insecure_skip_verify: bool) -> ssl.SSLContext:
    if insecure_skip_verify:
        return ssl._create_unverified_context()  # noqa: SLF001
    return ssl.create_default_context()


def _raise_tts_error(message: str, status_code: int, data: dict[str, Any] | None = None) -> None:
    raise ApiError(code=status_code, msg=message, status_code=status_code, data=data or {})
