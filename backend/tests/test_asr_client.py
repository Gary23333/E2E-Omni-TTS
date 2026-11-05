import asyncio
import io
import json
import unittest
import wave
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from core.asr_client import ASRClient


class ASRClientTests(unittest.IsolatedAsyncioTestCase):
    def websocket(self, messages):
        websocket = MagicMock()
        websocket.send = AsyncMock()
        websocket.recv = AsyncMock(side_effect=messages)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=websocket)
        context.__aexit__ = AsyncMock(return_value=False)
        return websocket, context

    async def test_empty_input_does_not_connect(self):
        with patch("core.asr_client.websockets.connect") as connect:
            for chunks in ([], [b""], [b"", b""]):
                self.assertEqual(await ASRClient().recognize_stream(chunks), "")
            connect.assert_not_called()

    async def test_pcm_config_callbacks_and_final_terminates(self):
        ws, context = self.websocket([
            "invalid", "[]", b"ignore", json.dumps({"text": "partial"}),
            json.dumps({"text": "recognized", "is_final": True}),
        ])
        partial, final = AsyncMock(), AsyncMock()
        with patch("core.asr_client.websockets.connect", return_value=context):
            result = await ASRClient().recognize_stream([b"\x01\x00", b"\x02\x00"], partial, final, 8000)
        self.assertEqual(result, "recognized")
        partial.assert_awaited_once_with("partial")
        final.assert_awaited_once_with("recognized")
        config = json.loads(ws.send.call_args_list[0].args[0])
        self.assertEqual(config["audio_fs"], 8000)
        self.assertEqual(config["wav_format"], "pcm")
        self.assertEqual(ws.send.call_args_list[1].args[0], b"\x01\x00\x02\x00")
        self.assertEqual(json.loads(ws.send.call_args_list[2].args[0]), {"is_speaking": False})
        self.assertEqual(ws.recv.await_count, 5)

    async def test_empty_final_terminates_without_callback(self):
        ws, context = self.websocket([json.dumps({"text": "", "is_final": True})])
        final = AsyncMock()
        with patch("core.asr_client.websockets.connect", return_value=context):
            self.assertEqual(await ASRClient().recognize_stream([b"\x00\x00"], on_final=final), "")
        final.assert_not_awaited()
        self.assertEqual(ws.recv.await_count, 1)

    async def test_transport_failure_retries_without_http_or_fake_text(self):
        client = ASRClient()
        final = AsyncMock()
        with patch("core.asr_client.websockets.connect", side_effect=ConnectionRefusedError) as connect, \
             patch("core.asr_client.asyncio.sleep", new_callable=AsyncMock), \
             patch.object(client, "_recognize_http", new_callable=AsyncMock) as http:
            self.assertEqual(await client.recognize_stream([b"\x00\x00"], on_final=final), "")
        self.assertEqual(connect.call_count, 3)
        http.assert_not_awaited()
        final.assert_not_awaited()

    async def test_receive_has_total_deadline_even_with_partial_messages(self):
        ws, context = self.websocket([])
        async def partial_forever():
            await asyncio.sleep(0)
            return json.dumps({"text": "partial"})
        ws.recv.side_effect = partial_forever
        client = ASRClient()
        client._response_timeout = 0.01
        with patch("core.asr_client.websockets.connect", return_value=context):
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(client._do_recognize([b"\x00\x00"], None, None, 16000), 1)
        self.assertGreater(ws.recv.await_count, 1)

    async def test_http_exact_path_wav_and_final_callback(self):
        captured = []
        def handle(request):
            captured.append(request)
            return httpx.Response(200, json={"result": "hello"})
        real_client = httpx.AsyncClient
        final, partial = AsyncMock(), AsyncMock()
        with patch("core.asr_client.httpx.AsyncClient", side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs)), \
             patch("core.asr_client.websockets.connect") as connect:
            client = ASRClient("https://asr.example/custom?language=en")
            result = await client.recognize_stream([b"\x01\x00"], partial, final, 8000)
        self.assertEqual(result, "hello")
        final.assert_awaited_once_with("hello")
        partial.assert_not_awaited()
        connect.assert_not_called()
        request = captured[0]
        self.assertEqual(str(request.url), "https://asr.example/custom?language=en")
        self.assertEqual(request.method, "POST")
        self.assertIn(b'name="audio"; filename="audio.wav"', request.content)
        self.assertIn(client._pcm_to_wav(b"\x01\x00", 8000), request.content)

    async def test_http_errors_empty_and_invalid_results_never_fabricate(self):
        real_client = httpx.AsyncClient
        for status, payload in [(500, {}), (200, {}), (200, {"text": ""}), (200, {"text": ["wrong type"]}), (200, [])]:
            with self.subTest(status=status, payload=payload):
                final = AsyncMock()
                def handle(request):
                    return httpx.Response(status, json=payload)
                with patch("core.asr_client.httpx.AsyncClient", side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs)):
                    self.assertEqual(await ASRClient("http://asr.example").recognize_stream([b"\x00\x00"], on_final=final), "")
                final.assert_not_awaited()

    async def test_invalid_pcm_or_scheme_is_empty(self):
        with patch("core.asr_client.websockets.connect") as connect:
            self.assertEqual(await ASRClient().recognize_stream([b"x"]), "")
            self.assertEqual(await ASRClient().recognize_stream([b"xx"], sample_rate=0), "")
            self.assertEqual(await ASRClient("ftp://bad").recognize_stream([b"xx"]), "")
        connect.assert_not_called()

    def test_wav_header_and_http_origin(self):
        client = ASRClient("https://asr.example/?language=en")
        self.assertEqual(client._http_url(), "https://asr.example/asr?language=en")
        pcm = b"\x01\x00" * 20
        with wave.open(io.BytesIO(client._pcm_to_wav(pcm, 24000)), "rb") as wav:
            self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), (1, 2, 24000))
            self.assertEqual(wav.readframes(20), pcm)

    async def test_connection_http_post_only_and_failure(self):
        real_client = httpx.AsyncClient
        for status, expected in [(405, "ok"), (503, "error")]:
            with self.subTest(status=status):
                with patch("core.asr_client.httpx.AsyncClient", side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(lambda request: httpx.Response(status)), **kwargs)):
                    self.assertEqual((await ASRClient("https://asr.example").test_connection())["status"], expected)


if __name__ == "__main__":
    unittest.main()
