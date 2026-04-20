import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.cir.schemas import CIR, CirChapter, LessonNode
from backend.app.common.config import get_settings
from backend.app.common.db import configure_database_url, reset_database_url
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

    def _signed_payload(self, payload: dict[str, object]) -> dict[str, object]:
        timestamp = "1713513600000"
        enc = generate_signature(payload, get_settings().static_key, timestamp)
        return {**payload, "time": timestamp, "enc": enc}


if __name__ == "__main__":
    unittest.main()
