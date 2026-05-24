import json
import base64
import logging
import asyncio
import struct
import re
import unicodedata
from datetime import datetime
from typing import Optional, Union, List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from schemas.models import Agent, AgentGroup, GlobalConfig, LLMMode, TranscriptEntry
from core.json_store import JsonStore, ConfigStore
from core.llm_client import LLMClient
from core.tts_client import TTSClient
from schemas.models import Skill
from core.skill_executor import SkillExecutor, DEFAULT_SKILLS
from core.rag_engine import RAGEngine
from core.agent_manager import AgentManager
from core.asr_client import ASRClient
from core.noise_manager import noise_manager

logger = logging.getLogger(__name__)
router = APIRouter()

STRONG_TTS_BREAKS = "。！？!?；;\n"
SOFT_TTS_BREAKS = "，,、：:"
MIN_TTS_SEGMENT_CHARS = 12
MAX_TTS_SEGMENT_CHARS = 90

def _strip_emoji(text: str) -> str:
    chars: list[str] = []
    for ch in text:
        code = ord(ch)
        category = unicodedata.category(ch)
        if category in {"So", "Sk"}:
            continue
        if (
            0x1F000 <= code <= 0x1FAFF
            or 0x2600 <= code <= 0x27BF
            or 0xFE00 <= code <= 0xFE0F
            or code == 0x200D
        ):
            continue
        chars.append(ch)
    return "".join(chars)


def sanitize_tts_text(text: str) -> str:
    """Remove visual-only Markdown and emoji before sending text to TTS."""
    text = _strip_emoji(text)
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}[-*_]{3,}\s*$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    text = re.sub(r"~~(.*?)~~", r"\1", text)
    text = re.sub(r"[#*_~`>\[\](){}<>|]", " ", text)
    text = text.replace("—", "，").replace("–", "，")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([，。！？；：,.!?;:])", r"\1", text)
    return text.strip()

def _get_wav_header(pcm_data: bytes, sample_rate: int = 16000) -> bytes:
    """Create a basic WAV header for raw PCM data."""
    header = b'RIFF'
    header += struct.pack('<I', 36 + len(pcm_data))
    header += b'WAVEfmt '
    header += struct.pack('<I', 16)
    header += struct.pack('<H', 1)
    header += struct.pack('<H', 1)
    header += struct.pack('<I', sample_rate)
    header += struct.pack('<I', sample_rate * 2)
    header += struct.pack('<H', 2)
    header += struct.pack('<H', 16)
    header += b'data'
    header += struct.pack('<I', len(pcm_data))
    return header + pcm_data

# ── Stores / singletons ─────────────────────────────────────────────────────

agent_store = JsonStore("agents.json", Agent)
group_store = JsonStore("agent_groups.json", AgentGroup)
skill_store = JsonStore("skills.json", Skill)

DEFAULTS = GlobalConfig().model_dump()
config_store = ConfigStore("global_config.json", DEFAULTS)

rag_engine = RAGEngine()


def _build_managers():
    """Build LLM, TTS, ASR, SkillExecutor, AgentManager from current config."""
    cfg = GlobalConfig(**config_store.get_all())
    llm = LLMClient(cfg.llmEndpoint, cfg.llmApiKey, cfg.llmModel)
    tts = TTSClient(cfg.ttsEndpoint, cfg.ttsModel, cfg.ttsResponseFormat)
    asr = ASRClient(cfg.asrEndpoint)
    skills = [s for s in JsonStore("skills.json", Skill).list_all() if s.enabled]
    executor = SkillExecutor(skills if skills else DEFAULT_SKILLS)
    
    # Initialize RAG engine with current config
    rag_engine.set_config(cfg)
    
    manager = AgentManager(llm, tts, executor, rag_engine)
    return llm, tts, asr, executor, manager, cfg


# ── WebSocket endpoint ───────────────────────────────────────────────────────

@router.websocket("/ws/voice/{session_id}")
async def voice_ws(ws: WebSocket, session_id: str):
    await ws.accept()
    logger.info(f"Voice WS connected: {session_id}")

    llm, tts, asr, executor, manager, cfg = _build_managers()
    transcript: List[Dict[str, Any]] = []
    audio_buffer: List[bytes] = []
    send_lock = asyncio.Lock()
    active_response: Dict[str, Any] = {"task": None, "bridge": None}

    async def send_json(msg: Dict[str, Any]):
        try:
            async with send_lock:
                await ws.send_text(json.dumps(msg, ensure_ascii=False))
        except Exception:
            pass

    async def send_audio_chunk(chunk: bytes):
        try:
            async with send_lock:
                await ws.send_bytes(chunk)
        except Exception:
            pass

    class StreamingTTSBridge:
        """Queues LLM text fragments and speaks them through streaming TTS."""

        def __init__(self, agent: Agent):
            self.agent = agent
            self.buffer = ""
            self.queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
            self.cancelled = False
            self.task = asyncio.create_task(self._run())

        async def feed(self, token: str):
            if not token or self.cancelled:
                return
            self.buffer += token
            self.buffer = sanitize_tts_text(self.buffer)
            await self._flush_ready_segments()

        async def finish(self):
            if self.cancelled:
                return
            tail = self.buffer.strip()
            self.buffer = ""
            if tail:
                await self.queue.put(tail)
            await self.queue.put(None)
            await self.task

        async def cancel(self):
            self.cancelled = True
            self.buffer = ""
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        async def _flush_ready_segments(self):
            while True:
                segment = self._pop_ready_segment()
                if not segment:
                    break
                await self.queue.put(segment)

        def _pop_ready_segment(self) -> Optional[str]:
            stripped = self.buffer.lstrip()
            if stripped != self.buffer:
                self.buffer = stripped

            strong_idx = self._first_break_index(STRONG_TTS_BREAKS)
            if strong_idx >= 0 and strong_idx + 1 >= MIN_TTS_SEGMENT_CHARS:
                return self._take(strong_idx + 1)

            soft_idx = self._last_break_index(SOFT_TTS_BREAKS)
            if soft_idx >= 0 and soft_idx + 1 >= 28:
                return self._take(soft_idx + 1)

            if len(self.buffer) >= MAX_TTS_SEGMENT_CHARS:
                return self._take(MAX_TTS_SEGMENT_CHARS)

            return None

        def _first_break_index(self, chars: str) -> int:
            indexes = [self.buffer.find(ch) for ch in chars if self.buffer.find(ch) >= 0]
            return min(indexes) if indexes else -1

        def _last_break_index(self, chars: str) -> int:
            indexes = [self.buffer.rfind(ch) for ch in chars if self.buffer.rfind(ch) >= 0]
            return max(indexes) if indexes else -1

        def _take(self, end: int) -> str:
            segment = self.buffer[:end].strip()
            self.buffer = self.buffer[end:]
            return segment

        async def _run(self):
            while True:
                text = await self.queue.get()
                if text is None:
                    break
                text = sanitize_tts_text(text)
                if not text:
                    continue

                async for chunk in manager.synthesize_speech(
                    text,
                    self.agent.voiceDescriptor or cfg.ttsVoiceDescriptor,
                    cfg.noiseType.value,
                    cfg.noiseVolume,
                ):
                    mixed_chunk = noise_manager.mix(
                        chunk,
                        cfg.noiseType.value,
                        cfg.noiseVolume,
                        cfg.customNoiseFile,
                    )
                    await send_audio_chunk(mixed_chunk)

    async def speak_text(text: str, agent: Agent):
        text = sanitize_tts_text(text)
        if not text:
            return
        async for chunk in manager.synthesize_speech(
            text,
            agent.voiceDescriptor or cfg.ttsVoiceDescriptor,
            cfg.noiseType.value,
            cfg.noiseVolume,
        ):
            mixed_chunk = noise_manager.mix(chunk, cfg.noiseType.value, cfg.noiseVolume, cfg.customNoiseFile)
            await send_audio_chunk(mixed_chunk)

    async def handle_processed_response(
        text: str,
        handoff: Optional[str],
        agent: Agent,
        tts_bridge: Optional[StreamingTTSBridge] = None,
    ):
        await send_json({"type": "llm_done"})
        
        # Handle handoff
        if handoff:
            target = next((a for a in manager._agents if a.id == handoff), None)
            if target:
                handoff_msg = f"正在为您转接至{target.name}，请稍候..."
                await send_json({"type": "waiting_start", "message": handoff_msg})
                transcript.append({"role": "system", "text": handoff_msg})
                await send_json({"type": "agent_switch", "agentId": target.id, "agentName": target.name})
                await send_json({"type": "waiting_end"})
                manager._active_agent = target

        # TTS
        transcript.append({"role": "agent", "text": text, "agentName": agent.name})
        await send_json({"type": "transcript_entry", "role": "agent", "text": text, "agentName": agent.name})

        if tts_bridge:
            await tts_bridge.finish()
        else:
            await speak_text(text, agent)
        await send_json({"type": "tts_done"})

    async def handle_llm_token(token: str, tts_bridge: StreamingTTSBridge):
        await send_json({"type": "llm_token", "text": token})
        await tts_bridge.feed(token)

    async def cancel_active_response(send_stop: bool = True):
        bridge = active_response.get("bridge")
        if bridge:
            await bridge.cancel()
            active_response["bridge"] = None

        task = active_response.get("task")
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        active_response["task"] = None

        if send_stop:
            await send_json({"type": "tts_stop"})
            await send_json({"type": "waiting_end"})

    async def run_text_response(text: str, active: Agent):
        bridge = StreamingTTSBridge(active)
        active_response["bridge"] = bridge
        try:
            response, handoff = await manager.process_message(
                text, active,
                on_token=lambda t: handle_llm_token(t, bridge),
                on_tool_start=lambda n, m: send_json({"type": "tool_call_start", "toolName": n, "message": m}),
                on_tool_end=lambda n: send_json({"type": "tool_call_end", "toolName": n}),
                on_waiting=lambda m: send_json({"type": "waiting_start", "message": m}),
            )
            await handle_processed_response(response, handoff, active, bridge)
        except asyncio.CancelledError:
            await bridge.cancel()
            raise
        finally:
            if active_response.get("bridge") is bridge:
                active_response["bridge"] = None
            if not bridge.task.done():
                await bridge.cancel()

    async def run_omni_response(full_pcm: bytes, active: Agent):
        try:
            logger.info("Processing Omni voice input")
            wav_data = _get_wav_header(full_pcm)
            audio_b64 = base64.b64encode(wav_data).decode("utf-8")

            await send_json({"type": "waiting_start", "message": "正在识别并理解语音..."})
            text = await asr.recognize_stream([full_pcm])
            logger.info(f"Omni ASR identified: {text}")

            if text:
                transcript.append({"role": "user", "text": text})
                await send_json({"type": "transcript_entry", "role": "user", "text": text})

            bridge = StreamingTTSBridge(active)
            active_response["bridge"] = bridge
            try:
                response, handoff = await manager.process_voice(
                    text if text else "用户语音输入", audio_b64, active,
                    on_token=lambda t: handle_llm_token(t, bridge)
                )
                await send_json({"type": "waiting_end"})
                await handle_processed_response(response, handoff, active, bridge)
            finally:
                if active_response.get("bridge") is bridge:
                    active_response["bridge"] = None
                if not bridge.task.done():
                    await bridge.cancel()
        except asyncio.CancelledError:
            await send_json({"type": "waiting_end"})
            raise

    async def run_asr_text_response(full_pcm: bytes, active: Agent):
        try:
            await send_json({"type": "waiting_start", "message": "正在识别语音..."})
            text = await asr.recognize_stream([full_pcm])
            await send_json({"type": "waiting_end"})

            if not text:
                await send_json({"type": "error", "message": "无法识别语音"})
                return

            transcript.append({"role": "user", "text": text})
            await send_json({"type": "transcript_entry", "role": "user", "text": text})

            await run_text_response(text, active)
        except asyncio.CancelledError:
            await send_json({"type": "waiting_end"})
            raise

    try:
        while True:
            raw = await ws.receive()

            if raw.get("type") == "websocket.receive":
                # ── Binary frame: audio data ──
                if "bytes" in raw and raw["bytes"]:
                    audio_buffer.append(raw["bytes"])
                    continue

                # ── Text frame: JSON control message ──
                if "text" in raw and raw["text"]:
                    msg = json.loads(raw["text"])
                    msg_type = msg.get("type")

                    # ── Start call ──
                    if msg_type == "start_call":
                        scenario = msg.get("scenario", "inbound")
                        group_id = msg.get("agentGroupId", "")

                        groups = group_store.list_all()
                        group = next((g for g in groups if g.id == group_id), groups[0] if groups else None)

                        agents = []
                        if group:
                            all_agents = agent_store.list_all()
                            agents = [a for a in all_agents if a.id in group.agentIds and a.enabled]

                        if not agents:
                            agents = [a for a in agent_store.list_all() if a.enabled]
                        
                        if not agents:
                            await send_json({"type": "error", "message": "没有可用的客服"})
                            continue

                        default_agent = agents[0]
                        if group and group.defaultAgentId:
                            found = next((a for a in agents if a.id == group.defaultAgentId), None)
                            if found:
                                default_agent = found

                        manager.set_context(agents, group, default_agent)

                        await send_json({
                            "type": "call_started",
                            "sessionId": session_id,
                            "scenario": scenario,
                            "agentId": default_agent.id,
                            "agentName": default_agent.name,
                        })

                        if scenario == "inbound":
                            greeting = f"您好，我是{default_agent.name}，很高兴为您服务。请问有什么可以帮您？"
                            transcript.append({"role": "agent", "text": greeting, "agentName": default_agent.name})
                            await send_json({"type": "transcript_entry", "role": "agent", "text": greeting, "agentName": default_agent.name})

                            await speak_text(greeting, default_agent)
                            await send_json({"type": "tts_done"})

                    # ── Audio chunk ──
                    elif msg_type == "audio_chunk":
                        data_b64 = msg.get("data")
                        if data_b64:
                            decoded = base64.b64decode(data_b64)
                            audio_buffer.append(decoded)

                    # ── Text input ──
                    elif msg_type == "text_input":
                        text = msg.get("text", "").strip()
                        if not text: continue

                        transcript.append({"role": "user", "text": text})
                        await send_json({"type": "transcript_entry", "role": "user", "text": text})

                        active = manager._active_agent or (manager._agents[0] if manager._agents else None)
                        if not active:
                            await send_json({"type": "error", "message": "无活跃客服"})
                            continue

                        await cancel_active_response(send_stop=False)
                        task = asyncio.create_task(run_text_response(text, active))
                        active_response["task"] = task

                    # ── Audio end ──
                    elif msg_type == "audio_end":
                        if not audio_buffer: continue
                        
                        full_pcm = b"".join(audio_buffer)
                        audio_buffer = []
                        active = manager._active_agent or (manager._agents[0] if manager._agents else None)
                        if not active: continue

                        if cfg.llmMode == LLMMode.OMNI:
                            await cancel_active_response(send_stop=False)
                            task = asyncio.create_task(run_omni_response(full_pcm, active))
                            active_response["task"] = task
                        else:
                            await cancel_active_response(send_stop=False)
                            task = asyncio.create_task(run_asr_text_response(full_pcm, active))
                            active_response["task"] = task

                    # ── Interrupt ──
                    elif msg_type == "interrupt":
                        await cancel_active_response(send_stop=True)

                    # ── End call ──
                    elif msg_type == "end_call":
                        await cancel_active_response(send_stop=True)
                        await send_json({"type": "call_ended", "sessionId": session_id})
                        transcript = []
                        break

    except WebSocketDisconnect:
        logger.info(f"Voice WS disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Voice WS error: {e}", exc_info=True)
        try:
            await send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
