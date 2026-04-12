from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from importlib import import_module
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.common.config import get_settings


class Base(DeclarativeBase):
    pass


_database_url_override: str | None = None
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_schema_initialized = False


def configure_database_url(database_url: str) -> None:
    global _database_url_override
    _database_url_override = database_url
    _reset_engine_state()


def reset_database_url() -> None:
    global _database_url_override
    _database_url_override = None
    _reset_engine_state()


def get_database_url() -> str:
    if _database_url_override:
        return _database_url_override

    settings = get_settings()
    if settings.db_url:
        return settings.db_url

    return (
        f"mysql+pymysql://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}?charset=utf8mb4"
    )


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    database_url = get_database_url()
    engine_kwargs: dict[str, Any] = {"future": True, "echo": settings.db_echo}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_pre_ping"] = True

    try:
        _engine = create_engine(database_url, **engine_kwargs)
    except ModuleNotFoundError as exc:
        if "pymysql" in str(exc):
            raise RuntimeError("当前数据库 URL 使用 mysql+pymysql，但运行环境未安装 pymysql") from exc
        raise
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _session_factory


def init_db() -> None:
    global _schema_initialized
    if _schema_initialized:
        return

    _load_model_modules()

    Base.metadata.create_all(get_engine())
    _schema_initialized = True


def drop_db() -> None:
    global _schema_initialized
    _load_model_modules()

    Base.metadata.drop_all(get_engine())
    _schema_initialized = False


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    init_db()
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _reset_engine_state() -> None:
    global _engine, _session_factory, _schema_initialized
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
    _schema_initialized = False


def _load_model_modules() -> None:
    import_module("backend.app.tasks.models")
    import_module("backend.app.script.models")
