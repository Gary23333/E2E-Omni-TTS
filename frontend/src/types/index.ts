// ── Agent ──────────────────────────────────────────────────────────────────

export interface Agent {
  id: string;
  name: string;
  role: string;
  systemPrompt: string;
  voiceDescriptor: string;
  temperature: number;
  maxTokens: number;
  enabledToolIds: string[];
  ragEnabled: boolean;
  enabled: boolean;
}

export interface CollaborationRule {
  id: string;
  triggerAgentId: string;
  targetAgentId: string;
  condition: string;
}

export interface AgentGroup {
  id: string;
  name: string;
  description: string;
  agentIds: string[];
  defaultAgentId: string;
  routerPrompt: string;
  collaborationRules: CollaborationRule[];
}

// ── Skill ──────────────────────────────────────────────────────────────────

export type SkillType = 'builtin' | 'http' | 'script';

export interface SkillConfig {
  url?: string;
  method?: string;
  headers?: Record<string, string>;
  code?: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  type: SkillType;
  enabled: boolean;
  parameters: Record<string, unknown>;
  config: SkillConfig;
}

// ── RAG ────────────────────────────────────────────────────────────────────

export type DocStatus = 'processing' | 'ready' | 'error';

export interface RAGDocument {
  id: string;
  filename: string;
  status: DocStatus;
  enabled: boolean;
  uploadedAt: string;
  chunkCount: number;
  error?: string;
}

// ── Config ─────────────────────────────────────────────────────────────────

export type NoiseType = 'none' | 'cafe' | 'office' | 'street' | 'custom';
export type LLMMode = 'omni' | 'text_asr';

export interface GlobalConfig {
  systemTitle: string;
  systemSubtitle: string;
  llmEndpoint: string;
  llmApiKey: string;
  llmModel: string;
  ttsEndpoint: string;
  ttsModel: string;
  ttsVoiceDescriptor: string;
  ttsResponseFormat: string;
  asrEndpoint: string;
  embedEndpoint: string;
  embedApiKey: string;
  embedModel: string;
  llmMode: LLMMode;
  noiseType: NoiseType;
  noiseVolume: number;
  customNoiseFile: string | null;
  waitingMusicEnabled: boolean;
}

// ── Session / Transcript ───────────────────────────────────────────────────

export type TranscriptRole = 'user' | 'agent' | 'system' | 'tool';

export interface TranscriptEntry {
  role: TranscriptRole;
  text: string;
  agentName?: string;
  agentId?: string;
  timestamp?: string;
  toolName?: string;
}

export type CallStatus = 'idle' | 'connecting' | 'active' | 'on_hold' | 'ended';
export type Scenario = 'inbound' | 'outbound';
export type InputMode = 'voice' | 'text';

// ── WebSocket Messages ─────────────────────────────────────────────────────

export interface WSBaseMessage {
  type: string;
}

export interface WSCallStarted extends WSBaseMessage {
  type: 'call_started';
  sessionId: string;
  scenario: Scenario;
  agentId: string;
  agentName: string;
}

export interface WSCallEnded extends WSBaseMessage {
  type: 'call_ended';
  sessionId: string;
}

export interface WSAgentSwitch extends WSBaseMessage {
  type: 'agent_switch';
  agentId: string;
  agentName: string;
}

export interface WSTranscriptEntry extends WSBaseMessage {
  type: 'transcript_entry';
  role: TranscriptRole;
  text: string;
  agentName?: string;
}

export interface WSLLMToken extends WSBaseMessage {
  type: 'llm_token';
  text: string;
}

export interface WSLLMDone extends WSBaseMessage {
  type: 'llm_done';
}

export interface WSTTSDone extends WSBaseMessage {
  type: 'tts_done';
}

export interface WSTTSStop extends WSBaseMessage {
  type: 'tts_stop';
}

export interface WSToolCallStart extends WSBaseMessage {
  type: 'tool_call_start';
  toolName: string;
  message: string;
}

export interface WSToolCallEnd extends WSBaseMessage {
  type: 'tool_call_end';
  toolName: string;
}

export interface WSWaitingStart extends WSBaseMessage {
  type: 'waiting_start';
  message: string;
}

export interface WSWaitingEnd extends WSBaseMessage {
  type: 'waiting_end';
}

export interface WSError extends WSBaseMessage {
  type: 'error';
  message: string;
}

export type WSMessage =
  | WSCallStarted
  | WSCallEnded
  | WSAgentSwitch
  | WSTranscriptEntry
  | WSLLMToken
  | WSLLMDone
  | WSTTSDone
  | WSTTSStop
  | WSToolCallStart
  | WSToolCallEnd
  | WSWaitingStart
  | WSWaitingEnd
  | WSError;

// ── API Responses ──────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  status: 'ok' | 'error';
  message?: string;
}

export interface TestConnectionResponse {
  status: 'ok' | 'error';
  code?: number;
  message?: string;
  mode?: string;
}
