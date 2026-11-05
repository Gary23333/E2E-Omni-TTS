import json
import logging
import httpx
import asyncio
from urllib.parse import urlparse
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """Async OpenAI-compatible LLM client with retry logic."""

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
        max_retries: int = 2,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
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

        if tools:
            body["tools"] = tools
            # The orchestrator executes one tool per round.
            body["parallel_tool_calls"] = False
        if tool_choice is not None:
            body["tool_choice"] = tool_choice

        if stream:
            return self._stream_chat(url, body, max_retries)
        else:
            return await self._sync_chat(url, body, max_retries)

    @staticmethod
    def _serialize_tool_calls(tool_calls: list[dict]) -> str:
        if len(tool_calls) != 1:
            raise ValueError("Expected exactly one tool call per completion")
        function = tool_calls[0].get("function", {})
        name = function.get("name")
        arguments = function.get("arguments", "{}")
        if not isinstance(name, str) or not name:
            raise ValueError("Tool call is missing its function name")
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object")
        return json.dumps({"__tool_call__": {"name": name, "arguments": arguments}}, ensure_ascii=False)

    async def _sync_chat(self, url: str, body: dict, max_retries: int = 2) -> str:
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(url, json=body, headers=self._headers())
                    resp.raise_for_status()
                    data = resp.json()
                    message = data["choices"][0]["message"]
                    if message.get("tool_calls"):
                        return self._serialize_tool_calls(message["tool_calls"])
                    return self._extract_message_text(message)
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:  # Rate limit
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"Rate limited, retrying in {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                elif e.response.status_code >= 500:  # Server error
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"Server error {e.response.status_code}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"Connection error, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"LLM chat error: {e}")
                raise

        raise last_error

    async def _stream_chat(self, url: str, body: dict, max_retries: int = 2) -> AsyncGenerator[str, None]:
        last_error = None

        for attempt in range(max_retries + 1):
            emitted = False
            tool_calls: dict[int, dict] = {}
            try:
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
                                    emitted = True
                                    yield content
                                for delta_call in delta.get("tool_calls") or []:
                                    index = delta_call.get("index", 0)
                                    call = tool_calls.setdefault(index, {"function": {"name": "", "arguments": ""}})
                                    function = delta_call.get("function") or {}
                                    for key in ("name", "arguments"):
                                        call["function"][key] += function.get(key) or ""
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
                if tool_calls:
                    yield self._serialize_tool_calls([tool_calls[key] for key in sorted(tool_calls)])
                return  # Success, exit retry loop
            except httpx.HTTPStatusError as e:
                last_error = e
                if emitted:
                    # Replaying a partially delivered stream duplicates text/audio.
                    raise
                if e.response.status_code == 429:  # Rate limit
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"Rate limited during streaming, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                elif e.response.status_code >= 500:  # Server error
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"Server error during streaming, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if emitted:
                    # Replaying a partially delivered stream duplicates text/audio.
                    raise
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"Connection error during streaming, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"LLM stream error: {e}")
                raise

        raise last_error
