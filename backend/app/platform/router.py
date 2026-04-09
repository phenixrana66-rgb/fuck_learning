from fastapi import APIRouter, Request

from backend.app.common.responses import success_response
from backend.app.common.security import verify_signature_placeholder
from backend.app.platform.schemas import SyncCourseRequest, SyncUserRequest
from backend.app.platform.service import sync_course, sync_user

router = APIRouter(tags=["platform"])


@router.post("/platform/syncCourse")
def sync_course_endpoint(payload: SyncCourseRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = sync_course(payload)
    return success_response(request, data, msg="课程同步成功")


@router.post("/platform/syncUser")
def sync_user_endpoint(payload: SyncUserRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = sync_user(payload)
    return success_response(request, data, msg="用户同步成功")
