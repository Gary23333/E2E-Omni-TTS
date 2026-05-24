import { useEffect, useRef, useState } from 'react';
import {
  Trash2, FileText, ToggleLeft, ToggleRight, Loader2, CheckCircle2,
  AlertCircle, BookOpen, FileType2, Cloud,
} from 'lucide-react';
import { useRAGStore } from '../../stores/ragStore';

export function RAGManager() {
  const { documents, load, upload, remove, toggle } = useRAGStore();
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => { load(); }, [load]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    files.forEach(f => upload(f));
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach(f => upload(f));
    if (fileRef.current) fileRef.current.value = '';
  };

  const readyCount = documents.filter(d => d.status === 'ready').length;
  const totalChunks = documents.reduce((s, d) => s + (d.status === 'ready' ? d.chunkCount : 0), 0);

  return (
    <div className="h-full flex flex-col text-slate-200">
      {/* Header */}
      <div className="px-10 py-8 border-b border-white/[0.06] bg-white/[0.02] backdrop-blur-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="absolute -inset-1.5 bg-gradient-to-tr from-primary-500 to-accent-400 rounded-2xl blur opacity-30" />
              <div className="relative w-14 h-14 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center text-primary-400 shadow-2xl">
                <BookOpen size={26} />
              </div>
            </div>
            <div>
              <h2 className="text-2xl font-black tracking-tight uppercase italic">
                <span className="text-gradient-modern">知识库管理</span>
              </h2>
              <p className="text-xs text-slate-500 mt-1.5 font-medium uppercase tracking-widest">
                RAG · Chunking · FAISS Vector Store
              </p>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-3">
            <Metric label="文档总数" value={String(documents.length)} />
            <Metric label="就绪" value={String(readyCount)} highlight />
            <Metric label="切片" value={String(totalChunks)} />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-10 custom-scrollbar bg-slate-950/20">
        <div className="max-w-4xl mx-auto space-y-5">
          {/* Upload zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            className={`relative overflow-hidden rounded-[2rem] border-2 border-dashed transition-all duration-500 cursor-pointer group ${
              dragOver
                ? 'border-primary-500/60 bg-primary-500/10 shadow-[0_0_50px_rgba(34,197,94,0.15)] scale-[1.01]'
                : 'border-white/[0.08] bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]'
            }`}
          >
            {/* Floating bg orbs */}
            <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-primary-500/10 blur-3xl pointer-events-none" />
            <div className="absolute -bottom-10 -left-10 w-40 h-40 rounded-full bg-accent-500/10 blur-3xl pointer-events-none" />

            <div className="relative px-10 py-14 text-center">
              <div className="relative inline-flex items-center justify-center w-20 h-20 mb-6">
                <div className={`absolute inset-0 rounded-3xl bg-gradient-to-tr from-primary-500/30 to-accent-500/30 blur-xl transition ${dragOver ? 'opacity-100 scale-110' : 'opacity-50'}`} />
                <div className="relative w-20 h-20 rounded-3xl bg-slate-900 border border-white/10 flex items-center justify-center shadow-2xl group-hover:scale-105 group-hover:rotate-3 transition-all duration-500">
                  <Cloud size={36} className={`${dragOver ? 'text-primary-300' : 'text-primary-400'} transition-colors`} />
                </div>
              </div>
              <h3 className="text-xl font-black text-white tracking-tight mb-2 uppercase italic">
                {dragOver ? 'Release to Upload' : '拖拽文件到此处'}
              </h3>
              <p className="text-sm text-slate-400 font-medium">或点击此处选择文件 · 支持批量上传</p>

              <div className="flex justify-center gap-2 mt-6 flex-wrap">
                {['PDF', 'DOCX', 'TXT', 'MD'].map(ext => (
                  <span
                    key={ext}
                    className="px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-[10px] font-black text-slate-300 uppercase tracking-widest"
                  >
                    {ext}
                  </span>
                ))}
              </div>

              <input
                ref={fileRef} type="file" multiple
                accept=".pdf,.docx,.txt,.md"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>
          </div>

          {/* Document list */}
          <div className="space-y-3">
            {documents.map(doc => (
              <div
                key={doc.id}
                className="group glass-card glass-card-glow rounded-[1.5rem] p-4 flex items-center gap-4 animate-in fade-in slide-in-from-bottom-2 duration-500"
              >
                <div className="relative shrink-0">
                  <div className="absolute -inset-1 rounded-2xl blur opacity-25 bg-gradient-to-tr from-primary-500 to-accent-500 group-hover:opacity-40 transition" />
                  <div className="relative w-12 h-12 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center">
                    <FileType2 size={22} className="text-primary-400" />
                  </div>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="font-bold text-white truncate">{doc.filename}</div>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <StatusBadge status={doc.status} chunkCount={doc.chunkCount} error={doc.error} />
                    {doc.uploadedAt && (
                      <span className="text-[10px] font-mono text-slate-500 tabular-nums">
                        {new Date(doc.uploadedAt).toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => toggle(doc.id)}
                  className="press shrink-0"
                  title={doc.enabled ? '禁用' : '启用'}
                >
                  {doc.enabled ? (
                    <ToggleRight size={32} className="text-primary-400 drop-shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
                  ) : (
                    <ToggleLeft size={32} className="text-slate-600" />
                  )}
                </button>

                <button
                  onClick={() => remove(doc.id)}
                  className="press shrink-0 p-2 rounded-xl bg-white/[0.04] hover:bg-red-500/20 text-slate-400 hover:text-red-300 transition-all"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>

          {documents.length === 0 && (
            <div className="text-center py-16">
              <div className="w-20 h-20 mx-auto mb-5 rounded-3xl bg-slate-900 border border-white/10 flex items-center justify-center text-slate-500">
                <FileText size={36} />
              </div>
              <p className="text-slate-500 text-sm font-medium">暂无文档，上传文件开始构建知识库</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({
  status, chunkCount, error,
}: { status: 'processing' | 'ready' | 'error'; chunkCount: number; error?: string }) {
  if (status === 'ready') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 text-[10px] font-black uppercase tracking-widest">
        <CheckCircle2 size={11} />
        Ready · {chunkCount} chunks
      </span>
    );
  }
  if (status === 'processing') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-yellow-500/15 text-yellow-400 border border-yellow-500/20 text-[10px] font-black uppercase tracking-widest">
        <Loader2 size={11} className="animate-spin" />
        Processing
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/15 text-red-400 border border-red-500/20 text-[10px] font-black uppercase tracking-widest"
      title={error}
    >
      <AlertCircle size={11} />
      Error
    </span>
  );
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex flex-col items-end px-4 py-2 rounded-2xl bg-white/[0.03] border border-white/[0.06] min-w-[80px]">
      <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">{label}</span>
      <span className={`text-lg font-black tabular-nums ${highlight ? 'text-primary-400' : 'text-white'}`}>
        {value}
      </span>
    </div>
  );
}
