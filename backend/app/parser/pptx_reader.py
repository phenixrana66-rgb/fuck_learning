from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

import httpx
from pptx import Presentation

from backend.app.common.exceptions import ApiError
from backend.app.parser.schemas import ExtractedPresentation, ExtractedSlide, FileInfo


def extract_pptx_presentation(file_url: str) -> tuple[FileInfo, ExtractedPresentation]:
    file_name, file_bytes = _load_source_bytes(file_url)
    if not file_name.lower().endswith(".pptx"):
        raise ApiError(code=400, msg="当前 demo 仅支持 .pptx 文件，请传入可访问的 PPTX 文件", status_code=400)

    try:
        presentation = Presentation(BytesIO(file_bytes))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(code=400, msg="PPTX 文件无法解析，请确认文件内容有效", status_code=400) from exc

    slides: list[ExtractedSlide] = []
    for index, slide in enumerate(presentation.slides, start=1):
        body_texts: list[str] = []
        table_texts: list[str] = []
        title: str | None = None

        for shape in slide.shapes:
            current_title = _extract_title(shape)
            if current_title and not title:
                title = current_title

            text_frame = getattr(shape, "text_frame", None)
            if text_frame is not None:
                text = _normalize_text(getattr(text_frame, "text", None))
                if text:
                    body_texts.append(text)

            table = getattr(shape, "table", None)
            if table is not None:
                rows: list[str] = []
                for row in table.rows:
                    values = [_normalize_text(cell.text) for cell in row.cells]
                    values = [value for value in values if value]
                    if values:
                        rows.append(" | ".join(values))
                if rows:
                    table_texts.append("\n".join(rows))

        notes = _extract_notes(slide)
        if not title:
            title = body_texts[0][:40] if body_texts else f"第{index}页"

        slides.append(
            ExtractedSlide(
                slideNumber=index,
                title=title,
                bodyTexts=body_texts,
                tableTexts=table_texts,
                notes=notes,
            )
        )

    if not slides:
        raise ApiError(code=400, msg="PPTX 中没有可解析的页面", status_code=400)

    file_info = FileInfo(fileName=file_name, fileSize=len(file_bytes), pageCount=len(slides))
    extracted = ExtractedPresentation(slides=slides)
    return file_info, extracted


def _load_source_bytes(file_url: str) -> tuple[str, bytes]:
    parsed = urlparse(file_url)
    if parsed.scheme in {"http", "https"}:
        try:
            response = httpx.get(file_url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300]
            raise ApiError(code=400, msg=f"下载 PPTX 文件失败：{detail}", status_code=400) from exc
        except httpx.HTTPError as exc:
            raise ApiError(code=400, msg=f"下载 PPTX 文件失败：{exc}", status_code=400) from exc

        name = PurePosixPath(parsed.path).name or "courseware.pptx"
        return name, response.content

    if parsed.scheme == "file":
        local_path = Path(unquote(parsed.path.lstrip("/")))
    else:
        local_path = Path(file_url)

    if not local_path.exists() or not local_path.is_file():
        raise ApiError(code=400, msg="PPTX 文件不存在，请检查 fileUrl 是否可访问", status_code=400)

    return local_path.name, local_path.read_bytes()


def _extract_title(shape: object) -> str | None:
    if not hasattr(shape, "is_placeholder") or not getattr(shape, "is_placeholder"):
        return None
    placeholder_format = getattr(shape, "placeholder_format", None)
    placeholder_type = getattr(placeholder_format, "type", None)
    placeholder_name = str(placeholder_type).lower() if placeholder_type is not None else ""
    if "title" not in placeholder_name and "center_title" not in placeholder_name and "subtitle" not in placeholder_name:
        return None
    text_frame = getattr(shape, "text_frame", None)
    if text_frame is None:
        return None
    text = _normalize_text(getattr(text_frame, "text", None))
    return text or None


def _extract_notes(slide: object) -> str | None:
    try:
        notes_slide = getattr(slide, "notes_slide")
    except Exception:  # noqa: BLE001
        return None

    text_frame = getattr(notes_slide, "notes_text_frame", None)
    if text_frame is None:
        return None
    text = _normalize_text(getattr(text_frame, "text", None))
    return text or None


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return "\n".join(line.strip() for line in value.splitlines() if line.strip())
