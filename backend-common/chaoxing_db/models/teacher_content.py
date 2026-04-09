from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class ChapterPptAsset(Base):
    __tablename__ = "chapter_ppt_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("course_chapters.id"), nullable=False)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(Enum("ppt", "pptx", "pdf", name="ppt_asset_type"), nullable=False)
    file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int | None]
    page_count: Mapped[int | None]
    upload_status: Mapped[str] = mapped_column(
        Enum("uploaded", "parsing", "parsed", "failed", name="ppt_upload_status"), default="uploaded", nullable=False
    )
    version_no: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    chapter: Mapped["CourseChapter"] = relationship(back_populates="ppt_assets")
    parse_tasks: Mapped[list["ChapterParseTask"]] = relationship(back_populates="ppt_asset")


class ChapterParseTask(Base):
    __tablename__ = "chapter_parse_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    parse_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("course_chapters.id"), nullable=False)
    ppt_asset_id: Mapped[int] = mapped_column(ForeignKey("chapter_ppt_assets.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    llm_model: Mapped[str | None] = mapped_column(String(64))
    is_extract_key_point: Mapped[bool] = mapped_column(default=True)
    task_status: Mapped[str] = mapped_column(
        Enum("processing", "completed", "failed", name="parse_task_status"), default="processing", nullable=False
    )
    error_msg: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    chapter: Mapped["CourseChapter"] = relationship(back_populates="parse_tasks")
    ppt_asset: Mapped["ChapterPptAsset"] = relationship(back_populates="parse_tasks")
    parse_result: Mapped["ChapterParseResult | None"] = relationship(back_populates="parse_task", uselist=False)
    knowledge_nodes: Mapped[list["ChapterKnowledgeNode"]] = relationship(back_populates="parse_task")
    scripts: Mapped[list["ChapterScript"]] = relationship(back_populates="parse_task")


class ChapterParseResult(Base):
    __tablename__ = "chapter_parse_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    parse_task_id: Mapped[int] = mapped_column(ForeignKey("chapter_parse_tasks.id"), nullable=False, unique=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("course_chapters.id"), nullable=False)
    ppt_asset_id: Mapped[int] = mapped_column(ForeignKey("chapter_ppt_assets.id"), nullable=False)
    chapter_summary: Mapped[str | None] = mapped_column(Text)
    parsed_outline: Mapped[dict | list | None] = mapped_column(JSON)
    key_points: Mapped[dict | list | None] = mapped_column(JSON)
    formulas: Mapped[dict | list | None] = mapped_column(JSON)
    charts: Mapped[dict | list | None] = mapped_column(JSON)
    page_mapping: Mapped[dict | list | None] = mapped_column(JSON)
    raw_llm_output: Mapped[str | None] = mapped_column(Text)
    normalized_content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    parse_task: Mapped["ChapterParseTask"] = relationship(back_populates="parse_result")


class ChapterKnowledgeNode(Base):
    __tablename__ = "chapter_knowledge_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    parse_task_id: Mapped[int] = mapped_column(ForeignKey("chapter_parse_tasks.id"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("course_chapters.id"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("chapter_knowledge_nodes.id"))
    node_code: Mapped[str] = mapped_column(String(64), nullable=False)
    node_name: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str] = mapped_column(
        Enum("unit", "chapter", "subchapter", "knowledge", name="knowledge_node_type"),
        default="knowledge",
        nullable=False,
    )
    level_no: Mapped[int] = mapped_column(default=1, nullable=False)
    is_key_point: Mapped[bool] = mapped_column(default=False, nullable=False)
    page_start: Mapped[int | None]
    page_end: Mapped[int | None]
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)

    parse_task: Mapped["ChapterParseTask"] = relationship(back_populates="knowledge_nodes")
    parent: Mapped["ChapterKnowledgeNode | None"] = relationship(remote_side="ChapterKnowledgeNode.id", back_populates="children")
    children: Mapped[list["ChapterKnowledgeNode"]] = relationship(back_populates="parent")


class ChapterScript(Base):
    __tablename__ = "chapter_scripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    script_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("course_chapters.id"), nullable=False)
    parse_task_id: Mapped[int] = mapped_column(ForeignKey("chapter_parse_tasks.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    teaching_style: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)
    speech_speed: Mapped[str] = mapped_column(String(16), default="normal", nullable=False)
    custom_opening: Mapped[str | None] = mapped_column(Text)
    script_status: Mapped[str] = mapped_column(
        Enum("generated", "edited", "published", name="script_status"), default="generated", nullable=False
    )
    edit_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    chapter: Mapped["CourseChapter"] = relationship(back_populates="scripts")
    parse_task: Mapped["ChapterParseTask"] = relationship(back_populates="scripts")
    sections: Mapped[list["ChapterScriptSection"]] = relationship(back_populates="script")
    audio_assets: Mapped[list["ChapterAudioAsset"]] = relationship(back_populates="script")


class ChapterScriptSection(Base):
    __tablename__ = "chapter_script_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("chapter_scripts.id"), nullable=False)
    section_code: Mapped[str] = mapped_column(String(64), nullable=False)
    section_name: Mapped[str] = mapped_column(String(255), nullable=False)
    section_content: Mapped[str] = mapped_column(Text, nullable=False)
    duration_sec: Mapped[int | None]
    related_node_id: Mapped[int | None] = mapped_column(ForeignKey("chapter_knowledge_nodes.id"))
    related_page_range: Mapped[str | None] = mapped_column(String(64))
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)

    script: Mapped["ChapterScript"] = relationship(back_populates="sections")


class ChapterAudioAsset(Base):
    __tablename__ = "chapter_audio_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("course_chapters.id"), nullable=False)
    script_id: Mapped[int] = mapped_column(ForeignKey("chapter_scripts.id"), nullable=False)
    voice_type: Mapped[str] = mapped_column(String(32), nullable=False)
    audio_format: Mapped[str] = mapped_column(String(16), default="mp3", nullable=False)
    audio_url: Mapped[str] = mapped_column(String(255), nullable=False)
    total_duration_sec: Mapped[int | None]
    file_size: Mapped[int | None]
    bit_rate: Mapped[int | None]
    status: Mapped[str] = mapped_column(
        Enum("generated", "published", name="audio_asset_status"), default="generated", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    script: Mapped["ChapterScript"] = relationship(back_populates="audio_assets")
