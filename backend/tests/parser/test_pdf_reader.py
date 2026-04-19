import tempfile
import unittest
from pathlib import Path

import fitz

from backend.app.common.exceptions import ApiError
from backend.app.parser.pdf_reader import extract_pdf_presentation


class PdfReaderTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    def test_extract_pdf_presentation_returns_pages_and_previews(self) -> None:
        pdf_path = self._create_text_pdf(
            "demo.pdf",
            [
                "第一章 绪论\n这是第一页的课程说明。",
                "第二页 内容\n这里是第二页正文。",
            ],
        )
        preview_dir = Path(self.temp_dir.name) / "previews"

        file_info, extracted = extract_pdf_presentation(
            pdf_path.as_uri(),
            preview_output_dir=preview_dir,
            preview_public_base="/courseware-previews/parse-demo",
        )

        self.assertEqual(file_info.fileName, "demo.pdf")
        self.assertEqual(file_info.pageCount, 2)
        self.assertEqual(extracted.sourceType, "pdf")
        self.assertEqual(len(extracted.slides), 2)
        self.assertEqual(extracted.slides[0].slideNumber, 1)
        self.assertEqual(extracted.slides[0].previewUrl, "/courseware-previews/parse-demo/page-1.png")
        self.assertTrue((preview_dir / "page-1.png").exists())
        self.assertTrue(extracted.slides[0].bodyTexts)

    def test_extract_pdf_presentation_rejects_image_only_pdf(self) -> None:
        pdf_path = self._create_image_only_pdf("image-only.pdf")

        with self.assertRaises(ApiError) as context:
            extract_pdf_presentation(pdf_path.as_uri())

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("可提取文本", context.exception.msg)

    def _create_text_pdf(self, file_name: str, page_texts: list[str]) -> Path:
        assert self.temp_dir is not None
        target = Path(self.temp_dir.name) / file_name
        document = fitz.open()
        for text in page_texts:
            page = document.new_page()
            page.insert_text((72, 72), text, fontsize=14)
        document.save(target)
        document.close()
        return target

    def _create_image_only_pdf(self, file_name: str) -> Path:
        assert self.temp_dir is not None
        target = Path(self.temp_dir.name) / file_name
        document = fitz.open()
        page = document.new_page()
        page.draw_rect(fitz.Rect(72, 72, 240, 240), color=(0, 0, 0), fill=(0.7, 0.7, 0.7))
        document.save(target)
        document.close()
        return target
