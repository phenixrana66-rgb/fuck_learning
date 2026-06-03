import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.student_runtime.qa_image_generation_service import (
    IMAGE_GENERATION_MODE,
    build_image_generation_prompt,
    generate_qa_image,
)


class QaImageGenerationServiceTestCase(unittest.TestCase):
    @patch("backend.app.student_runtime.qa_image_generation_service.get_section_knowledge_points_for_qa")
    @patch("backend.app.student_runtime.qa_image_generation_service.get_page_context_for_qa")
    @patch("backend.app.student_runtime.qa_image_generation_service.get_section_context_for_qa")
    def test_build_image_generation_prompt_uses_compact_context(
        self,
        mock_get_section_context,
        mock_get_page_context,
        mock_get_points,
    ) -> None:
        mock_get_section_context.return_value = {"courseName": "数据结构", "sectionName": "二叉树"}
        mock_get_page_context.return_value = {
            "pageTitle": "遍历方式",
            "pageSummary": "介绍前序、中序、后序遍历。",
            "parsedContent": "这段完整正文不应进入图片生成 prompt。",
        }
        mock_get_points.return_value = [{"pointName": "前序遍历"}, {"pointName": "中序遍历"}]

        prompt = build_image_generation_prompt(
            object(),
            lesson_id="lesson-1",
            section_id="section-1",
            page_no=1,
            prompt="画一张讲解图",
        )

        self.assertIn("学生提示词：画一张讲解图", prompt)
        self.assertIn("课程：数据结构", prompt)
        self.assertIn("章节：二叉树", prompt)
        self.assertIn("当前页：遍历方式", prompt)
        self.assertIn("相关知识点：前序遍历、中序遍历", prompt)
        self.assertIn("页面摘要：介绍前序、中序、后序遍历。", prompt)
        self.assertNotIn("完整正文", prompt)

    @patch("backend.app.student_runtime.qa_image_generation_service.store_qa_image_from_url")
    @patch("backend.app.student_runtime.qa_image_generation_service.DashScopeClient")
    @patch("backend.app.student_runtime.qa_image_generation_service.build_image_generation_prompt")
    def test_generate_qa_image_returns_local_attachment_payload(
        self,
        mock_build_prompt,
        mock_dashscope_client,
        mock_store_image,
    ) -> None:
        mock_build_prompt.return_value = "compact prompt"
        mock_dashscope_client.return_value.create_image_generation_task.return_value = {
            "task_id": "task-001",
            "status": "PENDING",
        }
        mock_dashscope_client.return_value.get_image_generation_task.return_value = {
            "task_id": "task-001",
            "status": "SUCCEEDED",
            "results": [{"url": "https://example.com/generated.png"}],
            "model": "wanx2.1-t2i-turbo",
        }
        mock_store_image.return_value = SimpleNamespace(
            to_payload=lambda: {
                "type": "image",
                "storageProvider": "local",
                "storageKey": "generated/demo.png",
                "url": "/cache/qa-images/generated/demo.png",
                "name": "generated-image.png",
                "mimeType": "image/png",
                "size": 128,
            }
        )

        result = generate_qa_image(
            object(),
            lesson_id="lesson-1",
            section_id="section-1",
            page_no=1,
            prompt="画一张讲解图",
        )

        self.assertEqual(result["mode"], IMAGE_GENERATION_MODE)
        self.assertEqual(result["generation"]["status"], "SUCCEEDED")
        self.assertEqual(result["attachments"][0]["url"], "/cache/qa-images/generated/demo.png")
        mock_store_image.assert_called_once_with(
            image_url="https://example.com/generated.png",
            file_name="generated-image-1.png",
            subdir="generated",
            timeout=30.0,
        )


if __name__ == "__main__":
    unittest.main()
