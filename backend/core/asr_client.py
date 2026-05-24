import json
import logging
import asyncio
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


class ASRClient:
    """Mock ASR client for testing."""

    def __init__(self, endpoint: str = "ws://localhost:10095"):
        self.endpoint = endpoint

    async def recognize_stream(
        self,
        audio_chunks: list[bytes],
        on_partial: Optional[Callable[[str], Awaitable[None]]] = None,
        on_final: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> str:
        """Mock implementation: returns a fixed string after a short delay."""
        await asyncio.sleep(0.5)
        text = "你好，我想咨询业务。"
        if on_final:
            await on_final(text)
        return text
