from __future__ import annotations

from dataclasses import dataclass, replace

from sqlalchemy.orm import Session

from backend.app.common.config import get_settings
from backend.chaoxing_db.models import QARuntimeConfig


RUNTIME_SCOPE_KEY = "student_qa_global"
MIN_RETRIEVAL_TOP_K = 1
MAX_RETRIEVAL_TOP_K = 10


@dataclass(frozen=True)
class StudentQARuntimeConfig:
    qa_llm_model: str
    qa_multimodal_model: str
    qa_embedding_model: str
    retrieval_enabled: bool
    retrieval_top_k: int

    def with_retrieval_enabled(self, enabled: bool) -> "StudentQARuntimeConfig":
        return replace(self, retrieval_enabled=bool(enabled))

    def to_dict(self) -> dict[str, object]:
        return {
            "qaLlmModel": self.qa_llm_model,
            "qaMultimodalModel": self.qa_multimodal_model,
            "qaEmbeddingModel": self.qa_embedding_model,
            "retrievalEnabled": self.retrieval_enabled,
            "retrievalTopK": self.retrieval_top_k,
        }

    def actual_chat_model(self, *, has_images: bool = False) -> str:
        if has_images and self.qa_multimodal_model:
            return self.qa_multimodal_model
        return self.qa_llm_model


def get_default_student_qa_runtime_config() -> StudentQARuntimeConfig:
    settings = get_settings()
    return StudentQARuntimeConfig(
        qa_llm_model=_normalize_model_name(settings.qa_llm_model, settings.qa_llm_model),
        qa_multimodal_model=_normalize_model_name(settings.qa_multimodal_model, settings.qa_llm_model),
        qa_embedding_model=_normalize_model_name(settings.qa_embedding_model, settings.qa_embedding_model),
        retrieval_enabled=True,
        retrieval_top_k=5,
    )


def get_student_qa_runtime_config(db: Session) -> StudentQARuntimeConfig:
    row = _find_runtime_config_row(db)
    if row is None:
        return get_default_student_qa_runtime_config()
    defaults = get_default_student_qa_runtime_config()
    return StudentQARuntimeConfig(
        qa_llm_model=_normalize_model_name(row.qa_llm_model, defaults.qa_llm_model),
        qa_multimodal_model=_normalize_model_name(row.qa_multimodal_model, defaults.qa_multimodal_model),
        qa_embedding_model=_normalize_model_name(row.qa_embedding_model, defaults.qa_embedding_model),
        retrieval_enabled=bool(row.retrieval_enabled),
        retrieval_top_k=_normalize_retrieval_top_k(row.retrieval_top_k, defaults.retrieval_top_k),
    )


def update_student_qa_runtime_config(db: Session, payload: dict[str, object]) -> dict[str, object]:
    defaults = get_default_student_qa_runtime_config()
    row = _find_runtime_config_row(db)
    if row is None:
        row = QARuntimeConfig(
            scope_key=RUNTIME_SCOPE_KEY,
            qa_llm_model=defaults.qa_llm_model,
            qa_multimodal_model=defaults.qa_multimodal_model,
            qa_embedding_model=defaults.qa_embedding_model,
            retrieval_enabled=defaults.retrieval_enabled,
            retrieval_top_k=defaults.retrieval_top_k,
        )
        db.add(row)
        db.flush()

    row.qa_llm_model = _normalize_model_name(payload.get("qaLlmModel"), defaults.qa_llm_model)
    row.qa_multimodal_model = _normalize_model_name(payload.get("qaMultimodalModel"), defaults.qa_multimodal_model)
    row.qa_embedding_model = _normalize_model_name(payload.get("qaEmbeddingModel"), defaults.qa_embedding_model)
    row.retrieval_enabled = bool(payload.get("retrievalEnabled", row.retrieval_enabled))
    row.retrieval_top_k = _normalize_retrieval_top_k(payload.get("retrievalTopK"), defaults.retrieval_top_k)
    db.commit()
    db.refresh(row)
    return build_student_qa_runtime_config_payload(db)


def reset_student_qa_runtime_config(db: Session) -> dict[str, object]:
    row = _find_runtime_config_row(db)
    if row is not None:
        db.delete(row)
        db.commit()
    return build_student_qa_runtime_config_payload(db)


def build_student_qa_runtime_config_payload(db: Session) -> dict[str, object]:
    defaults = get_default_student_qa_runtime_config()
    effective = get_student_qa_runtime_config(db)
    row = _find_runtime_config_row(db)
    warnings = _build_runtime_warnings(effective, defaults)
    data = {
        "config": effective.to_dict(),
        "defaults": defaults.to_dict(),
        "warnings": warnings,
        "overrideActive": row is not None,
    }
    if row is not None:
        data["updatedAt"] = row.updated_at.isoformat() if row.updated_at else ""
    return data


def _build_runtime_warnings(
    effective: StudentQARuntimeConfig,
    defaults: StudentQARuntimeConfig,
) -> list[str]:
    warnings: list[str] = []
    if effective.qa_embedding_model != defaults.qa_embedding_model:
        warnings.append("Embedding 模型已变更。要让现有向量数据和新模型保持一致，需要重新执行 qa_vector_sync_service。")
    return warnings


def _find_runtime_config_row(db: Session) -> QARuntimeConfig | None:
    return db.query(QARuntimeConfig).filter(QARuntimeConfig.scope_key == RUNTIME_SCOPE_KEY).first()


def _normalize_model_name(value: object, fallback: str) -> str:
    normalized = str(value or "").strip()
    return normalized or fallback


def _normalize_retrieval_top_k(value: object, fallback: int) -> int:
    try:
        number = int(value)
    except Exception:
        number = int(fallback)
    return max(MIN_RETRIEVAL_TOP_K, min(MAX_RETRIEVAL_TOP_K, number))
