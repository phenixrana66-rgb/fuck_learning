from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DECIMAL, DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

JsonValue = dict[str, Any] | list[Any]


class QASession(Base):
    __tablename__ = "qa_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    current_section_id: Mapped[int] = mapped_column(ForeignKey("lesson_sections.id"), nullable=False)
    session_title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(Enum("active", "archived", name="qa_session_status"), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    messages: Mapped[list["QAMessage"]] = relationship(back_populates="session")
    answers: Mapped[list["QAAnswer"]] = relationship(back_populates="session")


class QAMessage(Base):
    __tablename__ = "qa_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("qa_sessions.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sections.id"))
    role: Mapped[str] = mapped_column(Enum("user", "assistant", name="qa_message_role"), nullable=False)
    question_type: Mapped[str | None] = mapped_column(Enum("text", "voice", name="qa_question_type"))
    message_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    session: Mapped["QASession"] = relationship(back_populates="messages")
    question_answer: Mapped["QAAnswer | None"] = relationship(
        back_populates="question_message", foreign_keys="QAAnswer.question_message_id"
    )
    assistant_answer: Mapped["QAAnswer | None"] = relationship(
        back_populates="assistant_message", foreign_keys="QAAnswer.assistant_message_id"
    )


class QAAnswer(Base):
    __tablename__ = "qa_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    session_id: Mapped[int] = mapped_column(ForeignKey("qa_sessions.id"), nullable=False)
    question_message_id: Mapped[int] = mapped_column(ForeignKey("qa_messages.id"), nullable=False)
    assistant_message_id: Mapped[int] = mapped_column(ForeignKey("qa_messages.id"), nullable=False, unique=True)
    related_section_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sections.id"))
    answer_type: Mapped[str] = mapped_column(Enum("text", "mixed", name="qa_answer_type"), default="text")
    understanding_level: Mapped[str | None] = mapped_column(Enum("none", "partial", "full", name="qa_understanding_level"))
    recommended_section_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sections.id"))
    recommended_page_no: Mapped[int | None] = mapped_column(nullable=True)
    recommended_anchor_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_section_anchors.id"))
    next_sections_json: Mapped[JsonValue | None] = mapped_column(JSON)
    suggestions_json: Mapped[JsonValue | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    session: Mapped["QASession"] = relationship(back_populates="answers")
    question_message: Mapped["QAMessage"] = relationship(back_populates="question_answer", foreign_keys=[question_message_id])
    assistant_message: Mapped["QAMessage"] = relationship(back_populates="assistant_answer", foreign_keys=[assistant_message_id])
    knowledge_refs: Mapped[list["QAMessageKnowledgeRef"]] = relationship(back_populates="answer")


class QAMessageKnowledgeRef(Base):
    __tablename__ = "qa_message_knowledge_refs"

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_id: Mapped[int] = mapped_column(ForeignKey("qa_answers.id"), nullable=False)
    knowledge_point_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_section_knowledge_points.id"))
    knowledge_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)

    answer: Mapped["QAAnswer"] = relationship(back_populates="knowledge_refs")


class VoiceTranscript(Base):
    __tablename__ = "voice_transcripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("qa_sessions.id"))
    question_message_id: Mapped[int | None] = mapped_column(ForeignKey("qa_messages.id"))
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_sections.id"))
    audio_url: Mapped[str | None] = mapped_column(String(255))
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="zh-CN", nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(DECIMAL(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
