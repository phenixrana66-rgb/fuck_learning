from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError


class ApiError(Exception):
    def __init__(self, code: int, msg: str, status_code: int = 400, data: Any | None = None):
        self.code = code
        self.msg = msg
        self.status_code = status_code
        self.data = data or {}
        super().__init__(msg)


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ApiError):
        exc = ApiError(code=500, msg="服务端异常", status_code=500)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "msg": exc.msg,
            "data": exc.data,
            "requestId": getattr(request.state, "request_id", "req-unknown"),
        },
    )


def _map_unexpected_error(exc: Exception) -> tuple[int, int, str]:
    if isinstance(exc, OperationalError):
        raw = str(exc).lower()
        if "access denied" in raw:
            return 503, 503, "数据库认证失败，请检查 A12_DB_URL 或 A12_DB_USER / A12_DB_PASSWORD 配置"
        if "can't connect" in raw or "connection refused" in raw:
            return 503, 503, "数据库连接失败，请确认 MySQL 已启动且连接参数正确"
        return 503, 503, "数据库不可用，请检查 MySQL 连接配置"

    return 500, 500, "服务端异常"


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    status_code, code, msg = _map_unexpected_error(exc)
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "msg": msg,
            "data": {},
            "requestId": getattr(request.state, "request_id", "req-unknown"),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, cast(Any, api_error_handler))
    app.add_exception_handler(Exception, cast(Any, unexpected_error_handler))
