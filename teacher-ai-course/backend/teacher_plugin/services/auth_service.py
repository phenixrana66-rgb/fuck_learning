from sqlalchemy.orm import Session

from chaoxing_db.models import School, User, UserPlatformBinding

from config import Config


def _get_teacher_by_token(db: Session, token: str | None) -> User:
    teacher = (
        db.query(User)
        .filter(User.role == "teacher", User.auth_token == (token or Config.TEST_PLATFORM_TOKEN))
        .first()
    )
    if teacher:
        return teacher
    raise PermissionError("token 无效")


def sync_user(db: Session, token: str | None) -> dict:
    teacher = _get_teacher_by_token(db, token)
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


def require_teacher(db: Session, token: str | None) -> User:
    return _get_teacher_by_token(db, token)
