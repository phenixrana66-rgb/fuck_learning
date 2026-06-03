from __future__ import annotations

import json
from typing import Any

import httpx

from backend.app.student_runtime.qa_runtime_config_service import (
    PROVIDER_DASHSCOPE,
    PROVIDER_OPENAI_COMPATIBLE,
    ModelCapabilityConfig,
    resolve_api_key_ref,
)


class ModelProviderError(RuntimeError):
    pass


class ModelProviderConfigError(ModelProviderError):
    pass


class ModelProviderCapabilityError(ModelProviderError):
    pass


class BaseModelProviderAdapter:
    def __init__(self, config: ModelCapabilityConfig) -> None:
        self.config = config

    @property
    def api_key(self) -> str:
        key = resolve_api_key_ref(self.config.api_key_ref)
        if not key:
            raise ModelProviderConfigError(f"apiKeyRef 未配置或不存在：{self.config.api_key_ref}")
        return key

    @property
    def base_url(self) -> str:
        base_url = (self.config.base_url or "").rstrip("/")
        if not base_url:
            raise ModelProviderConfigError(f"{self.config.capability} 缺少 baseUrl")
        return base_url

    def chat_completion(self, *, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        raise ModelProviderCapabilityError(f"{self.config.provider} 不支持文本问答能力")

    def chat_multimodal_completion(
        self,
        *,
        prompt: str,
        image_data_urls: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        raise ModelProviderCapabilityError(f"{self.config.provider} 不支持图片理解能力")

    def create_image_generation_task(
        self,
        *,
        prompt: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise ModelProviderCapabilityError(f"{self.config.provider} 不支持图片生成能力")

    def get_image_generation_task(self, task_id: str) -> dict[str, Any]:
        raise ModelProviderCapabilityError(f"{self.config.provider} 不支持图片生成任务查询能力")

    def embed_texts(self, texts: list[str], *, text_type: str = "document") -> list[list[float]]:
        raise ModelProviderCapabilityError(f"{self.config.provider} 不支持 Embedding 能力")


class DashScopeProviderAdapter(BaseModelProviderAdapter):
    EMBEDDING_BATCH_SIZE = 10

    def chat_completion(self, *, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.config.model_name,
            "input": {"messages": messages},
            "parameters": {"result_format": "message", "temperature": 0.2},
        }
        url = self.base_url + "/api/v1/services/aigc/text-generation/generation"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.config.timeout_seconds, trust_env=False) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            return {
                "raw": data,
                "text": data["output"]["choices"][0]["message"]["content"],
                "usage": data.get("usage") or {},
                "request_id": data.get("request_id") or data.get("requestId"),
            }
        except Exception as exc:
            raise ModelProviderError(f"Unexpected DashScope chat response: {json.dumps(data, ensure_ascii=False)[:500]}") from exc

    def chat_multimodal_completion(
        self,
        *,
        prompt: str,
        image_data_urls: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        if not image_data_urls:
            return self.chat_completion(prompt=prompt, system_prompt=system_prompt)
        content: list[dict[str, Any]] = [
            {"type": "image_url", "image_url": {"url": image_url}}
            for image_url in image_data_urls
        ]
        content.append({"type": "text", "text": prompt})
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})
        payload = {"model": self.config.model_name, "messages": messages, "temperature": 0.2}
        url = self.base_url + "/compatible-mode/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.config.timeout_seconds, trust_env=False) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            return {
                "raw": data,
                "text": _extract_message_text(data["choices"][0]["message"]["content"]),
                "usage": data.get("usage") or {},
                "request_id": data.get("id") or data.get("request_id") or data.get("requestId"),
            }
        except Exception as exc:
            raise ModelProviderError(f"Unexpected DashScope multimodal response: {json.dumps(data, ensure_ascii=False)[:500]}") from exc

    def create_image_generation_task(
        self,
        *,
        prompt: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model": self.config.model_name,
            "input": {"prompt": prompt},
            "parameters": parameters or {},
        }
        url = self.base_url + "/api/v1/services/aigc/text2image/image-synthesis"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        with httpx.Client(timeout=self.config.timeout_seconds, trust_env=False) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            output = data["output"]
            return {
                "raw": data,
                "task_id": output["task_id"],
                "status": output.get("task_status") or "PENDING",
                "request_id": data.get("request_id") or data.get("requestId"),
                "model": self.config.model_name,
            }
        except Exception as exc:
            raise ModelProviderError(f"Unexpected DashScope image task response: {json.dumps(data, ensure_ascii=False)[:500]}") from exc

    def get_image_generation_task(self, task_id: str) -> dict[str, Any]:
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            raise ModelProviderError("DashScope image task id is empty.")
        url = self.base_url + f"/api/v1/tasks/{normalized_task_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=self.config.timeout_seconds, trust_env=False) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
        try:
            output = data["output"]
            return {
                "raw": data,
                "task_id": output.get("task_id") or normalized_task_id,
                "status": output.get("task_status") or "UNKNOWN",
                "results": output.get("results") or [],
                "metrics": output.get("task_metrics") or {},
                "usage": data.get("usage") or {},
                "request_id": data.get("request_id") or data.get("requestId"),
                "model": self.config.model_name,
            }
        except Exception as exc:
            raise ModelProviderError(f"Unexpected DashScope image task query response: {json.dumps(data, ensure_ascii=False)[:500]}") from exc

    def embed_texts(self, texts: list[str], *, text_type: str = "document") -> list[list[float]]:
        if not texts:
            return []
        url = self.base_url + "/api/v1/services/embeddings/text-embedding/text-embedding"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        dimensions = int(self.config.settings.get("dimensions") or 1024)
        all_embeddings: list[list[float]] = []
        with httpx.Client(timeout=self.config.timeout_seconds, trust_env=False) as client:
            for start in range(0, len(texts), self.EMBEDDING_BATCH_SIZE):
                chunk = texts[start : start + self.EMBEDDING_BATCH_SIZE]
                payload = {
                    "model": self.config.model_name,
                    "input": {"texts": chunk},
                    "parameters": {"text_type": text_type, "dimension": dimensions},
                }
                response = client.post(url, headers=headers, json=payload, timeout=max(self.config.timeout_seconds, 120.0))
                response.raise_for_status()
                data = response.json()
                all_embeddings.extend(_extract_dashscope_embeddings(data))
        return all_embeddings


class OpenAICompatibleProviderAdapter(BaseModelProviderAdapter):
    def chat_completion(self, *, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._chat(messages)

    def chat_multimodal_completion(
        self,
        *,
        prompt: str,
        image_data_urls: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        if not image_data_urls:
            return self.chat_completion(prompt=prompt, system_prompt=system_prompt)
        content: list[dict[str, Any]] = [
            {"type": "image_url", "image_url": {"url": image_url}}
            for image_url in image_data_urls
        ]
        content.append({"type": "text", "text": prompt})
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})
        return self._chat(messages)

    def embed_texts(self, texts: list[str], *, text_type: str = "document") -> list[list[float]]:
        if not texts:
            return []
        payload: dict[str, Any] = {"model": self.config.model_name, "input": texts}
        dimensions = self.config.settings.get("dimensions")
        if dimensions:
            payload["dimensions"] = int(dimensions)
        url = self.base_url + "/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=max(self.config.timeout_seconds, 120.0), trust_env=False) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        items = data.get("data") or []
        if not isinstance(items, list):
            raise ModelProviderError(f"Unexpected OpenAI-compatible embeddings response: {json.dumps(data, ensure_ascii=False)[:500]}")
        ordered = sorted(items, key=lambda item: int(item.get("index", 0)) if isinstance(item, dict) else 0)
        embeddings = [item.get("embedding") for item in ordered if isinstance(item, dict)]
        if len(embeddings) != len(texts) or any(not isinstance(item, list) for item in embeddings):
            raise ModelProviderError(f"Unexpected OpenAI-compatible embeddings response: {json.dumps(data, ensure_ascii=False)[:500]}")
        return embeddings

    def create_image_generation_task(
        self,
        *,
        prompt: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise ModelProviderCapabilityError("OpenAI-compatible provider 尚未配置图片生成能力")

    def _chat(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {"model": self.config.model_name, "messages": messages, "temperature": 0.2, "stream": False}
        url = self.base_url + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.config.timeout_seconds, trust_env=False) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            return {
                "raw": data,
                "text": _extract_message_text(data["choices"][0]["message"]["content"]),
                "usage": data.get("usage") or {},
                "request_id": data.get("id") or data.get("request_id") or data.get("requestId"),
            }
        except Exception as exc:
            raise ModelProviderError(f"Unexpected OpenAI-compatible chat response: {json.dumps(data, ensure_ascii=False)[:500]}") from exc


def build_provider_adapter(config: ModelCapabilityConfig) -> BaseModelProviderAdapter:
    provider = str(config.provider or "").strip().lower().replace("-", "_")
    if provider == PROVIDER_DASHSCOPE:
        return DashScopeProviderAdapter(config)
    if provider in {PROVIDER_OPENAI_COMPATIBLE, "openai"}:
        return OpenAICompatibleProviderAdapter(config)
    raise ModelProviderCapabilityError(f"暂不支持模型供应商：{config.provider}")


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts).strip()
    raise ModelProviderError(f"Unsupported model content payload: {json.dumps(content, ensure_ascii=False)[:300]}")


def _extract_dashscope_embeddings(data: dict[str, Any]) -> list[list[float]]:
    output = data.get("output", {})
    embeddings = output.get("embeddings") or output.get("text_embeddings") or []
    if not embeddings:
        raise ModelProviderError(f"Unexpected DashScope embedding response: {json.dumps(data, ensure_ascii=False)[:500]}")
    result: list[list[float]] = []
    for item in embeddings:
        embedding = item.get("embedding")
        if not isinstance(embedding, list):
            raise ModelProviderError(f"Unexpected DashScope embedding item: {json.dumps(item, ensure_ascii=False)[:300]}")
        result.append(embedding)
    return result
