import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8900/api';

const api = axios.create({ baseURL: API_BASE_URL });

// ── Agents ──
export const fetchAgents = () => api.get('/agents').then(r => r.data);
export const createAgent = (data: unknown) => api.post('/agents', data).then(r => r.data);
export const updateAgent = (id: string, data: unknown) => api.put(`/agents/${id}`, data).then(r => r.data);
export const deleteAgent = (id: string) => api.delete(`/agents/${id}`).then(r => r.data);

export const fetchGroups = () => api.get('/agents/groups/list').then(r => r.data);
export const createGroup = (data: unknown) => api.post('/agents/groups', data).then(r => r.data);
export const updateGroup = (id: string, data: unknown) => api.put(`/agents/groups/${id}`, data).then(r => r.data);
export const deleteGroup = (id: string) => api.delete(`/agents/groups/${id}`).then(r => r.data);

// ── RAG ──
export const fetchDocuments = () => api.get('/rag').then(r => r.data);
export const uploadDocument = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/rag/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data);
};
export const deleteDocument = (id: string) => api.delete(`/rag/${id}`).then(r => r.data);
export const toggleDocument = (id: string) => api.put(`/rag/${id}/toggle`).then(r => r.data);

// ── Skills ──
export const fetchSkills = () => api.get('/skills').then(r => r.data);
export const createSkill = (data: unknown) => api.post('/skills', data).then(r => r.data);
export const updateSkill = (id: string, data: unknown) => api.put(`/skills/${id}`, data).then(r => r.data);
export const deleteSkill = (id: string) => api.delete(`/skills/${id}`).then(r => r.data);
export const toggleSkill = (id: string) => api.put(`/skills/${id}/toggle`).then(r => r.data);

// ── Config ──
export const fetchConfig = () => api.get('/config').then(r => r.data);
export const updateConfig = (data: unknown) => api.put('/config', data).then(r => r.data);
export const testLLM = () => api.post('/config/test_llm').then(r => r.data);
export const testTTS = () => api.post('/config/test_tts').then(r => r.data);
export const testASR = () => api.post('/config/test_asr').then(r => r.data);
export const testEmbed = () => api.post('/config/test_embed').then(r => r.data);

export const fetchNoiseSamples = () => api.get<string[]>('/config/noise/samples').then(r => r.data);
export const uploadNoiseSample = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return api.post<{ filename: string }>('/config/noise/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data);
};
export const deleteNoiseSample = (filename: string) => api.delete(`/config/noise/${filename}`).then(r => r.data);

