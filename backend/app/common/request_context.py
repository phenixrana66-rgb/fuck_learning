from datetime import datetime
from uuid import uuid4

from fastapi import Request, Response


async def request_context_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-Id") or _build_request_id()
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


def _build_request_id() -> str:
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:8]
    return f"req-{now}-{suffix}"
