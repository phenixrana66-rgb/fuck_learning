from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from time import perf_counter

from sqlalchemy.orm import Session

from backend.app.common.db import session_scope
from backend.app.common.vector_db import vector_session_scope
from backend.app.student_runtime.qa_embedding_service import embed_texts
from backend.app.student_runtime.qa_retrieval_service import search_faq_candidates_with_embedding
from backend.chaoxing_db.models import QAFaqItem


REPORT_PATH = Path(__file__).resolve().parents[3] / 'docs' / 'qa_offline_eval_report.json'
DEFAULT_SAMPLE_SIZE = 200


def run_offline_eval(db: Session, sample_size: int | None = None) -> dict[str, float | int | list[dict[str, object]]]:
    items = db.query(QAFaqItem).filter(QAFaqItem.status == 'enabled').order_by(QAFaqItem.id.asc()).all()
    requested_sample_size = sample_size or DEFAULT_SAMPLE_SIZE
    items = items[:requested_sample_size]
    if not items:
        return {
            'sampleSize': 0,
            'top1HitRate': 0.0,
            'top3HitRate': 0.0,
            'top5HitRate': 0.0,
            'avgLatencyMs': 0.0,
            'badCases': [],
            'generatedAt': datetime.now().isoformat(timespec='seconds'),
        }

    questions = [item.canonical_question for item in items]
    started_embedding = perf_counter()
    embeddings = embed_texts(questions, text_type='query', batch_size=64)
    embedding_latency_ms = (perf_counter() - started_embedding) * 1000

    top1_hits = 0
    top3_hits = 0
    top5_hits = 0
    total_retrieval_latency_ms = 0.0
    bad_cases: list[dict[str, object]] = []

    with vector_session_scope() as vector_db:
        for index, item in enumerate(items):
            query_embedding = embeddings[index] if index < len(embeddings) else []
            started = perf_counter()
            candidates = search_faq_candidates_with_embedding(
                db,
                item.canonical_question,
                query_embedding,
                top_k=5,
                vector_db=vector_db,
            )
            total_retrieval_latency_ms += (perf_counter() - started) * 1000
            candidate_ids = [candidate['faqId'] for candidate in candidates]
            if candidate_ids[:1] and item.id == candidate_ids[0]:
                top1_hits += 1
            if item.id in candidate_ids[:3]:
                top3_hits += 1
            if item.id in candidate_ids[:5]:
                top5_hits += 1
            else:
                bad_cases.append(
                    {
                        'faqId': item.id,
                        'question': item.canonical_question,
                        'category': item.category,
                        'retrievedFaqIds': candidate_ids,
                    }
                )

    sample_count = len(items)
    return {
        'sampleSize': sample_count,
        'top1HitRate': round(top1_hits / sample_count, 4),
        'top3HitRate': round(top3_hits / sample_count, 4),
        'top5HitRate': round(top5_hits / sample_count, 4),
        'avgLatencyMs': round(total_retrieval_latency_ms / sample_count, 2),
        'embeddingLatencyMs': round(embedding_latency_ms, 2),
        'badCases': bad_cases[:20],
        'generatedAt': datetime.now().isoformat(timespec='seconds'),
    }


def write_eval_report(report: dict[str, object]) -> Path:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return REPORT_PATH


if __name__ == '__main__':
    import sys

    sample_size = int(sys.argv[1]) if len(sys.argv) > 1 else None
    with session_scope() as db:
        report = run_offline_eval(db, sample_size=sample_size)
    path = write_eval_report(report)
    print(json.dumps({'reportPath': str(path), **report}, ensure_ascii=False, indent=2))
