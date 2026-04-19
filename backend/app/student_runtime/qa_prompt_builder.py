from __future__ import annotations

import json
from typing import Any


PROMPT_VERSION = "qa-rag-v2"


def build_system_prompt() -> str:
    return (
        "你是一名面向高校课程学习场景的智能助教。"
        "请优先依据课程 FAQ、当前章节/PPT 全文上下文、当前页内容和知识点回答问题。"
        "其中整份 PPT 是默认参考范围，当前页内容具有更高权重。"
        "只有在需要解释、整合、通俗表达时，才基于检索结果进行教学化生成。"
        "如果整份 PPT 的上下文已经足以支撑回答，就不要直接说信息不足。"
        "输出必须是 JSON，不要附带 Markdown、代码块或额外说明。"
    )


def build_prompt(bundle: dict[str, Any], question: str, history: list[dict[str, str]] | None = None) -> str:
    payload = {
        "question": question,
        "lessonContext": bundle.get("lesson"),
        "questionIntent": bundle.get("questionIntent"),
        "retrievalStrategy": {
            "defaultScope": "whole_ppt",
            "currentPageWeight": "high",
            "sectionWeight": "medium",
        },
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
        "1. 如果 questionIntent=definition 且 faqCandidates 非空，优先复用 FAQ 标准答案，不要自由发挥。\n"
        "2. 默认把整份 PPT/整章内容作为参考范围，不要只依据当前页作答。\n"
        "3. 如果当前页与问题直接相关，优先使用当前页证据；其余页内容用于补充定义、上下文、前后联系和跨页总结。\n"
        "4. 如果问题是总结、比较、关系、章节主线或全局理解类问题，优先综合整份 PPT 的相关内容，再用当前页内容做重点补充。\n"
        "5. 仅当 pageContext.hasMeaningfulContent=true 时，pageContext.parsedContent 才能作为强证据。\n"
        "6. answer 使用简洁中文，先给直接答案，再补充一两句解释。\n"
        "7. relatedKnowledgePoints 只返回与当前问题直接相关的知识点。\n"
        "8. understandingLevel 只能是 weak、partial、complete。\n"
        "9. resumeAnchor 尽量返回最适合继续学习的锚点；没有明确锚点时返回当前页。\n"
        "10. confidenceScore 返回 0 到 1 之间的小数。\n"
        "11. 只有在 FAQ、整份 PPT 上下文、当前页和知识点都无法支持回答时，才说明信息不足。\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
