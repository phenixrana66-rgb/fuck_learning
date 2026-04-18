from __future__ import annotations

import re
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from backend.app.common.vector_db import QAVectorChunk, vector_session_scope
from backend.app.student_runtime.db_learning_service import (
    get_page_context_for_qa,
    get_section_context_for_qa,
    get_section_knowledge_points_for_qa,
)
from backend.app.student_runtime.qa_embedding_service import embed_text
from backend.chaoxing_db.models import QAFaqItem, QAFaqVariant


PLACEHOLDER_PAGE_PATTERN = re.compile(r"本页为《.+》课件第\s*\d+\s*页。?")


def classify_question_intent(question: str) -> str:
    text = (question or "").strip()
    if not text:
        return "generative"
    definition_patterns = ("什么是", "是什么", "定义", "含义", "概念", "指什么", "是什么意思")
    generative_patterns = ("为什么", "怎么", "如何", "关系", "区别", "联系", "应用", "举例", "通俗", "解释", "整合", "总结", "归纳")
    if any(pattern in text for pattern in definition_patterns):
        return "definition"
    if any(pattern in text for pattern in generative_patterns):
        return "generative"
    return "contextual"


def search_faq_candidates(db: Session, question: str, top_k: int = 5) -> list[dict[str, Any]]:
    text = (question or "").strip()
    if not text:
        return []
    try:
        query_embedding = embed_text(text, text_type="query")
    except Exception:
        query_embedding = []
    return search_faq_candidates_with_embedding(db, text, query_embedding, top_k=top_k)


def search_faq_candidates_with_embedding(
    db: Session,
    question: str,
    query_embedding: list[float] | None,
    top_k: int = 5,
    vector_db: Session | None = None,
) -> list[dict[str, Any]]:
    text = (question or "").strip()
    if not text:
        return []
    lowered = text.lower()
    keyword_rows = (
        db.query(QAFaqVariant, QAFaqItem)
        .join(QAFaqItem, QAFaqItem.id == QAFaqVariant.faq_item_id)
        .filter(QAFaqVariant.is_active == True, QAFaqItem.status == "enabled")  # noqa: E712
        .filter(func.lower(QAFaqVariant.variant_text).like(f"%{lowered}%"))
        .order_by(QAFaqVariant.sort_no.asc(), QAFaqVariant.id.asc())
        .limit(top_k)
        .all()
    )
    results: list[dict[str, Any]] = []
    seen: set[int] = set()
    for variant, item in keyword_rows:
        if item.id in seen:
            continue
        seen.add(item.id)
        results.append(
            {
                "faqId": item.id,
                "question": item.canonical_question,
                "answer": item.answer_text,
                "category": item.category,
                "source": "keyword",
            }
        )
    if len(results) >= top_k:
        return results[:top_k]

    if not query_embedding:
        return results[:top_k]

    try:
        if vector_db is not None:
            rows = (
                vector_db.query(QAVectorChunk.source_id)
                .filter(QAVectorChunk.source_type == "faq_variant", QAVectorChunk.is_active == True)  # noqa: E712
                .order_by(QAVectorChunk.embedding.cosine_distance(query_embedding))
                .limit(top_k * 2)
                .all()
            )
        else:
            with vector_session_scope() as vector_session:
                rows = (
                    vector_session.query(QAVectorChunk.source_id)
                    .filter(QAVectorChunk.source_type == "faq_variant", QAVectorChunk.is_active == True)  # noqa: E712
                    .order_by(QAVectorChunk.embedding.cosine_distance(query_embedding))
                    .limit(top_k * 2)
                    .all()
                )
    except Exception:
        return results[:top_k]

    variant_ids = [source_id for (source_id,) in rows if source_id]
    if not variant_ids:
        return results[:top_k]

    variants = {variant.id: variant for variant in db.query(QAFaqVariant).filter(QAFaqVariant.id.in_(variant_ids)).all()}
    faq_ids = [variant.faq_item_id for variant in variants.values()]
    faq_items = {item.id: item for item in db.query(QAFaqItem).filter(QAFaqItem.id.in_(faq_ids)).all()}
    for (source_id,) in rows:
        variant = variants.get(source_id)
        if not variant:
            continue
        item = faq_items.get(variant.faq_item_id)
        if not item or item.id in seen or item.status != "enabled":
            continue
        seen.add(item.id)
        results.append(
            {
                "faqId": item.id,
                "question": item.canonical_question,
                "answer": item.answer_text,
                "category": item.category,
                "source": "vector",
            }
        )
        if len(results) >= top_k:
            break
    return results[:top_k]


def search_section_context(
    db: Session,
    lesson_id: str | int | None,
    section_id: str | int | None,
    page_no: int | None,
    question: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    section_context = get_section_context_for_qa(db, lesson_id, section_id)
    if not section_context:
        return []

    chunks: list[dict[str, Any]] = []
    chapter_context_text = (section_context.get("chapterContextText") or "").strip()
    if chapter_context_text:
        chunks.append(
            {
                "chunkId": f"chapter_context:{section_context['sectionDbId']}",
                "sourceType": "chapter_context",
                "chunkText": chapter_context_text,
                "pageNo": None,
            }
        )

    page_context = get_page_context_for_qa(db, lesson_id, section_id, page_no)
    if page_context and page_context.get("parsedContent") and page_context.get("hasMeaningfulContent"):
        chunks.append(
            {
                "chunkId": f"page_content:{page_context['pageDbId']}",
                "sourceType": "page_content",
                "chunkText": page_context["parsedContent"],
                "pageNo": page_context.get("pageNo"),
            }
        )

    try:
        query_embedding = embed_text(question, text_type="query")
    except Exception:
        query_embedding = []

    if query_embedding:
        try:
            with vector_session_scope() as vector_db:
                query = (
                    vector_db.query(QAVectorChunk)
                    .filter(
                        QAVectorChunk.lesson_id == section_context["lessonDbId"],
                        QAVectorChunk.section_id == section_context["sectionDbId"],
                        QAVectorChunk.is_active == True,  # noqa: E712
                        QAVectorChunk.source_type.in_(["section_summary", "page_content", "knowledge_point"]),
                    )
                )
                if page_no:
                    query = query.order_by(
                        case((QAVectorChunk.page_no == page_no, 0), else_=1),
                        QAVectorChunk.embedding.cosine_distance(query_embedding),
                    )
                else:
                    query = query.order_by(QAVectorChunk.embedding.cosine_distance(query_embedding))
                rows = [
                    {
                        "source_type": row.source_type,
                        "source_id": row.source_id,
                        "page_no": row.page_no,
                        "chunk_text": row.chunk_text,
                    }
                    for row in query.limit(max(top_k * 2, 8)).all()
                ]
        except Exception:
            rows = []

        for row in rows:
            chunk_text = (row["chunk_text"] or "").strip()
            if not chunk_text:
                continue
            if row["source_type"] == "page_content" and PLACEHOLDER_PAGE_PATTERN.fullmatch(chunk_text):
                continue
            chunk_id = f"{row['source_type']}:{row['source_id']}"
            if any(existing["chunkId"] == chunk_id for existing in chunks):
                continue
            chunks.append(
                {
                    "chunkId": chunk_id,
                    "sourceType": row["source_type"],
                    "chunkText": chunk_text,
                    "pageNo": row["page_no"],
                }
            )
            if len(chunks) >= max(top_k + 1, 6):
                break

    if len(chunks) < max(top_k, 4):
        for point in get_section_knowledge_points_for_qa(db, lesson_id, section_id):
            chunk_id = f"knowledge_point:{point['id']}"
            chunk_text = _join_point_text(point["pointName"], point["pointSummary"])
            if not chunk_text or any(existing["chunkId"] == chunk_id for existing in chunks):
                continue
            chunks.append(
                {
                    "chunkId": chunk_id,
                    "sourceType": "knowledge_point",
                    "chunkText": chunk_text,
                    "pageNo": None,
                }
            )
            if len(chunks) >= max(top_k + 1, 6):
                break
    return chunks


def build_qa_context_bundle(
    db: Session,
    lesson_id: str | int | None,
    section_id: str | int | None,
    page_no: int | None,
    question: str,
) -> dict[str, Any]:
    section_context = get_section_context_for_qa(db, lesson_id, section_id)
    page_context = get_page_context_for_qa(db, lesson_id, section_id, page_no)
    return {
        "lesson": {"lessonId": lesson_id, "sectionId": section_id},
        "questionIntent": classify_question_intent(question),
        "section": section_context,
        "page": page_context,
        "knowledge_points": get_section_knowledge_points_for_qa(db, lesson_id, section_id),
        "faq_candidates": search_faq_candidates(db, question),
        "context_chunks": search_section_context(db, lesson_id, section_id, page_no, question),
    }


def _join_point_text(point_name: str, point_summary: str) -> str:
    point_name = (point_name or "").strip()
    point_summary = (point_summary or "").strip()
    if point_name and point_summary:
        return f"{point_name}：{point_summary}"
    return point_name or point_summary
