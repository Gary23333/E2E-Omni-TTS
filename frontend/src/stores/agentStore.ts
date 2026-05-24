import { create } from 'zustand';
import type { Agent, AgentGroup } from '../types';
import * as api from '../api/client';

interface AgentState {
  agents: Agent[];
  groups: AgentGroup[];
  selectedGroupId: string;
  load: () => Promise<void>;
  createAgent: (a: Agent) => Promise<void>;
  updateAgent: (id: string, data: Partial<Agent>) => Promise<void>;
  deleteAgent: (id: string) => Promise<void>;
  createGroup: (g: AgentGroup) => Promise<void>;
  updateGroup: (id: string, data: Partial<AgentGroup>) => Promise<void>;
  deleteGroup: (id: string) => Promise<void>;
  selectGroup: (id: string) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  agents: [],
  groups: [],
  selectedGroupId: '',

  load: async () => {
    const [agents, groups] = await Promise.all([api.fetchAgents(), api.fetchGroups()]);
    set({ agents, groups });
  },

  createAgent: async (a) => {
    await api.createAgent(a);
    const agents = await api.fetchAgents();
    set({ agents });
  },

  updateAgent: async (id, data) => {
    await api.updateAgent(id, data);
    const agents = await api.fetchAgents();
    set({ agents });
  },

  deleteAgent: async (id) => {
    await api.deleteAgent(id);
    const agents = await api.fetchAgents();
    set({ agents });
  },

  createGroup: async (g) => {
    await api.createGroup(g);
    const groups = await api.fetchGroups();
    set({ groups });
  },

  updateGroup: async (id, data) => {
    await api.updateGroup(id, data);
    const groups = await api.fetchGroups();
    set({ groups });
  },

  deleteGroup: async (id) => {
    await api.deleteGroup(id);
    const groups = await api.fetchGroups();
    set({ groups });
  },

  selectGroup: (id) => set({ selectedGroupId: id }),
}));
