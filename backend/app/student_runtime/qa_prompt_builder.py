from __future__ import annotations

import json
from typing import Any


PROMPT_VERSION = "qa-rag-v1"


def build_system_prompt() -> str:
    return (
        "你是一名面向高校课程学习场景的智能助教。"
        "知识库采用三层结构：结构化FAQ知识库、课件内容知识库和大模型生成层。"
        "定义类问题优先使用 FAQ 标准答案；课堂上下文问题优先使用当前课程、当前章节、当前页以及整章课件内容。"
        "只有在需要解释、整合、通俗表达时，才基于检索结果进行教学化生成。"
        "如果整章上下文足以支持解释，就不要直接回答信息不足。"
        "如果无法给出精确公式或严格定义，可以先基于当前章节内容做谨慎解释，再指出建议回看的知识点。"
        "只有在 FAQ、整章上下文、当前页和知识点都无法支持回答时，才允许明确说明信息不足。"
        "输出必须是 JSON，不要附加 Markdown、代码块或额外解释。"
    )


def build_prompt(bundle: dict[str, Any], question: str, history: list[dict[str, str]] | None = None) -> str:
    payload = {
        "question": question,
        "lessonContext": bundle.get("lesson"),
        "questionIntent": bundle.get("questionIntent"),
        "sectionContext": bundle.get("section"),
        "pageContext": bundle.get("page"),
        "contextChunks": bundle.get("context_chunks"),
        "knowledgePoints": bundle.get("knowledge_points"),
        "faqCandidates": bundle.get("faq_candidates"),
        "history": history or [],
        "outputSchema": {
            "answer": "string",
            "relatedKnowledgePoints": ["string"],
            "understandingLevel": "weak|partial|complete",
            "weakPoints": ["string"],
            "resumeAnchor": {
                "anchorId": "string",
                "anchorTitle": "string",
                "pageNo": 1,
            },
            "confidenceScore": 0.0,
        },
    }
    return (
        "请根据以下 JSON 上下文回答用户问题，并严格只返回 JSON。\n"
        "规则：\n"
        "1. 若 questionIntent=definition 且 faqCandidates 非空，优先复用 FAQ 标准答案，不要自由发挥。\n"
        "2. 若问题与课堂内容有关，优先使用 sectionContext.chapterContextText、contextChunks、knowledgePoints。\n"
        "3. 仅当问题需要解释、整合、通俗表达时，再基于检索结果做教学化生成。\n"
        "4. pageContext.parsedContent 只有在 pageContext.hasMeaningfulContent=true 时才作为有效依据。\n"
        "5. answer 使用简洁中文，先给直接答案，再补充一两句解释。\n"
        "6. relatedKnowledgePoints 只返回与当前问题直接相关的知识点。\n"
        "7. understandingLevel 只能是 weak、partial、complete。\n"
        "8. resumeAnchor 尽量返回最适合继续学习的锚点；没有明确锚点时返回当前页。\n"
        "9. confidenceScore 返回 0 到 1 之间的小数。\n"
        "10. 只有在 FAQ、整章上下文、当前页和知识点都无法支持回答时，才说明信息不足。\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
