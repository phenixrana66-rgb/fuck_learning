from datetime import datetime
from uuid import uuid4

from backend.app.common.exceptions import ApiError
from backend.app.script.schemas import GenerateScriptRequest, ScriptDetail, ScriptSection, ScriptSummary, UpdateScriptRequest

_SCRIPT_STORE: dict[str, ScriptDetail] = {}


def generate_script(payload: GenerateScriptRequest) -> ScriptSummary:
    script_id = _build_id("script")
    sections = [
        ScriptSection(
            sectionId="sec001",
            sectionName="开场引入",
            content=payload.customOpening or "同学们好，下面我们进入本节内容的核心讲解。",
            duration=15,
            relatedChapterId="chap-001",
        ),
        ScriptSection(
            sectionId="sec002",
            sectionName="核心知识点讲解",
            content="本节先解释概念定义，再给出核心重点与课堂理解路径。",
            duration=45,
            relatedChapterId="chap-001",
            relatedPage="1-3",
            keyPoints=["概念定义", "关键特征", "课堂理解方法"],
        ),
    ]
    detail = ScriptDetail(
        scriptId=script_id,
        parseId=payload.parseId,
        teachingStyle=payload.teachingStyle,
        speechSpeed=payload.speechSpeed,
        scriptStructure=sections,
    )
    _SCRIPT_STORE[script_id] = detail
    return ScriptSummary(
        scriptId=script_id,
        scriptStructure=sections,
        editUrl=f"/teacher/scripts/{script_id}/edit",
        audioGenerateUrl="/api/v1/lesson/generateAudio",
    )


def get_script(script_id: str) -> ScriptDetail:
    script = _SCRIPT_STORE.get(script_id)
    if not script:
        raise ApiError(code=404, msg="脚本不存在", status_code=404)
    return script


def update_script(script_id: str, payload: UpdateScriptRequest) -> ScriptDetail:
    script = get_script(script_id)
    script.scriptStructure = payload.scriptStructure
    script.version += 1
    return script


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"
