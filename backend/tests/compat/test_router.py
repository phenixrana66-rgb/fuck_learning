import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.common.db import get_db
from backend.app.main import create_app
from backend.app.script.schemas import ScriptDetail, ScriptSection, ScriptSummary


class CompatRouterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()

        def override_get_db():
            yield object()

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @patch('backend.app.compat.router.generate_main_script')
    def test_generate_script_new_payload_uses_main_service(self, mock_generate_main_script) -> None:
        mock_generate_main_script.return_value = ScriptSummary(
            scriptId='script-001',
            scriptStructure=[
                ScriptSection(sectionId='sec001', sectionName='intro', content='alpha script', duration=40),
                ScriptSection(sectionId='sec002', sectionName='body', content='beta script', duration=35),
            ],
            editUrl='/teacher/scripts/script-001/edit',
            audioGenerateUrl='/api/v1/lesson/generateAudio',
        )

        response = self.client.post(
            '/api/v1/lesson/generateScript',
            json={
                'parseId': 'parse-001',
                'teachingStyle': 'detailed',
                'speechSpeed': 'normal',
                'customOpening': '',
                'enc': 'demo-signature',
                'time': '1700000000000',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['data']['scriptId'], 'script-001')
        self.assertEqual(len(payload['data']['scriptStructure']), 2)
        self.assertEqual(payload['data']['editUrl'], '/teacher/scripts/script-001/edit')
        self.assertEqual(payload['data']['audioGenerateUrl'], '/api/v1/lesson/generateAudio')

        mock_generate_main_script.assert_called_once()
        request_payload = mock_generate_main_script.call_args.args[0]
        self.assertEqual(request_payload.parseId, 'parse-001')
        self.assertEqual(request_payload.teachingStyle, 'detailed')
        self.assertEqual(request_payload.speechSpeed, 'normal')
        self.assertEqual(request_payload.customOpening, '')
        self.assertEqual(request_payload.enc, 'demo-signature')
        self.assertEqual(request_payload.time, '1700000000000')

    @patch('backend.app.compat.router.get_script')
    def test_get_script_endpoint_uses_main_service(self, mock_get_script) -> None:
        mock_get_script.return_value = ScriptDetail(
            scriptId='script-001',
            parseId='parse-001',
            teachingStyle='standard',
            speechSpeed='normal',
            scriptStructure=[
                ScriptSection(sectionId='sec001', sectionName='intro', content='alpha script', duration=40)
            ],
            version=1,
            generationStatus='running',
            completedSections=1,
            totalSections=3,
            currentSectionId='sec002',
            currentSectionName='第二章',
            startedAt='2026-04-16T08:00:00Z',
        )

        response = self.client.get('/api/v1/scripts/script-001')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['data']['scriptId'], 'script-001')
        self.assertEqual(payload['data']['generationStatus'], 'running')
        self.assertEqual(payload['data']['completedSections'], 1)
        self.assertEqual(payload['data']['currentSectionName'], '第二章')
        mock_get_script.assert_called_once_with('script-001')

    def test_generate_script_old_payload_is_rejected(self) -> None:
        response = self.client.post(
            '/api/v1/lesson/generateScript',
            json={'parseId': 'parse-001', 'scriptType': 'detail'},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload['msg'], 'generateScript payload is invalid')
        self.assertIn('errors', payload['data'])

    @patch('backend.app.compat.router.generate_main_audio')
    def test_generate_audio_new_payload_uses_main_service(self, mock_generate_main_audio) -> None:
        mock_generate_main_audio.return_value = {
            'audioId': 'audio-001',
            'scriptId': 'script-001',
            'audioUrl': 'https://example.com/audio/audio-001.mp3',
            'audioInfo': {
                'totalDuration': 90,
                'fileSize': 1024,
                'format': 'mp3',
                'bitRate': 128000,
            },
            'sectionAudios': [
                {'sectionId': 'sec001', 'audioUrl': 'https://example.com/audio/audio-001.mp3', 'duration': 45}
            ],
            'taskStatus': 'completed',
            'status': 'success',
        }

        response = self.client.post(
            '/api/v1/lesson/generateAudio',
            json={
                'scriptId': 'script-001',
                'voiceType': 'female_standard',
                'audioFormat': 'mp3',
                'sectionIds': [],
                'enc': 'demo-signature',
                'time': '1700000000000',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['data']['audioId'], 'audio-001')
        self.assertEqual(payload['data']['scriptId'], 'script-001')
        self.assertEqual(payload['data']['taskStatus'], 'completed')

        mock_generate_main_audio.assert_called_once()
        request_payload = mock_generate_main_audio.call_args.args[0]
        self.assertEqual(request_payload.scriptId, 'script-001')
        self.assertEqual(request_payload.voiceType, 'female_standard')
        self.assertEqual(request_payload.audioFormat, 'mp3')
        self.assertEqual(request_payload.sectionIds, [])
        self.assertEqual(request_payload.enc, 'demo-signature')
        self.assertEqual(request_payload.time, '1700000000000')

    def test_generate_audio_old_payload_is_rejected(self) -> None:
        response = self.client.post(
            '/api/v1/lesson/generateAudio',
            json={'scriptId': 'script-001', 'voiceType': 'female_standard'},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload['msg'], 'generateAudio payload is invalid')
        self.assertIn('errors', payload['data'])
