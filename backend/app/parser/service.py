from pathlib import Path

from backend.app.common.exceptions import ApiError
from backend.app.parser.llm_client import generate_outline_with_llm
from backend.app.parser.pdf_reader import extract_pdf_presentation
from backend.app.parser.pptx_reader import extract_pptx_presentation
from backend.app.parser.schemas import ExtractedPresentation, FileInfo, OutlineResult, PreviewChapter, PreviewSubChapter, StructurePreview


def parse_courseware(
    course_id: str,
    file_url: str,
    file_type: str,
    is_extract_key_point: bool,
    *,
    preview_output_dir: Path | None = None,
    preview_public_base: str | None = None,
) -> tuple[FileInfo, StructurePreview, ExtractedPresentation]:
    if file_type == "pdf":
        file_info, extracted = extract_pdf_presentation(
            file_url,
            preview_output_dir=preview_output_dir,
            preview_public_base=preview_public_base,
        )
    elif file_type in {"ppt", "pptx"}:
        file_info, extracted = extract_pptx_presentation(file_url)
    else:
        raise ApiError(code=400, msg=f"不支持的课件类型：{file_type}", status_code=400)

    outline = generate_outline_with_llm(course_id, extracted, is_extract_key_point)
    preview = _outline_to_structure_preview(course_id, outline, file_info.pageCount)
    return file_info, preview, extracted


def build_file_info(file_url: str, file_type: str) -> FileInfo:
    if file_type in {"ppt", "pptx"}:
        file_info, _ = extract_pptx_presentation(file_url)
        return file_info
    if file_type == "pdf":
        file_info, _ = extract_pdf_presentation(file_url)
        return file_info

    file_name = file_url.split("/")[-1] or f"courseware.{file_type}"
    page_count = 18
    return FileInfo(fileName=file_name, fileSize=2_048_000, pageCount=page_count)


def build_structure_preview(
    course_id: str,
    file_url: str,
    file_type: str,
    is_extract_key_point: bool = True,
) -> StructurePreview:
    _, preview, _ = parse_courseware(course_id, file_url, file_type, is_extract_key_point)
    return preview


def _outline_to_structure_preview(course_id: str, outline: OutlineResult, page_count: int) -> StructurePreview:
    chapters: list[PreviewChapter] = []
    next_page = 1
    last_page = max(page_count, 1)

    if not outline.chapters:
        raise ApiError(code=502, msg="LLM 未返回有效章节结构，请检查 PPT 内容或提示词配置", status_code=502)

    for chapter_index, outline_chapter in enumerate(outline.chapters, start=1):
        sub_chapters: list[PreviewSubChapter] = []
        for subchapter_index, outline_subchapter in enumerate(outline_chapter.subChapters, start=1):
            page_start = _clamp_page(outline_subchapter.pageStart, next_page, last_page)
            page_end = _clamp_page(outline_subchapter.pageEnd, page_start, last_page)
            next_page = min(page_end + 1, last_page)
            sub_chapters.append(
                PreviewSubChapter(
                    subChapterId=f"{course_id}-sub-{chapter_index:03d}-{subchapter_index:03d}",
                    subChapterName=outline_subchapter.name.strip() or f"第{subchapter_index}小节",
                    isKeyPoint=outline_subchapter.isKeyPoint,
                    pageRange=f"{page_start}-{page_end}",
                )
            )

        if not sub_chapters:
            sub_chapters.append(
                PreviewSubChapter(
                    subChapterId=f"{course_id}-sub-{chapter_index:03d}-001",
                    subChapterName="内容整理",
                    isKeyPoint=True,
                    pageRange=f"{next_page}-{last_page}",
                )
            )

        chapters.append(
            PreviewChapter(
                chapterId=f"{course_id}-chap-{chapter_index:03d}",
                chapterName=outline_chapter.name.strip() or f"第{chapter_index}章",
                subChapters=sub_chapters,
            )
        )

    _ensure_last_page_covered(chapters, last_page)
    return StructurePreview(chapters=chapters)


def _clamp_page(page: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(page, maximum))


def _ensure_last_page_covered(chapters: list[PreviewChapter], last_page: int) -> None:
    if not chapters or not chapters[-1].subChapters:
        return
    last_subchapter = chapters[-1].subChapters[-1]
    start_text, end_text = last_subchapter.pageRange.split("-")
    start = int(start_text)
    end = int(end_text)
    if end < last_page:
        last_subchapter.pageRange = f"{start}-{last_page}"
