from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import httpx
from dashscope.audio.asr.transcription import Transcription
from dashscope.utils.oss_utils import OssUtils

from backend.app.common.config import get_settings


class DashScopeClient:
    EMBEDDING_BATCH_SIZE = 10

    def __init__(self) -> None:
        self.settings = get_settings()

    def ensure_ready(self) -> None:
        if not self.settings.dashscope_api_key:
            raise RuntimeError('DashScope API key is not configured.')

    def chat_completion(self, *, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        self.ensure_ready()
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        payload = {
            'model': self.settings.qa_llm_model,
            'input': {'messages': messages},
            'parameters': {'result_format': 'message', 'temperature': 0.2},
        }
        url = self.settings.dashscope_base_url.rstrip('/') + '/api/v1/services/aigc/text-generation/generation'
        headers = {
            'Authorization': f'Bearer {self.settings.dashscope_api_key}',
            'Content-Type': 'application/json',
        }
        with httpx.Client(timeout=self.settings.llm_timeout_seconds, trust_env=False) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            return {
                'raw': data,
                'text': data['output']['choices'][0]['message']['content'],
                'usage': data.get('usage') or {},
                'request_id': data.get('request_id') or data.get('requestId'),
            }
        except Exception as exc:
            raise RuntimeError(f"Unexpected DashScope chat response: {json.dumps(data, ensure_ascii=False)[:500]}") from exc

    def embed_texts(self, texts: list[str], *, text_type: str = 'document') -> list[list[float]]:
        self.ensure_ready()
        if not texts:
            return []
        url = self.settings.dashscope_base_url.rstrip('/') + '/api/v1/services/embeddings/text-embedding/text-embedding'
        headers = {
            'Authorization': f'Bearer {self.settings.dashscope_api_key}',
            'Content-Type': 'application/json',
        }
        all_embeddings: list[list[float]] = []
        with httpx.Client(timeout=self.settings.llm_timeout_seconds, trust_env=False) as client:
            for start in range(0, len(texts), self.EMBEDDING_BATCH_SIZE):
                chunk = texts[start : start + self.EMBEDDING_BATCH_SIZE]
                payload = {
                    'model': self.settings.qa_embedding_model,
                    'input': {'texts': chunk},
                    'parameters': {
                        'text_type': text_type,
                        'dimension': self.settings.qa_embedding_dimensions,
                    },
                }
                response = client.post(url, headers=headers, json=payload, timeout=120.0)
                response.raise_for_status()
                data = response.json()
                all_embeddings.extend(self._extract_embeddings(data))
        return all_embeddings

    def transcribe_audio(self, *, file_name: str, audio_bytes: bytes) -> str:
        self.ensure_ready()
        suffix = Path(file_name or 'voice.webm').suffix or '.webm'
        temp_path: str | None = None
        try:
            with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            oss_url, _ = OssUtils.upload(
                model=self.settings.qa_asr_model,
                file_path=temp_path,
                api_key=self.settings.dashscope_api_key,
            )
            task = Transcription.async_call(
                model=self.settings.qa_asr_model,
                file_urls=[oss_url],
                api_key=self.settings.dashscope_api_key,
                language_hints=['zh'],
                diarization_enabled=False,
                disfluency_removal_enabled=True,
            )
            result = Transcription.wait(task, api_key=self.settings.dashscope_api_key)
            transcript = self._collect_transcript_from_response(result)
            if not transcript:
                raise RuntimeError('语音识别未返回有效文本。')
            return transcript
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

    def _extract_embeddings(self, data: dict[str, Any]) -> list[list[float]]:
        output = data.get('output', {})
        embeddings = output.get('embeddings') or output.get('text_embeddings') or []
        if not embeddings:
            raise RuntimeError(f"Unexpected DashScope embedding response: {json.dumps(data, ensure_ascii=False)[:500]}")
        result: list[list[float]] = []
        for item in embeddings:
            embedding = item.get('embedding')
            if not isinstance(embedding, list):
                raise RuntimeError(f"Unexpected DashScope embedding item: {json.dumps(item, ensure_ascii=False)[:300]}")
            result.append(embedding)
        return result

    def _collect_transcript_from_response(self, response: Any) -> str:
        payload = dict(response)
        output = payload.get('output') or {}
        results = output.get('results') or output.get('result') or []
        if isinstance(results, dict):
            results = [results]
        texts: list[str] = []
        with httpx.Client(timeout=self.settings.qa_asr_timeout_seconds, trust_env=False) as client:
            for item in results:
                if not isinstance(item, dict):
                    continue
                transcription_url = item.get('transcription_url') or item.get('transcriptionUrl')
                if transcription_url:
                    remote = client.get(transcription_url)
                    remote.raise_for_status()
                    extracted = _extract_text_from_asr_json(remote.json())
                    if extracted:
                        texts.append(extracted)
                        continue
                extracted = _extract_text_from_asr_json(item)
                if extracted:
                    texts.append(extracted)
        deduped: list[str] = []
        seen: set[str] = set()
        for item in texts:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return '\n'.join(deduped).strip()


def _extract_text_from_asr_json(payload: Any) -> str:
    collected: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                normalized_key = str(key).lower()
                if normalized_key in {'text', 'sentence', 'transcript', 'content'} and isinstance(value, str):
                    text = value.strip()
                    if text:
                        collected.append(text)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in collected:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return '\n'.join(deduped).strip()
