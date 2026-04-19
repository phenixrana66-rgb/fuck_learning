from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

import httpx

from backend.app.common.exceptions import ApiError


def load_source_bytes(file_url: str, *, file_label: str, default_name: str) -> tuple[str, bytes]:
    parsed = urlparse(file_url)
    if parsed.scheme in {"http", "https"}:
        try:
            response = httpx.get(file_url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300]
            raise ApiError(code=400, msg=f"下载{file_label}文件失败：{detail}", status_code=400) from exc
        except httpx.HTTPError as exc:
            raise ApiError(code=400, msg=f"下载{file_label}文件失败：{exc}", status_code=400) from exc

        name = PurePosixPath(parsed.path).name or default_name
        return name, response.content

    if parsed.scheme == "file":
        local_path = Path(unquote(parsed.path.lstrip("/")))
    else:
        local_path = Path(file_url)

    if not local_path.exists() or not local_path.is_file():
        raise ApiError(code=400, msg=f"{file_label}文件不存在，请检查 fileUrl 是否可访问", status_code=400)

    return local_path.name, local_path.read_bytes()
