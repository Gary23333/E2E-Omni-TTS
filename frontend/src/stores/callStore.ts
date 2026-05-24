import { create } from 'zustand';
import type { CallStatus, Scenario, InputMode, TranscriptEntry } from '../types';

interface CallState {
  status: CallStatus;
  scenario: Scenario;
  inputMode: InputMode;
  sessionId: string;
  agentGroupId: string;
  currentAgentId: string;
  currentAgentName: string;
  transcript: TranscriptEntry[];
  isRecording: boolean;
  isTTSPlaying: boolean;
  isWaiting: boolean;
  waitingMessage: string;
  llmPartialText: string;

  setScenario: (s: Scenario) => void;
  setInputMode: (m: InputMode) => void;
  setAgentGroup: (id: string) => void;
  setStatus: (s: CallStatus) => void;
  setAgent: (id: string, name: string) => void;
  addTranscript: (entry: TranscriptEntry) => void;
  clearTranscript: () => void;
  setRecording: (v: boolean) => void;
  setTTSPlaying: (v: boolean) => void;
  setWaiting: (v: boolean, msg?: string) => void;
  setLLMPartial: (text: string) => void;
  appendLLMToken: (token: string) => void;
  reset: () => void;
}

const initialState = {
  status: 'idle' as CallStatus,
  scenario: 'inbound' as Scenario,
  inputMode: 'text' as InputMode,
  sessionId: '',
  agentGroupId: '',
  currentAgentId: '',
  currentAgentName: '',
  transcript: [] as TranscriptEntry[],
  isRecording: false,
  isTTSPlaying: false,
  isWaiting: false,
  waitingMessage: '',
  llmPartialText: '',
};

export const useCallStore = create<CallState>((set) => ({
  ...initialState,

  setScenario: (scenario) => set({ scenario }),
  setInputMode: (inputMode) => set({ inputMode }),
  setAgentGroup: (agentGroupId) => set({ agentGroupId }),
  setStatus: (status) => set({ status }),
  setAgent: (currentAgentId, currentAgentName) => set({ currentAgentId, currentAgentName }),
  addTranscript: (entry) => set((s) => ({ transcript: [...s.transcript, { ...entry, timestamp: new Date().toISOString() }] })),
  clearTranscript: () => set({ transcript: [] }),
  setRecording: (isRecording) => set({ isRecording }),
  setTTSPlaying: (isTTSPlaying) => set({ isTTSPlaying }),
  setWaiting: (isWaiting, msg = '') => set({ isWaiting, waitingMessage: msg }),
  setLLMPartial: (llmPartialText) => set({ llmPartialText }),
  appendLLMToken: (token) => set((s) => ({ llmPartialText: s.llmPartialText + token })),
  reset: () => set(initialState),
}));
