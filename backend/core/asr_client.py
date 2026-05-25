import json
import logging
import asyncio
import base64
import struct
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


class ASRClient:
    """ASR client supporting FunASR WebSocket protocol and HTTP fallback."""

    def __init__(self, endpoint: str = "ws://localhost:10095"):
        self.endpoint = endpoint
        self._mode = "2pass"  # online, offline, 2pass

    async def recognize_stream(
        self,
        audio_chunks: list[bytes],
        on_partial: Optional[Callable[[str], Awaitable[None]]] = None,
        on_final: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> str:
        """Recognize speech from audio chunks.

        Tries WebSocket (FunASR) first, falls back to HTTP Whisper-style API,
        then falls back to mock for demo/development.
        """
        if not audio_chunks:
            return ""

        full_pcm = b"".join(audio_chunks)

        # Try WebSocket FunASR
        if self.endpoint.startswith("ws"):
            try:
                result = await self._recognize_ws(full_pcm, on_partial, on_final)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"FunASR WebSocket failed: {e}. Trying HTTP fallback.")

        # Try HTTP ASR API (e.g., Whisper-compatible)
        try:
            result = await self._recognize_http(full_pcm)
            if result:
                return result
        except Exception as e:
            logger.warning(f"HTTP ASR failed: {e}. Using mock fallback.")

        # Mock fallback for demo
        await asyncio.sleep(0.3)
        text = "你好，我想咨询业务。"
        if on_final:
            await on_final(text)
        return text

    async def _recognize_ws(
        self,
        pcm_data: bytes,
        on_partial: Optional[Callable[[str], Awaitable[None]]] = None,
        on_final: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> str:
        """FunASR WebSocket protocol implementation."""
        try:
            import websockets
        except ImportError:
            raise RuntimeError("websockets package not installed")

        # Build WAV header for 16kHz mono 16-bit PCM
        wav_data = self._pcm_to_wav(pcm_data, 16000)

        uri = self.endpoint
        if not uri.endswith("/"):
            uri += "/"

        # FunASR protocol: send config first, then audio chunks
        config = {
            "mode": self._mode,
            "chunk_size": [5, 10, 5],
            "wav_name": "h5",
            "is_speaking": True,
        }

        final_text = ""
        async with websockets.connect(uri) as websocket:
            # Send config
            await websocket.send(json.dumps(config))

            # Send audio in chunks (FunASR expects 960 bytes = 30ms @ 16kHz 16bit mono)
            chunk_size = 960
            for i in range(0, len(wav_data), chunk_size):
                chunk = wav_data[i:i + chunk_size]
                await websocket.send(chunk)
                await asyncio.sleep(0.01)  # Flow control

            # Send end signal
            end_config = {"is_speaking": False}
            await websocket.send(json.dumps(end_config))

            # Collect results
            try:
                while True:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(msg)

                    # FunASR response format
                    text = data.get("text", "")
                    if not text:
                        text = data.get("nbest", [{}])[0].get("sentence", "")

                    is_final = data.get("is_final", False)

                    if text:
                        if is_final:
                            final_text = text
                            if on_final:
                                await on_final(text)
                        else:
                            if on_partial:
                                await on_partial(text)

                    # End of recognition
                    if data.get("mode") == "offline" and is_final:
                        break

            except asyncio.TimeoutError:
                pass

        return final_text

    async def _recognize_http(self, pcm_data: bytes) -> str:
        """HTTP ASR fallback using Whisper-compatible API."""
        import httpx

        # Try common ASR HTTP endpoints
        endpoints = [
            self.endpoint.replace("ws://", "http://").replace("wss://", "https://"),
        ]

        wav_data = self._pcm_to_wav(pcm_data, 16000)

        for url in endpoints:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    files = {"audio": ("audio.wav", wav_data, "audio/wav")}
                    resp = await client.post(f"{url}/asr", files=files)
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data.get("text", data.get("result", ""))
                        if text:
                            return text
            except Exception:
                continue

        return ""

    @staticmethod
    def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000) -> bytes:
        """Create a basic WAV header for raw PCM data."""
        header = b'RIFF'
        header += struct.pack('<I', 36 + len(pcm_data))
        header += b'WAVEfmt '
        header += struct.pack('<I', 16)
        header += struct.pack('<H', 1)  # PCM
        header += struct.pack('<H', 1)  # Mono
        header += struct.pack('<I', sample_rate)
        header += struct.pack('<I', sample_rate * 2)
        header += struct.pack('<H', 2)
        header += struct.pack('<H', 16)
        header += b'data'
        header += struct.pack('<I', len(pcm_data))
        return header + pcm_data
