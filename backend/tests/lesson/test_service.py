import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.cir.schemas import CIR, CirChapter, LessonNode
from backend.app.common.db import configure_database_url, reset_database_url, session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import clear_parse_tasks, create_parse_task, run_parse_task
from backend.app.lesson.schemas import GenerateAudioRequest, PlayRequest, PublishRequest
from backend.app.lesson.service import clear_lessons, generate_audio, play_lesson, publish_lesson
from backend.app.lesson.tts_client import TtsSynthesisResult
from backend.app.parser.schemas import FileInfo, StructurePreview
from backend.app.script.schemas import GenerateScriptRequest
from backend.app.script.service import clear_scripts, generate_script, get_script as get_script_detail
from backend.app.tasks.repository import configure_task_storage, reset_task_storage
from backend.app.tasks.service import clear_tasks
from backend.chaoxing_db.models import ChapterAudioAsset, ChapterScript


class LessonServiceTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    parse_payload: ParseRequest | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_task_storage(Path(self.temp_dir.name) / 'logs')
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'lesson-test.db'}")
        clear_tasks()
        clear_scripts()
        clear_parse_tasks()
        clear_lessons()
        self.parse_payload = ParseRequest(
            schoolId='school-001',
            userId='teacher-001',
            courseId='course-001',
            fileType='ppt',
            fileUrl='file:///tmp/demo.pptx',
            isExtractKeyPoint=True,
            enc='demo-signature',
        )

    def tearDown(self) -> None:
        clear_tasks()
        clear_scripts()
        clear_parse_tasks()
        clear_lessons()
        reset_database_url()
        reset_task_storage()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_generate_audio_publish_and_play_form_demo_chain(self, mock_parse_courseware, mock_build_cir, mock_synthesize_speech, mock_get_voice_cache_dir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        voice_cache_dir = Path(self.temp_dir.name) / 'voice-cache'
        mock_get_voice_cache_dir.return_value = voice_cache_dir
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=3500,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId='cw-course-001',
            title='??????',
            chapters=[
                CirChapter(
                    chapterId='course-001-chap-001',
                    chapterName='???',
                    nodes=[
                        LessonNode(nodeId='node-01-01', nodeName='???????', pageRefs=[1, 2], keyPoints=['??'], summary='????????????'),
                        LessonNode(nodeId='node-01-02', nodeName='???????', pageRefs=[3], keyPoints=['??'], summary='????????????????'),
                    ],
                )
            ],
        )
        script_summary = self._create_script_summary(parse_payload)
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        for index, section in enumerate(script_detail.scriptStructure[:2], start=1):
            section.content = f'short audio test section {index}'
        section_ids = [section.sectionId for section in script_detail.scriptStructure[:2]]

        with patch('backend.app.lesson.service.get_script', return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(
                    scriptId=script_summary.scriptId,
                    voiceType='female_standard',
                    audioFormat='mp3',
                    sectionIds=section_ids,
                    enc='demo-signature',
                ),
                base_url='http://testserver/',
            )
            publish = publish_lesson(
                PublishRequest(
                    coursewareId='cw-course-001',
                    scriptId=script_summary.scriptId,
                    audioId=audio['audioId'],
                    publisherId='teacher-demo',
                    enc='demo-signature',
                )
            )
        play = play_lesson(
            PlayRequest(
                lessonId=publish['lessonId'],
                userId='student-demo',
                resumeContext={'currentSectionId': script_detail.scriptStructure[0].sectionId},
                enc='demo-signature',
            )
        )

        with session_scope() as db:
            stored_audio = db.query(ChapterAudioAsset).join(ChapterScript).filter(ChapterScript.script_no == script_summary.scriptId).first()

        generated_filename = audio['audioUrl'].rsplit('/', 1)[-1]
        generated_file = voice_cache_dir / generated_filename

        self.assertIsNotNone(stored_audio)
        self.assertEqual(audio['taskStatus'], 'completed')
        self.assertEqual(audio['status'], 'success')
        self.assertEqual(audio['scriptId'], script_summary.scriptId)
        self.assertEqual(len(audio['sectionAudios']), len(section_ids))
        self.assertTrue(audio['audioUrl'].startswith('http://testserver/cache/voice/'))
        self.assertTrue(generated_file.exists())
        self.assertEqual(audio['audioInfo']['fileSize'], generated_file.stat().st_size)
        self.assertEqual(publish['publishStatus'], 'published')
        self.assertEqual(play['nodeSequence'], ['node-01-01', 'node-01-02'])
        self.assertEqual(play['scriptRefs'][0]['scriptId'], script_summary.scriptId)
        self.assertEqual(play['audioRefs'][0]['audioId'], audio['audioId'])

    @patch('backend.app.lesson.voice_storage.get_voice_cache_dir')
    @patch('backend.app.lesson.service.synthesize_speech')
    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_publish_rejects_mismatched_courseware(self, mock_parse_courseware, mock_build_cir, mock_synthesize_speech, mock_get_voice_cache_dir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_get_voice_cache_dir.return_value = Path(self.temp_dir.name) / 'voice-cache'
        mock_synthesize_speech.return_value = TtsSynthesisResult(
            audio_bytes=b'ID3demo-audio',
            duration_ms=1800,
            reqid='req-001',
            log_id='log-001',
            voice_type='volcano-voice',
        )
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId='cw-course-001',
            title='??????',
            chapters=[CirChapter(chapterId='course-001-chap-001', chapterName='???', nodes=[LessonNode(nodeId='node-01-01', nodeName='???????', pageRefs=[1], keyPoints=[], summary='???????')])],
        )
        script_summary = self._create_script_summary(parse_payload)
        script_detail = get_script_detail(script_summary.scriptId).model_copy(deep=True)
        for index, section in enumerate(script_detail.scriptStructure[:2], start=1):
            section.content = f'short audio mismatch section {index}'
        section_ids = [section.sectionId for section in script_detail.scriptStructure[:2]]
        with patch('backend.app.lesson.service.get_script', return_value=script_detail):
            audio = generate_audio(
                GenerateAudioRequest(scriptId=script_summary.scriptId, voiceType='female_standard', audioFormat='mp3', sectionIds=section_ids, enc='demo-signature'),
                base_url='http://testserver/',
            )

            with self.assertRaises(ApiError) as context:
                publish_lesson(
                    PublishRequest(
                        coursewareId='cw-course-999',
                        scriptId=script_summary.scriptId,
                        audioId=audio['audioId'],
                        publisherId='teacher-demo',
                        enc='demo-signature',
                    )
                )

        self.assertEqual(context.exception.status_code, 409)

    def test_play_rejects_missing_lesson(self) -> None:
        with self.assertRaises(ApiError) as context:
            play_lesson(PlayRequest(lessonId='lesson-missing', userId='student-demo', resumeContext=None, enc='demo-signature'))

        self.assertEqual(context.exception.status_code, 404)

    def _create_script_summary(self, parse_payload: ParseRequest):
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        return generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening=None,
                enc='demo-signature',
            )
        )
