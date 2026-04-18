from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.common.db import session_scope
from backend.app.common.vector_db import QAVectorChunk, vector_session_scope
from backend.app.student_runtime.db_learning_service import (
    get_section_context_for_qa,
    get_section_knowledge_points_for_qa,
)
from backend.app.student_runtime.qa_embedding_service import embed_texts
from backend.app.student_runtime.qa_retrieval_service import PLACEHOLDER_PAGE_PATTERN
from backend.chaoxing_db.models import LessonSectionPage, QAFaqItem, QAFaqVariant


def sync_faq_variants_to_vector_db(db: Session) -> int:
    rows = (
        db.query(QAFaqVariant, QAFaqItem)
        .join(QAFaqItem, QAFaqItem.id == QAFaqVariant.faq_item_id)
        .filter(QAFaqVariant.is_active == True, QAFaqItem.status == "enabled")  # noqa: E712
        .all()
    )
    texts = [variant.variant_text for variant, _item in rows]
    embeddings = embed_texts(texts, text_type="document")
    count = 0
    with vector_session_scope() as vector_db:
        for (variant, _item), embedding in zip(rows, embeddings):
            vector_db.query(QAVectorChunk).filter(
                QAVectorChunk.source_type == "faq_variant",
                QAVectorChunk.source_id == variant.id,
            ).delete(synchronize_session=False)
            vector_db.add(
                QAVectorChunk(
                    source_type="faq_variant",
                    source_id=variant.id,
                    lesson_id=None,
                    section_id=None,
                    page_no=None,
                    chunk_text=variant.variant_text,
                    metadata_json={"faqItemId": variant.faq_item_id, "variantType": variant.variant_type},
                    embedding=embedding,
                    is_active=variant.is_active,
                )
            )
            count += 1
    return count


def sync_section_context_to_vector_db(db: Session, lesson_id: str | int | None, section_id: str | int | None) -> int:
    section_context = get_section_context_for_qa(db, lesson_id, section_id)
    if not section_context:
        return 0

    payloads: list[tuple[str, int, int | None, str, dict[str, object]]] = []
    if section_context.get("summary"):
        payloads.append(
            (
                "section_summary",
                section_context["sectionDbId"],
                None,
                section_context["summary"],
                {"sectionId": section_context["sectionDbId"]},
            )
        )
    if section_context.get("chapterContextText"):
        payloads.append(
            (
                "section_summary",
                section_context["sectionDbId"] * 1000000,
                None,
                section_context["chapterContextText"],
                {"sectionId": section_context["sectionDbId"], "chunkKind": "chapter_context"},
            )
        )

    pages = (
        db.query(LessonSectionPage)
        .filter(LessonSectionPage.section_id == section_context["sectionDbId"])
        .order_by(LessonSectionPage.page_no.asc())
        .all()
    )
    for page in pages:
        if page.parsed_content and not PLACEHOLDER_PAGE_PATTERN.fullmatch((page.parsed_content or "").strip()):
            payloads.append(
                (
                    "page_content",
                    page.id,
                    page.page_no,
                    page.parsed_content,
                    {"sectionId": page.section_id, "pageNo": page.page_no},
                )
            )

    for point in get_section_knowledge_points_for_qa(db, lesson_id, section_id):
        point_name = (point["pointName"] or "").strip()
        point_summary = (point["pointSummary"] or "").strip()
        chunk_text = f"{point_name}：{point_summary}" if point_name and point_summary else point_name or point_summary
        payloads.append(
            (
                "knowledge_point",
                point["id"],
                None,
                chunk_text,
                {"sectionId": section_context["sectionDbId"], "pointName": point_name},
            )
        )

    embeddings = embed_texts([item[3] for item in payloads], text_type="document")
    count = 0
    with vector_session_scope() as vector_db:
        for (source_type, source_id, page_no, chunk_text, metadata), embedding in zip(payloads, embeddings):
            vector_db.query(QAVectorChunk).filter(
                QAVectorChunk.source_type == source_type,
                QAVectorChunk.source_id == source_id,
            ).delete(synchronize_session=False)
            vector_db.add(
                QAVectorChunk(
                    source_type=source_type,
                    source_id=source_id,
                    lesson_id=section_context["lessonDbId"],
                    section_id=section_context["sectionDbId"],
                    page_no=page_no,
                    chunk_text=chunk_text,
                    metadata_json=metadata,
                    embedding=embedding,
                    is_active=True,
                )
            )
            count += 1
    return count


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "faq"
    with session_scope() as db:
        if mode == "faq":
            print({"syncedFaqVariants": sync_faq_variants_to_vector_db(db)})
        elif mode == "section" and len(sys.argv) >= 4:
            print({"syncedSectionChunks": sync_section_context_to_vector_db(db, sys.argv[2], sys.argv[3])})
        else:
            raise SystemExit("Usage: python -m backend.app.student_runtime.qa_vector_sync_service faq | section <lesson_id> <section_id>")
