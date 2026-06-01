import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.cir.schemas import CIR, CirChapter, LessonNode
from backend.app.common.config import get_settings
from backend.app.common.db import configure_database_url, reset_database_url, session_scope
from backend.app.common.security import generate_signature
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import clear_parse_tasks, create_parse_task, run_parse_task
from backend.app.lesson.schemas import GenerateAudioRequest, PublishRequest
from backend.app.lesson.service import clear_lessons, generate_audio, publish_lesson
from backend.app.lesson.tts_client import TtsSynthesisResult
from backend.app.main import create_app
from backend.app.parser.schemas import FileInfo, StructurePreview
from backend.app.script.schemas import GenerateScriptRequest
from backend.app.script.service import clear_scripts, generate_script, get_script as get_script_detail
from backend.chaoxing_db.models import ChapterPractice, Lesson, LessonSection, School, StudentPracticeAttempt, StudentSectionProgress, User


class StudentRouterTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'student-router-test.db'}")
        clear_scripts()
        clear_parse_tasks()
        clear_lessons()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        clear_scripts()
        clear_parse_tasks()
        clear_lessons()
        reset_database_url()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_auth_verify_returns_only_database_lessons(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        publish = self._publish_demo_lesson(
            mock_parse_courseware,
            mock_build_cir,
            mock_synthesize_speech,
            mock_get_voice_cache_dir,
        )

        response = self.client.post(
            "/student-api/auth/verify",
            json=self._signed_payload(
                {
                    "token": "student_demo_token_001",
                    "studentId": "S2026001",
                }
            ),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        lessons = payload["data"]["lessons"]
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["lessonId"], publish["lessonId"])
        self.assertNotIn("L10001", [item["lessonId"] for item in lessons])
        self.assertNotIn("L10002", [item["lessonId"] for item in lessons])

    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_resume_and_recent_chapters_follow_latest_page_read_progress(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        publish = self._publish_demo_lesson(
            mock_parse_courseware,
            mock_build_cir,
            mock_synthesize_speech,
            mock_get_voice_cache_dir,
        )
        section_id = self._get_first_section_id(publish["lessonId"])
        student_identifier = self._get_student_identifier()

        page_read_response = self.client.post(
            "/student-api/api/v1/progress/page/read",
            json=self._signed_payload(
                {
                    "studentId": student_identifier,
                    "lessonId": publish["lessonId"],
                    "sectionId": section_id,
                    "lessonPageId": f"{publish['lessonId']}-P1",
                    "pageNo": 1,
                }
            ),
        )
        self.assertEqual(page_read_response.status_code, 200)
        persisted_section_id = page_read_response.json()["data"]["sectionId"]

        resume_response = self.client.post(
            "/student-api/api/v1/lesson/resume",
            json=self._signed_payload(
                {
                    "studentId": student_identifier,
                    "lessonId": publish["lessonId"],
                    "anchorId": "stale-anchor",
                }
            ),
        )
        self.assertEqual(resume_response.status_code, 200)
        resume_payload = resume_response.json()["data"]
        self.assertEqual(resume_payload["pageNo"], 1)
        self.assertEqual(resume_payload["sectionId"], persisted_section_id)
        self.assertNotEqual(resume_payload["anchorId"], "stale-anchor")

        recent_response = self.client.post(
            "/student-api/api/v1/recentChapters/list",
            json=self._signed_payload(
                {
                    "studentId": student_identifier,
                    "limit": 3,
                }
            ),
        )
        self.assertEqual(recent_response.status_code, 200)
        items = recent_response.json()["data"]["items"]
        self.assertTrue(items)
        self.assertEqual(items[0]["lessonId"], publish["lessonId"])
        self.assertEqual(items[0]["sectionId"], persisted_section_id)
        self.assertEqual(items[0]["pageNo"], 1)

    @patch("backend.app.student_runtime.router.answer_question")
    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_qa_stream_accepts_image_only_payload(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
        mock_answer_question,
    ) -> None:
        publish = self._publish_demo_lesson(
            mock_parse_courseware,
            mock_build_cir,
            mock_synthesize_speech,
            mock_get_voice_cache_dir,
        )
        section_id = self._get_first_section_id(publish["lessonId"])
        mock_answer_question.return_value = {
            "answer": "已结合图片完成解读。",
            "relatedKnowledgePoints": ["k1"],
            "understandingLevel": "partial",
            "understandingLabel": "部分理解",
            "resumeAnchor": {"anchorTitle": "课程导学", "pageNo": 1},
            "weakPoints": [],
        }

        response = self.client.post(
            "/student-api/api/v1/qa/interact/stream",
            json=self._signed_payload(
                {
                    "studentId": "S2026001",
                    "lessonId": publish["lessonId"],
                    "sectionId": section_id,
                    "attachments": [self._demo_image_attachment()],
                }
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "done"', response.text)
        self.assertIn("已结合图片完成解读。", response.text)
        called_attachments = mock_answer_question.call_args.kwargs["attachments"]
        self.assertEqual(called_attachments[0]["mimeType"], "image/png")

    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_qa_sessions_save_and_list_preserve_image_attachments(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        publish = self._publish_demo_lesson(
            mock_parse_courseware,
            mock_build_cir,
            mock_synthesize_speech,
            mock_get_voice_cache_dir,
        )
        section_id = self._get_first_section_id(publish["lessonId"])
        student_identifier = self._get_student_identifier()

        save_response = self.client.post(
            "/student-api/api/v1/qa/sessions/save",
            json=self._signed_payload(
                {
                    "studentId": student_identifier,
                    "lessonId": publish["lessonId"],
                    "sectionId": section_id,
                    "session": {
                        "sessionId": "session-image-only",
                        "messages": [
                            {
                                "id": "user-1",
                                "role": "user",
                                "content": "",
                                "questionType": "image",
                                "attachments": [self._demo_image_attachment()],
                            },
                            {
                                "id": "assistant-1",
                                "role": "assistant",
                                "content": "图像问答已保存",
                                "relatedPoints": ["k1"],
                                "understandingLevel": "partial",
                                "resumePageNo": 1,
                            },
                        ],
                    },
                }
            ),
        )

        self.assertEqual(save_response.status_code, 200)
        saved_session = save_response.json()["data"]["session"]
        self.assertEqual(saved_session["title"], "图片提问")
        saved_attachment = saved_session["messages"][0]["attachments"][0]
        self.assertTrue(saved_attachment["url"].startswith("/cache/qa-images/"))
        self.assertTrue(saved_attachment["storageKey"])

        list_response = self.client.post(
            "/student-api/api/v1/qa/sessions/list",
            json=self._signed_payload(
                {
                    "studentId": student_identifier,
                    "lessonId": publish["lessonId"],
                }
            ),
        )

        self.assertEqual(list_response.status_code, 200)
        listed_session = list_response.json()["data"]["sessions"][0]
        self.assertEqual(listed_session["title"], "图片提问")
        self.assertEqual(listed_session["messages"][0]["questionType"], "image")
        self.assertTrue(listed_session["messages"][0]["attachments"][0]["url"].startswith("/cache/qa-images/"))

    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_qa_lab_course_outline_returns_lessons_sections_and_pages(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        publish = self._publish_demo_lesson(
            mock_parse_courseware,
            mock_build_cir,
            mock_synthesize_speech,
            mock_get_voice_cache_dir,
        )

        response = self.client.post(
            "/api/v1/qa-lab/course-outline",
            json={"courseId": "course-001"},
            headers=self._teacher_headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["courseId"], "course-001")
        self.assertTrue(payload["lessons"])
        self.assertEqual(payload["lessons"][0]["lessonId"], publish["lessonId"])
        self.assertTrue(payload["lessons"][0]["sections"])
        self.assertTrue(payload["lessons"][0]["sections"][0]["pages"])

    @patch("backend.app.student_runtime.qa_lab_service.answer_question")
    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_qa_lab_runtime_config_update_and_compare(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
        mock_answer_question,
    ) -> None:
        publish = self._publish_demo_lesson(
            mock_parse_courseware,
            mock_build_cir,
            mock_synthesize_speech,
            mock_get_voice_cache_dir,
        )
        section_id = self._get_first_section_id(publish["lessonId"])

        update_response = self.client.put(
            "/api/v1/qa-lab/runtime-config",
            json={
                "qaLlmModel": "qwen-plus",
                "qaMultimodalModel": "qwen-vl-plus",
                "qaEmbeddingModel": "text-embedding-v4-exp",
                "retrievalEnabled": True,
                "retrievalTopK": 7,
            },
            headers=self._teacher_headers(),
        )

        self.assertEqual(update_response.status_code, 200)
        updated_config = update_response.json()["data"]["config"]
        self.assertEqual(updated_config["qaLlmModel"], "qwen-plus")
        self.assertEqual(updated_config["retrievalTopK"], 7)
        self.assertTrue(update_response.json()["data"]["warnings"])
        self.assertTrue(update_response.json()["data"]["overrideActive"])

        reset_response = self.client.post(
            "/api/v1/qa-lab/runtime-config/reset",
            json={},
            headers=self._teacher_headers(),
        )

        self.assertEqual(reset_response.status_code, 200)
        reset_payload = reset_response.json()["data"]
        self.assertFalse(reset_payload["overrideActive"])
        self.assertEqual(reset_payload["config"], reset_payload["defaults"])
        self.assertNotIn("updatedAt", reset_payload)

        def _fake_answer_question(*_args, **kwargs):
            runtime_config = kwargs["runtime_config"]
            return {
                "answer": "检索开启回答" if runtime_config.retrieval_enabled else "检索关闭回答",
                "relatedKnowledgePoints": ["k1"],
                "understandingLevel": "partial",
                "understandingLabel": "部分理解",
                "resumeAnchor": {"anchorId": "", "anchorTitle": "课程导学", "pageNo": 1},
                "weakPoints": [],
                "debug": {
                    "runtimeConfig": {
                        **runtime_config.to_dict(),
                        "actualModel": runtime_config.actual_chat_model(has_images=False),
                    },
                    "latencyMs": 12 if runtime_config.retrieval_enabled else 8,
                    "faqCandidates": [],
                    "contextChunks": [],
                },
            }

        mock_answer_question.side_effect = _fake_answer_question

        compare_response = self.client.post(
            "/api/v1/qa-lab/compare",
            json={
                "lessonId": publish["lessonId"],
                "sectionId": section_id,
                "question": "这一页主要讲了什么？",
            },
            headers=self._teacher_headers(),
        )

        self.assertEqual(compare_response.status_code, 200)
        results = compare_response.json()["data"]["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["variantKey"], "retrieval_on")
        self.assertEqual(results[1]["variantKey"], "retrieval_off")
        self.assertTrue(results[0]["result"]["debug"]["runtimeConfig"]["retrievalEnabled"])
        self.assertFalse(results[1]["result"]["debug"]["runtimeConfig"]["retrievalEnabled"])
        self.assertEqual(mock_answer_question.call_count, 2)

    @patch("backend.app.student_runtime.qa_orchestrator.record_qa_answer_trace")
    @patch("backend.app.student_runtime.qa_orchestrator.get_settings")
    @patch("backend.app.student_runtime.qa_orchestrator.DashScopeClient")
    @patch("backend.app.student_runtime.qa_orchestrator.build_qa_context_bundle")
    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_student_qa_route_uses_runtime_config(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
        mock_build_bundle,
        mock_dashscope_client,
        mock_get_settings,
        mock_record_trace,
    ) -> None:
        publish = self._publish_demo_lesson(
            mock_parse_courseware,
            mock_build_cir,
            mock_synthesize_speech,
            mock_get_voice_cache_dir,
        )
        section_id = self._get_first_section_id(publish["lessonId"])
        student_identifier = self._get_student_identifier()

        update_response = self.client.put(
            "/api/v1/qa-lab/runtime-config",
            json={
                "qaLlmModel": "qwen-plus",
                "qaMultimodalModel": "qwen-vl-plus",
                "qaEmbeddingModel": "text-embedding-v4-exp",
                "retrievalEnabled": True,
                "retrievalTopK": 6,
            },
            headers=self._teacher_headers(),
        )
        self.assertEqual(update_response.status_code, 200)

        mock_get_settings.return_value = SimpleNamespace(
            dashscope_api_key="demo-key",
            qa_llm_provider="dashscope",
        )
        mock_build_bundle.return_value = {
            "lesson": {"lessonId": publish["lessonId"], "sectionId": section_id},
            "questionIntent": "generative",
            "section": {
                "lessonDbId": 1,
                "sectionDbId": 1,
                "sectionName": "课程导学",
                "summary": "这里是摘要",
                "chapterContextText": "",
            },
            "page": {"pageNo": 1, "anchorId": "", "anchorTitle": "课程导学"},
            "knowledge_points": [],
            "faq_candidates": [],
            "context_chunks": [],
        }
        mock_dashscope_client.return_value.chat_completion.return_value = {
            "text": json.dumps(
                {
                    "answer": "运行时配置已生效",
                    "relatedKnowledgePoints": [],
                    "understandingLevel": "partial",
                    "weakPoints": [],
                    "resumeAnchor": {"anchorId": "", "anchorTitle": "课程导学", "pageNo": 1},
                    "confidenceScore": 0.8,
                },
                ensure_ascii=False,
            ),
        }

        response = self.client.post(
            "/student-api/api/v1/qa/interact",
            json=self._signed_payload(
                {
                    "studentId": student_identifier,
                    "lessonId": publish["lessonId"],
                    "sectionId": section_id,
                    "question": "帮我总结这一页",
                    "pageNo": 1,
                }
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["answer"], "运行时配置已生效")
        runtime_config = mock_dashscope_client.call_args.kwargs["runtime_config"]
        self.assertEqual(runtime_config.qa_llm_model, "qwen-plus")
        self.assertEqual(runtime_config.qa_multimodal_model, "qwen-vl-plus")
        self.assertEqual(runtime_config.qa_embedding_model, "text-embedding-v4-exp")
        self.assertEqual(runtime_config.retrieval_top_k, 6)
        self.assertEqual(mock_build_bundle.call_args.kwargs["runtime_config"].qa_llm_model, "qwen-plus")
        mock_record_trace.assert_called_once()

    @patch("backend.app.student_runtime.router.answer_question")
    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_student_qa_route_returns_pace_suggestion(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
        mock_answer_question,
    ) -> None:
        publish = self._publish_demo_lesson(
            mock_parse_courseware,
            mock_build_cir,
            mock_synthesize_speech,
            mock_get_voice_cache_dir,
        )
        section_id = self._get_first_section_id(publish["lessonId"])
        student_identifier = self._get_student_identifier()
        mock_answer_question.return_value = {
            "answer": "建议先回看关键内容。",
            "relatedKnowledgePoints": ["k1"],
            "understandingLevel": "weak",
            "understandingLabel": "未理解",
            "resumeAnchor": {"anchorId": "", "anchorTitle": "课程导学", "pageNo": 1},
            "weakPoints": ["k1"],
        }

        response = self.client.post(
            "/student-api/api/v1/qa/interact",
            json=self._signed_payload(
                {
                    "studentId": student_identifier,
                    "lessonId": publish["lessonId"],
                    "sectionId": section_id,
                    "question": "我没懂这一页",
                    "pageNo": 1,
                }
            ),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["paceSuggestion"]["paceMode"], "reinforce")
        self.assertEqual(payload["paceSuggestion"]["triggerSource"], "qa")

    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_practice_checkpoint_route_returns_pace_suggestion(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        publish = self._publish_demo_lesson(
            mock_parse_courseware,
            mock_build_cir,
            mock_synthesize_speech,
            mock_get_voice_cache_dir,
        )
        section_id = self._get_first_section_id(publish["lessonId"])
        student_identifier = self._get_student_identifier()

        with session_scope() as db:
            section = (
                db.query(LessonSection)
                .join(Lesson, LessonSection.lesson_id == Lesson.id)
                .filter(Lesson.lesson_no == publish["lessonId"], LessonSection.section_code == section_id)
                .first()
            )
            assert section is not None
            student = db.query(User).filter(User.user_no == student_identifier).first()
            assert student is not None
            practice = ChapterPractice(
                practice_code="practice-router-001",
                course_id=section.course_id,
                chapter_id=section.source_chapter_id,
                created_by=section.lesson.teacher_id,
                practice_title="章节练习",
                practice_type="exercise",
                difficulty_level="medium",
                total_score=100,
                item_count=1,
                publish_status="published",
            )
            db.add(practice)
            db.flush()
            db.add(
                StudentPracticeAttempt(
                    attempt_no="attempt-router-001",
                    practice_id=practice.id,
                    student_id=student.id,
                    course_id=section.course_id,
                    lesson_id=section.lesson_id,
                    section_id=section.id,
                    accuracy_percent=72,
                    grading_status="graded",
                    attempt_status="graded",
                )
            )
            db.commit()

        response = self.client.post(
            "/student-api/api/v1/progress/practice/checkpoint",
            json=self._signed_payload(
                {
                    "studentId": student_identifier,
                    "lessonId": publish["lessonId"],
                    "sectionId": section_id,
                    "pageNo": 1,
                }
            ),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["practicePercent"], 72)
        self.assertEqual(payload["paceSuggestion"]["paceMode"], "supplement")
        self.assertEqual(payload["paceSuggestion"]["triggerSource"], "practice")

    @patch("backend.app.lesson.voice_storage.get_voice_cache_dir")
    @patch("backend.app.lesson.service.synthesize_speech")
    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_pace_skip_route_keeps_active_suggestion(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        publish = self._publish_demo_lesson(
            mock_parse_courseware,
            mock_build_cir,
            mock_synthesize_speech,
            mock_get_voice_cache_dir,
        )
        section_code = self._get_first_section_id(publish["lessonId"])
        student_identifier = self._get_student_identifier()

        with session_scope() as db:
            student = db.query(User).filter(User.user_no == student_identifier).first()
            assert student is not None
            section = (
                db.query(LessonSection)
                .join(Lesson, LessonSection.lesson_id == Lesson.id)
                .filter(Lesson.lesson_no == publish["lessonId"], LessonSection.section_code == section_code)
                .first()
            )
            assert section is not None
            db.add(
                StudentSectionProgress(
                    student_id=student.id,
                    course_id=section.course_id,
                    lesson_id=section.lesson_id,
                    unit_id=section.unit_id,
                    section_id=section.id,
                    pace_mode="reinforce",
                    pace_reason_summary="需要先强化关键内容。",
                    pace_trigger_source="qa",
                )
            )
            db.commit()

        response = self.client.post(
            "/student-api/api/v1/progress/pace/skip",
            json=self._signed_payload(
                {
                    "studentId": student_identifier,
                    "lessonId": publish["lessonId"],
                    "sectionId": section_code,
                    "pageNo": 1,
                }
            ),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["paceSuggestion"]
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["paceMode"], "reinforce")

    def _publish_demo_lesson(self, mock_parse_courseware, mock_build_cir, mock_synthesize_speech, mock_get_voice_cache_dir):
        assert self.temp_dir is not None
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / "voice-cache"
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b"ID3demo-audio",
            duration_ms=2200,
            reqid="req-001",
            log_id="log-001",
            voice_type="volcano-voice",
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId="cw-course-001",
            title="demo",
            chapters=[
                CirChapter(
                    chapterId="course-001-chap-001",
                    chapterName="chapter",
                    nodes=[
                        LessonNode(nodeId="node-01-01", nodeName="node-1", pageRefs=[1], keyPoints=["k1"], summary="summary-1"),
                    ],
                )
            ],
        )
        parse_payload = ParseRequest(
            schoolId="school-001",
            userId="teacher-001",
            courseId="course-001",
            fileType="ppt",
            fileUrl="file:///tmp/demo.pptx",
            isExtractKeyPoint=True,
            enc="demo-signature",
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        script_summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle="standard",
                speechSpeed="normal",
                customOpening=None,
                enc="demo-signature",
            )
        )
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        script_detail.scriptStructure[0].content = "router test script"

        with patch("backend.app.lesson.service.get_script", return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=script_summary.scriptId,
                    voiceType="female_standard",
                    audioFormat="mp3",
                    sectionIds=[script_detail.scriptStructure[0].sectionId],
                    enc="demo-signature",
                ),
                base_url="http://testserver/",
            )
            publish = publish_lesson(
                PublishRequest(
                    coursewareId="cw-course-001",
                    scriptId=script_summary.scriptId,
                    audioId=audio["audioId"],
                    publisherId="teacher-demo",
                    enc="demo-signature",
                )
            )

        return publish

    def _get_first_section_id(self, lesson_id: str) -> str:
        with session_scope() as db:
            row = (
                db.query(LessonSection.section_code)
                .join(Lesson, LessonSection.lesson_id == Lesson.id)
                .filter(Lesson.lesson_no == lesson_id)
                .order_by(LessonSection.sort_no.asc(), LessonSection.id.asc())
                .first()
            )
        if row and row[0]:
            return row[0]
        self.fail("Expected at least one section_code for the published lesson")

    def _demo_image_attachment(self) -> dict[str, object]:
        return {
            "type": "image",
            "name": "demo.png",
            "mimeType": "image/png",
            "dataUrl": (
                "data:image/png;base64,"
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6nL9sAAAAASUVORK5CYII="
            ),
        }

    def _get_student_identifier(self) -> str:
        with session_scope() as db:
            row = db.query(User.user_no).filter(User.role == "student").order_by(User.id.asc()).first()
            if row and row[0]:
                return row[0]
            school = db.query(School).order_by(School.id.asc()).first()
            if school is None:
                school = School(school_code="school-demo", school_name="测试学校", status=True)
                db.add(school)
                db.flush()
            student = User(user_no="student-router-001", user_name="测试学生", role="student", school_id=school.id, status=True)
            db.add(student)
            db.flush()
            return student.user_no

    def _signed_payload(self, payload: dict[str, object]) -> dict[str, object]:
        timestamp = "1713513600000"
        enc = generate_signature(payload, get_settings().static_key, timestamp)
        return {**payload, "time": timestamp, "enc": enc}

    def _teacher_headers(self) -> dict[str, str]:
        token = get_settings().teacher_test_platform_token
        with session_scope() as db:
            teacher = db.query(User).filter(User.role == "teacher").order_by(User.id.asc()).first()
            if teacher is not None and teacher.auth_token != token:
                teacher.auth_token = token
                db.flush()
        return {"X-Platform-Token": token}


if __name__ == "__main__":
    unittest.main()
