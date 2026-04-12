import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.cir.schemas import CIR, CirChapter, LessonNode
from backend.app.common.db import configure_database_url, reset_database_url
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import create_parse_task, run_parse_task
from backend.app.parser.schemas import FileInfo, StructurePreview
from backend.app.script.schemas import GenerateScriptRequest, UpdateScriptRequest
from backend.app.script.service import clear_scripts, generate_script, get_script, update_script
from backend.app.tasks.repository import configure_task_storage, reset_task_storage
from backend.app.tasks.service import clear_tasks


class ScriptServiceTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    parse_payload: ParseRequest | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_task_storage(Path(self.temp_dir.name) / "logs")
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'script-test.db'}")
        clear_tasks()
        clear_scripts()
        self.parse_payload = ParseRequest(
            schoolId="school-001",
            userId="teacher-001",
            courseId="course-001",
            fileType="ppt",
            fileUrl="file:///tmp/demo.pptx",
            isExtractKeyPoint=True,
            enc="demo-signature",
        )

    def tearDown(self) -> None:
        clear_tasks()
        clear_scripts()
        reset_database_url()
        reset_task_storage()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_generated_script_survives_service_reload(self, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId="cw-course-001",
            title="人工智能导论",
            chapters=[CirChapter(chapterId="course-001-chap-001", chapterName="第一章", nodes=[LessonNode(nodeId="node-01-01", nodeName="什么是人工智能", pageRefs=[1], keyPoints=["定义"], summary="介绍人工智能。")])],
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle="standard",
                speechSpeed="normal",
                customOpening=None,
                enc="demo-signature",
            )
        )

        reloaded = get_script(summary.scriptId)

        self.assertEqual(reloaded.scriptId, summary.scriptId)
        self.assertEqual(reloaded.scriptStructure[0].sectionName, "什么是人工智能")

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_generate_script_uses_completed_parse_result(self, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId="cw-course-001",
            title="人工智能导论",
            chapters=[
                CirChapter(
                    chapterId="course-001-chap-001",
                    chapterName="第一章",
                    nodes=[
                        LessonNode(nodeId="node-01-01", nodeName="什么是人工智能", pageRefs=[1, 2], keyPoints=["定义", "目标"], summary="介绍人工智能的基础定义。"),
                        LessonNode(nodeId="node-01-02", nodeName="人工智能的应用", pageRefs=[3], keyPoints=["案例"], summary="说明人工智能在课堂中的使用场景。"),
                    ],
                )
            ],
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)

        summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle="standard",
                speechSpeed="normal",
                customOpening="同学们好，今天我们先看人工智能的核心概念。",
                enc="demo-signature",
            )
        )

        self.assertEqual(len(summary.scriptStructure), 2)
        self.assertEqual(summary.scriptStructure[0].sectionName, "什么是人工智能")
        self.assertEqual(summary.scriptStructure[0].relatedChapterId, "course-001-chap-001")
        self.assertEqual(summary.scriptStructure[0].relatedPage, "1-2")
        self.assertIn("人工智能", summary.scriptStructure[0].content)
        self.assertEqual(summary.scriptStructure[1].keyPoints, ["案例"])

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_generate_script_rejects_non_completed_parse(self, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(coursewareId="cw-course-001", title="demo", chapters=[])
        accepted = create_parse_task(parse_payload)

        with self.assertRaises(ApiError) as context:
            generate_script(
                GenerateScriptRequest(
                    parseId=accepted.parseId,
                    teachingStyle="standard",
                    speechSpeed="normal",
                    customOpening=None,
                    enc="demo-signature",
                )
            )

        self.assertEqual(context.exception.status_code, 409)

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_update_script_increments_version(self, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(
            coursewareId="cw-course-001",
            title="人工智能导论",
            chapters=[CirChapter(chapterId="course-001-chap-001", chapterName="第一章", nodes=[LessonNode(nodeId="node-01-01", nodeName="什么是人工智能", pageRefs=[1], keyPoints=[], summary="介绍人工智能。")])],
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        summary = generate_script(
            GenerateScriptRequest(
                parseId=accepted.parseId,
                teachingStyle="standard",
                speechSpeed="normal",
                customOpening=None,
                enc="demo-signature",
            )
        )

        updated = update_script(
            summary.scriptId,
            UpdateScriptRequest(scriptStructure=summary.scriptStructure, versionRemark="demo", enc="demo-signature"),
        )

        self.assertEqual(updated.version, 2)
        self.assertEqual(get_script(summary.scriptId).version, 2)
