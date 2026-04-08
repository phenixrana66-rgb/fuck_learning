from datetime import UTC, datetime
from uuid import uuid4

from backend.app.cir.service import build_cir
from backend.app.common.exceptions import ApiError
from backend.app.courseware.schemas import ParseAcceptedData, ParseQueryData, ParseRequest
from backend.app.parser.schemas import ParseTaskStatus
from backend.app.parser.service import parse_courseware
from backend.app.tasks.service import create_task, mark_task_completed, mark_task_failed, mark_task_processing, require_task


def create_parse_task(payload: ParseRequest, request_id: str | None = None) -> ParseAcceptedData:
    parse_id = _build_id("parse")
    create_task(
        task_id=parse_id,
        task_type="lesson.parse",
        payload={"courseId": payload.courseId, "fileUrl": payload.fileUrl},
        request_id=request_id,
    )
    try:
        mark_task_processing(parse_id, progress_percent=10)
        file_info, preview = parse_courseware(
            course_id=payload.courseId,
            file_url=payload.fileUrl,
            file_type=payload.fileType,
            is_extract_key_point=payload.isExtractKeyPoint,
        )
        mark_task_processing(parse_id, progress_percent=70)
        cir = build_cir(courseware_id=f"cw-{payload.courseId}", preview=preview)
    except ApiError as exc:
        error_data = {**exc.data, "parseId": parse_id}
        mark_task_failed(parse_id, code=exc.code, msg=exc.msg, data=error_data)
        raise ApiError(code=exc.code, msg=exc.msg, status_code=exc.status_code, data=error_data) from exc
    except Exception as exc:  # noqa: BLE001
        error_data = {"parseId": parse_id}
        mark_task_failed(parse_id, code=500, msg="服务端错误", data=error_data)
        raise ApiError(code=500, msg="服务端错误", status_code=500, data=error_data) from exc

    task = ParseQueryData(
        parseId=parse_id,
        fileInfo=file_info,
        structurePreview=preview,
        taskStatus=ParseTaskStatus.COMPLETED,
        cir=cir,
        progressPercent=100,
    )
    mark_task_completed(parse_id, result=task.model_dump())
    return ParseAcceptedData(**task.model_dump(exclude={"cir", "progressPercent", "errorMessage"}))


def get_parse_task(parse_id: str) -> ParseQueryData:
    task = require_task(parse_id)
    if task.taskType != "lesson.parse":
        raise ApiError(code=404, msg="解析任务不存在", status_code=404)

    status = ParseTaskStatus(task.status)
    if status == ParseTaskStatus.COMPLETED:
        return ParseQueryData.model_validate(task.result)

    return ParseQueryData(
        parseId=parse_id,
        taskStatus=status,
        progressPercent=task.progressPercent,
        errorMessage=task.error.msg if task.error else None,
    )


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"
