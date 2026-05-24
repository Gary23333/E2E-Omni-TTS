import type { TranscriptEntry } from '../../types';
import { User, Bot, Settings2, Sparkles, MessageSquare } from 'lucide-react';

interface Props {
  entries: TranscriptEntry[];
  partialText: string;
  agentName: string;
}

export function TranscriptPanel({ entries, partialText, agentName }: Props) {
  if (entries.length === 0 && !partialText) {
    return (
      <div className="h-full flex items-center justify-center p-12">
        <div className="relative group max-w-md text-center">
          {/* Animated background glow */}
          <div className="absolute -inset-10 bg-primary-500/10 rounded-full blur-3xl group-hover:bg-primary-500/20 transition-all duration-1000" />
          
          <div className="relative">
             <div className="w-24 h-24 mx-auto mb-8 rounded-[2rem] bg-slate-900 border border-white/10 flex items-center justify-center shadow-2xl group-hover:scale-110 group-hover:rotate-3 transition-all duration-500">
                <MessageSquare size={40} className="text-primary-400" />
             </div>
             <h3 className="text-3xl font-black text-white mb-4 tracking-tight uppercase italic">Secure Link Ready</h3>
             <p className="text-slate-500 font-medium leading-relaxed mb-6">
               系统已就绪，所有音频流均采用端到端 48kHz 高保真传输。点击下方初始化开始智能客服会话。
             </p>
             <div className="flex justify-center gap-3">
                <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] font-black text-slate-400 uppercase tracking-widest">Low Latency</span>
                <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] font-black text-slate-400 uppercase tracking-widest">Encrypted</span>
             </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {entries.map((entry, i) => (
        <div 
          key={i} 
          className={`flex items-end gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500 ${entry.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
        >
          {/* Avatar Area */}
          <div className="shrink-0 mb-1">
             {entry.role === 'agent' || entry.role === 'system' ? (
                <div className="w-10 h-10 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center shadow-lg">
                   <Bot size={20} className="text-primary-400" />
                </div>
             ) : entry.role === 'user' ? (
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-primary-600 to-accent-500 flex items-center justify-center shadow-lg">
                   <User size={20} className="text-white" />
                </div>
             ) : (
                <div className="w-10 h-10 rounded-2xl bg-slate-800 border border-white/5 flex items-center justify-center">
                   <Settings2 size={18} className="text-yellow-400" />
                </div>
             )}
          </div>

          <div className={`flex flex-col max-w-[85%] ${entry.role === 'user' ? 'items-end' : 'items-start'}`}>
             {/* Name Label */}
             <div className="flex items-center gap-2 mb-1.5 px-1">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                   {entry.role === 'user' ? 'Authorized User' : entry.agentName || 'System Processor'}
                </span>
                {entry.timestamp && <span className="text-[9px] font-mono text-slate-600 tracking-tighter">{entry.timestamp}</span>}
             </div>

             {/* Message Bubble */}
             <div
               className={`relative overflow-hidden px-6 py-4 rounded-[2rem] shadow-xl border backdrop-blur-md transition-all ${
                 entry.role === 'user'
                   ? 'bg-white text-slate-950 border-white rounded-tr-sm font-semibold'
                   : entry.role === 'agent'
                   ? 'bg-slate-900/80 text-slate-200 border-white/[0.08] rounded-tl-sm'
                   : entry.role === 'tool'
                   ? 'bg-slate-950/40 text-yellow-200/80 border-yellow-500/20 rounded-xl text-sm italic'
                   : 'bg-white/5 text-slate-400 border-white/5 rounded-xl text-xs text-center w-full max-w-full italic'
               }`}
             >
               {entry.role === 'tool' && entry.toolName && (
                 <div className="flex items-center gap-2 mb-2 font-black uppercase tracking-tighter text-yellow-500 text-[10px]">
                   <Sparkles size={12} />
                   Executing Skill: {entry.toolName}
                 </div>
               )}
               <div className="whitespace-pre-wrap leading-relaxed tracking-wide">
                 {entry.text}
               </div>
               
               {/* Subtle grain overlay for agent */}
               {entry.role === 'agent' && (
                 <div className="absolute inset-0 pointer-events-none opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
               )}
             </div>
          </div>
        </div>
      ))}

      {/* LLM streaming partial text */}
      {partialText && (
        <div className="flex items-end gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="shrink-0 mb-1">
              <div className="w-10 h-10 rounded-2xl bg-slate-900 border border-primary-500/30 flex items-center justify-center shadow-[0_0_15px_rgba(34,197,94,0.2)]">
                  <Bot size={20} className="text-primary-400 animate-pulse" />
              </div>
          </div>
          
          <div className="flex flex-col max-w-[85%] items-start">
              <div className="flex items-center gap-2 mb-1.5 px-1">
                  <span className="text-[10px] font-black uppercase tracking-widest text-primary-500 animate-pulse">
                     {agentName} is thinking...
                  </span>
              </div>

              <div className="relative overflow-hidden px-6 py-4 rounded-[2rem] bg-slate-900/80 text-slate-200 border border-primary-500/20 rounded-tl-sm shadow-2xl">
                <div className="whitespace-pre-wrap leading-relaxed tracking-wide">
                  {partialText}
                  <span className="inline-flex ml-2 w-1.5 h-5 bg-primary-500 rounded-full animate-pulse align-middle" />
                </div>
                <div className="absolute inset-0 pointer-events-none opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
              </div>
          </div>
        </div>
      )}
    </div>
  );
}
