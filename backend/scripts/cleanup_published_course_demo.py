from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.common.db import session_scope
from backend.chaoxing_db.models import (
    ChapterAudioAsset,
    ChapterKnowledgeNode,
    ChapterParseResult,
    ChapterParseTask,
    ChapterPptAsset,
    ChapterPractice,
    ChapterPracticeItem,
    ChapterScript,
    ChapterScriptSection,
    ChapterSectionAudioAsset,
    Course,
    CourseChapter,
    CourseClass,
    CourseMember,
    CoursePlatformBinding,
    Lesson,
    LessonSection,
    LessonSectionAnchor,
    LessonSectionKnowledgePoint,
    LessonSectionPage,
    LessonUnit,
    Notification,
    NotificationReceipt,
    ProgressAdjustRecord,
    ProgressTrackLog,
    QAAnswer,
    QAAnswerTrace,
    QAMessage,
    QAMessageKnowledgeRef,
    QASession,
    ResumeRecord,
    StudentLessonProgress,
    StudentPageProgress,
    StudentPracticeAnswer,
    StudentPracticeAttempt,
    StudentSectionMasteryLog,
    StudentSectionProgress,
    VoiceTranscript,
)


DEFAULT_COURSE_ID = 1
DEFAULT_COURSE_CODE = "C10001"
DEFAULT_COURSE_NAME = "材料力学智慧课程 (15期2025春夏)"


@dataclass
class CleanupContext:
    course_id: int
    lesson_ids: list[int] = field(default_factory=list)
    lesson_unit_ids: list[int] = field(default_factory=list)
    lesson_section_ids: list[int] = field(default_factory=list)
    lesson_page_ids: list[int] = field(default_factory=list)
    lesson_anchor_ids: list[int] = field(default_factory=list)
    lesson_point_ids: list[int] = field(default_factory=list)
    chapter_ids: list[int] = field(default_factory=list)
    parse_task_ids: list[int] = field(default_factory=list)
    parse_result_ids: list[int] = field(default_factory=list)
    ppt_asset_ids: list[int] = field(default_factory=list)
    script_ids: list[int] = field(default_factory=list)
    script_section_ids: list[int] = field(default_factory=list)
    audio_asset_ids: list[int] = field(default_factory=list)
    section_audio_asset_ids: list[int] = field(default_factory=list)
    practice_ids: list[int] = field(default_factory=list)
    practice_item_ids: list[int] = field(default_factory=list)
    practice_attempt_ids: list[int] = field(default_factory=list)
    qa_session_ids: list[int] = field(default_factory=list)
    qa_message_ids: list[int] = field(default_factory=list)
    qa_answer_ids: list[int] = field(default_factory=list)
    notification_ids: list[int] = field(default_factory=list)
    course_class_ids: list[int] = field(default_factory=list)


@dataclass
class CleanupStats:
    course_id: int
    course_code: str
    course_name: str
    lesson_ids: list[int] = field(default_factory=list)
    chapter_ids: list[int] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    applied_deletes: dict[str, int] = field(default_factory=dict)


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _collect_ids(db, model, field, predicate) -> list[int]:
    return [int(value) for (value,) in db.query(field).filter(predicate).all()]


def _delete_by_ids(db, model, field, ids: list[int]) -> int:
    if not ids:
        return 0
    return db.query(model).filter(field.in_(ids)).delete(synchronize_session=False)


def _count_by_ids(db, model, field, ids: list[int]) -> int:
    if not ids:
        return 0
    return db.query(model).filter(field.in_(ids)).count()


def _resolve_course(db, *, course_id: int, course_code: str, course_name: str) -> Course:
    course = (
        db.query(Course)
        .filter(
            Course.id == course_id,
            Course.course_code == course_code,
            Course.course_name == course_name,
        )
        .first()
    )
    if course is None:
        raise SystemExit(
            "target course not found with exact identity: "
            f"id={course_id}, code={course_code}, name={course_name}"
        )
    return course


def _build_context(db, course_id: int) -> CleanupContext:
    context = CleanupContext(course_id=course_id)

    context.lesson_ids = _collect_ids(db, Lesson, Lesson.id, Lesson.course_id == course_id)
    context.lesson_unit_ids = _collect_ids(db, LessonUnit, LessonUnit.id, LessonUnit.course_id == course_id)
    context.lesson_section_ids = _collect_ids(db, LessonSection, LessonSection.id, LessonSection.course_id == course_id)
    context.lesson_page_ids = _collect_ids(
        db, LessonSectionPage, LessonSectionPage.id, LessonSectionPage.section_id.in_(context.lesson_section_ids or [-1])
    )
    context.lesson_anchor_ids = _collect_ids(
        db, LessonSectionAnchor, LessonSectionAnchor.id, LessonSectionAnchor.section_id.in_(context.lesson_section_ids or [-1])
    )
    context.lesson_point_ids = _collect_ids(
        db,
        LessonSectionKnowledgePoint,
        LessonSectionKnowledgePoint.id,
        LessonSectionKnowledgePoint.section_id.in_(context.lesson_section_ids or [-1]),
    )

    context.chapter_ids = _collect_ids(db, CourseChapter, CourseChapter.id, CourseChapter.course_id == course_id)
    context.parse_task_ids = _collect_ids(
        db, ChapterParseTask, ChapterParseTask.id, ChapterParseTask.course_id == course_id
    )
    context.parse_result_ids = _collect_ids(
        db, ChapterParseResult, ChapterParseResult.id, ChapterParseResult.course_id == course_id
    )
    context.ppt_asset_ids = _collect_ids(db, ChapterPptAsset, ChapterPptAsset.id, ChapterPptAsset.course_id == course_id)
    context.script_ids = _collect_ids(db, ChapterScript, ChapterScript.id, ChapterScript.course_id == course_id)
    context.script_section_ids = _collect_ids(
        db,
        ChapterScriptSection,
        ChapterScriptSection.id,
        ChapterScriptSection.script_id.in_(context.script_ids or [-1]),
    )
    context.audio_asset_ids = _collect_ids(
        db, ChapterAudioAsset, ChapterAudioAsset.id, ChapterAudioAsset.course_id == course_id
    )
    context.section_audio_asset_ids = _collect_ids(
        db,
        ChapterSectionAudioAsset,
        ChapterSectionAudioAsset.id,
        ChapterSectionAudioAsset.course_id == course_id,
    )

    context.practice_ids = _collect_ids(db, ChapterPractice, ChapterPractice.id, ChapterPractice.course_id == course_id)
    context.practice_item_ids = _collect_ids(
        db,
        ChapterPracticeItem,
        ChapterPracticeItem.id,
        ChapterPracticeItem.practice_id.in_(context.practice_ids or [-1]),
    )
    context.practice_attempt_ids = _collect_ids(
        db,
        StudentPracticeAttempt,
        StudentPracticeAttempt.id,
        StudentPracticeAttempt.course_id == course_id,
    )

    context.qa_session_ids = _collect_ids(db, QASession, QASession.id, QASession.course_id == course_id)
    context.qa_message_ids = _collect_ids(
        db, QAMessage, QAMessage.id, QAMessage.session_id.in_(context.qa_session_ids or [-1])
    )
    context.qa_answer_ids = _collect_ids(
        db, QAAnswer, QAAnswer.id, QAAnswer.session_id.in_(context.qa_session_ids or [-1])
    )

    context.notification_ids = _collect_ids(
        db, Notification, Notification.id, Notification.course_id == course_id
    )
    context.course_class_ids = _collect_ids(db, CourseClass, CourseClass.id, CourseClass.course_id == course_id)
    return context


def cleanup_course(*, course_id: int, course_code: str, course_name: str, apply: bool) -> CleanupStats:
    with session_scope() as db:
        course = _resolve_course(db, course_id=course_id, course_code=course_code, course_name=course_name)
        context = _build_context(db, course.id)
        stats = CleanupStats(
            course_id=course.id,
            course_code=course.course_code,
            course_name=course.course_name,
            lesson_ids=context.lesson_ids,
            chapter_ids=context.chapter_ids,
        )

        counts = stats.counts
        counts["course_platform_bindings"] = db.query(CoursePlatformBinding).filter(CoursePlatformBinding.course_id == course.id).count()
        counts["course_members"] = db.query(CourseMember).filter(CourseMember.course_id == course.id).count()
        counts["course_classes"] = len(context.course_class_ids)
        counts["course_chapters"] = len(context.chapter_ids)
        counts["lessons"] = len(context.lesson_ids)
        counts["lesson_units"] = len(context.lesson_unit_ids)
        counts["lesson_sections"] = len(context.lesson_section_ids)
        counts["lesson_section_pages"] = len(context.lesson_page_ids)
        counts["lesson_section_anchors"] = len(context.lesson_anchor_ids)
        counts["lesson_section_knowledge_points"] = len(context.lesson_point_ids)
        counts["student_lesson_progress"] = db.query(StudentLessonProgress).filter(StudentLessonProgress.course_id == course.id).count()
        counts["student_section_progress"] = db.query(StudentSectionProgress).filter(StudentSectionProgress.course_id == course.id).count()
        counts["student_page_progress"] = db.query(StudentPageProgress).filter(StudentPageProgress.course_id == course.id).count()
        counts["resume_records"] = db.query(ResumeRecord).filter(ResumeRecord.course_id == course.id).count()
        counts["progress_track_logs"] = db.query(ProgressTrackLog).filter(ProgressTrackLog.course_id == course.id).count()
        counts["progress_adjust_records"] = db.query(ProgressAdjustRecord).filter(ProgressAdjustRecord.course_id == course.id).count()
        counts["student_section_mastery_logs"] = db.query(StudentSectionMasteryLog).filter(StudentSectionMasteryLog.course_id == course.id).count()
        counts["notifications"] = len(context.notification_ids)
        counts["notification_receipts"] = _count_by_ids(
            db, NotificationReceipt, NotificationReceipt.notification_id, context.notification_ids
        )
        counts["qa_sessions"] = len(context.qa_session_ids)
        counts["qa_messages"] = len(context.qa_message_ids)
        counts["qa_answers"] = len(context.qa_answer_ids)
        counts["qa_message_knowledge_refs"] = _count_by_ids(
            db, QAMessageKnowledgeRef, QAMessageKnowledgeRef.answer_id, context.qa_answer_ids
        )
        counts["voice_transcripts"] = db.query(VoiceTranscript).filter(
            (VoiceTranscript.session_id.in_(context.qa_session_ids or [-1]))
            | (VoiceTranscript.question_message_id.in_(context.qa_message_ids or [-1]))
            | (VoiceTranscript.lesson_id.in_(context.lesson_ids or [-1]))
            | (VoiceTranscript.section_id.in_(context.lesson_section_ids or [-1]))
        ).count()
        counts["qa_answer_traces"] = db.query(QAAnswerTrace).filter(
            (QAAnswerTrace.session_id.in_(context.qa_session_ids or [-1]))
            | (QAAnswerTrace.question_message_id.in_(context.qa_message_ids or [-1]))
            | (QAAnswerTrace.answer_message_id.in_(context.qa_message_ids or [-1]))
            | (QAAnswerTrace.lesson_id.in_(context.lesson_ids or [-1]))
            | (QAAnswerTrace.section_id.in_(context.lesson_section_ids or [-1]))
        ).count()
        counts["chapter_practices"] = len(context.practice_ids)
        counts["chapter_practice_items"] = len(context.practice_item_ids)
        counts["student_practice_attempts"] = len(context.practice_attempt_ids)
        counts["student_practice_answers"] = _count_by_ids(
            db, StudentPracticeAnswer, StudentPracticeAnswer.attempt_id, context.practice_attempt_ids
        )
        counts["chapter_ppt_assets"] = len(context.ppt_asset_ids)
        counts["chapter_parse_tasks"] = len(context.parse_task_ids)
        counts["chapter_parse_results"] = len(context.parse_result_ids)
        counts["chapter_knowledge_nodes"] = db.query(ChapterKnowledgeNode).filter(
            ChapterKnowledgeNode.parse_task_id.in_(context.parse_task_ids or [-1])
        ).count()
        counts["chapter_scripts"] = len(context.script_ids)
        counts["chapter_script_sections"] = len(context.script_section_ids)
        counts["chapter_audio_assets"] = len(context.audio_asset_ids)
        counts["chapter_section_audio_assets"] = len(context.section_audio_asset_ids)
        counts["courses"] = 1

        if not apply:
            db.rollback()
            return stats

        deleted = stats.applied_deletes

        deleted["student_page_progress"] = (
            db.query(StudentPageProgress)
            .filter(StudentPageProgress.course_id == course.id)
            .delete(synchronize_session=False)
        )
        deleted["student_section_progress"] = (
            db.query(StudentSectionProgress)
            .filter(StudentSectionProgress.course_id == course.id)
            .delete(synchronize_session=False)
        )
        deleted["student_lesson_progress"] = (
            db.query(StudentLessonProgress)
            .filter(StudentLessonProgress.course_id == course.id)
            .delete(synchronize_session=False)
        )
        deleted["resume_records"] = (
            db.query(ResumeRecord)
            .filter(ResumeRecord.course_id == course.id)
            .delete(synchronize_session=False)
        )
        deleted["progress_track_logs"] = (
            db.query(ProgressTrackLog)
            .filter(ProgressTrackLog.course_id == course.id)
            .delete(synchronize_session=False)
        )
        deleted["progress_adjust_records"] = (
            db.query(ProgressAdjustRecord)
            .filter(ProgressAdjustRecord.course_id == course.id)
            .delete(synchronize_session=False)
        )
        deleted["student_section_mastery_logs"] = (
            db.query(StudentSectionMasteryLog)
            .filter(StudentSectionMasteryLog.course_id == course.id)
            .delete(synchronize_session=False)
        )

        deleted["qa_answer_traces"] = (
            db.query(QAAnswerTrace)
            .filter(
                (QAAnswerTrace.session_id.in_(context.qa_session_ids or [-1]))
                | (QAAnswerTrace.question_message_id.in_(context.qa_message_ids or [-1]))
                | (QAAnswerTrace.answer_message_id.in_(context.qa_message_ids or [-1]))
                | (QAAnswerTrace.lesson_id.in_(context.lesson_ids or [-1]))
                | (QAAnswerTrace.section_id.in_(context.lesson_section_ids or [-1]))
            )
            .delete(synchronize_session=False)
        )
        deleted["qa_message_knowledge_refs"] = _delete_by_ids(
            db, QAMessageKnowledgeRef, QAMessageKnowledgeRef.answer_id, context.qa_answer_ids
        )
        deleted["voice_transcripts"] = (
            db.query(VoiceTranscript)
            .filter(
                (VoiceTranscript.session_id.in_(context.qa_session_ids or [-1]))
                | (VoiceTranscript.question_message_id.in_(context.qa_message_ids or [-1]))
                | (VoiceTranscript.lesson_id.in_(context.lesson_ids or [-1]))
                | (VoiceTranscript.section_id.in_(context.lesson_section_ids or [-1]))
            )
            .delete(synchronize_session=False)
        )
        deleted["qa_answers"] = _delete_by_ids(db, QAAnswer, QAAnswer.id, context.qa_answer_ids)
        deleted["qa_messages"] = _delete_by_ids(db, QAMessage, QAMessage.id, context.qa_message_ids)
        deleted["qa_sessions"] = _delete_by_ids(db, QASession, QASession.id, context.qa_session_ids)

        deleted["student_practice_answers"] = _delete_by_ids(
            db, StudentPracticeAnswer, StudentPracticeAnswer.attempt_id, context.practice_attempt_ids
        )
        deleted["student_practice_attempts"] = _delete_by_ids(
            db, StudentPracticeAttempt, StudentPracticeAttempt.id, context.practice_attempt_ids
        )
        deleted["chapter_practice_items"] = _delete_by_ids(
            db, ChapterPracticeItem, ChapterPracticeItem.id, context.practice_item_ids
        )
        deleted["chapter_practices"] = _delete_by_ids(db, ChapterPractice, ChapterPractice.id, context.practice_ids)

        deleted["notification_receipts"] = _delete_by_ids(
            db, NotificationReceipt, NotificationReceipt.notification_id, context.notification_ids
        )
        deleted["notifications"] = _delete_by_ids(db, Notification, Notification.id, context.notification_ids)

        deleted["lesson_section_anchors"] = _delete_by_ids(
            db, LessonSectionAnchor, LessonSectionAnchor.id, context.lesson_anchor_ids
        )
        deleted["lesson_section_pages"] = _delete_by_ids(
            db, LessonSectionPage, LessonSectionPage.id, context.lesson_page_ids
        )
        deleted["lesson_section_knowledge_points"] = _delete_by_ids(
            db, LessonSectionKnowledgePoint, LessonSectionKnowledgePoint.id, context.lesson_point_ids
        )
        db.flush()
        deleted["lesson_sections"] = _delete_by_ids(db, LessonSection, LessonSection.id, context.lesson_section_ids)
        deleted["lesson_units"] = _delete_by_ids(db, LessonUnit, LessonUnit.id, context.lesson_unit_ids)
        deleted["lessons"] = _delete_by_ids(db, Lesson, Lesson.id, context.lesson_ids)
        db.flush()

        deleted["chapter_section_audio_assets"] = _delete_by_ids(
            db, ChapterSectionAudioAsset, ChapterSectionAudioAsset.id, context.section_audio_asset_ids
        )
        deleted["chapter_audio_assets"] = _delete_by_ids(
            db, ChapterAudioAsset, ChapterAudioAsset.id, context.audio_asset_ids
        )
        deleted["chapter_script_sections"] = _delete_by_ids(
            db, ChapterScriptSection, ChapterScriptSection.id, context.script_section_ids
        )
        deleted["chapter_scripts"] = _delete_by_ids(db, ChapterScript, ChapterScript.id, context.script_ids)

        knowledge_nodes = (
            db.query(ChapterKnowledgeNode)
            .filter(ChapterKnowledgeNode.parse_task_id.in_(context.parse_task_ids or [-1]))
            .order_by(ChapterKnowledgeNode.level_no.desc(), ChapterKnowledgeNode.id.desc())
            .all()
        )
        deleted["chapter_knowledge_nodes"] = 0
        for node in knowledge_nodes:
            db.delete(node)
            deleted["chapter_knowledge_nodes"] += 1
        db.flush()

        deleted["chapter_parse_results"] = _delete_by_ids(
            db, ChapterParseResult, ChapterParseResult.id, context.parse_result_ids
        )
        deleted["chapter_parse_tasks"] = _delete_by_ids(
            db, ChapterParseTask, ChapterParseTask.id, context.parse_task_ids
        )
        deleted["chapter_ppt_assets"] = _delete_by_ids(db, ChapterPptAsset, ChapterPptAsset.id, context.ppt_asset_ids)

        chapter_rows = (
            db.query(CourseChapter)
            .filter(CourseChapter.course_id == course.id)
            .order_by(CourseChapter.chapter_level.desc(), CourseChapter.id.desc())
            .all()
        )
        deleted["course_chapters"] = 0
        for chapter in chapter_rows:
            db.delete(chapter)
            deleted["course_chapters"] += 1
        db.flush()

        deleted["course_members"] = (
            db.query(CourseMember)
            .filter(CourseMember.course_id == course.id)
            .delete(synchronize_session=False)
        )
        deleted["course_classes"] = _delete_by_ids(db, CourseClass, CourseClass.id, context.course_class_ids)
        deleted["course_platform_bindings"] = (
            db.query(CoursePlatformBinding)
            .filter(CoursePlatformBinding.course_id == course.id)
            .delete(synchronize_session=False)
        )

        db.delete(course)
        deleted["courses"] = 1
        return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Safely remove one published demo course and all related records. Defaults to dry-run."
    )
    parser.add_argument("--course-id", type=int, default=DEFAULT_COURSE_ID)
    parser.add_argument("--course-code", default=DEFAULT_COURSE_CODE)
    parser.add_argument("--course-name", default=DEFAULT_COURSE_NAME)
    parser.add_argument("--apply", action="store_true", help="Persist the deletion. Omit for dry run.")
    args = parser.parse_args()

    stats = cleanup_course(
        course_id=args.course_id,
        course_code=_normalize_text(args.course_code),
        course_name=_normalize_text(args.course_name),
        apply=args.apply,
    )

    print("--- target course ---")
    print(f"course_id={stats.course_id}")
    print(f"course_code={stats.course_code}")
    print(f"course_name={stats.course_name}")
    print(f"lesson_ids={stats.lesson_ids}")
    print(f"chapter_ids={stats.chapter_ids}")
    print("--- related counts ---")
    for key in sorted(stats.counts):
        print(f"{key}={stats.counts[key]}")
    print(f"mode={'apply' if args.apply else 'dry-run'}")
    if args.apply:
        print("--- deleted counts ---")
        for key in sorted(stats.applied_deletes):
            print(f"{key}={stats.applied_deletes[key]}")


if __name__ == "__main__":
    main()
