import { create } from 'zustand';
import type { RAGDocument } from '../types';
import * as api from '../api/client';

interface RAGState {
  documents: RAGDocument[];
  load: () => Promise<void>;
  upload: (file: File) => Promise<void>;
  remove: (id: string) => Promise<void>;
  toggle: (id: string) => Promise<void>;
}

export const useRAGStore = create<RAGState>((set) => ({
  documents: [],

  load: async () => {
    const documents = await api.fetchDocuments();
    set({ documents });
  },

  upload: async (file) => {
    await api.uploadDocument(file);
    const documents = await api.fetchDocuments();
    set({ documents });
  },

  remove: async (id) => {
    await api.deleteDocument(id);
    const documents = await api.fetchDocuments();
    set({ documents });
  },

  toggle: async (id) => {
    await api.toggleDocument(id);
    const documents = await api.fetchDocuments();
    set({ documents });
  },
}));
