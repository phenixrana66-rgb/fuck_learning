from __future__ import annotations

import base64
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx

from backend.app.common.exceptions import ApiError
from backend.app.common.config import get_settings
from backend.app.common.storage import get_storage_manager


PROJECT_ROOT = Path(__file__).resolve().parents[3]
QA_IMAGE_CACHE_ROOT = PROJECT_ROOT / "cache" / "qa-images"
QA_IMAGE_PUBLIC_PREFIX = "/cache/qa-images"
QA_IMAGE_MAX_COUNT = 5
QA_IMAGE_MAX_SIZE_BYTES = 10 * 1024 * 1024
SUPPORTED_QA_IMAGE_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

_DATA_URL_RE = re.compile(r"^data:(?P<mime>image/[a-zA-Z0-9.+-]+);base64,(?P<data>.+)$", re.S)


@dataclass(slots=True)
class StoredQaImage:
    storage_provider: str
    storage_key: str
    url: str
    name: str
    mime_type: str
    size: int

    def to_payload(self) -> dict[str, object]:
        return {
            "type": "image",
            "storageProvider": self.storage_provider,
            "storageKey": self.storage_key,
            "url": self.url,
            "name": self.name,
            "mimeType": self.mime_type,
            "size": self.size,
        }


def get_qa_image_cache_dir() -> Path:
    QA_IMAGE_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return QA_IMAGE_CACHE_ROOT


def build_qa_image_public_url(storage_key: str) -> str:
    normalized = str(storage_key or "").replace("\\", "/").strip("/")
    return f"{QA_IMAGE_PUBLIC_PREFIX}/{normalized}"


def store_qa_image_from_data_url(
    *,
    data_url: str,
    file_name: str | None = None,
    mime_type: str | None = None,
) -> StoredQaImage:
    resolved_mime, raw_bytes = decode_qa_image_data_url(data_url, mime_type=mime_type)
    _ensure_image_size_within_limit(len(raw_bytes))
    extension = SUPPORTED_QA_IMAGE_MIME_TYPES[resolved_mime]
    safe_name = _normalize_file_name(file_name or f"image{extension}", extension)
    uuid_key = f"{uuid4().hex[:2]}/{uuid4().hex}{extension}"
    
    settings = get_settings()
    storage_provider = "s3" if settings.s3_enabled else "local"
    storage_manager = get_storage_manager()
    url = storage_manager.upload_bytes(raw_bytes, f"qa/{uuid_key}", content_type=resolved_mime)
    
    return StoredQaImage(
        storage_provider=storage_provider,
        storage_key=uuid_key,
        url=url,
        name=safe_name,
        mime_type=resolved_mime,
        size=len(raw_bytes),
    )


def store_qa_image_from_url(
    *,
    image_url: str,
    file_name: str | None = None,
    mime_type: str | None = None,
    subdir: str = "generated",
    timeout: float = 30.0,
) -> StoredQaImage:
    normalized_url = str(image_url or "").strip()
    if not normalized_url:
        raise ApiError(502, "图片生成结果为空", status_code=502)
    try:
        with httpx.Client(timeout=timeout, trust_env=False, follow_redirects=True) as client:
            response = client.get(normalized_url)
            response.raise_for_status()
            raw_bytes = response.content
    except Exception as exc:
        raise ApiError(502, "生成图片下载失败，请稍后重试", status_code=502) from exc
    if not raw_bytes:
        raise ApiError(502, "生成图片内容为空", status_code=502)
    _ensure_image_size_within_limit(len(raw_bytes))
    resolved_mime = (mime_type or response.headers.get("content-type", "").split(";")[0] or mimetypes.guess_type(normalized_url)[0] or "").lower()
    if resolved_mime not in SUPPORTED_QA_IMAGE_MIME_TYPES:
        raise ApiError(502, "生成图片格式暂不支持", status_code=502)
    extension = SUPPORTED_QA_IMAGE_MIME_TYPES[resolved_mime]
    safe_name = _normalize_file_name(file_name or f"generated-image{extension}", extension)
    safe_subdir = str(subdir or "generated").replace("\\", "/").strip("/")
    if not safe_subdir or safe_subdir.startswith("..") or "/../" in f"/{safe_subdir}/":
        safe_subdir = "generated"
    storage_key = f"{safe_subdir}/{uuid4().hex[:2]}/{uuid4().hex}{extension}"
    
    settings = get_settings()
    storage_provider = "s3" if settings.s3_enabled else "local"
    storage_manager = get_storage_manager()
    url = storage_manager.upload_bytes(raw_bytes, f"qa/{storage_key}", content_type=resolved_mime)
    
    return StoredQaImage(
        storage_provider=storage_provider,
        storage_key=storage_key,
        url=url,
        name=safe_name,
        mime_type=resolved_mime,
        size=len(raw_bytes),
    )


def decode_qa_image_data_url(data_url: str, *, mime_type: str | None = None) -> tuple[str, bytes]:
    normalized = str(data_url or "").strip()
    match = _DATA_URL_RE.match(normalized)
    if not match:
        raise ApiError(400, "图片数据格式不正确，仅支持 Base64 图片内容", status_code=400)
    resolved_mime = match.group("mime").lower()
    if resolved_mime not in SUPPORTED_QA_IMAGE_MIME_TYPES:
        raise ApiError(400, "仅支持 JPG、PNG、WEBP 图片", status_code=400)
    if mime_type and str(mime_type).strip().lower() != resolved_mime:
        raise ApiError(400, "图片类型与内容不一致", status_code=400)
    try:
        raw_bytes = base64.b64decode(match.group("data"), validate=True)
    except Exception as exc:
        raise ApiError(400, "图片 Base64 数据无效", status_code=400) from exc
    if not raw_bytes:
        raise ApiError(400, "图片内容不能为空", status_code=400)
    return resolved_mime, raw_bytes


def normalize_qa_image_attachments(raw_attachments: list[object] | None) -> list[dict[str, object]]:
    attachments = list(raw_attachments or [])
    if len(attachments) > QA_IMAGE_MAX_COUNT:
        raise ApiError(400, f"最多上传 {QA_IMAGE_MAX_COUNT} 张图片", status_code=400)
    normalized: list[dict[str, object]] = []
    for item in attachments:
        if not isinstance(item, dict):
            continue
        attachment_type = str(item.get("type") or "image").strip().lower()
        if attachment_type != "image":
            raise ApiError(400, "当前仅支持图片附件", status_code=400)
        normalized_item = {
            "type": "image",
            "storageProvider": item.get("storageProvider") or "local",
            "storageKey": item.get("storageKey") or "",
            "url": item.get("url") or "",
            "name": item.get("name") or "image",
            "mimeType": item.get("mimeType") or "",
            "size": item.get("size"),
            "dataUrl": item.get("dataUrl") or "",
        }
        data_url = str(normalized_item["dataUrl"]).strip()
        if data_url:
            resolved_mime, raw_bytes = decode_qa_image_data_url(data_url, mime_type=str(normalized_item["mimeType"] or "") or None)
            _ensure_image_size_within_limit(len(raw_bytes))
            normalized_item["mimeType"] = resolved_mime
            normalized_item["size"] = len(raw_bytes)
        normalized.append(normalized_item)
    return normalized


def load_qa_image_as_data_url(storage_key: str, mime_type: str | None = None) -> str:
    key = _normalize_storage_key(storage_key)
    storage_manager = get_storage_manager()
    try:
        raw_bytes = storage_manager.download_bytes(f"qa/{key}")
    except Exception as exc:
        raise ApiError(404, "图片资源不存在或已失效", status_code=404) from exc
        
    resolved_mime = (mime_type or mimetypes.guess_type(key)[0] or "image/jpeg").lower()
    encoded = base64.b64encode(raw_bytes).decode("ascii")
    return f"data:{resolved_mime};base64,{encoded}"


def storage_key_from_url(file_url: str) -> str | None:
    normalized = str(file_url or "").strip()
    # 兼容本地缓存 URL
    if normalized.startswith(QA_IMAGE_PUBLIC_PREFIX):
        suffix = normalized[len(QA_IMAGE_PUBLIC_PREFIX):].strip("/")
        return _normalize_storage_key(suffix) if suffix else None
        
    # 兼容 S3 的 URL 提取 (例如包含 /qa/ 路径的部分)
    if "/qa/" in normalized:
        suffix = normalized.split("/qa/", 1)[-1].strip("/")
        return _normalize_storage_key(suffix) if suffix else None
        
    return None


def _normalize_storage_key(storage_key: str) -> str:
    normalized = str(storage_key or "").replace("\\", "/").strip("/")
    if not normalized or normalized.startswith("..") or "/../" in f"/{normalized}/":
        raise ApiError(400, "图片存储标识非法", status_code=400)
    return normalized


def _normalize_file_name(file_name: str, extension: str) -> str:
    candidate = Path(str(file_name or "")).name or f"image{extension}"
    if "." not in candidate:
        return f"{candidate}{extension}"
    return candidate


def _ensure_image_size_within_limit(size: int) -> None:
    if size > QA_IMAGE_MAX_SIZE_BYTES:
        raise ApiError(400, "单张图片大小不能超过 10MB", status_code=400)
