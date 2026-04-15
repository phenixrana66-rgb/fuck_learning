import json
import re
from typing import Any

import httpx

from backend.app.cir.schemas import CIR, LessonNode
from backend.app.common.config import get_settings
from backend.app.common.exceptions import ApiError
from backend.app.script.schemas import GenerateScriptRequest, ScriptSection

_BANNED_PATTERNS = (
    re.compile(r'\bPage\s*\d+', re.IGNORECASE),
    re.compile(r'The slide', re.IGNORECASE),
    re.compile(r'The table', re.IGNORECASE),
    re.compile(r'speaker notes', re.IGNORECASE),
)
_TRANSITION_MARKERS = ('接着', '继续', '进一步', '下面', '随后', '在此基础上', '顺着这个思路', '过渡到')
_SUMMARY_MARKERS = ('最后', '总结', '回顾', '整体来看', '到这里', '归纳起来')


def generate_script_sections_with_llm(
    cir: CIR,
    payload: GenerateScriptRequest,
    sections: list[ScriptSection],
    section_nodes: dict[str, LessonNode],
) -> dict[str, str]:
    settings = get_settings()
    if not settings.llm_api_key:
        raise ApiError(code=500, msg='未配置 A12_LLM_API_KEY，无法调用脚本生成 LLM 接口', status_code=500)

    system_prompt = _build_system_prompt()
    messages: list[dict[str, str]] = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': _build_user_prompt(cir, payload, sections, section_nodes)},
    ]

    last_errors: list[str] = []
    for _ in range(2):
        content = _request_completion(messages, settings)
        result = _extract_section_contents(content)
        validation_errors = _validate_section_contents(result, payload, sections)
        if not validation_errors:
            return result
        last_errors = validation_errors
        messages.extend(
            [
                {'role': 'assistant', 'content': content},
                {'role': 'user', 'content': _build_revision_prompt(validation_errors)},
            ]
        )

    error_text = '；'.join(last_errors[:3]) if last_errors else '输出未通过质量校验'
    raise ApiError(code=502, msg=f'脚本生成 LLM 输出质量不足：{error_text}', status_code=502)


def _build_system_prompt() -> str:
    return (
        '你是高校教师讲稿生成助手。'
        '你会根据课件结构、知识点和页面原始内容，为每个 section 生成可直接授课的中文讲稿。'
        '你必须输出严格 JSON，格式为 {"sections": [{"sectionId": "sec001", "content": "..."}] }。'
        '不要输出 JSON 之外的任何说明。'
        '每个 content 都必须是自然中文，口吻像老师在课堂上讲解。'
        '每个 section 的讲稿都要包含三个语义动作：自然引入、贴合课件事实的讲解、承接下一节的过渡或总结。'
        '讲解必须优先使用 pageContents 中的标题、正文、表格和备注，不要只复述 sectionName、summary 或 keyPoints。'
        '除 VIN、WMI 等术语外，不要混入英文句式，不要写 Page、slide、table、speaker notes 这类元描述。'
        '不要照抄“理解、掌握、复述”这类教学目标模板，要把具体知识讲出来。'
    )


def _request_completion(messages: list[dict[str, str]], settings) -> str:
    request_payload = {
        'model': settings.llm_model,
        'temperature': 0.35,
        'stream': False,
        'messages': messages,
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
    return _extract_message_content(response_json)


def _build_user_prompt(
    cir: CIR,
    payload: GenerateScriptRequest,
    sections: list[ScriptSection],
    section_nodes: dict[str, LessonNode],
) -> str:
    chapter_lookup = {chapter.chapterId: chapter.chapterName for chapter in cir.chapters}
    ordered_sections: list[dict[str, Any]] = []

    for index, section in enumerate(sections):
        node = section_nodes.get(section.sectionId)
        previous_section = sections[index - 1] if index > 0 else None
        next_section = sections[index + 1] if index + 1 < len(sections) else None
        ordered_sections.append(
            {
                'sectionId': section.sectionId,
                'sectionName': section.sectionName,
                'relatedChapterId': section.relatedChapterId,
                'relatedChapterName': chapter_lookup.get(section.relatedChapterId or ''),
                'relatedPage': section.relatedPage,
                'sectionPosition': _section_position(index, len(sections)),
                'previousSectionName': previous_section.sectionName if previous_section else None,
                'nextSectionName': next_section.sectionName if next_section else None,
                'nodeSummary': node.summary if node else '',
                'keyPoints': section.keyPoints,
                'pageContents': _serialize_page_contents(node.pageContents if node else []),
            }
        )

    return json.dumps(
        {
            'courseTitle': cir.title,
            'teachingStyle': payload.teachingStyle,
            'speechSpeed': payload.speechSpeed,
            'customOpening': payload.customOpening,
            'requirements': [
                '每个 section 都必须返回一段完整讲稿，不能遗漏任何 sectionId。',
                '首段若 customOpening 非空，必须自然融入开场白。',
                '中间段必须有承接上一节并引向下一节的过渡语。',
                '最后一段必须做收束或总结，不能突然结束。',
                '讲解内容要基于 pageContents 的真实事实展开，优先讲定义、分类、用途、结构、规则、条件、表格信息。',
                '不要写 Page 1 is titled、The slide highlights 这类元描述，也不要输出英文模板。',
            ],
            'sections': ordered_sections,
        },
        ensure_ascii=False,
    )


def _section_position(index: int, total: int) -> str:
    if total <= 1:
        return 'single'
    if index == 0:
        return 'first'
    if index == total - 1:
        return 'last'
    return 'middle'


def _build_revision_prompt(validation_errors: list[str]) -> str:
    lines = ['你刚才的 JSON 已被解析，但以下 section 没通过质量校验，请直接重新输出完整 JSON：']
    lines.extend(f'- {error}' for error in validation_errors[:8])
    return '\n'.join(lines)


def _serialize_page_contents(page_contents: list[Any]) -> list[dict[str, Any]]:
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


def _extract_section_contents(content: str) -> dict[str, str]:
    parsed = _extract_json_object(content)
    sections = parsed.get('sections')
    if not isinstance(sections, list) or not sections:
        raise ApiError(code=502, msg='脚本生成 LLM 返回格式异常：缺少 sections', status_code=502)

    result: dict[str, str] = {}
    for item in sections:
        if not isinstance(item, dict):
            raise ApiError(code=502, msg='脚本生成 LLM 返回格式异常：section 不是对象', status_code=502)
        section_id = item.get('sectionId')
        section_content = item.get('content')
        if not isinstance(section_id, str) or not section_id.strip():
            raise ApiError(code=502, msg='脚本生成 LLM 返回格式异常：缺少 sectionId', status_code=502)
        if not isinstance(section_content, str) or not section_content.strip():
            raise ApiError(code=502, msg='脚本生成 LLM 返回格式异常：缺少 content', status_code=502)
        result[section_id] = section_content.strip()

    return result


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


def _validate_section_contents(
    generated_contents: dict[str, str],
    payload: GenerateScriptRequest,
    sections: list[ScriptSection],
) -> list[str]:
    errors: list[str] = []
    expected_ids = {section.sectionId for section in sections}
    missing_ids = [section_id for section_id in expected_ids if section_id not in generated_contents]
    if missing_ids:
        errors.append(f'缺少 section：{", ".join(sorted(missing_ids))}')

    for index, section in enumerate(sections):
        content = generated_contents.get(section.sectionId, '')
        if not content:
            continue
        if len(content.strip()) < 60:
            errors.append(f'{section.sectionId} 内容过短，无法形成可讲授的脚本')
        if any(pattern.search(content) for pattern in _BANNED_PATTERNS):
            errors.append(f'{section.sectionId} 含有 Page 或 The slide 之类的英文元描述')
        if _contains_goal_template(content):
            errors.append(f'{section.sectionId} 仍在重复“理解/掌握/复述”式模板目标')
        if _chinese_ratio(content) < 0.55:
            errors.append(f'{section.sectionId} 中文占比过低，疑似混入英文模板')
        if index == 0 and payload.customOpening and not _contains_opening_hint(content, payload.customOpening):
            errors.append(f'{section.sectionId} 没有自然融入自定义开场白')
        if index < len(sections) - 1 and not _has_transition_language(content, sections[index + 1].sectionName):
            errors.append(f'{section.sectionId} 缺少承接下一节的过渡语')
        if index == len(sections) - 1 and not _has_summary_language(content):
            errors.append(f'{section.sectionId} 结尾缺少总结或收束')

    return errors


def _contains_goal_template(content: str) -> bool:
    return all(token in content for token in ('理解', '掌握', '复述'))


def _contains_opening_hint(content: str, opening: str) -> bool:
    normalized_opening = re.sub(r'[\s，。；;：:、！？!?,]', '', opening)
    normalized_content = re.sub(r'[\s，。；;：:、！？!?,]', '', content)
    if not normalized_opening:
        return True
    return normalized_opening[: min(6, len(normalized_opening))] in normalized_content


def _has_transition_language(content: str, next_section_name: str) -> bool:
    return any(marker in content for marker in _TRANSITION_MARKERS) or next_section_name in content


def _has_summary_language(content: str) -> bool:
    return any(marker in content for marker in _SUMMARY_MARKERS)


def _chinese_ratio(content: str) -> float:
    chinese_count = len(re.findall(r'[\u4e00-\u9fff]', content))
    latin_count = len(re.findall(r'[A-Za-z]', content))
    denominator = chinese_count + latin_count
    if denominator == 0:
        return 0.0
    return chinese_count / denominator
