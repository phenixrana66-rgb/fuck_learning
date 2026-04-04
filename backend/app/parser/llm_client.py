import json
from typing import Any

import httpx

from backend.app.common.config import get_settings
from backend.app.common.exceptions import ApiError
from backend.app.parser.schemas import ExtractedPresentation, OutlineResult


def generate_outline_with_llm(
    course_id: str,
    extracted: ExtractedPresentation,
    is_extract_key_point: bool,
) -> OutlineResult:
    settings = get_settings()
    if not settings.llm_api_key:
        raise ApiError(code=500, msg="未配置 A12_LLM_API_KEY，无法调用 PPT 结构化 LLM 接口", status_code=500)

    payload = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是课件结构化分析助手。"
                    "你会根据 PPT 每页文本输出严格 JSON，结构必须为："
                    '{"title": "课程标题", "chapters": [{"name": "章节名", "subChapters": [{"name": "小节名", '
                    '"pageStart": 1, "pageEnd": 2, "isKeyPoint": true}]}]}。'
                    "pageStart/pageEnd 使用 slideNumber。"
                    "所有页必须被顺序覆盖，页码不能超出范围，章节和小节名称必须简洁明确。"
                    "不要输出 JSON 之外的任何说明。"
                ),
            },
            {
                "role": "user",
                "content": _build_user_prompt(course_id, extracted, is_extract_key_point),
            },
        ],
    }

    base_url = settings.llm_api_base_url.rstrip("/")
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise ApiError(code=502, msg=f"LLM 接口返回异常：{detail}", status_code=502) from exc
    except httpx.HTTPError as exc:
        raise ApiError(code=502, msg=f"调用 LLM 接口失败：{exc}", status_code=502) from exc

    response_json = _parse_llm_response_json(response)
    content = _extract_message_content(response_json)
    try:
        return OutlineResult.model_validate(_extract_json_object(content))
    except Exception as exc:  # noqa: BLE001
        raise ApiError(code=502, msg="LLM 返回的结构化结果无法解析", status_code=502) from exc


def _build_user_prompt(course_id: str, extracted: ExtractedPresentation, is_extract_key_point: bool) -> str:
    slide_payload: list[dict[str, Any]] = []
    for slide in extracted.slides:
        slide_payload.append(
            {
                "slideNumber": slide.slideNumber,
                "title": slide.title,
                "bodyTexts": slide.bodyTexts[:8],
                "tableTexts": slide.tableTexts[:4],
                "notes": slide.notes[:500] if slide.notes else None,
            }
        )

    return json.dumps(
        {
            "courseId": course_id,
            "isExtractKeyPoint": is_extract_key_point,
            "slideCount": len(extracted.slides),
            "slides": slide_payload,
            "requirements": [
                "至少输出 1 个 chapter",
                "每个 chapter 至少输出 1 个 subChapter",
                "按页码顺序组织，不要跳页",
                "如果某几页内容很少，可以合并为一个 subChapter",
                "isKeyPoint 应根据标题和正文是否属于核心概念、定义、方法或总结来判断",
            ],
        },
        ensure_ascii=False,
    )


def _extract_message_content(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ApiError(code=502, msg="LLM 接口返回格式异常：缺少 choices", status_code=502)

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ApiError(code=502, msg="LLM 接口返回格式异常：缺少 message", status_code=502)

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ApiError(code=502, msg="LLM 接口返回格式异常：缺少 content", status_code=502)
    return content


def _parse_llm_response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        response_json = response.json()
    except ValueError as exc:
        content_type = response.headers.get("content-type", "unknown")
        body_preview = response.text[:300].strip()
        if not body_preview:
            body_preview = "<empty body>"
        raise ApiError(
            code=502,
            msg=(
                "LLM 接口返回了非 JSON 内容："
                f"status={response.status_code}, content-type={content_type}, body={body_preview}"
            ),
            status_code=502,
        ) from exc

    if not isinstance(response_json, dict):
        raise ApiError(code=502, msg="LLM 接口返回格式异常：顶层不是 JSON 对象", status_code=502)
    return response_json


def _extract_json_object(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found")
    return json.loads(stripped[start : end + 1])
