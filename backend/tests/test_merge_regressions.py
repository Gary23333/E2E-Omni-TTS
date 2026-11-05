"""Offline regression checks for the PR #1 integration.

Run from backend: python -m unittest discover -s tests -v
No model endpoints or credentials are used.
"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx

from core.agent_manager import AgentManager
from core.json_store import JsonStore
from core.llm_client import LLMClient
from core.skill_executor import SkillExecutor
from schemas.models import Agent, GlobalConfig, Session, Skill
from routers import ws_voice

REAL_ASYNC_CLIENT = httpx.AsyncClient


class FakeLLM:
    def __init__(self, rounds):
        self.rounds = iter(rounds)
        self.requests = []

    async def chat(self, **kwargs):
        self.requests.append(kwargs)
        tokens = next(self.rounds)

        async def stream():
            for token in tokens:
                yield token
        return stream()


class ToolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.skill = Skill(id="allowed", name="test_tool", description="A test tool")
        self.executor = SkillExecutor([self.skill])

    def test_allowlist_filters_both_formats(self):
        self.assertEqual(self.executor.get_tool_definitions([]), "无可用工具")
        self.assertEqual(self.executor.get_tools_json_schema([]), [])
        self.assertIn("test_tool", self.executor.get_tool_definitions(["allowed"]))
        self.assertEqual(len(self.executor.get_tools_json_schema(["allowed"])), 1)

    async def test_allowlist_blocks_execution(self):
        func = AsyncMock(return_value="ok")
        with patch.dict("core.skill_executor.BUILTIN_SKILLS", {"test_tool": func}):
            result = await self.executor.execute("test_tool", {}, [])
            self.assertIn("未获授权", result)
            func.assert_not_awaited()
            self.assertEqual(await self.executor.execute("test_tool", {}, ["allowed"]), "ok")
            func.assert_awaited_once()

    def test_parser_rejects_incomplete_arguments(self):
        self.assertIsNone(self.executor.parse_tool_call('{"__tool_call__":{"name":"test_tool","arguments":"{\\\"x\\\":"}}'))
        self.assertIsNone(self.executor.parse_tool_call('{"tool_call":{"name":"test_tool","arguments":[]}}'))
        self.assertEqual(self.executor.parse_tool_call('{"__tool_call__":{"name":"test_tool","arguments":"{\\\"x\\\":1}"}}'), ("test_tool", {"x": 1}))

    async def test_tool_round_is_private_and_final_round_streams(self):
        llm = FakeLLM([
            ['{', '"tool_call": {"name":"test_tool",', '"arguments":{"x":1}}}'],
            ["查询", "完成。"],
        ])
        manager = AgentManager(llm, None, self.executor, Mock())
        agent = Agent(enabledToolIds=["allowed"])
        visible = []
        execute = AsyncMock(return_value="ok")

        async def on_token(token):
            visible.append(token)
        with patch.object(self.executor, "execute", execute):
            response, handoff = await manager.process_message("hi", agent, on_token)
        self.assertEqual(response, "查询完成。")
        self.assertIsNone(handoff)
        self.assertEqual(visible, ["查询", "完成。"])
        execute.assert_awaited_once_with("test_tool", {"x": 1}, ["allowed"])

    async def test_handoff_control_is_not_spoken(self):
        llm = FakeLLM([["好的，", "为您转接。", "[HAN", "DOFF:agent_tech]"]])
        manager = AgentManager(llm, None, self.executor, Mock())
        visible = []
        async def on_token(token):
            visible.append(token)
        response, handoff = await manager.process_message("hi", Agent(), on_token)
        self.assertEqual(handoff, "agent_tech")
        self.assertEqual("".join(visible), response)
        self.assertNotIn("HANDOFF", "".join(visible))

    async def test_handoff_preserves_suffix_after_leading_whitespace(self):
        llm = FakeLLM([["  好的，", "[HANDOFF:agent_tech]", "请稍候。"]])
        manager = AgentManager(llm, None, self.executor, Mock())
        visible = []
        async def on_token(token):
            visible.append(token)
        response, handoff = await manager.process_message("hi", Agent(), on_token)
        self.assertEqual(handoff, "agent_tech")
        self.assertEqual("".join(visible).strip(), response)
        self.assertIn("请稍候。", "".join(visible))

    async def test_no_tools_means_no_tools_in_prompt(self):
        manager = AgentManager(FakeLLM([["你好"]]), None, self.executor, Mock())
        messages = manager._build_messages("hi", Agent(enabledToolIds=[]))
        self.assertNotIn("test_tool", messages[0]["content"])


class LLMTests(unittest.IsolatedAsyncioTestCase):
    def factory(self, handler):
        transport = httpx.MockTransport(handler)
        return lambda **kwargs: REAL_ASYNC_CLIENT(transport=transport, **kwargs)

    async def test_stream_assembles_fragmented_tool_arguments(self):
        chunks = [
            {"tool_calls": [{"index": 0, "function": {"name": "test_tool", "arguments": ""}}]},
            {"tool_calls": [{"index": 0, "function": {"arguments": '{"city":'}}]},
            {"tool_calls": [{"index": 0, "function": {"arguments": '"北京"}'}}]},
        ]
        body = "".join("data: " + json.dumps({"choices": [{"delta": c}]}) + "\n\n" for c in chunks) + "data: [DONE]\n\n"
        def handler(request):
            request_body = json.loads(request.content)
            self.assertEqual(request_body["tools"], [{"type": "function"}])
            self.assertFalse(request_body["parallel_tool_calls"])
            return httpx.Response(200, text=body)
        client = LLMClient("http://test.invalid/v1")
        with patch("core.llm_client.httpx.AsyncClient", self.factory(handler)):
            stream = await client.chat([], stream=True, tools=[{"type": "function"}])
            tokens = [token async for token in stream]
        self.assertEqual(len(tokens), 1)
        self.assertEqual(json.loads(tokens[0])["__tool_call__"], {"name": "test_tool", "arguments": {"city": "北京"}})

    async def test_sync_tool_call_is_preserved(self):
        payload = {"choices": [{"message": {"content": None, "tool_calls": [{"function": {"name": "test_tool", "arguments": '{"x":1}'}}]}}]}
        with patch("core.llm_client.httpx.AsyncClient", self.factory(lambda request: httpx.Response(200, json=payload))):
            result = await LLMClient("http://test.invalid/v1").chat([])
        self.assertEqual(json.loads(result)["__tool_call__"]["arguments"], {"x": 1})

    async def test_partial_stream_is_not_replayed_after_timeout(self):
        calls = []
        class BrokenStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
                raise httpx.ReadTimeout("test timeout")
        def handler(request):
            calls.append(request)
            return httpx.Response(200, stream=BrokenStream())
        tokens = []
        with patch("core.llm_client.httpx.AsyncClient", self.factory(handler)):
            stream = await LLMClient("http://test.invalid/v1").chat([], stream=True)
            with self.assertRaises(httpx.ReadTimeout):
                async for token in stream:
                    tokens.append(token)
        self.assertEqual(tokens, ["hello"])
        self.assertEqual(len(calls), 1)

    async def test_retry_before_output_is_preserved(self):
        calls = []
        def handler(request):
            calls.append(request)
            if len(calls) == 1:
                raise httpx.ConnectError("test connect")
            return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n')
        with patch("core.llm_client.httpx.AsyncClient", self.factory(handler)), patch("core.llm_client.asyncio.sleep", AsyncMock()):
            stream = await LLMClient("http://test.invalid/v1").chat([], stream=True)
            self.assertEqual([token async for token in stream], ["ok"])
        self.assertEqual(len(calls), 2)

    def test_multiple_tool_calls_are_not_silently_dropped(self):
        with self.assertRaises(ValueError):
            LLMClient._serialize_tool_calls([{"function": {}}, {"function": {}}])


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def _run_session(self, ending, with_text=False):
        agent = Agent(id="a", name="测试", enabledToolIds=[])
        manager = AgentManager(FakeLLM([["你好。"]]), None, SkillExecutor([]), Mock())
        async def synthesize(*args, **kwargs):
            yield b"\x00\x00"
        manager.synthesize_speech = synthesize
        frames = [{"type": "websocket.receive", "text": json.dumps({"type": "start_call"})}]
        if with_text:
            frames.append({"type": "websocket.receive", "text": json.dumps({"type": "text_input", "text": "你好"})})
        frames.append(ending)
        class Socket:
            def __init__(self):
                self.messages = []
            async def accept(self):
                pass
            async def send_text(self, text):
                self.messages.append(json.loads(text))
            async def send_bytes(self, data):
                pass
            async def receive(self):
                if len(frames) == 1 and with_text:
                    for _ in range(100):
                        if any(m.get("type") == "llm_done" for m in self.messages):
                            break
                        await asyncio.sleep(0)
                return frames.pop(0)
        with tempfile.TemporaryDirectory() as tmp, patch("core.json_store.DATA_DIR", Path(tmp)):
            store = JsonStore("sessions.json", Session)
            with patch.object(ws_voice, "_build_managers", return_value=(None, None, None, None, manager, GlobalConfig())), patch.object(ws_voice, "agent_store", SimpleNamespace(list_all=lambda: [agent])), patch.object(ws_voice, "group_store", SimpleNamespace(list_all=lambda: [])), patch.object(ws_voice, "session_store", store):
                await asyncio.wait_for(ws_voice.voice_ws(Socket(), "test-session"), timeout=2)
            saved = store.get("test-session")
            self.assertEqual(len(store.list_all()), 1)
            self.assertEqual(saved.status, "ended")
            self.assertIsNotNone(saved.endedAt)
            self.assertTrue(saved.startedAt.endswith("+00:00"))
            self.assertTrue(all(e.timestamp.endswith("+00:00") for e in saved.transcript))
            self.assertIn("很高兴", saved.transcript[0].text)
            if with_text:
                self.assertEqual(saved.transcript[-2].role, "user")
                self.assertEqual(saved.transcript[-1].text, "你好。")

    async def test_explicit_end_persists_transcript(self):
        await self._run_session({"type": "websocket.receive", "text": '{"type":"end_call"}'}, with_text=True)

    async def test_disconnect_finalizes_session(self):
        await self._run_session({"type": "websocket.disconnect"})

    def test_save_upserts_without_duplicate_session(self):
        with tempfile.TemporaryDirectory() as tmp, patch("core.json_store.DATA_DIR", Path(tmp)):
            store = JsonStore("sessions.json", Session)
            store.save(Session(id="one"))
            store.save(Session(id="one", status="ended"))
            self.assertEqual(len(store.list_all()), 1)
            self.assertEqual(store.get("one").status, "ended")


class LocalExposureTests(unittest.TestCase):
    def test_backend_defaults_do_not_expose_configuration_to_network_or_any_origin(self):
        import ast
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text()
        tree = ast.parse(source)
        cors_calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                      and isinstance(n.func, ast.Attribute) and n.func.attr == "add_middleware"]
        cors_kwargs = {k.arg: ast.literal_eval(k.value) for k in cors_calls[0].keywords}
        self.assertEqual(cors_kwargs["allow_origins"], ["http://localhost:5173", "http://127.0.0.1:5173"])
        self.assertFalse(cors_kwargs["allow_credentials"])
        run_calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Attribute) and n.func.attr == "run"]
        self.assertEqual(next(ast.literal_eval(k.value) for k in run_calls[0].keywords if k.arg == "host"), "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
