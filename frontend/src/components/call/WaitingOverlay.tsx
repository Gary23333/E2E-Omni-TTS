import { Loader2 } from 'lucide-react';

interface Props {
  message: string;
}

export function WaitingOverlay({ message }: Props) {
  return (
    <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-md flex items-center justify-center z-30 animate-in fade-in duration-300">
      {/* Halo */}
      <div className="absolute w-[420px] h-[420px] rounded-full bg-primary-500/15 blur-3xl animate-pulse-glow pointer-events-none" />
      <div className="absolute w-[260px] h-[260px] rounded-full bg-accent-500/10 blur-3xl pointer-events-none" />

      <div className="relative glass-card glass-card-glow rounded-[2rem] px-10 py-8 flex flex-col items-center gap-5 min-w-[280px] animate-in fade-in slide-in-from-bottom-4 duration-500">
        {/* Concentric rings */}
        <div className="relative w-20 h-20 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border-2 border-primary-500/20" />
          <div className="absolute inset-2 rounded-full border-2 border-t-primary-500 border-r-accent-500 border-b-transparent border-l-transparent animate-spin" />
          <div className="absolute inset-5 rounded-full bg-gradient-to-tr from-primary-500/30 to-accent-500/30 backdrop-blur-md flex items-center justify-center">
            <Loader2 size={20} className="text-white animate-spin" />
          </div>
        </div>

        {/* Bouncing dots */}
        <div className="flex gap-1.5 mt-1">
          <div className="w-2 h-2 rounded-full bg-gradient-to-r from-primary-400 to-accent-400 dot-bounce-1" />
          <div className="w-2 h-2 rounded-full bg-gradient-to-r from-primary-400 to-accent-400 dot-bounce-2" />
          <div className="w-2 h-2 rounded-full bg-gradient-to-r from-primary-400 to-accent-400 dot-bounce-3" />
        </div>

        <div className="text-center">
          <p className="text-white font-bold tracking-wide">{message || '请稍候...'}</p>
          <p className="text-[10px] text-slate-500 font-black tracking-[0.2em] uppercase mt-1.5">
            系统处理中 · 请稍候
          </p>
        </div>
      </div>
    </div>
  );
}
