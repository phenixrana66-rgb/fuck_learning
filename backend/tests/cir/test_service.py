import unittest

from backend.app.cir.service import build_cir
from backend.app.parser.schemas import ExtractedPresentation, ExtractedSlide, PreviewChapter, PreviewSubChapter, StructurePreview


class CirServiceTestCase(unittest.TestCase):
    def test_build_cir_extracts_grounded_key_points_from_slide_content(self) -> None:
        preview = StructurePreview(
            chapters=[
                PreviewChapter(
                    chapterId='chapter-001',
                    chapterName='第一章',
                    subChapters=[
                        PreviewSubChapter(
                            subChapterId='sub-001',
                            subChapterName='VIN的用途与基本内容',
                            pageRange='7-8',
                        )
                    ],
                )
            ]
        )
        extracted = ExtractedPresentation(
            slides=[
                ExtractedSlide(
                    slideNumber=7,
                    title='车辆识别代码编号',
                    bodyTexts=[
                        '车辆识别代码（Vehicle Identification Number，VIN）由一组字母和阿拉伯数字组成，共17位。',
                        '它相当于汽车的身份证，用于识别车辆信息。',
                    ],
                ),
                ExtractedSlide(
                    slideNumber=8,
                    title='基本内容',
                    bodyTexts=['了解国内外 VIN 码举例，知道 VIN 位置。'],
                ),
            ]
        )

        cir = build_cir('cw-001', preview, extracted)
        node = cir.chapters[0].nodes[0]

        self.assertIn('车辆识别代码编号', node.keyPoints)
        self.assertTrue(any('17位' in point for point in node.keyPoints))
        self.assertFalse(any('理解' in point and '核心内容' in point for point in node.keyPoints))
        self.assertIn('17位', node.summary)


if __name__ == '__main__':
    unittest.main()
