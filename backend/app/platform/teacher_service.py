from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.common.config import get_settings
from backend.chaoxing_db.models import CourseClass, CourseMember, CoursePlatformBinding, School, User, UserPlatformBinding

JsonDict = dict[str, object]


def require_teacher(db: Session, token: str | None) -> User:
    settings = get_settings()
    teacher = (
        db.query(User)
        .filter(User.role == "teacher", User.auth_token == (token or settings.teacher_test_platform_token))
        .first()
    )
    if teacher:
        return teacher
    raise PermissionError("token 无效")


def sync_user(db: Session, token: str | None) -> JsonDict:
    teacher = require_teacher(db, token)
    school = db.query(School).filter(School.id == teacher.school_id).first()
    binding = (
        db.query(UserPlatformBinding)
        .filter(UserPlatformBinding.user_id == teacher.id, UserPlatformBinding.external_role == "teacher")
        .first()
    )
    return {
        "teacherId": binding.external_user_id if binding else teacher.user_no,
        "userId": teacher.user_no,
        "teacherName": teacher.user_name,
        "userName": teacher.user_name,
        "schoolId": school.school_code if school else "",
        "schoolName": school.school_name if school else "",
    }


def sync_courses(db: Session, teacher: User) -> dict[str, list[dict[str, str]]]:
    memberships = (
        db.query(CourseMember)
        .filter(CourseMember.user_id == teacher.id, CourseMember.member_role == "teacher")
        .all()
    )
    course_list: list[dict[str, str]] = []
    for membership in memberships:
        course = membership.course
        if not course:
            continue
        binding = db.query(CoursePlatformBinding).filter(CoursePlatformBinding.course_id == course.id).first()
        school = db.query(School).filter(School.id == course.school_id).first()
        class_obj = None
        if membership.class_id:
            class_obj = db.query(CourseClass).filter(CourseClass.id == membership.class_id).first()
        course_list.append(
            {
                "courseId": binding.external_course_id if binding else course.course_code,
                "courseName": course.course_name,
                "classId": class_obj.class_code if class_obj else "",
                "schoolId": school.school_code if school else "",
            }
        )
    return {"courseList": course_list}
