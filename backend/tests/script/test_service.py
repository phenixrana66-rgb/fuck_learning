import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.cir.schemas import CIR, CirChapter, LessonNode
from backend.app.common.db import configure_database_url, reset_database_url, session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import clear_parse_tasks, create_parse_task, run_parse_task
from backend.app.parser.schemas import FileInfo, StructurePreview
from backend.app.script.schemas import GenerateScriptRequest, UpdateScriptRequest
from backend.app.script.service import clear_scripts, generate_script, get_script, update_script
from backend.chaoxing_db.models import ChapterAudioAsset, ChapterScript, ChapterScriptSection, ChapterSectionAudioAsset


class ScriptServiceTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    parse_payload: ParseRequest | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'script-test.db'}")
        clear_scripts()
        clear_parse_tasks()
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
        clear_scripts()
        clear_parse_tasks()
        reset_database_url()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    @patch('backend.app.script.service.generate_script_section_with_llm')
    def test_generate_script_starts_background_generation_and_persists_llm_content(
        self,
        mock_generate_script_section_with_llm,
        mock_parse_courseware,
        mock_build_cir,
    ) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = _build_single_node_cir()
        mock_generate_script_section_with_llm.return_value = {
            'content': '同学们好，我们先从人工智能的定义说起。人工智能强调让机器完成原本需要人类智能参与的任务。理解了这个定义，后面再看具体应用就顺畅了。',
            'summaryForNext': '这一部分已经说明了人工智能的基本定义，后面可以继续展开应用。',
        }
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)

        summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening='同学们好',
                enc='demo-signature',
            )
        )

        self.assertEqual(summary.generationStatus, 'running')
        self.assertEqual(summary.completedSections, 0)
        self.assertEqual(summary.scriptStructure[0].content, '')

        detail = self._wait_for_script_status(summary.scriptId, expected_status='completed')
        self.assertEqual(detail.generationStatus, 'completed')
        self.assertEqual(detail.completedSections, 1)
        self.assertIn('人工智能的定义', detail.scriptStructure[0].content)

    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    @patch('backend.app.script.service.generate_script_section_with_llm')
    def test_generate_script_marks_failure_when_section_generation_fails(
        self,
        mock_generate_script_section_with_llm,
        mock_parse_courseware,
        mock_build_cir,
    ) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = _build_single_node_cir()
        mock_generate_script_section_with_llm.side_effect = ApiError(
            code=502,
            msg='脚本生成 LLM 接口返回异常',
            status_code=502,
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)

        summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening=None,
                enc='demo-signature',
            )
        )
        detail = self._wait_for_script_status(summary.scriptId, expected_status='failed')

        self.assertEqual(detail.generationStatus, 'failed')
        self.assertIn('脚本生成 LLM 接口返回异常', detail.errorMsg or '')
        self.assertEqual(detail.scriptStructure[0].content, '')

    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    @patch('backend.app.script.service.generate_script_section_with_llm')
    def test_generate_script_uses_completed_parse_result(self, mock_generate_script_section_with_llm, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId='cw-course-001',
            title='人工智能导论',
            chapters=[
                CirChapter(
                    chapterId='course-001-chap-001',
                    chapterName='第一章',
                    nodes=[
                        LessonNode(nodeId='node-01-01', nodeName='什么是人工智能', pageRefs=[1, 2], keyPoints=['定义', '目标'], summary='介绍人工智能的基础定义。'),
                        LessonNode(nodeId='node-01-02', nodeName='人工智能的应用', pageRefs=[3], keyPoints=['案例'], summary='说明人工智能在课堂中的使用场景。'),
                    ],
                )
            ],
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)

        mock_generate_script_section_with_llm.side_effect = [
            {
                'content': '同学们好，先把人工智能的定义说清楚。简单来说，它是让机器去完成通常需要人类智能参与的任务。把这个起点抓住，后面再看应用就容易理解了。',
                'summaryForNext': '这一部分已经讲清了人工智能的定义，接下来可以进入应用场景。',
            },
            {
                'content': '有了前面的定义，我们再看人工智能的应用。课堂里常见的应用包括智能问答、作业分析和学习推荐，这些例子能帮助大家把概念落到实际场景中。到这里，这一章的主线就完整了。',
                'summaryForNext': '人工智能的应用场景已经交代清楚。',
            },
        ]
        summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening='同学们好，今天我们先看人工智能的核心概念。',
                enc='demo-signature',
            )
        )

        detail = self._wait_for_script_status(summary.scriptId, expected_status='completed')
        self.assertEqual(len(detail.scriptStructure), 2)
        self.assertEqual(detail.scriptStructure[0].relatedPage, '1-2')
        self.assertEqual(detail.scriptStructure[1].keyPoints, ['案例'])
        self.assertEqual(detail.completedSections, 2)

    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_generate_script_uses_fallback_when_parse_has_no_nodes(self, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(coursewareId='cw-course-001', title='人工智能导论', chapters=[])
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)

        summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening='同学们好，下面我们开始。',
                enc='demo-signature',
            )
        )

        self.assertEqual(summary.generationStatus, 'completed')
        self.assertEqual(len(summary.scriptStructure), 1)
        self.assertIn('暂时还没有抽取出可直接生成脚本的章节节点', summary.scriptStructure[0].content)

    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    def test_generate_script_rejects_non_completed_parse(self, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(coursewareId='cw-course-001', title='demo', chapters=[])
        accepted = create_parse_task(parse_payload)

        with self.assertRaises(ApiError) as context:
            generate_script(
                GenerateScriptRequest(
                    parseId=accepted.parseId,
                    teachingStyle='standard',
                    speechSpeed='normal',
                    customOpening=None,
                    enc='demo-signature',
                )
            )

        self.assertEqual(context.exception.status_code, 409)

    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    @patch('backend.app.script.service.generate_script_section_with_llm')
    def test_generated_script_survives_service_reload(self, mock_generate_script_section_with_llm, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = _build_single_node_cir()
        mock_generate_script_section_with_llm.return_value = {
            'content': '这节课先把人工智能的定义说清楚，后面再看应用就更容易理解。',
            'summaryForNext': '人工智能定义已经讲完。',
        }
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening=None,
                enc='demo-signature',
            )
        )

        detail = self._wait_for_script_status(summary.scriptId, expected_status='completed')
        reloaded = get_script(summary.scriptId)

        self.assertEqual(reloaded.scriptId, detail.scriptId)
        self.assertEqual(reloaded.scriptStructure[0].sectionName, '什么是人工智能')

    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    @patch('backend.app.script.service.generate_script_section_with_llm')
    def test_update_script_increments_version(self, mock_generate_script_section_with_llm, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = _build_single_node_cir()
        mock_generate_script_section_with_llm.return_value = {
            'content': '先把人工智能的定义讲清楚，再继续往后展开。',
            'summaryForNext': '人工智能定义已经讲完。',
        }
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening=None,
                enc='demo-signature',
            )
        )
        detail = self._wait_for_script_status(summary.scriptId, expected_status='completed')

        updated = update_script(
            summary.scriptId,
            UpdateScriptRequest(scriptStructure=detail.scriptStructure, versionRemark='demo', enc='demo-signature'),
        )

        self.assertEqual(updated.version, 2)
        self.assertEqual(get_script(summary.scriptId).version, 2)

    @patch('backend.app.courseware.service.build_cir')
    @patch('backend.app.courseware.service.parse_courseware')
    @patch('backend.app.script.service.generate_script_section_with_llm')
    def test_update_script_preserves_existing_section_audio_links(self, mock_generate_script_section_with_llm, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName='demo.pptx', fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = _build_single_node_cir()
        mock_generate_script_section_with_llm.return_value = {
            'content': '先把人工智能的定义讲清楚，再继续往后展开。',
            'summaryForNext': '人工智能定义已经讲完。',
        }
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle='standard',
                speechSpeed='normal',
                customOpening=None,
                enc='demo-signature',
            )
        )
        detail = self._wait_for_script_status(summary.scriptId, expected_status='completed')

        with session_scope() as db:
            script = db.query(ChapterScript).filter(ChapterScript.script_no == summary.scriptId).first()
            self.assertIsNotNone(script)
            section = (
                db.query(ChapterScriptSection)
                .filter(ChapterScriptSection.script_id == script.id, ChapterScriptSection.section_code == detail.scriptStructure[0].sectionId)
                .first()
            )
            self.assertIsNotNone(section)
            audio_asset = ChapterAudioAsset(
                course_id=script.course_id,
                chapter_id=script.chapter_id,
                script_id=script.id,
                voice_type='female_standard',
                audio_format='mp3',
                audio_url='http://test/audio.mp3',
                total_duration_sec=20,
                file_size=1024,
                bit_rate=128,
                status='generated',
            )
            db.add(audio_asset)
            db.flush()
            section_audio = ChapterSectionAudioAsset(
                audio_asset_id=audio_asset.id,
                course_id=script.course_id,
                chapter_id=script.chapter_id,
                script_id=script.id,
                script_section_id=section.id,
                voice_type='female_standard',
                audio_format='mp3',
                audio_url='http://test/audio-section.mp3',
                duration_sec=20,
                file_size=1024,
                bit_rate=128,
                status='generated',
                sort_no=0,
            )
            db.add(section_audio)
            db.flush()
            original_section_id = section.id
            section_audio_id = section_audio.id

        updated = update_script(
            summary.scriptId,
            UpdateScriptRequest(scriptStructure=detail.scriptStructure, versionRemark='preserve-audio-links', enc='demo-signature'),
        )

        with session_scope() as db:
            section = (
                db.query(ChapterScriptSection)
                .join(ChapterScript, ChapterScriptSection.script_id == ChapterScript.id)
                .filter(ChapterScript.script_no == summary.scriptId, ChapterScriptSection.section_code == detail.scriptStructure[0].sectionId)
                .first()
            )
            section_audio = db.query(ChapterSectionAudioAsset).filter(ChapterSectionAudioAsset.id == section_audio_id).first()
            section_id = section.id if section is not None else None
            section_audio_section_id = section_audio.script_section_id if section_audio is not None else None

        self.assertEqual(updated.version, 2)
        self.assertIsNotNone(section_id)
        self.assertEqual(section_id, original_section_id)
        self.assertIsNotNone(section_audio)
        self.assertEqual(section_audio_section_id, original_section_id)

    def _wait_for_script_status(self, script_id: str, expected_status: str, timeout_seconds: float = 2.0):
        deadline = time.time() + timeout_seconds
        last_detail = None
        while time.time() < deadline:
            last_detail = get_script(script_id)
            if last_detail.generationStatus == expected_status:
                return last_detail
            time.sleep(0.05)
        self.fail(f'script {script_id} did not reach status {expected_status}, last status={getattr(last_detail, "generationStatus", None)}')


def _build_single_node_cir() -> CIR:
    return CIR(
        coursewareId='cw-course-001',
        title='人工智能导论',
        chapters=[
            CirChapter(
                chapterId='course-001-chap-001',
                chapterName='第一章',
                nodes=[
                    LessonNode(
                        nodeId='node-01-01',
                        nodeName='什么是人工智能',
                        pageRefs=[1],
                        keyPoints=['定义'],
                        summary='介绍人工智能。',
                    )
                ],
            )
        ],
    )


if __name__ == '__main__':
    unittest.main()


