from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from pptx import Presentation

from backend.app.common.exceptions import ApiError
from backend.app.parser.schemas import ExtractedPresentation, ExtractedSlide, FileInfo
from backend.app.parser.source_loader import load_source_bytes

POWERSHELL_EXE = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
POWERPOINT_EXPORT_SCRIPT = """\
param(
    [Parameter(Mandatory = $true)][string]$InputPath,
    [Parameter(Mandatory = $true)][string]$OutputDir
)
$ErrorActionPreference = 'Stop'
$ppt = $null
$presentation = $null
try {
    $ppt = New-Object -ComObject PowerPoint.Application
    $presentation = $ppt.Presentations.Open($InputPath, $true, $false, $false)
    $presentation.Export($OutputDir, 'PNG')
}
finally {
    if ($presentation -ne $null) {
        $presentation.Close()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation)
    }
    if ($ppt -ne $null) {
        $ppt.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt)
    }
}
"""


def extract_pptx_presentation(
    file_url: str,
    *,
    preview_output_dir: Path | None = None,
    preview_public_base: str | None = None,
) -> tuple[FileInfo, ExtractedPresentation]:
    file_name, file_bytes = load_source_bytes(file_url, file_label="PPTX", default_name="courseware.pptx")
    normalized_name = file_name.lower()
    if normalized_name.endswith(".ppt"):
        raise ApiError(code=400, msg="当前环境暂仅支持 .pptx 文件预览生成，请先将 .ppt 转为 .pptx 后重试", status_code=400)
    if not normalized_name.endswith(".pptx"):
        raise ApiError(code=400, msg="当前 demo 仅支持 .pptx 文件，请传入可访问的 PPTX 文件", status_code=400)

    try:
        presentation = Presentation(BytesIO(file_bytes))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(code=400, msg="PPTX 文件无法解析，请确认文件内容有效", status_code=400) from exc

    slide_count = len(presentation.slides)
    preview_urls = _build_preview_urls(
        file_name=file_name,
        file_bytes=file_bytes,
        slide_count=slide_count,
        output_dir=preview_output_dir,
        public_base=preview_public_base,
    )

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
                previewUrl=preview_urls.get(index),
            )
        )

    if not slides:
        raise ApiError(code=400, msg="PPTX 中没有可解析的页面", status_code=400)

    file_info = FileInfo(fileName=file_name, fileSize=len(file_bytes), pageCount=len(slides))
    extracted = ExtractedPresentation(sourceType="pptx", slides=slides)
    return file_info, extracted


def _build_preview_urls(
    *,
    file_name: str,
    file_bytes: bytes,
    slide_count: int,
    output_dir: Path | None,
    public_base: str | None,
) -> dict[int, str]:
    if output_dir is None or not public_base:
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pptx-preview-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        input_path = temp_dir / Path(file_name).name
        export_dir = temp_dir / "exported"
        export_dir.mkdir(parents=True, exist_ok=True)
        input_path.write_bytes(file_bytes)

        _export_with_powerpoint(input_path, export_dir)
        exported_files = _collect_exported_images(export_dir)
        if not exported_files:
            raise ApiError(code=500, msg="PowerPoint 未导出任何页图，请检查本机 Office 渲染能力", status_code=500)
        if slide_count and len(exported_files) != slide_count:
            raise ApiError(
                code=500,
                msg=f"PowerPoint 导出的页图数量异常，期望 {slide_count} 页，实际 {len(exported_files)} 页",
                status_code=500,
            )

        preview_urls: dict[int, str] = {}
        for index, source_path in enumerate(exported_files, start=1):
            target_path = output_dir / f"page-{index}.png"
            shutil.copy2(source_path, target_path)
            preview_urls[index] = f"{public_base.rstrip('/')}/page-{index}.png"
        return preview_urls


def _export_with_powerpoint(input_path: Path, output_dir: Path) -> None:
    if not POWERSHELL_EXE.exists():
        raise ApiError(code=500, msg="当前环境缺少 PowerShell，无法调用 PowerPoint 导出课件页图", status_code=500)

    script_path = output_dir.parent / "export_pptx_preview.ps1"
    script_path.write_text(POWERPOINT_EXPORT_SCRIPT, encoding="utf-8")
    completed = subprocess.run(
        [
            str(POWERSHELL_EXE),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-InputPath",
            str(input_path),
            "-OutputDir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        message = detail[-1] if detail else "未知错误"
        raise ApiError(code=500, msg=f"调用 PowerPoint 导出页图失败：{message}", status_code=500)


def _collect_exported_images(export_dir: Path) -> list[Path]:
    numbered_files: list[tuple[int, Path]] = []
    for path in export_dir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".png":
            continue
        match = re.search(r"(\d+)$", path.stem)
        if not match:
            continue
        numbered_files.append((int(match.group(1)), path))
    numbered_files.sort(key=lambda item: item[0])
    return [path for _, path in numbered_files]


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
