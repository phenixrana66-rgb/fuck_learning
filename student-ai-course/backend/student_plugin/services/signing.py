import hashlib
import json


def _normalize(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def sort_and_join(payload):
    return "&".join(
        f"{key}={_normalize(payload[key])}"
        for key in sorted(payload.keys())
        if payload[key] not in ("", None)
    )


def generate_enc(payload, static_key, timestamp):
    raw = f"{sort_and_join(payload)}{static_key}{timestamp}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def verify_signature(payload, static_key):
    payload = dict(payload or {})
    enc = payload.pop("enc", "")
    timestamp = payload.pop("time", "")
    if not enc or not timestamp:
        return False
    return enc == generate_enc(payload, static_key, timestamp)
