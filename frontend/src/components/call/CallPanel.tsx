import { useState, useRef, useEffect, useCallback } from 'react';
import { Phone, PhoneOff, Mic, MicOff, Send, Pause, Volume2, ArrowDownUp, Bot, Radio, Wifi, Timer, Headphones } from 'lucide-react';
import { useCallStore } from '../../stores/callStore';
import { useAgentStore } from '../../stores/agentStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAudioRecorder } from '../../hooks/useAudioRecorder';
import { useAudioPlayer } from '../../hooks/useAudioPlayer';
import { WaitingOverlay } from './WaitingOverlay';
import { TranscriptPanel } from './TranscriptPanel';

export function CallPanel() {
  const call = useCallStore();
  const { groups } = useAgentStore();
  const { llmMode } = useSettingsStore();
  const ws = useWebSocket();
  const player = useAudioPlayer();
  const [textInput, setTextInput] = useState('');
  const [callDuration, setCallDuration] = useState(0);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<number | null>(null);

  const recorder = useAudioRecorder(
    (chunk) => ws.sendAudioChunk(chunk),
    () => ws.sendAudioEnd(),
  );

  // Timer logic
  useEffect(() => {
    if (call.status === 'active') {
      timerRef.current = window.setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setCallDuration(0);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [call.status]);

  useEffect(() => {
    const stopPlayback = () => player.stop();
    window.addEventListener('voice:tts_stop', stopPlayback);
    return () => window.removeEventListener('voice:tts_stop', stopPlayback);
  }, [player]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Auto-scroll transcript
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTo({
        top: transcriptRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [call.transcript, call.llmPartialText]);

  const handleStartCall = useCallback(async () => {
    const sessionId = `session_${Date.now()}`;
    call.setStatus('connecting');
    call.clearTranscript();
    call.setLLMPartial('');

    try {
      const client = await ws.connect(sessionId);

      // Register binary handler for audio chunks
      ws.onBinary((data: ArrayBuffer) => {
        player.playChunk(data);
      });

      ws.startCall(call.scenario, call.inputMode, call.agentGroupId);
    } catch (err) {
      call.setStatus('idle');
      console.error('Failed to connect:', err);
    }
  }, [call, ws, player]);

  const handleEndCall = useCallback(() => {
    ws.endCall();
    ws.disconnect();
    player.stop();
    recorder.stop();
    call.setStatus('idle');
  }, [ws, player, recorder, call]);

  const handleSendText = useCallback(() => {
    if (!textInput.trim()) return;
    ws.sendText(textInput.trim());
    setTextInput('');
  }, [textInput, ws]);

  const handleToggleRecording = useCallback(() => {
    if (call.isRecording) {
      recorder.stop();
      call.setRecording(false);
    } else {
      recorder.start();
      call.setRecording(true);
    }
  }, [call, recorder]);

  const isIdle = call.status === 'idle';
  const isActive = call.status === 'active';
  const isConnecting = call.status === 'connecting';
  const useVoiceInput = llmMode === 'omni' || call.inputMode === 'voice';

  return (
    <div className="h-full flex flex-col bg-slate-950/40 relative overflow-hidden">
      
      {/* Dynamic Header */}
      <div className="px-10 py-8 border-b border-white/[0.06] bg-white/[0.02] backdrop-blur-xl z-20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="relative group">
               <div className={`absolute -inset-2 bg-gradient-to-tr from-primary-500 to-accent-400 rounded-3xl blur opacity-20 transition duration-1000 ${isActive ? 'opacity-40 animate-pulse' : ''}`} />
               <div className={`relative w-16 h-16 rounded-[1.5rem] bg-slate-900 border border-white/10 flex items-center justify-center shadow-2xl transition-all duration-500 ${isActive ? 'scale-105 border-primary-500/50' : ''}`}>
                  <Headphones size={28} className={isActive ? 'text-primary-400 animate-bounce' : 'text-slate-500'} />
               </div>
            </div>
            
            <div className="flex flex-col">
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-black tracking-tight text-white uppercase">
                  {call.scenario === 'inbound' ? '呼入通话 (Inbound)' : '主动外呼 (Outbound)'}
                </h2>
                {isActive && (
                  <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-black uppercase tracking-widest border border-emerald-500/30">
                     Live
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-1.5">
                 <p className="text-slate-400 font-medium text-sm">
                   {isActive ? `Session with ${call.currentAgentName}` : isConnecting ? 'Authenticating...' : 'Engine Ready'}
                 </p>
                 {isActive && (
                   <>
                    <div className="w-1 h-1 rounded-full bg-slate-700" />
                    <div className="flex items-center gap-1.5 text-slate-400 font-mono text-sm">
                       <Timer size={14} className="text-primary-400" />
                       {formatTime(callDuration)}
                    </div>
                   </>
                 )}
              </div>
            </div>
          </div>

          {/* Context Controls */}
          <div className="flex items-center gap-4 bg-slate-900/50 p-2 rounded-3xl border border-white/5 shadow-inner">
            {isIdle && (
              <>
                <button
                  onClick={() => call.setScenario(call.scenario === 'inbound' ? 'outbound' : 'inbound')}
                  className="flex items-center gap-2 px-5 py-2.5 text-xs font-bold rounded-2xl border border-white/5 bg-white/5 hover:bg-white/10 transition-all text-slate-300 hover:text-white"
                >
                  <ArrowDownUp size={14} className="text-primary-400" />
                  SCENARIO
                </button>

                <button
                  onClick={() => call.setInputMode(call.inputMode === 'text' ? 'voice' : 'text')}
                  className="flex items-center gap-2 px-5 py-2.5 text-xs font-bold rounded-2xl border border-white/5 bg-white/5 hover:bg-white/10 transition-all text-slate-300 hover:text-white"
                >
                  <Radio size={14} className="text-primary-400" />
                  {call.inputMode === 'text' ? 'TEXTUAL' : 'VOICE'}
                </button>

                {groups.length > 0 && (
                  <div className="relative group">
                    <select
                      value={call.agentGroupId || groups[0]?.id || ''}
                      onChange={(e) => call.setAgentGroup(e.target.value)}
                      className="appearance-none px-6 py-2.5 pr-10 text-xs font-black rounded-2xl border border-white/5 bg-slate-800 text-white focus:outline-none focus:border-primary-500/50 transition-all uppercase tracking-widest cursor-pointer"
                    >
                      <option value="">Agent Cluster</option>
                      {groups.map(g => (
                        <option key={g.id} value={g.id}>{g.name}</option>
                      ))}
                    </select>
                    <ArrowDownUp size={12} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
                  </div>
                )}
              </>
            )}
            {!isIdle && (
               <div className="flex items-center gap-4 px-6 py-2">
                  <div className="flex flex-col items-center">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Link</span>
                    <Wifi size={14} className="text-emerald-500" />
                  </div>
                  <div className="w-px h-6 bg-white/10" />
                  <div className="flex flex-col items-center">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Enc</span>
                    <Bot size={14} className="text-primary-400" />
                  </div>
               </div>
            )}
          </div>
        </div>
      </div>

      {/* Immersive Audio/Transcript Area */}
      <div className="flex-1 flex flex-col overflow-hidden relative group">
        
        {/* Decorative elements */}
        <div className="absolute top-0 inset-x-0 h-32 bg-gradient-to-b from-slate-950/40 to-transparent z-10 pointer-events-none" />
        <div className="absolute bottom-0 inset-x-0 h-32 bg-gradient-to-t from-slate-950/40 to-transparent z-10 pointer-events-none" />

        <div 
          ref={transcriptRef} 
          className="flex-1 overflow-y-auto px-10 py-12 space-y-8 no-scrollbar scroll-smooth"
        >
          <TranscriptPanel entries={call.transcript} partialText={call.llmPartialText} agentName={call.currentAgentName} />
        </div>

        {/* Global Loading / Waiting Overlay */}
        {call.isWaiting && <WaitingOverlay message={call.waitingMessage} />}
      </div>

      {/* Control Deck */}
      <div className="px-10 pb-10 pt-6 border-t border-white/[0.06] bg-white/[0.01] backdrop-blur-2xl z-20">
        {isIdle ? (
          <div className="flex justify-center">
            <button
              onClick={handleStartCall}
              disabled={isConnecting}
              className="group relative flex items-center gap-4 px-12 py-5 bg-white text-slate-950 rounded-[2rem] font-black text-xl shadow-[0_20px_50px_rgba(255,255,255,0.1)] hover:shadow-[0_20px_70px_rgba(255,255,255,0.2)] hover:-translate-y-1 transition-all duration-500 disabled:opacity-50"
            >
              <div className="w-10 h-10 rounded-full bg-slate-950 flex items-center justify-center text-white group-hover:rotate-12 transition-transform">
                <Phone size={20} fill="currentColor" />
              </div>
              {isConnecting ? 'ESTABLISHING...' : 'INITIALIZE CONNECTION'}
            </button>
          </div>
        ) : (
          <div className="max-w-5xl mx-auto flex items-center gap-6">
            
            {/* Real-time Interaction Input */}
            {!useVoiceInput && (
              <div className="flex-1 flex gap-3 p-1.5 bg-slate-900/60 rounded-[2.5rem] border border-white/5 focus-within:border-primary-500/50 focus-within:bg-slate-900/80 transition-all duration-500 group shadow-2xl">
                <input
                  type="text"
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendText()}
                  placeholder="Draft your message..."
                  className="flex-1 bg-transparent px-8 py-4 text-slate-200 placeholder-slate-600 font-semibold focus:outline-none"
                />
                <button
                  onClick={handleSendText}
                  disabled={!textInput.trim()}
                  className="w-14 h-14 bg-white text-slate-950 rounded-full flex items-center justify-center hover:scale-105 active:scale-95 disabled:opacity-20 disabled:grayscale transition-all shadow-xl"
                >
                  <Send size={24} />
                </button>
              </div>
            )}

            {/* Futuristic Mic Toggle */}
            {useVoiceInput && (
              <div className="flex-1 flex justify-center">
                 <button
                  onClick={handleToggleRecording}
                  className={`relative group p-8 rounded-full transition-all duration-700 ${
                    call.isRecording
                      ? 'bg-red-500 text-white shadow-[0_0_60px_rgba(239,68,68,0.4)]'
                      : 'bg-slate-900 border border-white/10 text-slate-400 hover:text-white hover:border-white/30'
                  }`}
                >
                  {call.isRecording && (
                    <div className="absolute inset-0 rounded-full animate-ping bg-red-500 opacity-20" />
                  )}
                  <div className="relative z-10">
                    {call.isRecording ? <MicOff size={36} /> : <Mic size={36} />}
                  </div>
                </button>
              </div>
            )}

            {/* Quick Actions Stack */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => ws.interrupt()}
                className="w-14 h-14 flex items-center justify-center rounded-[1.25rem] bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 hover:bg-yellow-500/20 transition-all"
                title="Force Interrupt"
              >
                <Pause size={24} />
              </button>

              <button
                onClick={handleEndCall}
                className="w-16 h-16 flex items-center justify-center rounded-[1.5rem] bg-red-500 text-white shadow-[0_10px_30px_rgba(239,68,68,0.2)] hover:bg-red-600 hover:shadow-[0_15px_40px_rgba(239,68,68,0.3)] transition-all"
                title="Disconnect"
              >
                <PhoneOff size={28} fill="currentColor" />
              </button>
            </div>

            {/* Dynamic Telemetry Status */}
            <div className="hidden lg:flex items-center gap-4 min-w-[240px]">
              <div className="flex-1 flex flex-col gap-2">
                 {/* TTS Waveform */}
                 <div className="h-10 flex items-end justify-center gap-1">
                    {Array.from({length: 14}).map((_, i) => (
                       <span
                         key={i}
                         className="wave-bar"
                         style={{
                            height: '100%',
                            animationDelay: `${i * 0.08}s`,
                            animationDuration: `${0.7 + (i % 4) * 0.15}s`,
                            opacity: call.isTTSPlaying ? 1 : 0.18,
                            transform: call.isTTSPlaying ? undefined : 'scaleY(0.18)',
                            animationPlayState: call.isTTSPlaying ? 'running' : 'paused',
                         }}
                       />
                    ))}
                 </div>
                 <div className="flex justify-between">
                    <span className="text-[10px] font-black tracking-widest text-slate-500 uppercase">Downlink</span>
                    <span className={`text-[10px] font-black tracking-widest uppercase ${call.isTTSPlaying ? 'text-primary-400' : 'text-slate-600'}`}>
                      {call.isTTSPlaying ? 'Receiving Audio' : 'Standby'}
                    </span>
                 </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
