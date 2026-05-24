import { create } from 'zustand';
import type { Skill } from '../types';
import * as api from '../api/client';

interface SkillState {
  skills: Skill[];
  load: () => Promise<void>;
  create: (s: Skill) => Promise<void>;
  update: (id: string, data: Partial<Skill>) => Promise<void>;
  remove: (id: string) => Promise<void>;
  toggle: (id: string) => Promise<void>;
}

export const useSkillStore = create<SkillState>((set) => ({
  skills: [],

  load: async () => {
    const skills = await api.fetchSkills();
    set({ skills });
  },

  create: async (s) => {
    await api.createSkill(s);
    const skills = await api.fetchSkills();
    set({ skills });
  },

  update: async (id, data) => {
    await api.updateSkill(id, data);
    const skills = await api.fetchSkills();
    set({ skills });
  },

  remove: async (id) => {
    await api.deleteSkill(id);
    const skills = await api.fetchSkills();
    set({ skills });
  },

  toggle: async (id) => {
    await api.toggleSkill(id);
    const skills = await api.fetchSkills();
    set({ skills });
  },
}));
