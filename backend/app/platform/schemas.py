from typing import Literal

from pydantic import Field

from backend.app.common.schemas import AppBaseModel


class TeacherInfo(AppBaseModel):
    teacherId: str
    teacherName: str


class CourseInfo(AppBaseModel):
    courseId: str
    courseName: str
    schoolId: str
    schoolName: str
    teacherInfo: list[TeacherInfo] = Field(default_factory=list)
    term: str | None = None
    credit: float | None = None
    period: int | None = None
    courseCover: str | None = None


class SyncCourseRequest(AppBaseModel):
    platformId: str
    courseInfo: CourseInfo
    enc: str
    time: str | None = None


class ContactInfo(AppBaseModel):
    phone: str | None = None
    email: str | None = None


class UserInfo(AppBaseModel):
    userId: str
    userName: str
    role: Literal["student", "teacher"]
    schoolId: str
    relatedCourseIds: list[str] = Field(default_factory=list)
    contactInfo: ContactInfo | None = None


class SyncUserRequest(AppBaseModel):
    platformId: str
    userInfo: UserInfo
    enc: str
    time: str | None = None
