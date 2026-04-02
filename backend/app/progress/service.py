from datetime import datetime
from uuid import uuid4

from backend.app.progress.schemas import AdjustProgressRequest, TrackProgressRequest

_PROGRESS_STORE: dict[str, dict] = {}


def track_progress(payload: TrackProgressRequest) -> dict:
    track_id = _build_id("track")
    _PROGRESS_STORE[track_id] = payload.model_dump()
    return {
        "trackId": track_id,
        "totalProgress": payload.progressPercent,
        "nextSectionSuggest": payload.currentSectionId,
    }


def adjust_progress(payload: AdjustProgressRequest) -> dict:
    adjust_type = "normal"
    supplement_content = None
    continue_section_id = payload.currentSectionId

    if payload.understandingLevel == "partial":
        adjust_type = "supplement"
        supplement_content = {
            "content": "系统建议插入一段补讲内容，帮助学生进一步理解当前章节。",
            "duration": 30,
            "relatedExample": "示例：围绕当前知识点补充一个课堂例题。",
        }
    elif payload.understandingLevel == "none":
        adjust_type = "supplement"
        continue_section_id = _fallback_section_id(payload.currentSectionId)
        supplement_content = {
            "content": "系统建议先回到前置节点进行回补，再返回当前节点继续学习。",
            "duration": 45,
            "relatedExample": "示例：重新解释前置概念，再切回本节。",
        }
    elif payload.understandingLevel == "full":
        adjust_type = "accelerate"

    return {
        "adjustPlan": {
            "continueSectionId": continue_section_id,
            "adjustType": adjust_type,
            "supplementContent": supplement_content,
            "nextSections": [
                {
                    "sectionId": continue_section_id,
                    "adjustedDuration": 60,
                    "isKeyPointStrengthen": payload.understandingLevel != "full",
                }
            ],
        }
    }


def _fallback_section_id(current_section_id: str) -> str:
    if current_section_id.startswith("sec"):
        suffix = current_section_id[3:]
        if suffix.isdigit():
            number = int(suffix)
            if number > 1:
                return f"sec{number - 1:03d}"
    return current_section_id


def _build_id(prefix: str) -> str:
    return f"{prefix}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6]}"
