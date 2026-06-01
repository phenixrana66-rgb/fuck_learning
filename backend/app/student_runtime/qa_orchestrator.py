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
from backend.app.student_runtime.qa_image_storage import load_qa_image_as_data_url, storage_key_from_url
from backend.app.student_runtime.qa_prompt_builder import (
    DEFAULT_IMAGE_ONLY_QUESTION,
    PROMPT_VERSION,
    build_prompt,
    build_system_prompt,
)
from backend.app.student_runtime.qa_retrieval_service import build_qa_context_bundle
from backend.app.student_runtime.qa_runtime_config_service import StudentQARuntimeConfig, get_student_qa_runtime_config


def answer_question(
    db: Session,
    *,
    lesson_id: str | int | None,
    section_id: str | int | None,
    page_no: int | None,
    question: str,
    attachments: list[dict[str, Any]] | None = None,
    history: list[dict[str, str]] | None = None,
    runtime_config: StudentQARuntimeConfig | None = None,
    include_debug: bool = False,
    record_trace: bool = True,
) -> dict[str, Any] | None:
    if not section_id:
        return None
    image_data_urls = _collect_multimodal_image_data_urls(attachments or [])
    effective_question = (question or "").strip() or (DEFAULT_IMAGE_ONLY_QUESTION if image_data_urls else "")
    effective_runtime_config = runtime_config or get_student_qa_runtime_config(db)
    bundle = build_qa_context_bundle(
        db,
        lesson_id,
        section_id,
        page_no,
        effective_question,
        runtime_config=effective_runtime_config,
    )
    settings = get_settings()
    if effective_question and bundle.get("questionIntent") == "definition" and bundle.get("faq_candidates") and not image_data_urls:
        direct_result = _build_direct_faq_answer(bundle)
        return _compose_answer_response(
            direct_result,
            bundle=bundle,
            runtime_config=effective_runtime_config,
            include_debug=include_debug,
            latency_ms=0,
            mode="direct_faq",
            used_fallback=False,
            has_images=bool(image_data_urls),
        )
    if not settings.dashscope_api_key:
        fallback = interact_with_section_context(db, lesson_id, section_id, effective_question, page_no)
        return _compose_answer_response(
            fallback,
            bundle=bundle,
            runtime_config=effective_runtime_config,
            include_debug=include_debug,
            latency_ms=0,
            mode="context_fallback",
            used_fallback=True,
            has_images=bool(image_data_urls),
        )

    prompt = build_prompt(bundle, effective_question, history=history)
    started = time.perf_counter()
    try:
        client = DashScopeClient(runtime_config=effective_runtime_config)
        raw = (
            client.chat_multimodal_completion(prompt=prompt, image_data_urls=image_data_urls, system_prompt=build_system_prompt())
            if image_data_urls
            else client.chat_completion(prompt=prompt, system_prompt=build_system_prompt())
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        parsed = _parse_model_payload(raw["text"])
        result = _normalize_model_payload(parsed, bundle)
        if _should_fallback_to_context_answer(result["answer"], bundle):
            fallback = interact_with_section_context(db, lesson_id, section_id, effective_question, page_no)
            return _compose_answer_response(
                fallback,
                bundle=bundle,
                runtime_config=effective_runtime_config,
                include_debug=include_debug,
                latency_ms=latency_ms,
                mode="context_fallback",
                used_fallback=True,
                has_images=bool(image_data_urls),
            )
        if record_trace:
            record_qa_answer_trace(
                db,
                {
                    "lesson_id": bundle.get("section", {}).get("lessonDbId"),
                    "section_id": bundle.get("section", {}).get("sectionDbId"),
                    "page_no": bundle.get("page", {}).get("pageNo"),
                    "model_provider": settings.qa_llm_provider,
                    "model_name": effective_runtime_config.actual_chat_model(has_images=bool(image_data_urls)),
                    "embedding_model": effective_runtime_config.qa_embedding_model,
                    "faq_hit_ids_json": [item["faqId"] for item in bundle.get("faq_candidates", [])],
                    "context_chunk_ids_json": [item["chunkId"] for item in bundle.get("context_chunks", [])],
                    "prompt_version": PROMPT_VERSION,
                    "latency_ms": latency_ms,
                    "confidence_score": result.get("confidenceScore"),
                },
            )
        return _compose_answer_response(
            result,
            bundle=bundle,
            runtime_config=effective_runtime_config,
            include_debug=include_debug,
            latency_ms=latency_ms,
            mode="model",
            used_fallback=False,
            has_images=bool(image_data_urls),
        )
    except Exception:
        fallback = interact_with_section_context(db, lesson_id, section_id, effective_question, page_no)
        return _compose_answer_response(
            fallback,
            bundle=bundle,
            runtime_config=effective_runtime_config,
            include_debug=include_debug,
            latency_ms=None,
            mode="context_fallback",
            used_fallback=True,
            has_images=bool(image_data_urls),
        )


def _compose_answer_response(
    payload: dict[str, Any] | None,
    *,
    bundle: dict[str, Any],
    runtime_config: StudentQARuntimeConfig,
    include_debug: bool,
    latency_ms: int | None,
    mode: str,
    used_fallback: bool,
    has_images: bool,
) -> dict[str, Any]:
    data = payload or {}
    response = {
        "answer": data.get("answer") or "",
        "relatedKnowledgePoints": data.get("relatedKnowledgePoints") or [],
        "understandingLevel": data.get("understandingLevel") or "partial",
        "understandingLabel": data.get("understandingLabel") or _understanding_label(data.get("understandingLevel") or "partial"),
        "resumeAnchor": data.get("resumeAnchor") or {"anchorId": "", "anchorTitle": "", "pageNo": 1},
        "weakPoints": data.get("weakPoints") or [],
    }
    if include_debug:
        response["debug"] = _build_debug_payload(
            bundle,
            runtime_config=runtime_config,
            latency_ms=latency_ms,
            mode=mode,
            used_fallback=used_fallback,
            has_images=has_images,
        )
    return response


def _build_debug_payload(
    bundle: dict[str, Any],
    *,
    runtime_config: StudentQARuntimeConfig,
    latency_ms: int | None,
    mode: str,
    used_fallback: bool,
    has_images: bool,
) -> dict[str, Any]:
    return {
        "promptVersion": PROMPT_VERSION,
        "questionIntent": bundle.get("questionIntent") or "",
        "mode": mode,
        "usedFallback": used_fallback,
        "latencyMs": latency_ms,
        "runtimeConfig": {
            **runtime_config.to_dict(),
            "actualModel": runtime_config.actual_chat_model(has_images=has_images),
        },
        "faqCandidates": bundle.get("faq_candidates") or [],
        "contextChunks": bundle.get("context_chunks") or [],
        "knowledgePoints": bundle.get("knowledge_points") or [],
    }


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


def _collect_multimodal_image_data_urls(attachments: list[dict[str, Any]]) -> list[str]:
    image_data_urls: list[str] = []
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        if str(attachment.get("type") or "image") != "image":
            continue
        data_url = str(attachment.get("dataUrl") or "").strip()
        if data_url:
            image_data_urls.append(data_url)
            continue
        storage_key = str(attachment.get("storageKey") or "").strip()
        if not storage_key:
            storage_key = storage_key_from_url(str(attachment.get("url") or "").strip()) or ""
        if storage_key:
            image_data_urls.append(load_qa_image_as_data_url(storage_key, mime_type=str(attachment.get("mimeType") or "")))
    return image_data_urls
