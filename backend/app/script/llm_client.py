import json
import re
from typing import Any

import httpx

from backend.app.cir.schemas import CirSlideContent
from backend.app.common.config import get_settings
from backend.app.common.exceptions import ApiError
from backend.app.script.schemas import GenerateScriptRequest


def generate_script_section_with_llm(
    payload: GenerateScriptRequest,
    *,
    section_name: str,
    section_key_points: list[str],
    page_contents: list[CirSlideContent],
    previous_summary: str | None,
    next_section_name: str | None,
    is_first_section: bool,
    is_last_section: bool,
) -> dict[str, str]:
    settings = get_settings()
    if not settings.llm_api_key:
        raise ApiError(code=500, msg='未配置 A12_LLM_API_KEY，无法调用脚本生成 LLM 接口', status_code=500)

    request_payload = {
        'model': settings.llm_model,
        'temperature': 0.55,
        'stream': False,
        'messages': [
            {
                'role': 'system',
                'content': _build_system_prompt(),
            },
            {
                'role': 'user',
                'content': _build_user_prompt(
                    payload,
                    section_name=section_name,
                    section_key_points=section_key_points,
                    page_contents=page_contents,
                    previous_summary=previous_summary,
                    next_section_name=next_section_name,
                    is_first_section=is_first_section,
                    is_last_section=is_last_section,
                ),
            },
        ],
    }

    base_url = settings.llm_api_base_url.rstrip('/')
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(
                f'{base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {settings.llm_api_key}',
                    'Content-Type': 'application/json',
                },
                json=request_payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise ApiError(code=502, msg=f'脚本生成 LLM 接口返回异常：{detail}', status_code=502) from exc
    except httpx.HTTPError as exc:
        raise ApiError(code=502, msg=f'调用脚本生成 LLM 接口失败：{exc}', status_code=502) from exc

    response_json = _parse_llm_response_json(response)
    content = _extract_message_content(response_json)
    return _extract_section_result(content)


def _build_system_prompt() -> str:
    return (
        '你是高校课堂讲稿写作助手。'
        '请根据当前章节的课件内容，生成可以直接拿来授课的中文讲稿。'
        '讲稿必须非常口语化、循循善诱，像老师面对学生讲解，不要像摘要器、解说词或系统提示。'
        '必须严格围绕课件原始内容展开，优先解释定义、分类、结构、规则、步骤、表格信息和举例。'
        '不要写“课件标题聚焦”“结合课件内容”“课堂上可以把重点收束为”这类元话术。'
        '不要复读“理解、掌握、复述”这类教学目标句。'
        '除 VIN、WMI 等术语外，不要混入英文句式。'
        '只输出严格 JSON，格式为 {"content": "...", "summaryForNext": "..."}。'
        'content 是当前章节讲稿；summaryForNext 是给下一章节使用的 1 到 2 句承接总结。'
    )


def _build_user_prompt(
    payload: GenerateScriptRequest,
    *,
    section_name: str,
    section_key_points: list[str],
    page_contents: list[CirSlideContent],
    previous_summary: str | None,
    next_section_name: str | None,
    is_first_section: bool,
    is_last_section: bool,
) -> str:
    return json.dumps(
        {
            'teachingStyle': payload.teachingStyle,
            'speechSpeed': payload.speechSpeed,
            'customOpening': payload.customOpening,
            'currentSection': {
                'sectionName': section_name,
                'keyPoints': section_key_points,
                'pageContents': _serialize_page_contents(page_contents),
                'isFirstSection': is_first_section,
                'isLastSection': is_last_section,
            },
            'previousSectionSummary': previous_summary,
            'nextSectionName': next_section_name,
            'requirements': [
                'content 只写当前章节，不要把整份课件都概述一遍。',
                '如果是首章且 customOpening 非空，请自然融入开场白。',
                '开头要自然切入本章主题，不要机械重复固定模板。',
                '中间要把课件里的核心事实讲明白，可以适度补一句老师式解释，但不能脱离原始内容。',
                '如果存在下一章节，结尾要自然过渡到下一章节。',
                '如果已经是最后一章节，结尾做课堂收束。',
                'summaryForNext 保持简短，只概括已讲内容和下一章如何承接。',
            ],
        },
        ensure_ascii=False,
    )


def _serialize_page_contents(page_contents: list[CirSlideContent]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for page_content in page_contents:
        serialized.append(
            {
                'slideNumber': page_content.slideNumber,
                'title': page_content.title,
                'bodyTexts': page_content.bodyTexts,
                'tableTexts': page_content.tableTexts,
                'notes': page_content.notes,
            }
        )
    return serialized


def _parse_llm_response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        response_json = response.json()
    except ValueError as exc:
        content_type = response.headers.get('content-type', 'unknown')
        body_preview = response.text[:300].strip() or '<empty body>'
        raise ApiError(
            code=502,
            msg=(
                '脚本生成 LLM 接口返回了非 JSON 内容，'
                f'status={response.status_code}, content-type={content_type}, body={body_preview}'
            ),
            status_code=502,
        ) from exc

    if not isinstance(response_json, dict):
        raise ApiError(code=502, msg='脚本生成 LLM 接口返回格式异常：顶层不是 JSON 对象', status_code=502)
    return response_json


def _extract_message_content(response_json: dict[str, Any]) -> str:
    choices = response_json.get('choices')
    if not isinstance(choices, list) or not choices:
        raise ApiError(code=502, msg='脚本生成 LLM 接口返回格式异常：缺少 choices', status_code=502)

    message = choices[0].get('message')
    if not isinstance(message, dict):
        raise ApiError(code=502, msg='脚本生成 LLM 接口返回格式异常：缺少 message', status_code=502)

    content = message.get('content')
    if not isinstance(content, str) or not content.strip():
        raise ApiError(code=502, msg='脚本生成 LLM 接口返回格式异常：缺少 content', status_code=502)
    return content


def _extract_section_result(content: str) -> dict[str, str]:
    parsed = _extract_json_object(content)
    section_content = parsed.get('content')
    summary_for_next = parsed.get('summaryForNext')
    if not isinstance(section_content, str) or not section_content.strip():
        raise ApiError(code=502, msg='脚本生成 LLM 返回格式异常：缺少 content', status_code=502)

    normalized_content = section_content.strip()
    normalized_summary = (
        summary_for_next.strip()
        if isinstance(summary_for_next, str) and summary_for_next.strip()
        else _build_fallback_summary(normalized_content)
    )
    return {
        'content': normalized_content,
        'summaryForNext': normalized_summary,
    }


def _build_fallback_summary(content: str) -> str:
    normalized = ' '.join(part.strip() for part in content.splitlines() if part.strip())
    parts = [segment.strip() for segment in re.split(r'[。！？!?]', normalized) if segment.strip()]
    if not parts:
        return normalized[:60] or '上一章节已经讲完。'
    summary = parts[-1]
    return summary[:60] if len(summary) > 60 else summary


def _extract_json_object(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith('```'):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = '\n'.join(lines[1:-1]).strip()

    start = stripped.find('{')
    end = stripped.rfind('}')
    if start == -1 or end == -1 or end <= start:
        raise ApiError(code=502, msg='脚本生成 LLM 返回的结果无法解析为 JSON', status_code=502)
    try:
        parsed = json.loads(stripped[start : end + 1])
    except ValueError as exc:
        raise ApiError(code=502, msg='脚本生成 LLM 返回的结果无法解析为 JSON', status_code=502) from exc

    if not isinstance(parsed, dict):
        raise ApiError(code=502, msg='脚本生成 LLM 返回格式异常：顶层不是对象', status_code=502)
    return parsed
