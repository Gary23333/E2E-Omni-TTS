import json
import logging
import asyncio
import websockets
from typing import Optional, Callable, Awaitable, List

logger = logging.getLogger(__name__)


class ASRClient:
    """ASR client for FunASR WebSocket service.

    Supports streaming audio input and returns recognition results.
    Compatible with FunASR's WebSocket protocol.
    """

    def __init__(self, endpoint: str = "ws://localhost:10095"):
        self.endpoint = endpoint
        self._connection = None

    async def recognize_stream(
        self,
        audio_chunks: List[bytes],
        on_partial: Optional[Callable[[str], Awaitable[None]]] = None,
        on_final: Optional[Callable[[str], Awaitable[None]]] = None,
        sample_rate: int = 16000,
    ) -> str:
        """
        Recognize speech from audio chunks using FunASR WebSocket protocol.

        Args:
            audio_chunks: List of PCM audio chunks (16kHz, 16-bit, mono)
            on_partial: Callback for partial recognition results
            on_final: Callback for final recognition results
            sample_rate: Audio sample rate (default: 16000)

        Returns:
            Final recognized text
        """
        if not audio_chunks:
            return ""

        try:
            return await self._recognize_with_retry(
                audio_chunks, on_partial, on_final, sample_rate
            )
        except Exception as e:
            logger.error(f"ASR recognition failed: {e}")
            return ""

    async def _recognize_with_retry(
        self,
        audio_chunks: List[bytes],
        on_partial: Optional[Callable[[str], Awaitable[None]]],
        on_final: Optional[Callable[[str], Awaitable[None]]],
        sample_rate: int,
        max_retries: int = 2,
    ) -> str:
        """Recognize with retry logic."""
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return await self._do_recognize(
                    audio_chunks, on_partial, on_final, sample_rate
                )
            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.InvalidStatusCode,
                    ConnectionRefusedError) as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = 0.5 * (attempt + 1)
                    logger.warning(f"ASR connection failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"ASR recognition error: {e}")
                return ""

        logger.error(f"ASR recognition failed after {max_retries + 1} attempts: {last_error}")
        return ""

    async def _do_recognize(
        self,
        audio_chunks: List[bytes],
        on_partial: Optional[Callable[[str], Awaitable[None]]],
        on_final: Optional[Callable[[str], Awaitable[None]]],
        sample_rate: int,
    ) -> str:
        """Perform actual recognition via FunASR WebSocket."""
        uri = self.endpoint

        # Merge all chunks into one buffer
        full_audio = b"".join(audio_chunks)
        if not full_audio:
            return ""

        async with websockets.connect(
            uri,
            ping_interval=20,
            ping_timeout=60,
            close_timeout=10,
        ) as websocket:
            # FunASR expects JSON message first with config
            # Then binary audio data
            # Finally a JSON message indicating end of audio

            # Send initial config message
            config_msg = {
                "mode": "online",
                "chunk_size": [5, 10, 5],
                "wav_name": "stream",
                "is_speaking": True,
                "wav_format": "pcm",
                "audio_fs": sample_rate,
            }
            await websocket.send(json.dumps(config_msg))

            # Send audio in chunks to simulate streaming
            chunk_size = 9600  # 300ms at 16kHz 16-bit mono
            for i in range(0, len(full_audio), chunk_size):
                chunk = full_audio[i:i + chunk_size]
                await websocket.send(chunk)
                # Small delay to simulate real-time streaming
                await asyncio.sleep(0.01)

            # Send end of audio signal
            end_msg = {
                "is_speaking": False,
            }
            await websocket.send(json.dumps(end_msg))

            # Receive results
            final_text = ""

            try:
                async for message in websocket:
                    if isinstance(message, str):
                        try:
                            data = json.loads(message)
                            text = data.get("text", "")
                            is_final = data.get("is_final", False)

                            if text:
                                if is_final:
                                    final_text = text
                                    if on_final:
                                        await on_final(text)
                                else:
                                    if on_partial:
                                        await on_partial(text)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse ASR response: {message}")
                    else:
                        # Binary message (not expected from FunASR)
                        logger.debug(f"Received unexpected binary message from ASR")

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"ASR WebSocket closed: {e}")
                if not final_text:
                    raise

            return final_text

    async def test_connection(self) -> dict:
        """Test connection to ASR service."""
        try:
            async with websockets.connect(
                self.endpoint,
                ping_interval=None,
                open_timeout=5,
                close_timeout=5,
            ) as websocket:
                return {"status": "ok", "message": "Connected to ASR service"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
