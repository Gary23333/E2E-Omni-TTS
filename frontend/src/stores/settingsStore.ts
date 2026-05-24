import { create } from 'zustand';
import type { GlobalConfig } from '../types';
import { fetchConfig, updateConfig } from '../api/client';

interface SettingsState extends GlobalConfig {
  loaded: boolean;
  load: () => Promise<void>;
  update: (partial: Partial<GlobalConfig>) => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  systemTitle: '智能语音客服',
  systemSubtitle: 'Voice CS Demo',
  llmEndpoint: 'http://localhost:8000/v1',
  llmApiKey: '',
  llmModel: 'gpt-4o',
  ttsEndpoint: 'http://localhost:8001/v1',
  ttsModel: 'openbmb/VoxCPM2',
  ttsVoiceDescriptor: '(A warm young woman)',
  ttsResponseFormat: 'pcm',
  asrEndpoint: 'ws://localhost:10095',
  embedEndpoint: 'http://localhost:8000/v1',
  embedApiKey: '',
  embedModel: 'text-embedding-3-small',
  llmMode: 'text_asr',
  noiseType: 'none',
  noiseVolume: 0.1,
  customNoiseFile: null,
  waitingMusicEnabled: true,
  loaded: false,

  load: async () => {
    try {
      const data = await fetchConfig();
      set({ ...data, loaded: true });
    } catch {
      set({ loaded: true });
    }
  },

  update: async (partial) => {
    const data = await updateConfig(partial);
    set(data);
  },
}));
