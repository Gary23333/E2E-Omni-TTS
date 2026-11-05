"""Offline security regressions. All credentials below are synthetic fixtures."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import FastAPI

from core.json_store import ConfigStore, JsonStore
from core.local_access import LocalOnlyMiddleware, MAX_REQUEST_BYTES
from core.upload_safety import safe_filename, safe_path, AUDIO_SUFFIXES
from schemas.models import GlobalConfig, RAGDocument
from routers import config, rag


class LocalAccessTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, *, kind='http', client='127.0.0.1', host='localhost:8900', origin=None, method='GET', frames=None, extra=()):
        sent = []
        called = []
        async def app(scope, receive, send):
            called.append(scope)
            if kind == 'http':
                if method == 'POST':
                    called.append(await receive())
                await send({'type': 'http.response.start', 'status': 200, 'headers': []})
                await send({'type': 'http.response.body', 'body': b'ok'})
            else:
                await send({'type': 'websocket.accept'})
        headers = [(b'host', host.encode())]
        if origin is not None:
            headers.append((b'origin', origin.encode()))
        headers.extend(extra)
        scope = {'type': kind, 'client': (client, 1234), 'headers': headers, 'method': method}
        frames = iter(frames or [{'type': 'http.request', 'body': b'hello', 'more_body': False}])
        async def receive():
            return next(frames)
        async def send(message):
            sent.append(message)
        await LocalOnlyMiddleware(app)(scope, receive, send)
        return sent, called

    async def test_loopback_ipv4_ipv6_and_native_clients_allowed(self):
        for address in ['127.0.0.1', '::1', '::ffff:127.0.0.1']:
            sent, called = await self.invoke(client=address)
            self.assertEqual(sent[0]['status'], 200)
            self.assertTrue(called)
        sent, _ = await self.invoke(origin='http://localhost:5173')
        self.assertEqual(sent[0]['status'], 200)

    async def test_remote_peer_cannot_spoof_forwarded_header(self):
        sent, called = await self.invoke(client='203.0.113.5', extra=[(b'x-forwarded-for', b'127.0.0.1')])
        self.assertEqual(sent[0]['status'], 403)
        self.assertFalse(called)

    async def test_rebinding_hosts_and_foreign_origins_blocked(self):
        for host in ['evil.example:8900', 'localhost.evil.example', 'localhost:invalid', 'user@localhost:8900']:
            sent, called = await self.invoke(host=host)
            self.assertEqual(sent[0]['status'], 403, host)
            self.assertFalse(called)
        for origin in ['https://evil.example', 'null', 'http://localhost:9999']:
            sent, _ = await self.invoke(origin=origin)
            self.assertEqual(sent[0]['status'], 403)

    async def test_cross_site_websocket_rejected_before_accept(self):
        sent, called = await self.invoke(kind='websocket', origin='https://evil.example')
        self.assertEqual(sent, [{'type': 'websocket.close', 'code': 1008}])
        self.assertFalse(called)
        sent, _ = await self.invoke(kind='websocket', origin='http://127.0.0.1:5173')
        self.assertEqual(sent[0]['type'], 'websocket.accept')

    async def test_duplicate_hosts_and_origins_rejected(self):
        for extra in [[(b'host', b'localhost')], [(b'origin', b'https://evil.example')]]:
            sent, _ = await self.invoke(origin='http://localhost:5173', extra=extra)
            self.assertEqual(sent[0]['status'], 403)

    async def test_body_cap_checks_content_length_and_chunked_requests(self):
        sent, called = await self.invoke(method='POST', extra=[(b'content-length', str(MAX_REQUEST_BYTES+1).encode())])
        self.assertEqual(sent[0]['status'], 413)
        self.assertFalse(called)
        with patch('core.local_access.MAX_REQUEST_BYTES', 4):
            sent, called = await self.invoke(method='POST', frames=[{'type': 'http.request', 'body': b'abc', 'more_body': True}, {'type': 'http.request', 'body': b'de', 'more_body': False}])
        self.assertEqual(sent[0]['status'], 413)
        self.assertFalse(called)
        sent, called = await self.invoke(method='POST')
        self.assertEqual(called[1]['body'], b'hello')


class ConfigAndUploadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.data_patch = patch('core.json_store.DATA_DIR', self.directory)
        self.data_patch.start()
        self.store = ConfigStore('test.json', GlobalConfig(llmApiKey='fixture-llm-secret', embedApiKey='fixture-embed-secret').model_dump())
        self.engine = Mock()
        self.noise_patch = patch.object(config, 'NOISE_DIR', self.directory / 'noise')
        self.noise_patch.start()
        self.rag_patch = patch.object(rag, 'RAG_DIR', self.directory / 'rag')
        self.rag_patch.start()
        self.docs_patch = patch.object(rag, 'doc_store', JsonStore('documents.json', RAGDocument))
        self.docs_patch.start()
        app = FastAPI()
        app.include_router(config.create_router(self.store, self.engine), prefix='/api/config')
        app.include_router(rag.create_router(self.store, self.engine), prefix='/api/rag')
        app.add_middleware(LocalOnlyMiddleware)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 9000)), base_url='http://localhost:8900')

    async def asyncTearDown(self):
        await self.client.aclose()
        for p in [self.docs_patch, self.rag_patch, self.noise_patch, self.data_patch]:
            p.stop()
        self.temp.cleanup()

    async def test_get_is_read_only_and_never_returns_saved_keys(self):
        with patch.object(self.store, 'update', wraps=self.store.update) as update:
            result = await self.client.get('/api/config')
        self.assertEqual(result.status_code, 200)
        self.assertNotIn('fixture-llm-secret', result.text)
        self.assertNotIn('fixture-embed-secret', result.text)
        self.assertEqual(result.json()['llmApiKey'], '')
        self.assertTrue(result.json()['llmApiKeySet'])
        update.assert_not_called()

    async def test_blank_form_preserves_keys_and_response_is_redacted(self):
        result = await self.client.put('/api/config', json={'systemTitle': 'Changed', 'llmApiKey': '', 'embedApiKey': '', 'llmApiKeySet': True})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.store.get_all()['llmApiKey'], 'fixture-llm-secret')
        self.assertEqual(self.store.get_all()['embedApiKey'], 'fixture-embed-secret')
        self.assertNotIn('fixture-', result.text)

    async def test_replace_clear_and_endpoint_change_do_not_redirect_old_key(self):
        result = await self.client.put('/api/config', json={'llmApiKey': 'new-fixture-key'})
        self.assertEqual(result.json()['llmApiKey'], '')
        self.assertEqual(self.store.get_all()['llmApiKey'], 'new-fixture-key')
        result = await self.client.put('/api/config', json={'clearLlmApiKey': True})
        self.assertFalse(result.json()['llmApiKeySet'])
        result = await self.client.put('/api/config', json={'embedEndpoint': 'https://new-provider.example/v1', 'embedApiKey': ''})
        self.assertFalse(result.json()['embedApiKeySet'])
        self.assertEqual(self.store.get_all()['embedApiKey'], '')

    async def test_invalid_secret_updates_and_traversal_are_rejected(self):
        for payload in [{'clearLlmApiKey': 'true'}, {'clearLlmApiKey': True, 'llmApiKey': 'fixture-secret'}, {'llmApiKey': ['fixture-secret']}, {'noiseVolume': 'fixture-secret'}, {'unexpected': True}]:
            result = await self.client.put('/api/config', json=payload)
            self.assertEqual(result.status_code, 422)
            self.assertNotIn('fixture-secret', result.text)
        result = await self.client.put('/api/config', json={'customNoiseFile': '../../config.wav'})
        self.assertEqual(result.status_code, 400)

    async def test_asr_health_uses_client_for_http_or_websocket(self):
        with patch('routers.config.ASRClient') as cls:
            cls.return_value.test_connection = AsyncMock(return_value={'status': 'ok'})
            result = await self.client.post('/api/config/test_asr')
            self.assertEqual(result.json()['status'], 'ok')
            cls.return_value.test_connection.assert_awaited_once()

    async def test_noise_upload_uses_new_name_and_refuses_traversal_and_large_files(self):
        result = await self.client.post('/api/config/noise/upload', files={'file': ('recording.wav', b'RIFF-test', 'audio/wav')})
        self.assertEqual(result.status_code, 200)
        name = result.json()['filename']
        self.assertNotEqual(name, 'recording.wav')
        self.assertEqual((self.directory/'noise'/name).read_bytes(), b'RIFF-test')
        result = await self.client.post('/api/config/noise/upload', files={'file': ('../../escape.wav', b'bad', 'audio/wav')})
        self.assertEqual(result.status_code, 400)
        with patch('core.upload_safety.MAX_UPLOAD_BYTES', 4):
            result = await self.client.post('/api/config/noise/upload', files={'file': ('big.wav', b'12345', 'audio/wav')})
        self.assertEqual(result.status_code, 413)

    async def test_rag_upload_rejects_path_traversal_before_processing(self):
        for filename in ['../../outside.txt', '/absolute.txt', 'bad.exe']:
            result = await self.client.post('/api/rag/upload', files={'file': (filename, b'bad', 'text/plain')})
            self.assertEqual(result.status_code, 400, filename)
        self.engine.process_document.assert_not_called()
        self.engine.process_document.return_value = 1
        result = await self.client.post('/api/rag/upload', files={'file': ('notes.txt', b'hello', 'text/plain')})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['status'], 'ready')

    def test_symlink_and_windows_filename_escape_are_rejected(self):
        outside = self.directory/'outside.wav'
        outside.write_bytes(b'not-a-secret')
        noise = self.directory/'noise'
        noise.mkdir()
        (noise/'link.wav').symlink_to(outside)
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            safe_path(noise, 'link.wav', AUDIO_SUFFIXES)
        for filename in ['..\\outside.wav', '/outside.wav', 'bad.wav\x00']:
            with self.assertRaises(HTTPException):
                safe_filename(filename, AUDIO_SUFFIXES)
