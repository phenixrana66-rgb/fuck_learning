from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.common.exceptions import ApiError, api_error_handler
from backend.app.common.request_context import request_context_middleware
from backend.app.student_runtime.router import router as student_router


def create_student_app() -> FastAPI:
    app = FastAPI(title="Student Plugin Backend")
    app.add_middleware(CORSMiddleware, allow_origin_regex=r"https?://.*", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.middleware("http")(request_context_middleware)
    app.add_exception_handler(ApiError, api_error_handler)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _exc: Exception):
        return JSONResponse(status_code=500, content={"code": 500, "msg": "学生端服务异常", "data": None, "requestId": getattr(request.state, "request_id", "req-unknown")})

    app.include_router(student_router)
    return app


app = create_student_app()
