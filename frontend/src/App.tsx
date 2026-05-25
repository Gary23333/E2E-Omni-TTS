import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useSettingsStore } from './stores/settingsStore';
import { useAgentStore } from './stores/agentStore';
import { Sidebar } from './components/layout/Sidebar';
import { CallPanel } from './components/call/CallPanel';
import { AgentConfig } from './components/config/AgentConfig';
import { RAGManager } from './components/config/RAGManager';
import { SkillManager } from './components/config/SkillManager';
import { SettingsPanel } from './components/config/SettingsPanel';

function AppLayout() {
  return (
    <div className="h-screen flex overflow-hidden relative bg-[#020617]">
      {/* Immersive background layer */}
      <div className="bg-mesh" />
      
      {/* Sidebar navigation */}
      <Sidebar />
      
      {/* Main interaction stage */}
      <main className="flex-1 overflow-hidden relative z-10 py-6 pr-6">
        <div className="h-full glass-panel rounded-[3rem] overflow-hidden shadow-2xl transition-all duration-700">
          <Routes>
            <Route path="/call" element={<CallPanel />} />
            <Route path="/agents" element={<AgentConfig />} />
            <Route path="/rag" element={<RAGManager />} />
            <Route path="/skills" element={<SkillManager />} />
            <Route path="/settings" element={<SettingsPanel />} />
            <Route path="/" element={<Navigate to="/call" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const settingsLoaded = useSettingsStore(s => s.loaded);
  const loadSettings = useSettingsStore(s => s.load);
  const loadAgents = useAgentStore(s => s.load);

  useEffect(() => {
    loadSettings();
    loadAgents();
  }, [loadSettings, loadAgents]);

  if (!settingsLoaded) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-[#020617]">
        <div className="relative">
           <div className="absolute -inset-10 bg-primary-500/20 rounded-full blur-3xl animate-pulse" />
           <div className="relative flex flex-col items-center">
              <div className="w-16 h-16 border-4 border-primary-500/20 border-t-primary-500 rounded-full animate-spin mb-6" />
              <div className="text-white/80 text-xl font-black tracking-widest uppercase italic">Initializing System</div>
           </div>
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
