from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import uuid


def _id() -> str:
    return uuid.uuid4().hex[:12]


# ── Agent ────────────────────────────────────────────────────────────────────

class Agent(BaseModel):
    id: str = Field(default_factory=_id)
    name: str = "新客服"
    role: str = "general"
    systemPrompt: str = "你是一个专业的客服助手。"
    voiceDescriptor: str = "(A warm young woman)"
    temperature: float = 0.7
    maxTokens: int = 1024
    enabledToolIds: list[str] = Field(default_factory=list)
    ragEnabled: bool = False
    enabled: bool = True


class CollaborationRule(BaseModel):
    id: str = Field(default_factory=_id)
    triggerAgentId: str
    targetAgentId: str
    condition: str  # natural language condition evaluated by LLM


class AgentGroup(BaseModel):
    id: str = Field(default_factory=_id)
    name: str = "默认客服组"
    description: str = ""
    agentIds: list[str] = Field(default_factory=list)
    defaultAgentId: str = ""
    routerPrompt: str = (
        "你是路由代理。根据用户消息判断应该由哪个客服处理。\n"
        "可用客服列表：\n{agent_list}\n\n"
        "用户消息：{user_message}\n\n"
        '请返回JSON格式：{"agent_id":"xxx","confidence":0.9,"reason":"原因"}'
    )
    collaborationRules: list[CollaborationRule] = Field(default_factory=list)


# ── Skill ────────────────────────────────────────────────────────────────────

class SkillType(str, Enum):
    BUILTIN = "builtin"
    HTTP = "http"
    SCRIPT = "script"


class SkillConfig(BaseModel):
    url: Optional[str] = None
    method: Optional[str] = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    code: Optional[str] = None


class Skill(BaseModel):
    id: str = Field(default_factory=_id)
    name: str = ""
    description: str = ""
    type: SkillType = SkillType.BUILTIN
    enabled: bool = True
    parameters: dict = Field(default_factory=dict)  # JSON Schema
    config: SkillConfig = Field(default_factory=SkillConfig)


# ── RAG ──────────────────────────────────────────────────────────────────────

class DocStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class RAGDocument(BaseModel):
    id: str = Field(default_factory=_id)
    filename: str = ""
    status: DocStatus = DocStatus.PROCESSING
    enabled: bool = True
    uploadedAt: str = ""
    chunkCount: int = 0
    error: Optional[str] = None


# ── Global Config ────────────────────────────────────────────────────────────

class NoiseType(str, Enum):
    NONE = "none"
    CAFE = "cafe"
    OFFICE = "office"
    STREET = "street"
    CUSTOM = "custom"


class LLMMode(str, Enum):
    OMNI = "omni"        # voice input -> LLM -> text out -> TTS
    TEXT_ASR = "text_asr" # voice -> ASR -> text -> LLM -> text -> TTS


class GlobalConfig(BaseModel):
    systemTitle: str = "智能语音客服"
    systemSubtitle: str = "Voice CS Demo"
    llmEndpoint: str = "http://localhost:8000/v1"
    llmApiKey: str = ""
    llmModel: str = "gpt-4o"
    ttsEndpoint: str = "http://localhost:8001/v1"
    ttsModel: str = "openbmb/VoxCPM2"
    ttsVoiceDescriptor: str = "(A warm young woman)"
    ttsResponseFormat: str = "pcm"
    asrEndpoint: str = "ws://localhost:10095"
    embedEndpoint: str = "http://localhost:8000/v1"
    embedApiKey: str = ""
    embedModel: str = "text-embedding-3-small"
    llmMode: LLMMode = LLMMode.TEXT_ASR
    noiseType: NoiseType = NoiseType.NONE
    noiseVolume: float = 0.1
    customNoiseFile: Optional[str] = None
    waitingMusicEnabled: bool = True


# ── Session / Transcript ─────────────────────────────────────────────────────

class TranscriptEntry(BaseModel):
    role: str  # "user" | "agent" | "system" | "tool"
    text: str
    agentName: Optional[str] = None
    agentId: Optional[str] = None
    timestamp: str = ""
    toolName: Optional[str] = None


class Session(BaseModel):
    id: str = Field(default_factory=_id)
    scenario: str = "inbound"  # "inbound" | "outbound"
    agentGroupId: str = ""
    activeAgentId: str = ""
    transcript: list[TranscriptEntry] = Field(default_factory=list)
    startedAt: str = ""
    endedAt: Optional[str] = None
    status: str = "active"  # "active" | "ended"
