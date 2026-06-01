from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base

UnsignedBigInt = Integer().with_variant(MYSQL_BIGINT(unsigned=True), "mysql")


class QARuntimeConfig(Base):
    __tablename__ = "qa_runtime_configs"

    id: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=True)
    scope_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    qa_llm_model: Mapped[str] = mapped_column(String(128), nullable=False)
    qa_multimodal_model: Mapped[str] = mapped_column(String(128), nullable=False)
    qa_embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    retrieval_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    retrieval_top_k: Mapped[int] = mapped_column(default=5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
