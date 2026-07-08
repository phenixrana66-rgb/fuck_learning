from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.app.common.config import get_setting, get_settings
from backend.chaoxing_db.models import ModelRuntimeConfig, StudentQARetrievalRuntimeConfig


GLOBAL_SCOPE_KEY = "global"
STUDENT_QA_SCOPE_KEY = "student_qa_global"

PROVIDER_DASHSCOPE = "dashscope"
PROVIDER_OPENAI_COMPATIBLE = "openai_compatible"

CAP_TEACHER_SCRIPT = "teacher_script_generation"
CAP_TEACHER_STRUCTURE_PARSE = "teacher_structure_parse"
CAP_STUDENT_TEXT_CHAT = "student_text_chat"
CAP_STUDENT_VISION_CHAT = "student_vision_chat"
CAP_STUDENT_IMAGE_GENERATION = "student_image_generation"
CAP_STUDENT_EMBEDDING = "student_embedding"

CAPABILITY_ORDER = [
    CAP_TEACHER_SCRIPT,
    CAP_TEACHER_STRUCTURE_PARSE,
    CAP_STUDENT_TEXT_CHAT,
    CAP_STUDENT_VISION_CHAT,
    CAP_STUDENT_IMAGE_GENERATION,
    CAP_STUDENT_EMBEDDING,
]

CAPABILITY_LABELS = {
    CAP_TEACHER_SCRIPT: "教师端讲稿生成",
    CAP_TEACHER_STRUCTURE_PARSE: "教师端结构化解析",
    CAP_STUDENT_TEXT_CHAT: "学生端文本问答",
    CAP_STUDENT_VISION_CHAT: "学生端图片理解",
    CAP_STUDENT_IMAGE_GENERATION: "学生端图片生成",
    CAP_STUDENT_EMBEDDING: "学生端 Embedding",
}

MIN_RETRIEVAL_TOP_K = 1
MAX_RETRIEVAL_TOP_K = 10


@dataclass(frozen=True)
class ModelCapabilityConfig:
    capability: str
    provider: str
    base_url: str
    api_key_ref: str
    model_name: str
    timeout_seconds: float = 60.0
    settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "capability": self.capability,
            "label": CAPABILITY_LABELS.get(self.capability, self.capability),
            "provider": self.provider,
            "baseUrl": self.base_url,
            "apiKeyRef": self.api_key_ref,
            "model": self.model_name,
            "modelName": self.model_name,
            "timeoutSeconds": self.timeout_seconds,
            "settings": dict(self.settings),
        }


@dataclass(frozen=True)
class StudentQARuntimeConfig:
    text_chat: ModelCapabilityConfig
    vision_chat: ModelCapabilityConfig
    image_generation: ModelCapabilityConfig
    embedding: ModelCapabilityConfig
    retrieval_enabled: bool
    retrieval_top_k: int

    @property
    def qa_llm_model(self) -> str:
        return self.text_chat.model_name

    @property
    def qa_multimodal_model(self) -> str:
        return self.vision_chat.model_name

    @property
    def qa_embedding_model(self) -> str:
        return self.embedding.model_name

    def with_retrieval_enabled(self, enabled: bool) -> "StudentQARuntimeConfig":
        return replace(self, retrieval_enabled=bool(enabled))

    def to_dict(self) -> dict[str, object]:
        return {
            "qaLlmModel": self.qa_llm_model,
            "qaMultimodalModel": self.qa_multimodal_model,
            "qaEmbeddingModel": self.qa_embedding_model,
            "retrievalEnabled": self.retrieval_enabled,
            "retrievalTopK": self.retrieval_top_k,
            "capabilities": {
                CAP_STUDENT_TEXT_CHAT: self.text_chat.to_dict(),
                CAP_STUDENT_VISION_CHAT: self.vision_chat.to_dict(),
                CAP_STUDENT_IMAGE_GENERATION: self.image_generation.to_dict(),
                CAP_STUDENT_EMBEDDING: self.embedding.to_dict(),
            },
        }

    def actual_chat_model(self, *, has_images: bool = False) -> str:
        if has_images and self.vision_chat.model_name:
            return self.vision_chat.model_name
        return self.text_chat.model_name

    def actual_chat_provider(self, *, has_images: bool = False) -> str:
        if has_images and self.vision_chat.provider:
            return self.vision_chat.provider
        return self.text_chat.provider


def resolve_api_key_ref(api_key_ref: str) -> str | None:
    normalized = _normalize_text(api_key_ref)
    if not normalized:
        return None
        
    # 兼容逻辑：若 api_key_ref 自身就是以 sk- 开头的真实密钥，则直接返回
    if normalized.startswith("sk-") or len(normalized) > 30:
        return api_key_ref
        
    value = get_setting(normalized)
    if value in (None, ""):
        # 回退检测：如果配置项不存在，但原输入就是 sk- Key，则直接返回
        if normalized.startswith("sk-") or len(normalized) > 20:
            return api_key_ref
        return None
    return str(value)


def get_default_capability_configs() -> dict[str, ModelCapabilityConfig]:
    settings = get_settings()
    dashscope_key_ref = "dashscope_api_key"
    return {
        CAP_TEACHER_SCRIPT: ModelCapabilityConfig(
            capability=CAP_TEACHER_SCRIPT,
            provider=PROVIDER_OPENAI_COMPATIBLE,
            base_url=_normalize_base_url(settings.llm_api_base_url),
            api_key_ref="llm_api_key",
            model_name=_normalize_text(settings.llm_model, "gpt-5.1-codex-mini"),
            timeout_seconds=_normalize_timeout(settings.llm_timeout_seconds, 60.0),
        ),
        CAP_TEACHER_STRUCTURE_PARSE: ModelCapabilityConfig(
            capability=CAP_TEACHER_STRUCTURE_PARSE,
            provider=PROVIDER_OPENAI_COMPATIBLE,
            base_url=_normalize_base_url(settings.llm_api_base_url),
            api_key_ref="llm_api_key",
            model_name=_normalize_text(settings.llm_model, "gpt-5.1-codex-mini"),
            timeout_seconds=_normalize_timeout(settings.llm_timeout_seconds, 60.0),
        ),
        CAP_STUDENT_TEXT_CHAT: ModelCapabilityConfig(
            capability=CAP_STUDENT_TEXT_CHAT,
            provider=_normalize_provider(settings.qa_llm_provider or PROVIDER_DASHSCOPE),
            base_url=_normalize_base_url(settings.dashscope_base_url),
            api_key_ref=dashscope_key_ref,
            model_name=_normalize_text(settings.qa_llm_model, "qwen-max"),
            timeout_seconds=_normalize_timeout(settings.llm_timeout_seconds, 60.0),
        ),
        CAP_STUDENT_VISION_CHAT: ModelCapabilityConfig(
            capability=CAP_STUDENT_VISION_CHAT,
            provider=_normalize_provider(settings.qa_llm_provider or PROVIDER_DASHSCOPE),
            base_url=_normalize_base_url(settings.dashscope_base_url),
            api_key_ref=dashscope_key_ref,
            model_name=_normalize_text(settings.qa_multimodal_model, settings.qa_llm_model),
            timeout_seconds=_normalize_timeout(settings.llm_timeout_seconds, 60.0),
        ),
        CAP_STUDENT_IMAGE_GENERATION: ModelCapabilityConfig(
            capability=CAP_STUDENT_IMAGE_GENERATION,
            provider=PROVIDER_DASHSCOPE,
            base_url=_normalize_base_url(settings.dashscope_base_url),
            api_key_ref=dashscope_key_ref,
            model_name=_normalize_text(settings.qa_image_generation_model, "wanx2.1-t2i-turbo"),
            timeout_seconds=_normalize_timeout(settings.qa_image_generation_timeout_seconds, 60.0),
            settings={
                "size": settings.qa_image_generation_size,
                "count": max(1, min(int(settings.qa_image_generation_count or 1), 1)),
                "pollIntervalSeconds": _normalize_timeout(settings.qa_image_generation_poll_interval_seconds, 2.0),
            },
        ),
        CAP_STUDENT_EMBEDDING: ModelCapabilityConfig(
            capability=CAP_STUDENT_EMBEDDING,
            provider=_normalize_provider(settings.qa_llm_provider or PROVIDER_DASHSCOPE),
            base_url=_normalize_base_url(settings.dashscope_base_url),
            api_key_ref=dashscope_key_ref,
            model_name=_normalize_text(settings.qa_embedding_model, "text-embedding-v4"),
            timeout_seconds=120.0,
            settings={"dimensions": int(settings.qa_embedding_dimensions or 1024)},
        ),
    }


def get_effective_capability_configs(db: Session) -> dict[str, ModelCapabilityConfig]:
    defaults = get_default_capability_configs()
    rows = (
        db.query(ModelRuntimeConfig)
        .filter(ModelRuntimeConfig.scope_key == GLOBAL_SCOPE_KEY, ModelRuntimeConfig.capability.in_(CAPABILITY_ORDER))
        .all()
    )
    effective = dict(defaults)
    for row in rows:
        default = defaults.get(row.capability)
        if default is None:
            continue
        effective[row.capability] = _row_to_capability(row, default)
    return effective


def get_effective_capability_config(db: Session, capability: str) -> ModelCapabilityConfig:
    normalized = _normalize_capability(capability)
    if normalized not in CAPABILITY_ORDER:
        raise ValueError(f"Unsupported model capability: {capability}")
    return get_effective_capability_configs(db)[normalized]


def get_teacher_llm_runtime_config(db: Session, capability: str) -> ModelCapabilityConfig:
    normalized = _normalize_capability(capability)
    if normalized not in {CAP_TEACHER_SCRIPT, CAP_TEACHER_STRUCTURE_PARSE}:
        raise ValueError(f"Unsupported teacher model capability: {capability}")
    return get_effective_capability_config(db, normalized)


def get_default_student_qa_runtime_config() -> StudentQARuntimeConfig:
    capabilities = get_default_capability_configs()
    return _build_student_runtime_config(capabilities, _default_retrieval_config())


def get_student_qa_runtime_config(db: Session) -> StudentQARuntimeConfig:
    capabilities = get_effective_capability_configs(db)
    return _build_student_runtime_config(capabilities, _get_retrieval_config(db))


def build_model_runtime_config_payload(db: Session) -> dict[str, object]:
    defaults = get_default_capability_configs()
    effective = get_effective_capability_configs(db)
    retrieval_defaults = _default_retrieval_config()
    retrieval = _get_retrieval_config(db)
    capability_rows = _find_capability_rows(db)
    retrieval_row = _find_retrieval_row(db)
    warnings = _build_runtime_warnings(effective, defaults)
    data: dict[str, object] = {
        "scopeKey": GLOBAL_SCOPE_KEY,
        "capabilities": _serialize_capabilities(effective),
        "defaults": _serialize_capabilities(defaults),
        "retrieval": _retrieval_to_dict(retrieval),
        "retrievalDefaults": _retrieval_to_dict(retrieval_defaults),
        "warnings": warnings,
        "overrideActive": bool(capability_rows or retrieval_row is not None),
    }
    updated_at = _latest_updated_at([*capability_rows, retrieval_row])
    if updated_at:
        data["updatedAt"] = updated_at.isoformat()
    return data


def update_model_runtime_config(db: Session, payload: dict[str, object]) -> dict[str, object]:
    _reject_secret_fields(payload)
    defaults = get_default_capability_configs()
    capability_payloads = _normalize_capabilities_payload(payload.get("capabilities"))
    for capability, item in capability_payloads.items():
        if capability not in CAPABILITY_ORDER:
            continue
        default = defaults[capability]
        row = _find_capability_row(db, capability)
        if row is None:
            row = ModelRuntimeConfig(scope_key=GLOBAL_SCOPE_KEY, capability=capability)
            db.add(row)
        config = _payload_to_capability(capability, item, default)
        row.provider = config.provider
        row.base_url = config.base_url
        row.api_key_ref = config.api_key_ref
        row.model_name = config.model_name
        row.timeout_seconds = config.timeout_seconds
        row.settings_json = json.dumps(config.settings, ensure_ascii=False, sort_keys=True)

    if isinstance(payload.get("retrieval"), dict):
        _update_retrieval_config_row(db, payload.get("retrieval") or {})

    db.commit()
    return build_model_runtime_config_payload(db)


def reset_model_runtime_config(db: Session) -> dict[str, object]:
    for row in _find_capability_rows(db):
        db.delete(row)
    retrieval_row = _find_retrieval_row(db)
    if retrieval_row is not None:
        db.delete(retrieval_row)
    db.commit()
    return build_model_runtime_config_payload(db)


def update_student_qa_runtime_config(db: Session, payload: dict[str, object]) -> dict[str, object]:
    _reject_secret_fields(payload)
    defaults = get_default_capability_configs()
    legacy_payload = {
        "capabilities": {
            CAP_STUDENT_TEXT_CHAT: {"model": payload.get("qaLlmModel")},
            CAP_STUDENT_VISION_CHAT: {"model": payload.get("qaMultimodalModel")},
            CAP_STUDENT_EMBEDDING: {"model": payload.get("qaEmbeddingModel")},
        },
        "retrieval": {
            "retrievalEnabled": payload.get("retrievalEnabled"),
            "retrievalTopK": payload.get("retrievalTopK"),
        },
    }
    for capability, item in legacy_payload["capabilities"].items():
        default = defaults[capability]
        row = _find_capability_row(db, capability)
        if row is None:
            row = ModelRuntimeConfig(scope_key=GLOBAL_SCOPE_KEY, capability=capability)
            db.add(row)
        current = _row_to_capability(row, default) if row.provider else default
        config = replace(current, model_name=_normalize_text(item.get("model"), default.model_name))
        row.provider = config.provider
        row.base_url = config.base_url
        row.api_key_ref = config.api_key_ref
        row.model_name = config.model_name
        row.timeout_seconds = config.timeout_seconds
        row.settings_json = json.dumps(config.settings, ensure_ascii=False, sort_keys=True)
    _update_retrieval_config_row(db, legacy_payload["retrieval"])
    db.commit()
    return build_student_qa_runtime_config_payload(db)


def reset_student_qa_runtime_config(db: Session) -> dict[str, object]:
    for capability in [CAP_STUDENT_TEXT_CHAT, CAP_STUDENT_VISION_CHAT, CAP_STUDENT_IMAGE_GENERATION, CAP_STUDENT_EMBEDDING]:
        row = _find_capability_row(db, capability)
        if row is not None:
            db.delete(row)
    retrieval_row = _find_retrieval_row(db)
    if retrieval_row is not None:
        db.delete(retrieval_row)
    db.commit()
    return build_student_qa_runtime_config_payload(db)


def build_student_qa_runtime_config_payload(db: Session) -> dict[str, object]:
    defaults = get_default_student_qa_runtime_config()
    effective = get_student_qa_runtime_config(db)
    capability_rows = [
        row for row in _find_capability_rows(db) if row.capability in {
            CAP_STUDENT_TEXT_CHAT,
            CAP_STUDENT_VISION_CHAT,
            CAP_STUDENT_IMAGE_GENERATION,
            CAP_STUDENT_EMBEDDING,
        }
    ]
    retrieval_row = _find_retrieval_row(db)
    data: dict[str, object] = {
        "config": effective.to_dict(),
        "defaults": defaults.to_dict(),
        "warnings": _build_student_runtime_warnings(effective, defaults),
        "overrideActive": bool(capability_rows or retrieval_row is not None),
    }
    updated_at = _latest_updated_at([*capability_rows, retrieval_row])
    if updated_at:
        data["updatedAt"] = updated_at.isoformat()
    return data


def _build_student_runtime_config(
    capabilities: dict[str, ModelCapabilityConfig],
    retrieval: dict[str, object],
) -> StudentQARuntimeConfig:
    return StudentQARuntimeConfig(
        text_chat=capabilities[CAP_STUDENT_TEXT_CHAT],
        vision_chat=capabilities[CAP_STUDENT_VISION_CHAT],
        image_generation=capabilities[CAP_STUDENT_IMAGE_GENERATION],
        embedding=capabilities[CAP_STUDENT_EMBEDDING],
        retrieval_enabled=bool(retrieval["retrievalEnabled"]),
        retrieval_top_k=_normalize_retrieval_top_k(retrieval["retrievalTopK"], 5),
    )


def _serialize_capabilities(configs: dict[str, ModelCapabilityConfig]) -> dict[str, dict[str, object]]:
    return {capability: configs[capability].to_dict() for capability in CAPABILITY_ORDER}


def _row_to_capability(row: ModelRuntimeConfig, default: ModelCapabilityConfig) -> ModelCapabilityConfig:
    return ModelCapabilityConfig(
        capability=row.capability,
        provider=_normalize_provider(row.provider or default.provider),
        base_url=_normalize_base_url(row.base_url or default.base_url),
        api_key_ref=_normalize_text(row.api_key_ref, default.api_key_ref),
        model_name=_normalize_text(row.model_name, default.model_name),
        timeout_seconds=_normalize_timeout(row.timeout_seconds, default.timeout_seconds),
        settings=_parse_settings_json(row.settings_json, default.settings),
    )


def _payload_to_capability(
    capability: str,
    payload: dict[str, object],
    default: ModelCapabilityConfig,
) -> ModelCapabilityConfig:
    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
    merged_settings = {**default.settings, **settings}
    return ModelCapabilityConfig(
        capability=capability,
        provider=_normalize_provider(payload.get("provider") or default.provider),
        base_url=_normalize_base_url(payload.get("baseUrl") or payload.get("base_url") or default.base_url),
        api_key_ref=_normalize_text(payload.get("apiKeyRef") or payload.get("api_key_ref"), default.api_key_ref),
        model_name=_normalize_text(payload.get("model") or payload.get("modelName") or payload.get("model_name"), default.model_name),
        timeout_seconds=_normalize_timeout(payload.get("timeoutSeconds") or payload.get("timeout_seconds"), default.timeout_seconds),
        settings=_normalize_capability_settings(capability, merged_settings),
    )


def _normalize_capabilities_payload(value: object) -> dict[str, dict[str, object]]:
    if isinstance(value, dict):
        result: dict[str, dict[str, object]] = {}
        for capability, item in value.items():
            normalized = _normalize_capability(capability)
            if isinstance(item, dict):
                result[normalized] = item
        return result
    if isinstance(value, list):
        result = {}
        for item in value:
            if not isinstance(item, dict):
                continue
            capability = _normalize_capability(item.get("capability"))
            if capability:
                result[capability] = item
        return result
    return {}


def _normalize_capability_settings(capability: str, settings: dict[str, object]) -> dict[str, object]:
    if capability == CAP_STUDENT_IMAGE_GENERATION:
        return {
            "size": _normalize_text(settings.get("size"), "1024*1024"),
            "count": max(1, min(_normalize_int(settings.get("count"), 1), 1)),
            "pollIntervalSeconds": _normalize_timeout(settings.get("pollIntervalSeconds"), 2.0),
        }
    if capability == CAP_STUDENT_EMBEDDING:
        return {"dimensions": max(1, _normalize_int(settings.get("dimensions"), 1024))}
    return dict(settings)


def _parse_settings_json(raw: str | None, fallback: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return dict(fallback)
    try:
        parsed = json.loads(raw)
    except ValueError:
        return dict(fallback)
    if not isinstance(parsed, dict):
        return dict(fallback)
    return {**fallback, **parsed}


def _default_retrieval_config() -> dict[str, object]:
    return {"retrievalEnabled": True, "retrievalTopK": 5}


def _get_retrieval_config(db: Session) -> dict[str, object]:
    row = _find_retrieval_row(db)
    if row is None:
        return _default_retrieval_config()
    return {
        "retrievalEnabled": bool(row.retrieval_enabled),
        "retrievalTopK": _normalize_retrieval_top_k(row.retrieval_top_k, 5),
    }


def _update_retrieval_config_row(db: Session, payload: dict[str, object]) -> None:
    defaults = _default_retrieval_config()
    row = _find_retrieval_row(db)
    if row is None:
        row = StudentQARetrievalRuntimeConfig(
            scope_key=STUDENT_QA_SCOPE_KEY,
            retrieval_enabled=bool(defaults["retrievalEnabled"]),
            retrieval_top_k=int(defaults["retrievalTopK"]),
        )
        db.add(row)
    row.retrieval_enabled = bool(payload.get("retrievalEnabled", payload.get("retrieval_enabled", row.retrieval_enabled)))
    row.retrieval_top_k = _normalize_retrieval_top_k(
        payload.get("retrievalTopK", payload.get("retrieval_top_k", row.retrieval_top_k)),
        int(defaults["retrievalTopK"]),
    )


def _retrieval_to_dict(payload: dict[str, object]) -> dict[str, object]:
    return {
        "retrievalEnabled": bool(payload.get("retrievalEnabled", True)),
        "retrievalTopK": _normalize_retrieval_top_k(payload.get("retrievalTopK"), 5),
    }


def _build_runtime_warnings(
    effective: dict[str, ModelCapabilityConfig],
    defaults: dict[str, ModelCapabilityConfig],
) -> list[str]:
    warnings: list[str] = []
    if (
        effective[CAP_STUDENT_EMBEDDING].model_name != defaults[CAP_STUDENT_EMBEDDING].model_name
        or effective[CAP_STUDENT_EMBEDDING].settings.get("dimensions") != defaults[CAP_STUDENT_EMBEDDING].settings.get("dimensions")
    ):
        warnings.append("Embedding 模型或维度已变更。要让现有向量数据和新模型保持一致，需要重新执行 qa_vector_sync_service。")
    return warnings


def _build_student_runtime_warnings(
    effective: StudentQARuntimeConfig,
    defaults: StudentQARuntimeConfig,
) -> list[str]:
    if (
        effective.embedding.model_name != defaults.embedding.model_name
        or effective.embedding.settings.get("dimensions") != defaults.embedding.settings.get("dimensions")
    ):
        return ["Embedding 模型或维度已变更。要让现有向量数据和新模型保持一致，需要重新执行 qa_vector_sync_service。"]
    return []


def _find_capability_rows(db: Session) -> list[ModelRuntimeConfig]:
    return (
        db.query(ModelRuntimeConfig)
        .filter(ModelRuntimeConfig.scope_key == GLOBAL_SCOPE_KEY, ModelRuntimeConfig.capability.in_(CAPABILITY_ORDER))
        .all()
    )


def _find_capability_row(db: Session, capability: str) -> ModelRuntimeConfig | None:
    return (
        db.query(ModelRuntimeConfig)
        .filter(ModelRuntimeConfig.scope_key == GLOBAL_SCOPE_KEY, ModelRuntimeConfig.capability == _normalize_capability(capability))
        .first()
    )


def _find_retrieval_row(db: Session) -> StudentQARetrievalRuntimeConfig | None:
    return (
        db.query(StudentQARetrievalRuntimeConfig)
        .filter(StudentQARetrievalRuntimeConfig.scope_key == STUDENT_QA_SCOPE_KEY)
        .first()
    )


def _latest_updated_at(rows: list[object | None]) -> datetime | None:
    candidates = [getattr(row, "updated_at", None) for row in rows if row is not None]
    candidates = [item for item in candidates if isinstance(item, datetime)]
    return max(candidates) if candidates else None


def _reject_secret_fields(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key or "").lower()
            if normalized in {"apikey", "api_key", "secret", "secretkey", "secret_key"}:
                raise ValueError("运行时配置不接受真实 API key，请使用 apiKeyRef。")
            _reject_secret_fields(item)
    elif isinstance(value, list):
        for item in value:
            _reject_secret_fields(item)


def _normalize_capability(value: object) -> str:
    return str(value or "").strip()


def _normalize_provider(value: object) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in {"openai", "openai_compatible", "openai-compatible"}:
        return PROVIDER_OPENAI_COMPATIBLE
    if normalized == PROVIDER_DASHSCOPE:
        return PROVIDER_DASHSCOPE
    return normalized or PROVIDER_DASHSCOPE


def _normalize_text(value: object, fallback: str = "") -> str:
    normalized = str(value or "").strip()
    return normalized or fallback


def _normalize_base_url(value: object) -> str:
    return str(value or "").strip().rstrip("/")


def _normalize_timeout(value: object, fallback: float) -> float:
    try:
        number = float(value)
    except Exception:
        number = float(fallback)
    return max(number, 1.0)


def _normalize_int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(fallback)


def _normalize_retrieval_top_k(value: object, fallback: int) -> int:
    return max(MIN_RETRIEVAL_TOP_K, min(MAX_RETRIEVAL_TOP_K, _normalize_int(value, fallback)))
