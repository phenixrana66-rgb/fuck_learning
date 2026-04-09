from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, code: int, msg: str, status_code: int = 400, data: Any | None = None):
        self.code = code
        self.msg = msg
        self.status_code = status_code
        self.data = data or {}
        super().__init__(msg)


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ApiError):
        exc = ApiError(code=500, msg="服务端错误", status_code=500)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "msg": exc.msg,
            "data": exc.data,
            "requestId": getattr(request.state, "request_id", "req-unknown"),
        },
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "msg": "服务端错误",
            "data": {},
            "requestId": getattr(request.state, "request_id", "req-unknown"),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, cast(Any, api_error_handler))
    app.add_exception_handler(Exception, cast(Any, unexpected_error_handler))
