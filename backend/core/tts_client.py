import base64
import logging
import httpx
import numpy as np
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class TTSClient:
    """HTTP client for vLLM-Omni /v1/audio/speech endpoint."""

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
    ) -> bytes:
        """Synthesize full audio. Returns raw audio bytes."""
        url = f"{self.endpoint}/audio/speech"
        body = {
            "model": self.model,
            "input": text,
            "voice": voice,
            "response_format": self.response_format,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=body)
            await self._raise_for_status(resp)
            return resp.content

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
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=body) as resp:
                await self._raise_for_status(resp)
                async for chunk in resp.aiter_bytes(4096):
                    if chunk:
                        yield chunk


def mix_noise(audio_bytes: bytes, noise_type: str, noise_volume: float, sample_rate: int = 48000) -> bytes:
    """Mix background noise with TTS audio output."""
    if noise_type == "none" or noise_volume <= 0:
        return audio_bytes

    # Convert bytes to float32 array
    audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    # Generate simple noise
    noise = np.random.randn(len(audio)).astype(np.float32) * noise_volume

    # Mix
    mixed = audio + noise
    mixed = np.clip(mixed, -1.0, 1.0)

    return (mixed * 32768).astype(np.int16).tobytes()
