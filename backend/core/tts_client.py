import logging
import httpx
import asyncio
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class TTSClient:
    """HTTP client for VoxCPM2 /v1/audio/speech endpoint with retry logic."""

    def __init__(self, endpoint: str, model: str = "openbmb/VoxCPM2", response_format: str = "pcm"):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.response_format = response_format

    def update_config(self, endpoint: str, model: str, response_format: str = "pcm"):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.response_format = response_format

    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        max_retries: int = 2,
    ) -> bytes:
        """Synthesize full audio. Returns raw audio bytes."""
        url = f"{self.endpoint}/audio/speech"
        body = {
            "model": self.model,
            "input": text,
            "voice": voice,
            "response_format": self.response_format,
        }

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(url, json=body)
                    await self._raise_for_status(resp)
                    return resp.content
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500 and attempt < max_retries:
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"TTS server error, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"TTS connection error, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raise last_error

    async def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            body = await resp.aread()
            detail = body.decode("utf-8", errors="replace")[:500] if body else resp.reason_phrase
            raise RuntimeError(
                f"TTS request failed: {resp.status_code} {resp.reason_phrase} from {resp.url}. "
                f"Response: {detail}"
            )

    async def synthesize_streaming(
        self,
        text: str,
        voice: str = "default",
        max_retries: int = 2,
    ) -> AsyncGenerator[bytes, None]:
        """Synthesize audio in streaming chunks."""
        url = f"{self.endpoint}/audio/speech"
        body = {
            "model": self.model,
            "input": text,
            "voice": voice,
            "response_format": self.response_format,
            "stream": True,
        }

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream("POST", url, json=body) as resp:
                        await self._raise_for_status(resp)
                        async for chunk in resp.aiter_bytes(4096):
                            if chunk:
                                yield chunk
                return  # Success, exit retry loop
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500 and attempt < max_retries:
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"TTS streaming server error, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 8)
                    logger.warning(f"TTS streaming connection error, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                logger.error(f"TTS streaming error: {e}")
                raise

        raise last_error
