from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_name: Mapped[str] = mapped_column(String(255), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    publish_version: Mapped[int] = mapped_column(default=1, nullable=False)
    publish_status: Mapped[str] = mapped_column(
        Enum("draft", "published", "archived", name="lesson_publish_status"), default="published", nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    course: Mapped["Course"] = relationship(back_populates="lessons")
    units: Mapped[list["LessonUnit"]] = relationship(back_populates="lesson")
    sections: Mapped[list["LessonSection"]] = relationship(back_populates="lesson")


class LessonUnit(Base):
    __tablename__ = "lesson_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    source_chapter_id: Mapped[int | None] = mapped_column(ForeignKey("course_chapters.id"))
    unit_code: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_title: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    lesson: Mapped["Lesson"] = relationship(back_populates="units")
    sections: Mapped[list["LessonSection"]] = relationship(back_populates="unit")


class LessonSection(Base):
    __tablename__ = "lesson_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey("lesson_units.id"), nullable=False)
    source_chapter_id: Mapped[int] = mapped_column(ForeignKey("course_chapters.id"), nullable=False)
    parse_result_id: Mapped[int | None] = mapped_column(ForeignKey("chapter_parse_results.id"))
    ppt_asset_id: Mapped[int | None] = mapped_column(ForeignKey("chapter_ppt_assets.id"))
    script_id: Mapped[int | None] = mapped_column(ForeignKey("chapter_scripts.id"))
    audio_asset_id: Mapped[int | None] = mapped_column(ForeignKey("chapter_audio_assets.id"))
    section_code: Mapped[str] = mapped_column(String(64), nullable=False)
    section_name: Mapped[str] = mapped_column(String(255), nullable=False)
    section_summary: Mapped[str | None] = mapped_column(Text)
    student_visible: Mapped[bool] = mapped_column(default=True, nullable=False)
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    lesson: Mapped["Lesson"] = relationship(back_populates="sections")
    unit: Mapped["LessonUnit"] = relationship(back_populates="sections")
    pages: Mapped[list["LessonSectionPage"]] = relationship(back_populates="section")
    anchors: Mapped[list["LessonSectionAnchor"]] = relationship(back_populates="section")
    knowledge_points: Mapped[list["LessonSectionKnowledgePoint"]] = relationship(back_populates="section")


class LessonSectionPage(Base):
    __tablename__ = "lesson_section_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("lesson_sections.id"), nullable=False)
    source_ppt_asset_id: Mapped[int | None] = mapped_column(ForeignKey("chapter_ppt_assets.id"))
    source_page_no: Mapped[int | None]
    page_no: Mapped[int] = mapped_column(nullable=False)
    page_title: Mapped[str | None] = mapped_column(String(255))
    page_summary: Mapped[str | None] = mapped_column(Text)
    ppt_page_url: Mapped[str | None] = mapped_column(String(255))
    parsed_content: Mapped[str | None] = mapped_column(Text)
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)

    section: Mapped["LessonSection"] = relationship(back_populates="pages")
    anchors: Mapped[list["LessonSectionAnchor"]] = relationship(back_populates="lesson_page")


class LessonSectionAnchor(Base):
    __tablename__ = "lesson_section_anchors"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("lesson_sections.id"), nullable=False)
    lesson_page_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_section_pages.id"))
    anchor_code: Mapped[str] = mapped_column(String(64), nullable=False)
    anchor_title: Mapped[str] = mapped_column(String(255), nullable=False)
    page_no: Mapped[int | None]
    start_time_sec: Mapped[int | None]
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)

    section: Mapped["LessonSection"] = relationship(back_populates="anchors")
    lesson_page: Mapped["LessonSectionPage | None"] = relationship(back_populates="anchors")


class LessonSectionKnowledgePoint(Base):
    __tablename__ = "lesson_section_knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("lesson_sections.id"), nullable=False)
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("chapter_knowledge_nodes.id"))
    point_code: Mapped[str] = mapped_column(String(64), nullable=False)
    point_name: Mapped[str] = mapped_column(String(255), nullable=False)
    point_summary: Mapped[str | None] = mapped_column(Text)
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)

    section: Mapped["LessonSection"] = relationship(back_populates="knowledge_points")
