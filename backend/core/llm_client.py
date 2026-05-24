import json
import logging
import httpx
from urllib.parse import urlparse
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """Async OpenAI-compatible LLM client."""

    def __init__(self, endpoint: str, api_key: str = "", model: str = "gpt-4o"):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model

    def update_config(self, endpoint: str, api_key: str, model: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            if self._is_mimo_endpoint():
                h["api-key"] = self.api_key
                h["Authorization"] = f"Bearer {self.api_key}"
            else:
                h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _is_mimo_endpoint(self) -> bool:
        host = urlparse(self.endpoint).netloc.lower()
        return "xiaomimimo.com" in host

    def _token_limit_param(self) -> str:
        return "max_completion_tokens" if self._is_mimo_endpoint() else "max_tokens"

    def _extract_message_text(self, message: dict) -> str:
        return message.get("content") or ""

    def _extract_delta_text(self, delta: dict) -> str:
        return delta.get("content") or ""

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
    ):
        """Send chat completion request. Returns full text or async token generator."""
        url = f"{self.endpoint}/chat/completions"
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            self._token_limit_param(): max_tokens,
        }

        if stream:
            return self._stream_chat(url, body)
        else:
            return await self._sync_chat(url, body)

    async def _sync_chat(self, url: str, body: dict) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=body, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            return self._extract_message_text(data["choices"][0]["message"])

    async def _stream_chat(self, url: str, body: dict) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=body, headers=self._headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        content = self._extract_delta_text(delta)
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
