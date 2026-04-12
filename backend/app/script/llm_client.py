import json
from typing import Any

import httpx

from backend.app.cir.schemas import CIR, LessonNode
from backend.app.common.config import get_settings
from backend.app.common.exceptions import ApiError
from backend.app.script.schemas import GenerateScriptRequest, ScriptSection


def generate_script_sections_with_llm(
    cir: CIR,
    payload: GenerateScriptRequest,
    sections: list[ScriptSection],
    section_nodes: dict[str, LessonNode],
) -> dict[str, str]:
    settings = get_settings()
    if not settings.llm_api_key:
        raise ApiError(code=500, msg="未配置 A12_LLM_API_KEY，无法调用脚本生成 LLM 接口", status_code=500)

    request_payload = {
        "model": settings.llm_model,
        "temperature": 0.4,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是课堂讲稿生成助手。"
                    "你会基于课程结构、关键知识点和课件原始页内容，为每个 section 生成适合教师讲授的中文讲稿。"
                    '你必须输出严格 JSON，格式为：{"sections": [{"sectionId": "sec001", "content": "..."}]}。'
                    "不要输出 JSON 之外的任何说明。"
                    "每个 content 都要自然、可讲述、贴近教学口吻，不要写编号列表。"
                    "讲稿必须优先依据 pageContents 中的标题、正文、表格和备注来展开解释，不能只写概述性导语。"
                    "如果 pageContents 中出现定义、分类、组成、用途、条件、步骤或表格数据，必须把这些具体内容讲出来。"
                    "除首段必要引入外，不要反复使用‘今天我们学习’‘接下来我们进入’这类空泛过渡。"
                    "不要脱离 pageContents 虚构案例，不要只重复 keyPoints。"
                ),
            },
            {
                "role": "user",
                "content": _build_user_prompt(cir, payload, sections, section_nodes),
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
                json=request_payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise ApiError(code=502, msg=f"脚本生成 LLM 接口返回异常：{detail}", status_code=502) from exc
    except httpx.HTTPError as exc:
        raise ApiError(code=502, msg=f"调用脚本生成 LLM 接口失败：{exc}", status_code=502) from exc

    response_json = _parse_llm_response_json(response)
    content = _extract_message_content(response_json)
    return _extract_section_contents(content)
def _build_user_prompt(
    cir: CIR,
    payload: GenerateScriptRequest,
    sections: list[ScriptSection],
    section_nodes: dict[str, LessonNode],
) -> str:
    chapter_lookup = {chapter.chapterId: chapter.chapterName for chapter in cir.chapters}
    section_payload: list[dict[str, Any]] = []
    for section in sections:
        node = section_nodes.get(section.sectionId)
        section_payload.append(
            {
                "sectionId": section.sectionId,
                "sectionName": section.sectionName,
                "relatedChapterId": section.relatedChapterId,
                "relatedChapterName": chapter_lookup.get(section.relatedChapterId or ""),
                "relatedPage": section.relatedPage,
                "nodeSummary": node.summary if node else "",
                "keyPoints": section.keyPoints,
                "pageContents": _serialize_page_contents(node.pageContents if node else []),
            }
        )

    return json.dumps(
        {
            "courseTitle": cir.title,
            "teachingStyle": payload.teachingStyle,
            "speechSpeed": payload.speechSpeed,
            "customOpening": payload.customOpening,
            "requirements": [
                "每个 section 返回一段完整讲稿，不要遗漏任何 sectionId",
                "只输出与给定 sectionId 对应的 content，不要增加额外字段",
                "讲稿应覆盖 sectionName、nodeSummary 和 keyPoints，但必须以 pageContents 里的真实内容为讲解主体",
                "优先把 pageContents 中能直接讲授的概念、定义、分类、组成、条件、表格信息解释清楚",
                "如果 section 覆盖多页，要按页内容自然串起来，而不是只写一段总述",
                "如果 customOpening 非空，只在首段自然融入，不要在后续段落重复",
                "内容要忠于课件主题，不要虚构未提供的事实或案例",
            ],
            "sections": section_payload,
        },
        ensure_ascii=False,
    )


def _serialize_page_contents(page_contents: list[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for page_content in page_contents:
        serialized.append(
            {
                "slideNumber": page_content.slideNumber,
                "title": page_content.title,
                "bodyTexts": page_content.bodyTexts,
                "tableTexts": page_content.tableTexts,
                "notes": page_content.notes,
            }
        )
    return serialized


def _parse_llm_response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        response_json = response.json()
    except ValueError as exc:
        content_type = response.headers.get("content-type", "unknown")
        body_preview = response.text[:300].strip() or "<empty body>"
        raise ApiError(
            code=502,
            msg=(
                "脚本生成 LLM 接口返回了非 JSON 内容："
                f"status={response.status_code}, content-type={content_type}, body={body_preview}"
            ),
            status_code=502,
        ) from exc

    if not isinstance(response_json, dict):
        raise ApiError(code=502, msg="脚本生成 LLM 接口返回格式异常：顶层不是 JSON 对象", status_code=502)
    return response_json


def _extract_message_content(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ApiError(code=502, msg="脚本生成 LLM 接口返回格式异常：缺少 choices", status_code=502)

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ApiError(code=502, msg="脚本生成 LLM 接口返回格式异常：缺少 message", status_code=502)

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ApiError(code=502, msg="脚本生成 LLM 接口返回格式异常：缺少 content", status_code=502)
    return content


def _extract_section_contents(content: str) -> dict[str, str]:
    parsed = _extract_json_object(content)
    sections = parsed.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ApiError(code=502, msg="脚本生成 LLM 返回格式异常：缺少 sections", status_code=502)

    result: dict[str, str] = {}
    for item in sections:
        if not isinstance(item, dict):
            raise ApiError(code=502, msg="脚本生成 LLM 返回格式异常：section 不是对象", status_code=502)
        section_id = item.get("sectionId")
        section_content = item.get("content")
        if not isinstance(section_id, str) or not section_id.strip():
            raise ApiError(code=502, msg="脚本生成 LLM 返回格式异常：缺少 sectionId", status_code=502)
        if not isinstance(section_content, str) or not section_content.strip():
            raise ApiError(code=502, msg="脚本生成 LLM 返回格式异常：缺少 content", status_code=502)
        result[section_id] = section_content.strip()

    return result


def _extract_json_object(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ApiError(code=502, msg="脚本生成 LLM 返回的结果无法解析为 JSON", status_code=502)
    try:
        parsed = json.loads(stripped[start : end + 1])
    except ValueError as exc:
        raise ApiError(code=502, msg="脚本生成 LLM 返回的结果无法解析为 JSON", status_code=502) from exc

    if not isinstance(parsed, dict):
        raise ApiError(code=502, msg="脚本生成 LLM 返回格式异常：顶层不是对象", status_code=502)
    return parsed
