import { useEffect, useState } from 'react';
import { useSettingsStore } from './stores/settingsStore';
import { useAgentStore } from './stores/agentStore';
import { Sidebar } from './components/layout/Sidebar';
import { CallPanel } from './components/call/CallPanel';
import { AgentConfig } from './components/config/AgentConfig';
import { RAGManager } from './components/config/RAGManager';
import { SkillManager } from './components/config/SkillManager';
import { SettingsPanel } from './components/config/SettingsPanel';

type Page = 'call' | 'agents' | 'rag' | 'skills' | 'settings';

export default function App() {
  const [page, setPage] = useState<Page>('call');
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
    <div className="h-screen flex overflow-hidden relative bg-[#020617]">
      {/* Immersive background layer */}
      <div className="bg-mesh" />
      
      {/* Sidebar navigation */}
      <Sidebar currentPage={page} onNavigate={setPage} />
      
      {/* Main interaction stage */}
      <main className="flex-1 overflow-hidden relative z-10 py-6 pr-6">
        <div className="h-full glass-panel rounded-[3rem] overflow-hidden shadow-2xl transition-all duration-700">
          <PageContent page={page} />
        </div>
      </main>
    </div>
  );
}

function PageContent({ page }: { page: Page }) {
  switch (page) {
    case 'call': return <CallPanel />;
    case 'agents': return <AgentConfig />;
    case 'rag': return <RAGManager />;
    case 'skills': return <SkillManager />;
    case 'settings': return <SettingsPanel />;
    default: return <CallPanel />;
  }
}
