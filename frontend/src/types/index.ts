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

export interface Skill {
  id: string;
  name: string;
  description: string;
  type: 'builtin' | 'http' | 'script';
  enabled: boolean;
  parameters: Record<string, unknown>;
  config: {
    url?: string;
    method?: string;
    headers?: Record<string, string>;
    code?: string;
  };
}

export interface RAGDocument {
  id: string;
  filename: string;
  status: 'processing' | 'ready' | 'error';
  enabled: boolean;
  uploadedAt: string;
  chunkCount: number;
  error?: string;
}

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

export interface TranscriptEntry {
  role: 'user' | 'agent' | 'system' | 'tool';
  text: string;
  agentName?: string;
  agentId?: string;
  timestamp?: string;
  toolName?: string;
}

export type CallStatus = 'idle' | 'connecting' | 'active' | 'on_hold' | 'ended';
export type Scenario = 'inbound' | 'outbound';
export type InputMode = 'voice' | 'text';

export interface WSMessage {
  type: string;
  [key: string]: unknown;
}
