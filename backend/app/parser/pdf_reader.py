from __future__ import annotations

from pathlib import Path

import fitz

from backend.app.common.exceptions import ApiError
from backend.app.parser.schemas import ExtractedPresentation, ExtractedSlide, FileInfo
from backend.app.parser.source_loader import load_source_bytes


def extract_pdf_presentation(
    file_url: str,
    *,
    preview_output_dir: Path | None = None,
    preview_public_base: str | None = None,
) -> tuple[FileInfo, ExtractedPresentation]:
    file_name, file_bytes = load_source_bytes(file_url, file_label="PDF", default_name="courseware.pdf")
    if not file_name.lower().endswith(".pdf"):
        raise ApiError(code=400, msg="当前仅支持 .pdf 文件，请传入可访问的 PDF 文件", status_code=400)

    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ApiError(code=400, msg="PDF 文件无法解析，请确认文件内容有效", status_code=400) from exc

    try:
        if document.page_count <= 0:
            raise ApiError(code=400, msg="PDF 中没有可解析的页面", status_code=400)

        if preview_output_dir is not None:
            preview_output_dir.mkdir(parents=True, exist_ok=True)

        slides: list[ExtractedSlide] = []
        has_extracted_text = False
        for index, page in enumerate(document, start=1):
            blocks = _extract_text_blocks(page)
            title = _choose_page_title(blocks, index)
            body_texts = blocks[:8]
            preview_url = _render_preview_page(
                page,
                page_no=index,
                output_dir=preview_output_dir,
                public_base=preview_public_base,
            )
            if body_texts:
                has_extracted_text = True
            slides.append(
                ExtractedSlide(
                    slideNumber=index,
                    title=title,
                    bodyTexts=body_texts,
                    tableTexts=[],
                    notes=None,
                    previewUrl=preview_url,
                )
            )

        if not has_extracted_text:
            raise ApiError(code=400, msg="当前仅支持可提取文本的 PDF，暂不支持扫描版或纯图片 PDF", status_code=400)

        file_info = FileInfo(fileName=file_name, fileSize=len(file_bytes), pageCount=len(slides))
        extracted = ExtractedPresentation(sourceType="pdf", slides=slides)
        return file_info, extracted
    finally:
        document.close()


def _extract_text_blocks(page: fitz.Page) -> list[str]:
    texts: list[str] = []
    for block in page.get_text("blocks"):
        text = _normalize_text(block[4] if len(block) > 4 else None)
        if text:
            texts.append(text)
    return texts


def _choose_page_title(blocks: list[str], page_no: int) -> str:
    if not blocks:
        return f"第{page_no}页"

    first_block = blocks[0]
    first_line = first_block.splitlines()[0].strip()
    title_candidate = first_line or first_block
    return title_candidate[:80] if title_candidate else f"第{page_no}页"


def _render_preview_page(
    page: fitz.Page,
    *,
    page_no: int,
    output_dir: Path | None,
    public_base: str | None,
) -> str | None:
    if output_dir is None or not public_base:
        return None

    target_path = output_dir / f"page-{page_no}.png"
    matrix = fitz.Matrix(1.5, 1.5)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    pixmap.save(target_path)
    return f"{public_base.rstrip('/')}/page-{page_no}.png"


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return "\n".join(line.strip() for line in value.splitlines() if line.strip())
