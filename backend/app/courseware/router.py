from fastapi import APIRouter, Request

from backend.app.common.responses import success_response
from backend.app.common.security import verify_signature_placeholder
from backend.app.courseware.schemas import ParseRequest
from backend.app.courseware.service import create_parse_task, get_parse_task

router = APIRouter(tags=["courseware"])


@router.post("/lesson/parse")
def create_parse_task_endpoint(payload: ParseRequest, request: Request) -> dict:
    verify_signature_placeholder(payload.enc, payload.time)
    data = create_parse_task(payload)
    return success_response(request, data.model_dump(), msg="课件解析任务已创建")


@router.get("/lesson/parse/{parseId}")
def get_parse_task_endpoint(parseId: str, request: Request) -> dict:
    data = get_parse_task(parseId)
    return success_response(request, data.model_dump(), msg="课件解析结果查询成功")
