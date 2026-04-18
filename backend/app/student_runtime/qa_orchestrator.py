from __future__ import annotations

import json
import re
import time
from typing import Any

from sqlalchemy.orm import Session

from backend.app.common.config import get_settings
from backend.app.student_runtime.db_learning_service import interact_with_section_context
from backend.app.student_runtime.db_qa_service import record_qa_answer_trace
from backend.app.student_runtime.qa_dashscope_client import DashScopeClient
from backend.app.student_runtime.qa_prompt_builder import PROMPT_VERSION, build_prompt, build_system_prompt
from backend.app.student_runtime.qa_retrieval_service import build_qa_context_bundle


def answer_question(
    db: Session,
    *,
    lesson_id: str | int | None,
    section_id: str | int | None,
    page_no: int | None,
    question: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    if not section_id:
        return None
    bundle = build_qa_context_bundle(db, lesson_id, section_id, page_no, question)
    settings = get_settings()
    if bundle.get("questionIntent") == "definition" and bundle.get("faq_candidates"):
        return _build_direct_faq_answer(bundle)
    if not settings.dashscope_api_key:
        return interact_with_section_context(db, lesson_id, section_id, question, page_no)

    prompt = build_prompt(bundle, question, history=history)
    started = time.perf_counter()
    try:
        raw = DashScopeClient().chat_completion(prompt=prompt, system_prompt=build_system_prompt())
        latency_ms = int((time.perf_counter() - started) * 1000)
        parsed = _parse_model_payload(raw["text"])
        result = _normalize_model_payload(parsed, bundle)
        if _should_fallback_to_context_answer(result["answer"], bundle):
            return interact_with_section_context(db, lesson_id, section_id, question, page_no)
        record_qa_answer_trace(
            db,
            {
                "lesson_id": bundle.get("section", {}).get("lessonDbId"),
                "section_id": bundle.get("section", {}).get("sectionDbId"),
                "page_no": bundle.get("page", {}).get("pageNo"),
                "model_provider": settings.qa_llm_provider,
                "model_name": settings.qa_llm_model,
                "embedding_model": settings.qa_embedding_model,
                "faq_hit_ids_json": [item["faqId"] for item in bundle.get("faq_candidates", [])],
                "context_chunk_ids_json": [item["chunkId"] for item in bundle.get("context_chunks", [])],
                "prompt_version": PROMPT_VERSION,
                "latency_ms": latency_ms,
                "confidence_score": result.get("confidenceScore"),
            },
        )
        return {
            "answer": result["answer"],
            "relatedKnowledgePoints": result["relatedKnowledgePoints"],
            "understandingLevel": result["understandingLevel"],
            "understandingLabel": _understanding_label(result["understandingLevel"]),
            "resumeAnchor": result["resumeAnchor"],
            "weakPoints": result["weakPoints"],
        }
    except Exception:
        return interact_with_section_context(db, lesson_id, section_id, question, page_no)


def _build_direct_faq_answer(bundle: dict[str, Any]) -> dict[str, Any]:
    faq = (bundle.get("faq_candidates") or [None])[0]
    if not faq:
        return {
            "answer": "",
            "relatedKnowledgePoints": [],
            "understandingLevel": "partial",
            "understandingLabel": "部分理解",
            "resumeAnchor": {"anchorId": "", "anchorTitle": "", "pageNo": 1},
            "weakPoints": [],
        }
    page = bundle.get("page") or {}
    section = bundle.get("section") or {}
    related_points = [item["pointName"] for item in (bundle.get("knowledge_points") or [])[:3]]
    return {
        "answer": faq["answer"],
        "relatedKnowledgePoints": related_points,
        "understandingLevel": "complete",
        "understandingLabel": "完全理解",
        "resumeAnchor": {
            "anchorId": str(page.get("anchorId") or ""),
            "anchorTitle": page.get("anchorTitle") or section.get("sectionName") or "",
            "pageNo": int(page.get("pageNo") or 1),
        },
        "weakPoints": [],
    }


def _parse_model_payload(raw_text: str) -> dict[str, Any]:
    stripped = (raw_text or "").strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.S)
        if match:
            stripped = match.group(1)
    return json.loads(stripped)


def _normalize_model_payload(payload: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    page = bundle.get("page") or {}
    section = bundle.get("section") or {}
    related_points = payload.get("relatedKnowledgePoints") or [
        item["pointName"] for item in (bundle.get("knowledge_points") or [])[:3]
    ]
    understanding = payload.get("understandingLevel")
    if understanding not in {"weak", "partial", "complete"}:
        understanding = "partial"
    resume_anchor = payload.get("resumeAnchor") or {}
    return {
        "answer": payload.get("answer") or section.get("summary") or "",
        "relatedKnowledgePoints": related_points[:5],
        "understandingLevel": understanding,
        "weakPoints": (payload.get("weakPoints") or related_points[:2])[:3] if understanding != "complete" else [],
        "resumeAnchor": {
            "anchorId": str(resume_anchor.get("anchorId") or page.get("anchorId") or ""),
            "anchorTitle": resume_anchor.get("anchorTitle") or page.get("anchorTitle") or section.get("sectionName") or "",
            "pageNo": int(resume_anchor.get("pageNo") or page.get("pageNo") or 1),
        },
        "confidenceScore": _normalize_confidence(payload.get("confidenceScore")),
    }


def _normalize_confidence(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if number < 0:
        return 0.0
    if number > 1:
        return 1.0
    return number


def _understanding_label(level: str) -> str:
    return {
        "weak": "未理解",
        "partial": "部分理解",
        "complete": "完全理解",
    }.get(level, "部分理解")


def _should_fallback_to_context_answer(answer: str, bundle: dict[str, Any]) -> bool:
    text = (answer or "").strip()
    if not text:
        return True
    if "信息不足" not in text:
        return False
    section = bundle.get("section") or {}
    if section.get("chapterContextText"):
        return True
    return bool(bundle.get("context_chunks"))
