from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy import BigInteger
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base

JsonValue = dict[str, Any] | list[Any]
UnsignedBigInt = BigInteger().with_variant(MYSQL_BIGINT(unsigned=True), "mysql")


class QAFaqItem(Base):
    __tablename__ = "qa_faq_items"

    id: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=True)
    category: Mapped[str | None] = mapped_column(String(128))
    canonical_question: Mapped[str] = mapped_column(String(512), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    match_mode: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), default="enabled", nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="organizer_dataset", nullable=False)
    source_file: Mapped[str | None] = mapped_column(String(255))
    source_sheet: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class QAFaqVariant(Base):
    __tablename__ = "qa_faq_variants"

    id: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=True)
    faq_item_id: Mapped[int] = mapped_column(UnsignedBigInt, ForeignKey("qa_faq_items.id"), nullable=False)
    variant_text: Mapped[str] = mapped_column(String(512), nullable=False)
    variant_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class QAAnswerTrace(Base):
    __tablename__ = "qa_answer_traces"

    id: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=True)
    session_id: Mapped[int | None] = mapped_column(UnsignedBigInt, ForeignKey("qa_sessions.id"))
    question_message_id: Mapped[int | None] = mapped_column(UnsignedBigInt, ForeignKey("qa_messages.id"))
    answer_message_id: Mapped[int | None] = mapped_column(UnsignedBigInt, ForeignKey("qa_messages.id"))
    lesson_id: Mapped[int | None] = mapped_column(UnsignedBigInt, ForeignKey("lessons.id"))
    section_id: Mapped[int | None] = mapped_column(UnsignedBigInt, ForeignKey("lesson_sections.id"))
    page_no: Mapped[int | None] = mapped_column(nullable=True)
    model_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    faq_hit_ids_json: Mapped[JsonValue | None] = mapped_column(JSON)
    context_chunk_ids_json: Mapped[JsonValue | None] = mapped_column(JSON)
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
