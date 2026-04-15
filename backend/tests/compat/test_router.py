import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.common.db import get_db
from backend.app.main import create_app
from backend.app.script.schemas import ScriptSection, ScriptSummary


class CompatRouterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()

        def override_get_db():
            yield object()

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @patch("backend.app.compat.router.generate_main_script")
    def test_generate_script_new_payload_uses_main_service(self, mock_generate_main_script) -> None:
        mock_generate_main_script.return_value = ScriptSummary(
            scriptId="script-001",
            scriptStructure=[
                ScriptSection(sectionId="sec001", sectionName="intro", content="alpha script", duration=40),
                ScriptSection(sectionId="sec002", sectionName="body", content="beta script", duration=35),
            ],
            editUrl="/teacher/scripts/script-001/edit",
            audioGenerateUrl="/api/v1/lesson/generateAudio",
        )

        response = self.client.post(
            "/api/v1/lesson/generateScript",
            json={
                "parseId": "parse-001",
                "teachingStyle": "detailed",
                "speechSpeed": "normal",
                "customOpening": "",
                "enc": "demo-signature",
                "time": "1700000000000",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["scriptId"], "script-001")
        self.assertEqual(len(payload["data"]["scriptStructure"]), 2)
        self.assertEqual(payload["data"]["editUrl"], "/teacher/scripts/script-001/edit")
        self.assertEqual(payload["data"]["audioGenerateUrl"], "/api/v1/lesson/generateAudio")

        mock_generate_main_script.assert_called_once()
        request_payload = mock_generate_main_script.call_args.args[0]
        self.assertEqual(request_payload.parseId, "parse-001")
        self.assertEqual(request_payload.teachingStyle, "detailed")
        self.assertEqual(request_payload.speechSpeed, "normal")
        self.assertEqual(request_payload.customOpening, "")
        self.assertEqual(request_payload.enc, "demo-signature")
        self.assertEqual(request_payload.time, "1700000000000")

    def test_generate_script_old_payload_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/lesson/generateScript",
            json={"parseId": "parse-001", "scriptType": "detail"},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["msg"], "generateScript payload is invalid")
        self.assertIn("errors", payload["data"])
