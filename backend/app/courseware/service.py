from datetime import datetime
from uuid import uuid4

from backend.app.cir.service import build_cir
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseAcceptedData, ParseQueryData, ParseRequest
from backend.app.parser.schemas import ParseTaskStatus
from backend.app.parser.service import parse_courseware
from backend.app.tasks.schemas import TaskRecord
from backend.app.tasks.service import upsert_task

_PARSE_TASKS: dict[str, ParseQueryData] = {}


def create_parse_task(payload: ParseRequest) -> ParseAcceptedData:
    parse_id = _build_id("parse")
    file_info, preview = parse_courseware(
        course_id=payload.courseId,
        file_url=payload.fileUrl,
        file_type=payload.fileType,
        is_extract_key_point=payload.isExtractKeyPoint,
    )
    cir = build_cir(courseware_id=f"cw-{payload.courseId}", preview=preview)

    task = ParseQueryData(
        parseId=parse_id,
        fileInfo=file_info,
        structurePreview=preview,
        taskStatus=ParseTaskStatus.COMPLETED,
        cir=cir,
        progressPercent=100,
    )
    _PARSE_TASKS[parse_id] = task
    upsert_task(
        TaskRecord(
            taskId=parse_id,
            taskType="lesson.parse",
            status=ParseTaskStatus.COMPLETED.value,
            payload={"courseId": payload.courseId, "fileUrl": payload.fileUrl},
        )
    )
    return ParseAcceptedData(**task.model_dump(exclude={"cir", "progressPercent"}))


def get_parse_task(parse_id: str) -> ParseQueryData:
    task = _PARSE_TASKS.get(parse_id)
    if not task:
        raise ApiError(code=404, msg="解析任务不存在", status_code=404)

    task_data = task.model_dump(exclude={"taskStatus", "progressPercent"})
    return ParseQueryData(
        **task_data,
        taskStatus=ParseTaskStatus.COMPLETED,
        progressPercent=100,
    )


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"
