from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.types import JSON

from backend.app.common.config import get_settings


class VectorBase(DeclarativeBase):
    pass


class QAVectorChunk(VectorBase):
    __tablename__ = "qa_vector_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_id: Mapped[int | None] = mapped_column(Integer)
    section_id: Mapped[int | None] = mapped_column(Integer)
    page_no: Mapped[int | None] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_schema_initialized = False


def get_vector_database_url() -> str:
    settings = get_settings()
    if not settings.vector_db_url:
        raise RuntimeError("Vector database URL is not configured.")
    return settings.vector_db_url


def get_vector_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_vector_database_url(),
            future=True,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 5,
                "sslmode": "disable",
            },
        )
    return _engine


def get_vector_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_vector_engine(), autoflush=False, autocommit=False, future=True)
    return _session_factory


def init_vector_db() -> None:
    global _schema_initialized
    if _schema_initialized:
        return

    engine = get_vector_engine()
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        VectorBase.metadata.create_all(connection)
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_qa_vector_chunks_embedding "
                "ON qa_vector_chunks USING hnsw (embedding vector_cosine_ops)"
            )
        )
    _schema_initialized = True


@contextmanager
def vector_session_scope() -> Generator[Session, None, None]:
    init_vector_db()
    session = get_vector_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_vector_db() -> Generator[Session, None, None]:
    init_vector_db()
    session = get_vector_session_factory()()
    try:
        yield session
    finally:
        session.close()
