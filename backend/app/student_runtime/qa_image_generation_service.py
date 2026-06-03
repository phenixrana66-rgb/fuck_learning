from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from backend.app.common.exceptions import ApiError
from backend.app.student_runtime.db_learning_service import (
    get_page_context_for_qa,
    get_section_context_for_qa,
    get_section_knowledge_points_for_qa,
)
from backend.app.student_runtime.qa_image_storage import store_qa_image_from_url
from backend.app.student_runtime.qa_provider_adapters import ModelProviderError, build_provider_adapter
from backend.app.student_runtime.qa_runtime_config_service import get_student_qa_runtime_config

logger = logging.getLogger(__name__)

IMAGE_GENERATION_MODE = "image_generation"
IMAGE_GENERATION_SUCCESS_ANSWER = "已根据你的描述生成图片。"
IMAGE_GENERATION_FAILURE_ANSWER = "这次图片没有生成成功，可能是描述不够清晰、服务暂时繁忙或内容不适合生成。请换一种学习场景描述再试。"


def generate_qa_image(
    db: Session,
    *,
    lesson_id: str | int | None,
    section_id: str | int | None,
    page_no: int | None,
    prompt: str,
) -> dict[str, Any]:
    normalized_prompt = " ".join(str(prompt or "").split()).strip()
    if not normalized_prompt:
        raise ApiError(400, "请输入图片生成描述", status_code=400)

    runtime_config = get_student_qa_runtime_config(db)
    image_config = runtime_config.image_generation
    timeout_seconds = float(image_config.timeout_seconds or 60.0)
    poll_interval = float(image_config.settings.get("pollIntervalSeconds") or 2.0)
    started = time.perf_counter()
    try:
        adapter = build_provider_adapter(image_config)
        task = adapter.create_image_generation_task(
            prompt=build_image_generation_prompt(
                db,
                lesson_id=lesson_id,
                section_id=section_id,
                page_no=page_no,
                prompt=normalized_prompt,
            ),
            parameters={
                "size": image_config.settings.get("size") or "1024*1024",
                "n": max(1, min(int(image_config.settings.get("count") or 1), 1)),
            },
        )
        result = _wait_for_image_task(
            task["task_id"],
            adapter=adapter,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval,
        )
        attachments = _store_generated_images(result.get("results") or [], timeout=timeout_seconds)
        if not attachments:
            raise RuntimeError("DashScope image task succeeded without image results.")
        return {
            "answer": IMAGE_GENERATION_SUCCESS_ANSWER,
            "mode": IMAGE_GENERATION_MODE,
            "attachments": attachments,
            "relatedKnowledgePoints": [],
            "generation": {
                "status": "SUCCEEDED",
                "model": result.get("model") or image_config.model_name,
                "imageCount": len(attachments),
                "latencyMs": int((time.perf_counter() - started) * 1000),
            },
        }
    except ApiError as exc:
        logger.warning("student QA image generation failed: status=%s message=%s", exc.status_code, exc.msg)
        return _build_failure_payload(
            model_name=image_config.model_name,
            latency_ms=int((time.perf_counter() - started) * 1000),
            message=exc.msg,
        )
    except ModelProviderError as exc:
        logger.warning("student QA image generation provider config failure: %s", exc)
        return _build_failure_payload(
            model_name=image_config.model_name,
            latency_ms=int((time.perf_counter() - started) * 1000),
            message=str(exc),
        )
    except Exception as exc:
        logger.warning("student QA image generation provider failure: %s", exc)
        return _build_failure_payload(
            model_name=image_config.model_name,
            latency_ms=int((time.perf_counter() - started) * 1000),
            message=IMAGE_GENERATION_FAILURE_ANSWER,
        )


def build_image_generation_prompt(
    db: Session,
    *,
    lesson_id: str | int | None,
    section_id: str | int | None,
    page_no: int | None,
    prompt: str,
) -> str:
    section = get_section_context_for_qa(db, lesson_id, section_id) or {}
    page = get_page_context_for_qa(db, lesson_id, section_id, page_no) or {}
    points = get_section_knowledge_points_for_qa(db, lesson_id, section_id)
    point_names = [str(item.get("pointName") or "").strip() for item in points if item.get("pointName")]
    context_lines = [
        "请生成一张适合学生理解课程内容的教学解释图。",
        f"学生提示词：{prompt}",
    ]
    course_name = str(section.get("courseName") or "").strip()
    section_name = str(section.get("sectionName") or "").strip()
    page_title = str(page.get("pageTitle") or page.get("anchorTitle") or "").strip()
    page_summary = str(page.get("pageSummary") or "").strip()
    if course_name:
        context_lines.append(f"课程：{course_name}")
    if section_name:
        context_lines.append(f"章节：{section_name}")
    if page_title:
        context_lines.append(f"当前页：{page_title}")
    if point_names:
        context_lines.append(f"相关知识点：{'、'.join(point_names[:6])}")
    if page_summary:
        context_lines.append(f"页面摘要：{page_summary[:120]}")
    context_lines.append("要求：画面清晰、面向课堂学习，尽量用示意图表达，不要堆叠大量文字。")
    return "\n".join(context_lines)


def _wait_for_image_task(
    task_id: str,
    *,
    adapter,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(float(timeout_seconds or 60.0), 1.0)
    interval = max(float(poll_interval_seconds or 2.0), 0.5)
    last_result: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last_result = adapter.get_image_generation_task(task_id)
        status = str(last_result.get("status") or "").upper()
        if status == "SUCCEEDED":
            return last_result
        if status in {"FAILED", "CANCELED", "UNKNOWN"}:
            raise RuntimeError(f"DashScope image task ended with status={status}")
        time.sleep(interval)
    raise RuntimeError(f"DashScope image task timed out; last_status={last_result.get('status')}")


def _store_generated_images(results: list[dict[str, Any]], *, timeout: float) -> list[dict[str, object]]:
    attachments: list[dict[str, object]] = []
    for index, item in enumerate(results):
        image_url = str(item.get("url") or item.get("image_url") or "").strip()
        if not image_url:
            continue
        stored = store_qa_image_from_url(
            image_url=image_url,
            file_name=f"generated-image-{index + 1}.png",
            subdir="generated",
            timeout=min(max(timeout, 1.0), 30.0),
        )
        attachments.append(stored.to_payload())
    return attachments


def _build_failure_payload(*, model_name: str, latency_ms: int, message: str | None = None) -> dict[str, Any]:
    answer = message if message and message != IMAGE_GENERATION_FAILURE_ANSWER else IMAGE_GENERATION_FAILURE_ANSWER
    return {
        "answer": answer,
        "mode": IMAGE_GENERATION_MODE,
        "attachments": [],
        "relatedKnowledgePoints": [],
        "generation": {
            "status": "FAILED",
            "model": model_name,
            "imageCount": 0,
            "latencyMs": latency_ms,
            "error": message or IMAGE_GENERATION_FAILURE_ANSWER,
        },
    }
