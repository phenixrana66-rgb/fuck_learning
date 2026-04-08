from __future__ import annotations

from datetime import datetime

from sqlalchemy import DECIMAL, DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class StudentLessonProgress(Base):
    __tablename__ = "student_lesson_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    total_progress: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00, nullable=False)
    overall_mastery_percent: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00, nullable=False)
    current_unit_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_units.id"))
    current_section_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sections.id"))
    current_anchor_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_section_anchors.id"))
    last_page_no: Mapped[int | None]
    last_operate_time: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class StudentSectionProgress(Base):
    __tablename__ = "student_section_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey("lesson_units.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("lesson_sections.id"), nullable=False)
    current_anchor_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_section_anchors.id"))
    last_page_no: Mapped[int | None]
    progress_percent: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00, nullable=False)
    mastery_percent: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00, nullable=False)
    understanding_level: Mapped[str | None] = mapped_column(Enum("none", "partial", "full", name="section_understanding_level"))
    last_qa_message_id: Mapped[int | None] = mapped_column(ForeignKey("qa_messages.id"))
    last_practice_attempt_id: Mapped[int | None] = mapped_column(ForeignKey("student_practice_attempts.id"))
    last_operate_time: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class StudentPageProgress(Base):
    __tablename__ = "student_page_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("lesson_sections.id"), nullable=False)
    lesson_page_id: Mapped[int] = mapped_column(ForeignKey("lesson_section_pages.id"), nullable=False)
    page_no: Mapped[int] = mapped_column(nullable=False)
    read_percent: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00, nullable=False)
    is_completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    stay_seconds: Mapped[int] = mapped_column(default=0, nullable=False)
    first_read_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ResumeRecord(Base):
    __tablename__ = "resume_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sections.id"))
    anchor_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_section_anchors.id"))
    page_no: Mapped[int | None]
    resume_time_sec: Mapped[int | None]
    resume_type: Mapped[str] = mapped_column(Enum("auto", "manual", "ai_recommended", name="resume_type"), default="auto", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class ProgressTrackLog(Base):
    __tablename__ = "progress_track_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("lesson_sections.id"), nullable=False)
    anchor_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_section_anchors.id"))
    page_no: Mapped[int | None]
    qa_answer_id: Mapped[int | None] = mapped_column(ForeignKey("qa_answers.id"))
    track_source: Mapped[str] = mapped_column(
        Enum("page_read", "qa", "practice", "manual", name="progress_track_source"), default="page_read", nullable=False
    )
    progress_percent: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00, nullable=False)
    last_operate_time: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class ProgressAdjustRecord(Base):
    __tablename__ = "progress_adjust_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("lesson_sections.id"), nullable=False)
    qa_answer_id: Mapped[int | None] = mapped_column(ForeignKey("qa_answers.id"))
    understanding_level: Mapped[str | None] = mapped_column(Enum("none", "partial", "full", name="progress_adjust_understanding"))
    adjust_type: Mapped[str] = mapped_column(
        Enum("keep", "review", "advance", "supplement", name="progress_adjust_type"), default="keep", nullable=False
    )
    continue_section_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sections.id"))
    recommended_page_no: Mapped[int | None]
    recommended_anchor_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_section_anchors.id"))
    supplement_content: Mapped[str | None] = mapped_column(Text)
    adjust_payload: Mapped[dict | list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class StudentSectionMasteryLog(Base):
    __tablename__ = "student_section_mastery_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("lesson_sections.id"), nullable=False)
    practice_attempt_id: Mapped[int | None] = mapped_column(ForeignKey("student_practice_attempts.id"))
    qa_answer_id: Mapped[int | None] = mapped_column(ForeignKey("qa_answers.id"))
    source_type: Mapped[str] = mapped_column(
        Enum("progress_sync", "practice_submit", "qa_answer", "manual_recalc", name="mastery_source_type"), nullable=False
    )
    page_progress_contribution: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00, nullable=False)
    practice_contribution: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00, nullable=False)
    qa_contribution: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00, nullable=False)
    final_mastery_percent: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    detail_json: Mapped[dict | list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
