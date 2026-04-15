import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.cir.schemas import CIR, CirChapter, LessonNode
from backend.app.common.db import configure_database_url, reset_database_url, session_scope
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import clear_parse_tasks, create_parse_task, run_parse_task
from backend.app.parser.schemas import FileInfo, StructurePreview
from backend.app.script.repository import clear_script_records, load_script, save_script
from backend.app.script.schemas import ScriptDetail, ScriptSection
from backend.chaoxing_db.models import ChapterScript, ChapterScriptSection


class ScriptRepositoryTestCase(unittest.TestCase):
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    parse_payload: ParseRequest | None = None

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_database_url(f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'script-repository-test.db'}")
        clear_script_records()
        clear_parse_tasks()
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
        clear_script_records()
        clear_parse_tasks()
        reset_database_url()
        assert self.temp_dir is not None
        self.temp_dir.cleanup()

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_save_script_persists_to_teacher_content_tables(self, mock_parse_courseware, mock_build_cir) -> None:
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
                        LessonNode(
                            nodeId="node-01-01",
                            nodeName="什么是人工智能",
                            pageRefs=[1, 2],
                            keyPoints=["定义", "目标"],
                            summary="介绍人工智能的基础定义。",
                        )
                    ],
                )
            ],
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)

        script = ScriptDetail(
            scriptId="script-repo-001",
            parseId=accepted.parseId,
            teachingStyle="standard",
            speechSpeed="normal",
            scriptStructure=[
                ScriptSection(
                    sectionId="sec001",
                    sectionName="什么是人工智能",
                    content="同学们好，这一节我们先理解人工智能的定义。",
                    duration=43,
                    relatedPage="1-2",
                )
            ],
            version=1,
        )

        save_script(script)
        reloaded = load_script("script-repo-001")

        with session_scope() as db:
            stored_script = db.query(ChapterScript).filter(ChapterScript.script_no == "script-repo-001").first()
            stored_section = db.query(ChapterScriptSection).join(ChapterScript).filter(ChapterScript.script_no == "script-repo-001").first()

        self.assertIsNotNone(stored_script)
        self.assertIsNotNone(stored_section)
        self.assertIsNotNone(reloaded)
        assert reloaded is not None
        self.assertEqual(reloaded.parseId, accepted.parseId)
        self.assertEqual(reloaded.scriptStructure[0].sectionName, "什么是人工智能")
        self.assertEqual(reloaded.scriptStructure[0].relatedChapterId, "course-001-chap-001")
        self.assertEqual(reloaded.scriptStructure[0].keyPoints, ["定义", "目标"])

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_save_script_rejects_non_completed_parse(self, mock_parse_courseware, mock_build_cir) -> None:
        parse_payload = self.parse_payload
        assert parse_payload is not None
        mock_parse_courseware.return_value = (
            FileInfo(fileName="demo.pptx", fileSize=1024, pageCount=8),
            StructurePreview(chapters=[]),
        )
        mock_build_cir.return_value = CIR(coursewareId="cw-course-001", title="人工智能导论", chapters=[])
        accepted = create_parse_task(parse_payload)

        with self.assertRaises(ApiError) as context:
            save_script(
                ScriptDetail(
                    scriptId="script-repo-pending",
                    parseId=accepted.parseId,
                    teachingStyle="standard",
                    speechSpeed="normal",
                    scriptStructure=[
                        ScriptSection(
                            sectionId="sec001",
                            sectionName="课件导入",
                            content="讲稿内容",
                            duration=40,
                        )
                    ],
                    version=1,
                )
            )

        self.assertEqual(context.exception.status_code, 409)

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_save_script_rejects_parse_id_mismatch_for_existing_script(self, mock_parse_courseware, mock_build_cir) -> None:
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
                    nodes=[LessonNode(nodeId="node-01-01", nodeName="什么是人工智能", pageRefs=[1], keyPoints=["定义"], summary="介绍人工智能。")],
                )
            ],
        )
        first_parse = create_parse_task(parse_payload)
        run_parse_task(first_parse.parseId, parse_payload)
        second_parse = create_parse_task(parse_payload)
        run_parse_task(second_parse.parseId, parse_payload)

        save_script(
            ScriptDetail(
                scriptId="script-repo-003",
                parseId=first_parse.parseId,
                teachingStyle="standard",
                speechSpeed="normal",
                scriptStructure=[
                    ScriptSection(
                        sectionId="sec001",
                        sectionName="什么是人工智能",
                        content="第一次保存",
                        duration=40,
                    )
                ],
                version=1,
            )
        )

        with self.assertRaises(ApiError) as context:
            save_script(
                ScriptDetail(
                    scriptId="script-repo-003",
                    parseId=second_parse.parseId,
                    teachingStyle="standard",
                    speechSpeed="normal",
                    scriptStructure=[
                        ScriptSection(
                            sectionId="sec001",
                            sectionName="什么是人工智能",
                            content="第二次保存",
                            duration=45,
                        )
                    ],
                    version=2,
                )
            )

        self.assertEqual(context.exception.status_code, 409)

    @patch("backend.app.courseware.service.build_cir")
    @patch("backend.app.courseware.service.parse_courseware")
    def test_clear_script_records_removes_teacher_content_script_rows(self, mock_parse_courseware, mock_build_cir) -> None:
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
                    nodes=[LessonNode(nodeId="node-01-01", nodeName="什么是人工智能", pageRefs=[1], keyPoints=["定义"], summary="介绍人工智能。")],
                )
            ],
        )
        accepted = create_parse_task(parse_payload)
        run_parse_task(accepted.parseId, parse_payload)
        save_script(
            ScriptDetail(
                scriptId="script-repo-002",
                parseId=accepted.parseId,
                teachingStyle="standard",
                speechSpeed="normal",
                scriptStructure=[
                    ScriptSection(
                        sectionId="sec001",
                        sectionName="什么是人工智能",
                        content="讲稿内容",
                        duration=40,
                    )
                ],
                version=1,
            )
        )

        clear_script_records()

        with session_scope() as db:
            stored_script = db.query(ChapterScript).filter(ChapterScript.script_no == "script-repo-002").first()
            stored_sections = db.query(ChapterScriptSection).all()

        self.assertIsNone(stored_script)
        self.assertEqual(stored_sections, [])
