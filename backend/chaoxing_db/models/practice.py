from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DECIMAL, DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

if TYPE_CHECKING:
    from .course import CourseChapter

JsonValue = dict[str, Any] | list[Any]


class ChapterPractice(Base):
    __tablename__ = "chapter_practices"

    id: Mapped[int] = mapped_column(primary_key=True)
    practice_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("course_chapters.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    practice_title: Mapped[str] = mapped_column(String(255), nullable=False)
    practice_desc: Mapped[str | None] = mapped_column(Text)
    practice_type: Mapped[str] = mapped_column(Enum("exercise", "quiz", name="practice_type"), default="exercise", nullable=False)
    difficulty_level: Mapped[str] = mapped_column(
        Enum("easy", "medium", "hard", name="practice_difficulty"), default="medium", nullable=False
    )
    total_score: Mapped[float] = mapped_column(DECIMAL(8, 2), default=100.00, nullable=False)
    item_count: Mapped[int] = mapped_column(default=0, nullable=False)
    time_limit_minutes: Mapped[int | None] = mapped_column(nullable=True)
    publish_status: Mapped[str] = mapped_column(
        Enum("draft", "published", "closed", name="practice_publish_status"), default="draft", nullable=False
    )
    start_at: Mapped[datetime | None] = mapped_column(DateTime)
    end_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    chapter: Mapped["CourseChapter"] = relationship(back_populates="practices")
    items: Mapped[list["ChapterPracticeItem"]] = relationship(back_populates="practice")
    attempts: Mapped[list["StudentPracticeAttempt"]] = relationship(back_populates="practice")


class ChapterPracticeItem(Base):
    __tablename__ = "chapter_practice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    practice_id: Mapped[int] = mapped_column(ForeignKey("chapter_practices.id"), nullable=False)
    item_no: Mapped[str] = mapped_column(String(64), nullable=False)
    item_type: Mapped[str] = mapped_column(
        Enum("single_choice", "multiple_choice", "judge", "short_answer", "calculation", name="practice_item_type"),
        nullable=False,
    )
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[JsonValue | None] = mapped_column(JSON)
    correct_answer_json: Mapped[JsonValue | None] = mapped_column(JSON)
    analysis_text: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float] = mapped_column(DECIMAL(8, 2), default=0.00, nullable=False)
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)

    practice: Mapped["ChapterPractice"] = relationship(back_populates="items")
    answers: Mapped[list["StudentPracticeAnswer"]] = relationship(back_populates="item")


class StudentPracticeAttempt(Base):
    __tablename__ = "student_practice_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    practice_id: Mapped[int] = mapped_column(ForeignKey("chapter_practices.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"))
    section_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sections.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    total_score: Mapped[float | None] = mapped_column(DECIMAL(8, 2))
    correct_count: Mapped[int | None] = mapped_column(nullable=True)
    accuracy_percent: Mapped[float | None] = mapped_column(DECIMAL(5, 2))
    grading_status: Mapped[str] = mapped_column(
        Enum("pending", "graded", name="practice_grading_status"), default="pending", nullable=False
    )
    attempt_status: Mapped[str] = mapped_column(
        Enum("doing", "submitted", "graded", name="practice_attempt_status"), default="doing", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    practice: Mapped["ChapterPractice"] = relationship(back_populates="attempts")
    answers: Mapped[list["StudentPracticeAnswer"]] = relationship(back_populates="attempt")


class StudentPracticeAnswer(Base):
    __tablename__ = "student_practice_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("student_practice_attempts.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("chapter_practice_items.id"), nullable=False)
    student_answer_json: Mapped[JsonValue | None] = mapped_column(JSON)
    answer_text: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    earned_score: Mapped[float | None] = mapped_column(DECIMAL(8, 2))
    teacher_comment: Mapped[str | None] = mapped_column(Text)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime)

    attempt: Mapped["StudentPracticeAttempt"] = relationship(back_populates="answers")
    item: Mapped["ChapterPracticeItem"] = relationship(back_populates="answers")
