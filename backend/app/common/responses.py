from typing import Any

from fastapi import Request


def success_response(
    request: Request,
    data: Any,
    msg: str = "success",
    code: int = 200,
) -> dict[str, Any]:
    return {
        "code": code,
        "msg": msg,
        "data": data,
        "requestId": getattr(request.state, "request_id", "req-unknown"),
    }
