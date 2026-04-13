from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DECIMAL, DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

if TYPE_CHECKING:
    from .lesson import Lesson
    from .platform import Platform, School, User
    from .practice import ChapterPractice
    from .teacher_content import ChapterParseTask, ChapterPptAsset, ChapterScript

JsonValue = dict[str, Any] | list[Any]


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    term: Mapped[str | None] = mapped_column(String(32))
    credit: Mapped[float | None] = mapped_column(DECIMAL(4, 1))
    period: Mapped[int | None] = mapped_column(nullable=True)
    course_cover_url: Mapped[str | None] = mapped_column(String(255))
    course_status: Mapped[str] = mapped_column(
        Enum("draft", "published", "archived", name="course_status"), default="draft", nullable=False
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    school: Mapped["School"] = relationship(back_populates="courses")
    creator: Mapped["User | None"] = relationship(back_populates="created_courses")
    platform_bindings: Mapped[list["CoursePlatformBinding"]] = relationship(back_populates="course")
    classes: Mapped[list["CourseClass"]] = relationship(back_populates="course")
    members: Mapped[list["CourseMember"]] = relationship(back_populates="course")
    chapters: Mapped[list["CourseChapter"]] = relationship(back_populates="course")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="course")


class CoursePlatformBinding(Base):
    __tablename__ = "course_platform_bindings"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    external_course_id: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[JsonValue | None] = mapped_column(JSON)
    sync_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    platform: Mapped["Platform"] = relationship(back_populates="course_bindings")
    course: Mapped["Course"] = relationship(back_populates="platform_bindings")


class CourseClass(Base):
    __tablename__ = "course_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    class_name: Mapped[str] = mapped_column(String(128), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    course: Mapped["Course"] = relationship(back_populates="classes")
    school: Mapped["School"] = relationship(back_populates="classes")
    teacher: Mapped["User | None"] = relationship(back_populates="teaching_classes")
    members: Mapped[list["CourseMember"]] = relationship(back_populates="course_class")


class CourseMember(Base):
    __tablename__ = "course_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("course_classes.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    member_role: Mapped[str] = mapped_column(Enum("teacher", "student", name="course_member_role"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    course: Mapped["Course"] = relationship(back_populates="members")
    course_class: Mapped["CourseClass | None"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="course_memberships")


class CourseChapter(Base):
    __tablename__ = "course_chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("course_chapters.id"))
    chapter_code: Mapped[str] = mapped_column(String(64), nullable=False)
    chapter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    chapter_type: Mapped[str] = mapped_column(
        Enum("unit", "chapter", "section", name="course_chapter_type"), default="chapter", nullable=False
    )
    chapter_level: Mapped[int] = mapped_column(default=1, nullable=False)
    sort_no: Mapped[int] = mapped_column(default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("draft", "published", name="course_chapter_status"), default="draft", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    course: Mapped["Course"] = relationship(back_populates="chapters")
    parent: Mapped["CourseChapter | None"] = relationship(remote_side="CourseChapter.id", back_populates="children")
    children: Mapped[list["CourseChapter"]] = relationship(back_populates="parent")
    ppt_assets: Mapped[list["ChapterPptAsset"]] = relationship(back_populates="chapter")
    parse_tasks: Mapped[list["ChapterParseTask"]] = relationship(back_populates="chapter")
    scripts: Mapped[list["ChapterScript"]] = relationship(back_populates="chapter")
    practices: Mapped[list["ChapterPractice"]] = relationship(back_populates="chapter")
