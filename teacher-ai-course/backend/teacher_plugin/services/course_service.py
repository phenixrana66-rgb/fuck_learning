from sqlalchemy.orm import Session

from chaoxing_db.models import CourseClass, CourseMember, CoursePlatformBinding, School, User


def sync_courses(db: Session, teacher: User) -> dict:
    memberships = (
        db.query(CourseMember)
        .filter(CourseMember.user_id == teacher.id, CourseMember.member_role == "teacher")
        .all()
    )
    course_list = []
    for membership in memberships:
        course = membership.course
        if not course:
            continue
        binding = (
            db.query(CoursePlatformBinding)
            .filter(CoursePlatformBinding.course_id == course.id)
            .first()
        )
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
