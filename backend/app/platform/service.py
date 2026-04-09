from datetime import datetime

from backend.app.platform.schemas import SyncCourseRequest, SyncUserRequest


def sync_course(payload: SyncCourseRequest) -> dict:
    return {
        "internalCourseId": payload.courseInfo.courseId.replace("plat_", "") or "cou30001",
        "syncStatus": "success",
        "syncTime": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }


def sync_user(payload: SyncUserRequest) -> dict:
    role_prefix = "tea" if payload.userInfo.role == "teacher" else "stu"
    return {
        "internalUserId": payload.userInfo.userId.replace("plat_", "") or f"{role_prefix}20001",
        "syncStatus": "success",
        "authToken": f"token-{role_prefix}-{payload.userInfo.userId}",
    }
