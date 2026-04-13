from fastapi import FastAPI

from backend.app.common.config import get_settings
from backend.app.common.exceptions import register_exception_handlers
from backend.app.common.request_context import request_context_middleware
from backend.app.compat.router import router as compat_router
from backend.app.progress.router import router as progress_router
from backend.app.qa.router import router as qa_router
from backend.app.student_runtime.router import router as student_router


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    app.middleware("http")(request_context_middleware)
    register_exception_handlers(app)

    app.include_router(compat_router)
    app.include_router(qa_router, prefix=settings.api_prefix)
    app.include_router(progress_router, prefix=settings.api_prefix)
    app.include_router(student_router, prefix="/student-api")

    return app


app = create_app()
