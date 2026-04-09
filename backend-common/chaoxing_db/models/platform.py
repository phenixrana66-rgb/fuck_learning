from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    platform_name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_base_url: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user_bindings: Mapped[list["UserPlatformBinding"]] = relationship(back_populates="platform")
    course_bindings: Mapped[list["CoursePlatformBinding"]] = relationship(back_populates="platform")


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    school_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="school")
    courses: Mapped[list["Course"]] = relationship(back_populates="school")
    classes: Mapped[list["CourseClass"]] = relationship(back_populates="school")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(Enum("student", "teacher", "admin", name="user_role"), nullable=False)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(128))
    auth_token: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    school: Mapped["School"] = relationship(back_populates="users")
    platform_bindings: Mapped[list["UserPlatformBinding"]] = relationship(back_populates="user")
    created_courses: Mapped[list["Course"]] = relationship(back_populates="creator")
    teaching_classes: Mapped[list["CourseClass"]] = relationship(back_populates="teacher")
    course_memberships: Mapped[list["CourseMember"]] = relationship(back_populates="user")


class UserPlatformBinding(Base):
    __tablename__ = "user_platform_bindings"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    external_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    external_role: Mapped[str] = mapped_column(String(16), nullable=False)
    related_course_ids: Mapped[dict | list | None] = mapped_column(JSON)
    raw_payload: Mapped[dict | list | None] = mapped_column(JSON)
    sync_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    platform: Mapped["Platform"] = relationship(back_populates="user_bindings")
    user: Mapped["User"] = relationship(back_populates="platform_bindings")
