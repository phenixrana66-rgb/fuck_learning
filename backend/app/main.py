from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.common.config import get_settings
from backend.app.common.exceptions import register_exception_handlers
from backend.app.common.request_context import request_context_middleware
from backend.app.compat.router import router as compat_router
from backend.app.lesson.voice_storage import get_voice_cache_dir
from backend.app.progress.router import router as progress_router
from backend.app.qa.router import router as qa_router
from backend.app.student_runtime.router import router as student_router
from backend.app.teacher_runtime.extra_router import router as teacher_extra_router


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
COURSEWARE_PREVIEW_ROOT = PROJECT_ROOT / "public" / "courseware-previews"


def create_app() -> FastAPI:
    settings = get_settings()
    EXAMPLES_ROOT.mkdir(parents=True, exist_ok=True)
    COURSEWARE_PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    app.middleware("http")(request_context_middleware)
    register_exception_handlers(app)
    app.mount("/mock-remote/examples", StaticFiles(directory=str(PROJECT_ROOT / "examples")), name="mock-remote-examples")
    app.mount("/cache/voice", StaticFiles(directory=str(get_voice_cache_dir())), name="lesson-audio-cache")
    app.mount("/courseware-previews", StaticFiles(directory=str(COURSEWARE_PREVIEW_ROOT)), name="courseware-previews")

    app.include_router(teacher_extra_router, prefix=settings.api_prefix)
    app.include_router(compat_router, prefix=settings.api_prefix)
    app.include_router(qa_router, prefix=settings.api_prefix)
    app.include_router(progress_router, prefix=settings.api_prefix)
    app.include_router(student_router, prefix="/student-api")

    return app


app = create_app()
