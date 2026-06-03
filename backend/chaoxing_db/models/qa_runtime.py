from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base

UnsignedBigInt = Integer().with_variant(MYSQL_BIGINT(unsigned=True), "mysql")


class ModelRuntimeConfig(Base):
    __tablename__ = "model_runtime_configs"
    __table_args__ = (UniqueConstraint("scope_key", "capability", name="uk_model_runtime_scope_capability"),)

    id: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=True)
    scope_key: Mapped[str] = mapped_column(String(64), nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    settings_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class StudentQARetrievalRuntimeConfig(Base):
    __tablename__ = "student_qa_retrieval_runtime_configs"

    id: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=True)
    scope_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    retrieval_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    retrieval_top_k: Mapped[int] = mapped_column(default=5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
