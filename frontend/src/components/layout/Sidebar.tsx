import { Phone, Users, FileText, Wrench, Settings, Bot, Activity } from 'lucide-react';
import { useSettingsStore } from '../../stores/settingsStore';

type Page = 'call' | 'agents' | 'rag' | 'skills' | 'settings';

const navItems: { id: Page; label: string; icon: typeof Phone }[] = [
  { id: 'call', label: '通话交互', icon: Phone },
  { id: 'agents', label: '客服编排', icon: Users },
  { id: 'rag', label: '知识库管理', icon: FileText },
  { id: 'skills', label: '插件中心', icon: Wrench },
  { id: 'settings', label: '系统设置', icon: Settings },
];

interface Props {
  currentPage: Page;
  onNavigate: (page: Page) => void;
}

export function Sidebar({ currentPage, onNavigate }: Props) {
  const { systemTitle, systemSubtitle } = useSettingsStore();

  return (
    <aside className="w-72 flex flex-col shrink-0 py-6 pl-6 h-screen relative z-10">
      {/* Brand Logo Section */}
      <div className="mb-10 px-4">
        <div className="flex items-center gap-4 group cursor-pointer">
          <div className="relative">
            <div className="absolute -inset-1 bg-gradient-to-tr from-primary-500 to-accent-400 rounded-2xl blur opacity-30 group-hover:opacity-60 transition duration-500"></div>
            <div className="relative w-12 h-12 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center shadow-2xl transition-transform duration-500 group-hover:scale-105 group-hover:rotate-3">
              <Bot size={24} className="text-primary-400 group-hover:text-primary-300 transition-colors" />
            </div>
          </div>
          <div className="flex flex-col">
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/70 tracking-tight leading-tight">
              {systemTitle}
            </h1>
            <p className="text-xs font-medium text-primary-400/80 tracking-widest uppercase mt-0.5">
              {systemSubtitle}
            </p>
          </div>
        </div>
      </div>

      {/* Modern Navigation Menu */}
      <nav className="flex-1 space-y-1.5 px-2 overflow-y-auto no-scrollbar">
        {navItems.map(item => {
          const Icon = item.icon;
          const active = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3.5 px-4 py-3.5 rounded-2xl transition-all duration-300 group relative overflow-hidden ${
                active
                  ? 'text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {/* Active Background */}
              {active && (
                <>
                  <div className="absolute inset-0 bg-white/[0.08] backdrop-blur-md" />
                  <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-primary-500 to-accent-500" />
                  <div className="absolute inset-0 border border-white/10 rounded-2xl" />
                </>
              )}

              {/* Hover Effect */}
              {!active && (
                <div className="absolute inset-0 bg-white/0 group-hover:bg-white/[0.03] transition-colors duration-300" />
              )}

              <div className={`relative z-10 transition-all duration-300 ${active ? 'scale-110 text-primary-400' : 'group-hover:scale-110 group-hover:text-slate-200'}`}>
                <Icon size={20} strokeWidth={active ? 2.5 : 2} />
              </div>
              
              <span className={`relative z-10 font-semibold tracking-wide transition-colors duration-300 ${active ? 'text-white' : 'group-hover:text-slate-200'}`}>
                {item.label}
              </span>

              {active && (
                <div className="relative z-10 ml-auto">
                   <div className="w-1.5 h-1.5 rounded-full bg-primary-400 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                </div>
              )}
            </button>
          );
        })}
      </nav>

      {/* System Status Dashboard Footer */}
      <div className="mt-auto pr-6 py-6">
        <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2rem] p-5 shadow-2xl">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-tighter">System Online</span>
            </div>
            <span className="text-[10px] text-white/30 font-mono">v0.5.0</span>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-white/5 border border-white/10">
              <Activity size={16} className="text-primary-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-end mb-1">
                <p className="text-white/60 text-[10px] font-medium truncate uppercase tracking-widest">Network Latency</p>
                <span className="text-white/80 text-[10px] font-mono">24ms</span>
              </div>
              <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-primary-500 to-accent-500 w-1/4 rounded-full" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
