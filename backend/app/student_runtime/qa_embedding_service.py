from __future__ import annotations

from backend.app.student_runtime.qa_dashscope_client import DashScopeClient
from backend.app.student_runtime.qa_runtime_config_service import StudentQARuntimeConfig


def embed_text(
    text: str,
    *,
    text_type: str = "document",
    runtime_config: StudentQARuntimeConfig | None = None,
) -> list[float]:
    texts = [text.strip()] if text and text.strip() else []
    if not texts:
        return []
    return DashScopeClient(runtime_config=runtime_config).embed_texts(texts, text_type=text_type)[0]


def embed_texts(texts, text_type="document", batch_size=64, runtime_config: StudentQARuntimeConfig | None = None):
    # 按batch_size分批处理，避免单次请求过大
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        # 调用DashScope接口，分批获取向量
        batch_emb = DashScopeClient(runtime_config=runtime_config).embed_texts(batch, text_type=text_type)
        embeddings.extend(batch_emb)
    return embeddings
