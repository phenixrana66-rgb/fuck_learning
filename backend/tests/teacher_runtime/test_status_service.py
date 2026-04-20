import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

from backend.app.cir.schemas import CIR
from backend.app.common.db import configure_database_url, reset_database_url, session_scope
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import clear_parse_tasks, create_parse_task, run_parse_task
from backend.app.lesson.schemas import GenerateAudioRequest
from backend.app.lesson.service import generate_audio
from backend.app.lesson.tts_client import TtsSynthesisResult
from backend.app.parser.schemas import FileInfo, StructurePreview
from backend.app.script.schemas import GenerateScriptRequest
from backend.app.script.service import clear_scripts, generate_script
from backend.app.teacher_runtime.status_service import (
    get_lesson_status,
    list_audios_by_script,
    list_courseware_assets,
    list_scripts_by_parse,
)


class TeacherRuntimeStatusServiceTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'teacher-runtime-status-test.db'}")
        clear_scripts()
        clear_parse_tasks()

    def tearDown(self) -> None:
        clear_scripts()
        clear_parse_tasks()
        reset_database_url()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_list_courseware_assets_returns_versioned_history(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        mock_parse_courseware.side_effect = self._mock_parse_courseware
        mock_build_cir.return_value = CIR(coursewareId='cw-course-001', title='demo', chapters=[])
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / 'voice-cache'
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=1800,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )

        first_parse = self._create_completed_parse('pptx', 'file:///tmp/demo-v1.pptx')
        second_parse = self._create_completed_parse('pdf', 'file:///tmp/demo-v2.pdf')
        script_summary = generate_script(
            GenerateScriptRequest(
                parseId=first_parse,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening=None,
                enc='demo-signature',
            )
        )
        generate_audio(
            GenerateAudioRequest(
                scriptId=script_summary.scriptId,
                voiceType='female_standard',
                audioFormat='mp3',
                sectionIds=[],
                enc='demo-signature',
            ),
            base_url='http://testserver/',
        )

        with session_scope() as db:
            data = list_courseware_assets(db, 'course-001')

        self.assertEqual(data['courseId'], 'course-001')
        self.assertTrue(data['chapterId'])
        self.assertEqual(len(data['assets']), 2)
        self.assertEqual([item['versionNo'] for item in data['assets']], [2, 1])
        self.assertEqual(data['assets'][0]['fileName'], 'demo-v2.pdf')
        self.assertEqual(data['assets'][0]['parseTasks'][0]['parseId'], second_parse)
        self.assertEqual(data['assets'][1]['parseTasks'][0]['parseId'], first_parse)
        self.assertEqual(data['assets'][1]['parseTasks'][0]['scriptCount'], 1)
        self.assertEqual(data['assets'][1]['parseTasks'][0]['audioCount'], 1)

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_list_scripts_by_parse_returns_selected_parse_scripts(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        mock_parse_courseware.side_effect = self._mock_parse_courseware
        mock_build_cir.return_value = CIR(coursewareId='cw-course-001', title='demo', chapters=[])
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / 'voice-cache'
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=1800,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )

        target_parse = self._create_completed_parse('pptx', 'file:///tmp/demo-v1.pptx')
        self._create_completed_parse('pdf', 'file:///tmp/demo-v2.pdf')
        script_summary = generate_script(
            GenerateScriptRequest(
                parseId=target_parse,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening=None,
                enc='demo-signature',
            )
        )
        generate_audio(
            GenerateAudioRequest(
                scriptId=script_summary.scriptId,
                voiceType='female_standard',
                audioFormat='mp3',
                sectionIds=[],
                enc='demo-signature',
            ),
            base_url='http://testserver/',
        )

        with session_scope() as db:
            data = list_scripts_by_parse(db, target_parse)

        self.assertEqual(data['parseId'], target_parse)
        self.assertEqual(len(data['scripts']), 1)
        self.assertEqual(data['scripts'][0]['scriptId'], script_summary.scriptId)
        self.assertEqual(data['scripts'][0]['audioCount'], 1)
        self.assertEqual(data['fileName'], 'demo-v1.pptx')

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_list_audios_by_script_returns_existing_audio_versions(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        mock_parse_courseware.side_effect = self._mock_parse_courseware
        mock_build_cir.return_value = CIR(coursewareId='cw-course-001', title='demo', chapters=[])
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / 'voice-cache'
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=1800,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )

        target_parse = self._create_completed_parse('pptx', 'file:///tmp/demo-v1.pptx')
        script_summary = generate_script(
            GenerateScriptRequest(
                parseId=target_parse,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening=None,
                enc='demo-signature',
            )
        )
        generate_audio(
            GenerateAudioRequest(
                scriptId=script_summary.scriptId,
                voiceType='female_standard',
                audioFormat='mp3',
                sectionIds=[],
                enc='demo-signature',
            ),
            base_url='http://testserver/',
        )
        generate_audio(
            GenerateAudioRequest(
                scriptId=script_summary.scriptId,
                voiceType='male_standard',
                audioFormat='mp3',
                sectionIds=[],
                enc='demo-signature',
            ),
            base_url='http://testserver/',
        )

        with session_scope() as db:
            data = list_audios_by_script(db, script_summary.scriptId)

        self.assertEqual(data['scriptId'], script_summary.scriptId)
        self.assertEqual(data['parseId'], target_parse)
        self.assertEqual(len(data['audios']), 2)
        self.assertEqual(data['audios'][0]['voiceType'], 'male_standard')
        self.assertEqual(data['audios'][1]['voiceType'], 'female_standard')
        self.assertTrue(all(item['audioUrl'].startswith('/cache/voice/') for item in data['audios']))

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_get_lesson_status_normalizes_testserver_audio_url(
        self,
        mock_parse_courseware,
        mock_build_cir,
        mock_synthesize_speech,
        mock_get_voice_cache_dir,
    ) -> None:
        mock_parse_courseware.side_effect = self._mock_parse_courseware
        mock_build_cir.return_value = CIR(coursewareId='cw-course-001', title='demo', chapters=[])
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / 'voice-cache'
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=1800,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )

        target_parse = self._create_completed_parse('pptx', 'file:///tmp/demo-v1.pptx')
        script_summary = generate_script(
            GenerateScriptRequest(
                parseId=target_parse,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening=None,
                enc='demo-signature',
            )
        )
        generate_audio(
            GenerateAudioRequest(
                scriptId=script_summary.scriptId,
                voiceType='female_standard',
                audioFormat='mp3',
                sectionIds=[],
                enc='demo-signature',
            ),
            base_url='http://testserver/',
        )

        with session_scope() as db:
            data = get_lesson_status(db, 'course-001')

        self.assertTrue(data['audio']['audioUrl'].startswith('/cache/voice/'))

    def _create_completed_parse(self, file_type: str, file_url: str) -> str:
        payload = ParseRequest(
            schoolId='school-001',
            userId='teacher-001',
            courseId='course-001',
            fileType=file_type,
            fileUrl=file_url,
            isExtractKeyPoint=True,
            enc='demo-signature',
        )
        accepted = create_parse_task(payload)
        run_parse_task(accepted.parseId, payload)
        return accepted.parseId

    def _mock_parse_courseware(self, *_args, **kwargs):
        file_url = kwargs.get('file_url') or (_args[1] if len(_args) > 1 else 'file:///tmp/demo.pptx')
        file_name = Path(urlparse(file_url).path).name or 'demo.pptx'
        return (
            FileInfo(fileName=file_name, fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
