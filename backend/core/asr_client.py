import asyncio
import io
import json
import logging
import wave
from typing import Optional, Callable, Awaitable, List
from urllib.parse import urlsplit, urlunsplit

import httpx
import websockets

logger = logging.getLogger(__name__)


class ASRClient:
    """Recognize signed 16-bit little-endian mono PCM.

    ws(s) endpoints use FunASR's WebSocket protocol with raw PCM, not WAV.
    Explicit http(s) endpoints use a custom multipart API: an ``audio`` WAV
    file is posted and the response must contain a string ``text`` or ``result``.
    A bare HTTP origin uses /asr; an explicit path is used unchanged. This is
    not the OpenAI/Whisper API. Failed WebSockets never fall back to HTTP.
    """

    def __init__(self, endpoint: str = "ws://localhost:10095"):
        self.endpoint = endpoint
        self._connection = None
        self._response_timeout = 30.0

    async def recognize_stream(
        self,
        audio_chunks: List[bytes],
        on_partial: Optional[Callable[[str], Awaitable[None]]] = None,
        on_final: Optional[Callable[[str], Awaitable[None]]] = None,
        sample_rate: int = 16000,
    ) -> str:
        """Return recognized final text, or an empty string on failure/silence.

        Callbacks are asynchronous. HTTP delivers only a final callback.
        sample_rate describes the supplied PCM; this client does not resample.
        """
        if not audio_chunks or not any(audio_chunks):
            return ""
        try:
            if sample_rate <= 0 or sum(map(len, audio_chunks)) % 2:
                raise ValueError("Expected whole 16-bit PCM samples and a positive sample rate")
            return await self._recognize_with_retry(
                audio_chunks, on_partial, on_final, sample_rate
            )
        except Exception as exc:
            logger.error("ASR recognition failed: %s", exc)
            return ""

    async def _recognize_with_retry(
        self,
        audio_chunks: List[bytes],
        on_partial: Optional[Callable[[str], Awaitable[None]]],
        on_final: Optional[Callable[[str], Awaitable[None]]],
        sample_rate: int,
        max_retries: int = 2,
    ) -> str:
        """Retry transient transport failures, never fabricate recognition."""
        for attempt in range(max_retries + 1):
            try:
                return await self._do_recognize(
                    audio_chunks, on_partial, on_final, sample_rate
                )
            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.InvalidStatusCode,
                    OSError, asyncio.TimeoutError, httpx.TransportError) as exc:
                if attempt == max_retries:
                    logger.error("ASR recognition failed after %s attempts: %s", attempt + 1, exc)
                    return ""
                await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as exc:
                logger.error("ASR recognition error: %s", exc)
                return ""
        return ""

    def _http_url(self) -> str:
        parts = urlsplit(self.endpoint)
        return urlunsplit(parts._replace(path=parts.path if parts.path not in ("", "/") else "/asr"))

    async def _do_recognize(
        self,
        audio_chunks: List[bytes],
        on_partial: Optional[Callable[[str], Awaitable[None]]],
        on_final: Optional[Callable[[str], Awaitable[None]]],
        sample_rate: int,
    ) -> str:
        full_audio = b"".join(audio_chunks)
        if not full_audio:
            return ""
        scheme = urlsplit(self.endpoint).scheme.lower()
        if scheme in ("http", "https"):
            text = await self._recognize_http(full_audio, sample_rate)
            if text and on_final:
                await on_final(text)
            return text
        if scheme not in ("ws", "wss"):
            raise ValueError("ASR endpoint must use ws, wss, http or https")

        async with websockets.connect(
            self.endpoint, ping_interval=20, ping_timeout=60,
            open_timeout=5, close_timeout=5,
        ) as websocket:
            await websocket.send(json.dumps({
                "mode": "online", "chunk_size": [5, 10, 5],
                "wav_name": "stream", "is_speaking": True,
                "wav_format": "pcm", "audio_fs": sample_rate,
            }))
            for offset in range(0, len(full_audio), 9600):
                await websocket.send(full_audio[offset:offset + 9600])
                await asyncio.sleep(0.01)
            await websocket.send(json.dumps({"is_speaking": False}))

            async def receive_final():
                while True:
                    message = await websocket.recv()
                    if not isinstance(message, str):
                        continue
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        logger.warning("Ignoring malformed ASR response")
                        continue
                    if not isinstance(data, dict):
                        continue
                    text = data.get("text", "")
                    if not isinstance(text, str):
                        text = ""
                    if data.get("is_final") is True:
                        if text and on_final:
                            await on_final(text)
                        # Empty final results mean silence, not a reason to wait.
                        return text
                    if text and on_partial:
                        await on_partial(text)

            # One deadline for the entire receive phase, not per message:
            # endless partial/malformed messages cannot keep it alive forever.
            return await asyncio.wait_for(receive_final(), self._response_timeout)

    async def _recognize_http(self, pcm_data: bytes, sample_rate: int = 16000) -> str:
        """Call the configured custom multipart ASR API (not Whisper API)."""
        async with httpx.AsyncClient(timeout=self._response_timeout, follow_redirects=False) as client:
            response = await client.post(
                self._http_url(),
                files={"audio": ("audio.wav", self._pcm_to_wav(pcm_data, sample_rate), "audio/wav")},
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            return ""
        text = data.get("text", data.get("result", ""))
        return text if isinstance(text, str) else ""

    @staticmethod
    def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm_data)
        return buffer.getvalue()

    async def test_connection(self) -> dict:
        """Probe reachability, not recognition quality or HTTP model readiness."""
        try:
            if urlsplit(self.endpoint).scheme.lower() in ("http", "https"):
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                    response = await client.get(self._http_url())
                    # POST-only endpoints commonly reject GET with 405.
                    if response.status_code != 405:
                        response.raise_for_status()
            else:
                async with websockets.connect(
                    self.endpoint, ping_interval=None, open_timeout=5, close_timeout=5,
                ):
                    pass
            return {"status": "ok", "message": "Connected to ASR service"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}
