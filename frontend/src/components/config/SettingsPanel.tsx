import { useState, useEffect, useRef } from 'react';
import { Settings, Volume2, Radio, Mic, Save, Check, ShieldCheck, Monitor, Sparkles, Activity, AlertCircle, Loader2, Database, Play, Square, Upload, Trash2, Headphones } from 'lucide-react';
import { useSettingsStore } from '../../stores/settingsStore';
import { testLLM, testTTS, testASR, testEmbed, fetchNoiseSamples, uploadNoiseSample, deleteNoiseSample } from '../../api/client';
import type { GlobalConfig, NoiseType, LLMMode } from '../../types';

export function SettingsPanel() {
  const store = useSettingsStore();
  const [form, setForm] = useState<GlobalConfig>({
    systemTitle: '', systemSubtitle: '',
    llmEndpoint: '', llmApiKey: '', llmModel: '',
    ttsEndpoint: '', ttsModel: '', asrEndpoint: '',
    embedEndpoint: '', embedApiKey: '', embedModel: '',
    ttsVoiceDescriptor: '(A warm young woman)', ttsResponseFormat: 'pcm',
    llmMode: 'text_asr', noiseType: 'none', noiseVolume: 0.1,
    customNoiseFile: null,
    waitingMusicEnabled: true,
  });
  const [saved, setSaved] = useState(false);
  const [testStatus, setTestStatus] = useState<Record<string, { loading: boolean; status: 'ok' | 'error' | null; message?: string }>>({
    llm: { loading: false, status: null },
    tts: { loading: false, status: null },
    asr: { loading: false, status: null },
    embed: { loading: false, status: null },
  });

  const [noiseSamples, setNoiseSamples] = useState<string[]>([]);
  const [isPlaying, setIsPlaying] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setForm({
      systemTitle: store.systemTitle,
      systemSubtitle: store.systemSubtitle,
      llmEndpoint: store.llmEndpoint,
      llmApiKey: store.llmApiKey,
      llmModel: store.llmModel,
      ttsEndpoint: store.ttsEndpoint,
      ttsModel: store.ttsModel,
      ttsVoiceDescriptor: store.ttsVoiceDescriptor,
      ttsResponseFormat: store.ttsResponseFormat,
      asrEndpoint: store.asrEndpoint,
      embedEndpoint: store.embedEndpoint,
      embedApiKey: store.embedApiKey,
      embedModel: store.embedModel,
      llmMode: store.llmMode,
      noiseType: store.noiseType,
      noiseVolume: store.noiseVolume,
      customNoiseFile: store.customNoiseFile,
      waitingMusicEnabled: store.waitingMusicEnabled,
    });
    refreshNoiseSamples();
  }, [store]);

  const refreshNoiseSamples = async () => {
    try {
      const samples = await fetchNoiseSamples();
      setNoiseSamples(samples);
    } catch (e) {
      console.error('Failed to fetch noise samples', e);
    }
  };

  const handleSave = async () => {
    await store.update(form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleTest = async (type: 'llm' | 'tts' | 'asr' | 'embed') => {
    setTestStatus(prev => ({ ...prev, [type]: { loading: true, status: null } }));
    try {
      let res;
      if (type === 'llm') res = await testLLM();
      else if (type === 'tts') res = await testTTS();
      else if (type === 'asr') res = await testASR();
      else res = await testEmbed();

      if (res.status === 'ok') {
        setTestStatus(prev => ({ ...prev, [type]: { loading: false, status: 'ok' } }));
      } else {
        setTestStatus(prev => ({ ...prev, [type]: { loading: false, status: 'error', message: res.message } }));
      }
    } catch (e: any) {
      setTestStatus(prev => ({ ...prev, [type]: { loading: false, status: 'error', message: e.message } }));
    }
  };

  const togglePreview = (filename: string) => {
    if (isPlaying === filename) {
      audioRef.current?.pause();
      setIsPlaying(null);
    } else {
      if (audioRef.current) {
        audioRef.current.src = `http://localhost:8900/api/config/noise/file/${filename}`;
        audioRef.current.loop = true;
        audioRef.current.play();
        setIsPlaying(filename);
      }
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      try {
        const res = await uploadNoiseSample(file);
        await refreshNoiseSamples();
        set('customNoiseFile', res.filename);
        set('noiseType', 'custom');
      } catch (e) {
        alert('上传失败');
      }
    }
  };

  const handleDeleteNoise = async (filename: string) => {
    if (confirm(`确定要删除 ${filename} 吗？`)) {
      try {
        await deleteNoiseSample(filename);
        await refreshNoiseSamples();
        if (form.customNoiseFile === filename) {
          set('customNoiseFile', null);
          set('noiseType', 'none');
        }
      } catch (e) {
        alert('删除失败');
      }
    }
  };

  const set = <K extends keyof GlobalConfig>(key: K, val: GlobalConfig[K]) => setForm(f => ({ ...f, [key]: val }));

  return (
    <div className="h-full flex flex-col text-slate-200">
      <audio ref={audioRef} className="hidden" />
      
      {/* Glossy Header */}
      <div className="px-10 py-8 border-b border-white/[0.06] flex items-center justify-between bg-white/[0.02] backdrop-blur-md">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-primary-500/20 to-accent-500/20 border border-white/10 flex items-center justify-center text-primary-400">
             <Settings size={24} />
          </div>
          <div>
            <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/70">系统设置</h2>
            <p className="text-sm text-slate-500 mt-1 font-medium">全局模型端点、品牌信息与音频引擎配置</p>
          </div>
        </div>
        
        <button 
          onClick={handleSave} 
          className="group relative flex items-center gap-2 px-8 py-3.5 bg-white text-slate-900 rounded-2xl font-bold text-sm shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_30px_rgba(255,255,255,0.2)] transition-all duration-300 hover:-translate-y-0.5"
        >
          {saved ? <Check size={18} className="text-emerald-600" /> : <Save size={18} />}
          {saved ? '配置已保存' : '保存全局设置'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-10 no-scrollbar bg-slate-950/20">
        <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Brand Identity */}
          <Section icon={<Monitor size={20} />} title="品牌标识" className="md:col-span-2">
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Field label="系统主标题" value={form.systemTitle} onChange={v => set('systemTitle', v)} placeholder="例如：智能语音客服" />
                <Field label="系统副标题" value={form.systemSubtitle} onChange={v => set('systemSubtitle', v)} placeholder="例如：Voice CS Demo" />
             </div>
          </Section>

          {/* Service Health Checks */}
          <Section icon={<Activity size={20} />} title="服务连接健康测试" className="md:col-span-2">
             <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <TestCard label="LLM 服务" status={testStatus.llm} onTest={() => handleTest('llm')} />
                <TestCard label="TTS 服务" status={testStatus.tts} onTest={() => handleTest('tts')} />
                <TestCard label="ASR 服务" status={testStatus.asr} onTest={() => handleTest('asr')} disabled={form.llmMode === 'omni'} />
                <TestCard label="Embedding" status={testStatus.embed} onTest={() => handleTest('embed')} />
             </div>
             {Object.values(testStatus).some(s => s.status === 'error') && (
               <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3">
                  <AlertCircle size={18} className="text-red-400 shrink-0 mt-0.5" />
                  <div className="text-xs text-red-300 leading-relaxed">
                    测试失败。请检查 API 端点是否正确，且对应的后端服务已启动并允许跨域访问。
                  </div>
               </div>
             )}
          </Section>

          {/* LLM Mode */}
          <Section icon={<Sparkles size={20} />} title="智能引擎模式" className="md:col-span-2">
            <div className="flex gap-6">
              <ModeCard
                title="Omni 模式"
                desc="原生语音理解。低延迟，情感保留，支持流式音频直入大模型。"
                active={form.llmMode === 'omni'}
                onClick={() => set('llmMode', 'omni' as LLMMode)}
                badge="推荐"
              />
              <ModeCard
                title="ASR + Text 模式"
                desc="经典解耦方案。支持任意文字模型，更易于对文字内容进行精确控制。"
                active={form.llmMode === 'text_asr'}
                onClick={() => set('llmMode', 'text_asr' as LLMMode)}
              />
            </div>
          </Section>

          {/* LLM Config */}
          <Section icon={<ShieldCheck size={20} />} title="语言模型 (LLM)">
            <Field label="API 基准端点" value={form.llmEndpoint} onChange={v => set('llmEndpoint', v)} placeholder="http://api.openai.com/v1" />
            <Field label="API 凭据 (Key)" value={form.llmApiKey} onChange={v => set('llmApiKey', v)} placeholder="sk-..." type="password" />
            <Field label="部署模型 ID" value={form.llmModel} onChange={v => set('llmModel', v)} placeholder="gpt-4o" />
          </Section>

          {/* Embedding Config */}
          <Section icon={<Database size={20} />} title="向量模型 (Embedding)">
            <Field label="API 基准端点" value={form.embedEndpoint} onChange={v => set('embedEndpoint', v)} placeholder="http://api.openai.com/v1" />
            <Field label="API 凭据 (Key)" value={form.embedApiKey} onChange={v => set('embedApiKey', v)} placeholder="sk-..." type="password" />
            <Field label="模型 ID" value={form.embedModel} onChange={v => set('embedModel', v)} placeholder="text-embedding-3-small" />
            <div className="p-3 rounded-xl bg-primary-500/5 border border-primary-500/10">
               <p className="text-[10px] text-slate-500 leading-tight">若留空端点，系统将尝试加载本地 Sentence-Transformers 模型。</p>
            </div>
          </Section>

          {/* TTS Config */}
          <Section icon={<Volume2 size={20} />} title="语音合成 (TTS)">
            <Field label="VoxCPM2 服务端点" value={form.ttsEndpoint} onChange={v => set('ttsEndpoint', v)} placeholder="http://localhost:8001/v1" />
            <Field label="默认声音设计" value={form.ttsVoiceDescriptor} onChange={v => set('ttsVoiceDescriptor', v)} placeholder="(A warm young woman)" multiline />
            <div className="grid grid-cols-2 gap-4">
               <Field label="模型 ID" value={form.ttsModel} onChange={v => set('ttsModel', v)} />
               <Field label="响应格式" value={form.ttsResponseFormat} onChange={v => set('ttsResponseFormat', v)} />
            </div>
          </Section>

          {/* ASR & Network */}
          <Section icon={<Mic size={20} />} title="语音识别 (ASR)">
            <Field label="WebSocket 端点" value={form.asrEndpoint} onChange={v => set('asrEndpoint', v)} placeholder="ws://localhost:10095" />
            <div className="mt-6 p-4 rounded-xl bg-primary-500/5 border border-primary-500/10">
              <p className="text-[10px] uppercase tracking-widest text-primary-400 font-bold mb-1">状态</p>
              <p className="text-xs text-slate-400 leading-relaxed">ASR 引擎仅在「ASR+Text」模式下生效。浏览器端支持采样率自动重采样。</p>
            </div>
          </Section>

          {/* Environmental Audio */}
          <Section icon={<Headphones size={20} />} title="音频环境与交互" className="md:col-span-2">
             <div className="space-y-8">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                  {/* Left: Built-in Noise Types */}
                  <div className="space-y-4">
                    <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-3">预设场景噪音</label>
                    <div className="grid grid-cols-2 gap-3">
                      {(['none', 'cafe', 'office', 'street'] as NoiseType[]).map(type => (
                        <button
                          key={type}
                          onClick={() => set('noiseType', type)}
                          className={`flex items-center justify-between px-4 py-3 rounded-2xl border transition-all duration-300 ${
                            form.noiseType === type
                              ? 'bg-primary-500 text-white border-transparent shadow-[0_10px_20px_rgba(34,197,94,0.2)] scale-[1.02]'
                              : 'border-white/10 bg-white/5 text-slate-400 hover:bg-white/10'
                          }`}
                        >
                          <span className="text-sm font-bold">
                            {type === 'none' ? '安静环境' : type === 'cafe' ? '午后咖啡厅' : type === 'office' ? '写字楼' : '嘈杂街道'}
                          </span>
                          {type !== 'none' && (
                            <div 
                              onClick={(e) => { e.stopPropagation(); togglePreview(`${type}.wav`); }}
                              className={`p-1.5 rounded-lg ${isPlaying === `${type}.wav` ? 'bg-white/20 text-white' : 'bg-black/20 text-slate-500 hover:text-white'}`}
                            >
                              {isPlaying === `${type}.wav` ? <Square size={12} fill="currentColor" /> : <Play size={12} fill="currentColor" />}
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Right: Custom Noise Uploads */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between mb-3">
                      <label className="block text-xs font-black text-slate-500 uppercase tracking-widest">自定义环境音</label>
                      <button 
                        onClick={() => fileInputRef.current?.click()}
                        className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-primary-500/10 text-primary-400 border border-primary-500/20 text-[10px] font-black uppercase tracking-widest hover:bg-primary-500/20 transition-all"
                      >
                        <Upload size={12} />
                        上传音频
                      </button>
                      <input ref={fileInputRef} type="file" accept="audio/*" onChange={handleUpload} className="hidden" />
                    </div>

                    <div className="max-h-40 overflow-y-auto pr-2 custom-scrollbar space-y-2">
                      {noiseSamples.filter(s => !['cafe.wav', 'office.wav', 'street.wav'].includes(s)).map(file => (
                        <div 
                          key={file}
                          className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                            form.noiseType === 'custom' && form.customNoiseFile === file
                              ? 'bg-accent-500/10 border-accent-500/40 text-white'
                              : 'bg-white/5 border-white/5 text-slate-400 hover:border-white/10'
                          }`}
                        >
                          <button 
                            onClick={() => { set('noiseType', 'custom'); set('customNoiseFile', file); }}
                            className="flex-1 text-xs font-medium truncate text-left"
                          >
                            {file}
                          </button>
                          
                          <div className="flex items-center gap-1.5">
                            <button 
                              onClick={() => togglePreview(file)}
                              className={`p-1.5 rounded-lg ${isPlaying === file ? 'bg-accent-500 text-white shadow-glow' : 'bg-white/5 hover:bg-white/10'}`}
                            >
                              {isPlaying === file ? <Square size={12} fill="currentColor" /> : <Play size={12} fill="currentColor" />}
                            </button>
                            <button 
                              onClick={() => handleDeleteNoise(file)}
                              className="p-1.5 rounded-lg bg-white/5 hover:bg-red-500/20 hover:text-red-400 transition-colors"
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </div>
                      ))}
                      {noiseSamples.length === 0 && <div className="text-center py-8 text-[10px] text-slate-600 font-bold uppercase tracking-widest italic">暂无自定义音频</div>}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 pt-8 border-t border-white/[0.06]">
                  <div className="space-y-4">
                     <div className="flex justify-between items-center mb-3">
                        <label className="text-xs font-black text-slate-500 uppercase tracking-widest">混合强度 (Volume)</label>
                        <span className="text-xs font-mono text-primary-400">{Math.round(form.noiseVolume * 100)}%</span>
                     </div>
                     <input
                        type="range" min="0" max="1" step="0.05"
                        value={form.noiseVolume}
                        onChange={e => set('noiseVolume', +e.target.value)}
                        className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-primary-500"
                      />
                  </div>

                  <div className="flex items-center">
                    <label className="flex-1 group flex items-center justify-between p-6 rounded-[2rem] bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-all cursor-pointer shadow-xl">
                      <div className="flex flex-col">
                        <span className="text-base font-bold text-slate-200 group-hover:text-white transition-colors">等待音播报</span>
                        <span className="text-xs text-slate-500 font-medium mt-1">在思考或执行工具时自动填充音频</span>
                      </div>
                      <div className={`relative w-14 h-7 rounded-full transition-colors duration-300 ${form.waitingMusicEnabled ? 'bg-primary-500' : 'bg-slate-700'}`}>
                        <div className={`absolute top-1 left-1 w-5 h-5 bg-white rounded-full transition-transform duration-300 ${form.waitingMusicEnabled ? 'translate-x-7' : 'translate-x-0'}`} />
                      </div>
                      <input
                        type="checkbox"
                        checked={form.waitingMusicEnabled}
                        onChange={e => set('waitingMusicEnabled', e.target.checked)}
                        className="sr-only"
                      />
                    </label>
                  </div>
                </div>
             </div>
          </Section>
        </div>
      </div>
    </div>
  );
}

function Section({ icon, title, children, className = "" }: { icon: React.ReactNode; title: string; children: React.ReactNode, className?: string }) {
  return (
    <div className={`group bg-white/[0.03] backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/[0.06] hover:border-white/[0.12] transition-all duration-500 ${className}`}>
      <div className="flex items-center gap-4 mb-8">
        <div className="p-3 rounded-2xl bg-slate-900 border border-white/10 text-primary-400 shadow-xl group-hover:scale-110 transition-transform duration-500">
          {icon}
        </div>
        <h3 className="font-bold text-lg tracking-tight text-white/90">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function Field({ label, value, onChange, placeholder, type = 'text', multiline = false }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string; multiline?: boolean;
}) {
  return (
    <div className="mb-6 last:mb-0">
      <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">{label}</label>
      {multiline ? (
        <textarea
          value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
          className="w-full px-5 py-4 rounded-[1.5rem] border border-white/10 bg-slate-950/40 text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-primary-500/50 focus:bg-slate-900/60 transition-all min-h-32 resize-none"
        />
      ) : (
        <input
          type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
          className="w-full px-5 py-4 rounded-2xl border border-white/10 bg-slate-950/40 text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-primary-500/50 focus:bg-slate-900/60 transition-all h-14"
        />
      )}
    </div>
  );
}

function ModeCard({ title, desc, active, onClick, badge }: { title: string; desc: string; active: boolean; onClick: () => void, badge?: string }) {
  return (
    <button
      onClick={onClick}
      className={`relative flex-1 p-6 rounded-[2rem] border-2 text-left transition-all duration-500 group overflow-hidden ${
        active 
          ? 'border-primary-500/50 bg-primary-500/10 shadow-[0_0_40px_rgba(34,197,94,0.1)]' 
          : 'border-white/5 bg-slate-900/40 hover:border-white/10 hover:bg-slate-900/60'
      }`}
    >
      {active && (
         <div className="absolute top-0 right-0 p-4">
            <div className="w-2 h-2 rounded-full bg-primary-400 shadow-[0_0_10px_rgba(34,197,94,0.8)]" />
         </div>
      )}
      {badge && (
        <span className="absolute top-4 right-4 px-2 py-0.5 rounded-full bg-primary-500/20 text-primary-400 text-[8px] font-black uppercase tracking-widest border border-primary-500/20">
          {badge}
        </span>
      )}
      <div className={`font-bold text-lg mb-2 transition-colors duration-300 ${active ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'}`}>{title}</div>
      <div className={`text-xs leading-relaxed font-medium transition-colors duration-300 ${active ? 'text-white/70' : 'text-slate-500 group-hover:text-slate-400'}`}>{desc}</div>
    </button>
  );
}

function TestCard({ label, status, onTest, disabled }: { 
  label: string; 
  status: { loading: boolean; status: 'ok' | 'error' | null; message?: string };
  onTest: () => void;
  disabled?: boolean;
}) {
  return (
    <div className={`p-5 rounded-3xl border transition-all ${
      disabled ? 'opacity-40 grayscale pointer-events-none border-white/5 bg-white/2' : 'border-white/10 bg-white/[0.03] hover:border-white/20'
    }`}>
      <div className="flex justify-between items-center mb-4">
        <span className="text-xs font-black uppercase tracking-widest text-slate-400">{label}</span>
        {status.status === 'ok' && <Check size={16} className="text-emerald-400" />}
        {status.status === 'error' && <AlertCircle size={16} className="text-red-400" />}
      </div>
      
      <button
        onClick={onTest}
        disabled={status.loading || disabled}
        className={`w-full py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
          status.status === 'ok' 
            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
            : status.status === 'error'
            ? 'bg-red-500/20 text-red-400 border border-red-500/30'
            : 'bg-white/5 text-slate-300 border border-white/10 hover:bg-white/10'
        }`}
      >
        {status.loading ? <Loader2 size={14} className="animate-spin mx-auto" /> : status.status ? '重新测试' : '测试连接'}
      </button>
      
      {status.message && (
        <p className="mt-2 text-[8px] text-red-400/60 font-mono truncate" title={status.message}>
          {status.message}
        </p>
      )}
    </div>
  );
}
