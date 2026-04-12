from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.common.db import Base


class ScriptEntity(Base):
    __tablename__ = "script_records"

    script_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parse_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    teaching_style: Mapped[str] = mapped_column(String(32), nullable=False)
    speech_speed: Mapped[str] = mapped_column(String(16), nullable=False)
    script_structure_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
