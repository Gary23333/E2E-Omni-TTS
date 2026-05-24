import { useEffect, useState } from 'react';
import {
  Plus, Trash2, ToggleLeft, ToggleRight, Wrench, Globe, Code, Zap, X,
  Settings2, ChevronRight,
} from 'lucide-react';
import { useSkillStore } from '../../stores/skillStore';
import type { Skill } from '../../types';

const SKILL_TYPE_META: Record<Skill['type'], {
  icon: typeof Zap; label: string; color: string; gradient: string;
}> = {
  builtin: { icon: Zap,    label: '内置', color: 'text-blue-300',   gradient: 'from-blue-500/20 to-cyan-500/20' },
  http:    { icon: Globe,  label: 'HTTP', color: 'text-emerald-300', gradient: 'from-emerald-500/20 to-teal-500/20' },
  script:  { icon: Code,   label: '脚本', color: 'text-fuchsia-300', gradient: 'from-fuchsia-500/20 to-purple-500/20' },
};

export function SkillManager() {
  const { skills, load, create, update, remove, toggle } = useSkillStore();
  const [editing, setEditing] = useState<Skill | null>(null);

  useEffect(() => { load(); }, [load]);

  const defaultSkill: Skill = {
    id: '', name: '', description: '', type: 'http', enabled: true,
    parameters: { type: 'object', properties: {} },
    config: { url: '', method: 'GET', headers: {} },
  };

  const enabledCount = skills.filter(s => s.enabled).length;

  return (
    <div className="h-full flex flex-col text-slate-200">
      {/* Header */}
      <div className="px-10 py-8 border-b border-white/[0.06] bg-white/[0.02] backdrop-blur-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="absolute -inset-1.5 bg-gradient-to-tr from-primary-500 to-accent-400 rounded-2xl blur opacity-30" />
              <div className="relative w-14 h-14 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center text-primary-400 shadow-2xl">
                <Wrench size={26} />
              </div>
            </div>
            <div>
              <h2 className="text-2xl font-black tracking-tight uppercase italic">
                <span className="text-gradient-modern">插件中心</span>
              </h2>
              <p className="text-xs text-slate-500 mt-1.5 font-medium uppercase tracking-widest">
                内置插件 · HTTP API · 自定义脚本
              </p>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-3">
            <div className="px-4 py-2 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
              <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">已启用</span>
              <div className="text-lg font-black tabular-nums text-primary-400">
                {enabledCount}<span className="text-slate-600 text-sm">/{skills.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-10 custom-scrollbar bg-slate-950/20">
        <div className="max-w-4xl mx-auto space-y-5">
          <button
            onClick={() => setEditing({ ...defaultSkill })}
            className="press group inline-flex items-center gap-2.5 px-5 py-3 rounded-2xl bg-gradient-to-r from-primary-500 to-accent-500 text-white text-sm font-black shadow-[0_15px_30px_-10px_rgba(34,197,94,0.5)] hover:shadow-[0_20px_40px_-10px_rgba(34,197,94,0.7)] hover:-translate-y-0.5 transition-all duration-300"
          >
            <div className="w-6 h-6 rounded-lg bg-white/20 flex items-center justify-center group-hover:rotate-90 transition-transform duration-500">
              <Plus size={14} strokeWidth={3} />
            </div>
            <span className="tracking-wider uppercase">添加技能</span>
          </button>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {skills.map(skill => {
              const meta = SKILL_TYPE_META[skill.type];
              const Icon = meta.icon;
              return (
                <div
                  key={skill.id}
                  className="group glass-card glass-card-glow rounded-[1.5rem] p-5 animate-in fade-in slide-in-from-bottom-2 duration-500"
                >
                  <div className="flex items-start gap-4">
                    <div className="relative shrink-0">
                      <div className={`absolute -inset-1 rounded-2xl bg-gradient-to-tr ${meta.gradient} blur opacity-50 group-hover:opacity-80 transition`} />
                      <div className={`relative w-12 h-12 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center ${meta.color}`}>
                        <Icon size={20} />
                      </div>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-black text-base text-white tracking-tight truncate">
                          {skill.name || '未命名技能'}
                        </h4>
                        <span className={`px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/10 text-[10px] font-black uppercase tracking-widest ${meta.color}`}>
                          {meta.label}
                        </span>
                        {!skill.enabled && (
                          <span className="px-2 py-0.5 rounded-full bg-slate-800 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                            Off
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-2 leading-relaxed line-clamp-2">
                        {skill.description || '无描述'}
                      </p>
                      {skill.type === 'http' && skill.config.url && (
                        <code className="block mt-2.5 px-2.5 py-1.5 rounded-lg bg-slate-950/60 border border-white/[0.06] text-[10px] font-mono text-slate-400 truncate">
                          <span className="text-primary-400 mr-1.5">{skill.config.method || 'GET'}</span>
                          {skill.config.url}
                        </code>
                      )}
                    </div>

                    <div className="flex flex-col gap-2 items-end shrink-0">
                      <button
                        onClick={() => toggle(skill.id)}
                        className="press"
                        title={skill.enabled ? '禁用' : '启用'}
                      >
                        {skill.enabled ? (
                          <ToggleRight size={32} className="text-primary-400 drop-shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
                        ) : (
                          <ToggleLeft size={32} className="text-slate-600" />
                        )}
                      </button>
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => setEditing({ ...skill })}
                          className="press p-2 rounded-xl bg-white/[0.04] hover:bg-white/10 text-slate-400 hover:text-white transition-all"
                        >
                          <Wrench size={14} />
                        </button>
                        {skill.type !== 'builtin' && (
                          <button
                            onClick={() => remove(skill.id)}
                            className="press p-2 rounded-xl bg-white/[0.04] hover:bg-red-500/20 text-slate-400 hover:text-red-300 transition-all"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {skills.length === 0 && (
            <div className="text-center py-16">
              <div className="w-20 h-20 mx-auto mb-5 rounded-3xl bg-slate-900 border border-white/10 flex items-center justify-center text-slate-500">
                <Wrench size={36} />
              </div>
              <p className="text-slate-500 text-sm font-medium">暂无技能，点击上方按钮添加</p>
            </div>
          )}
        </div>

        {editing && (
          <SkillEditModal
            skill={editing}
            onSave={(s) => {
              if (s.id && skills.find(sk => sk.id === s.id)) update(s.id, s);
              else create(s);
              setEditing(null);
            }}
            onClose={() => setEditing(null)}
          />
        )}
      </div>
    </div>
  );
}

function SkillEditModal({
  skill, onSave, onClose,
}: { skill: Skill; onSave: (s: Skill) => void; onClose: () => void }) {
  const [form, setForm] = useState(skill);
  const set = <K extends keyof Skill>(key: K, val: Skill[K]) => setForm(f => ({ ...f, [key]: val }));

  return (
    <div
      className="fixed inset-0 bg-slate-950/70 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-in fade-in duration-300"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-xl rounded-[2rem] overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500"
        onClick={e => e.stopPropagation()}
      >
        <div className="absolute -inset-px rounded-[2rem] bg-gradient-to-br from-primary-500/30 via-transparent to-accent-500/30 blur opacity-50 pointer-events-none" />
        <div className="relative glass-card rounded-[2rem] max-h-[88vh] overflow-y-auto custom-scrollbar">
          <div className="sticky top-0 z-10 flex items-center justify-between px-7 py-5 bg-slate-950/80 backdrop-blur-xl border-b border-white/[0.06]">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-slate-900 border border-white/10 flex items-center justify-center text-primary-400">
                <Settings2 size={16} />
              </div>
              <h3 className="text-lg font-black text-white tracking-tight">
                {skill.id ? '编辑技能' : '添加技能'}
              </h3>
            </div>
            <button
              onClick={onClose}
              className="press p-2 rounded-xl bg-white/[0.04] hover:bg-white/10 text-slate-400 hover:text-white transition-all"
            >
              <X size={18} />
            </button>
          </div>

          <div className="px-7 py-6 space-y-5">
            <Field label="名称">
              <Input value={form.name} onChange={v => set('name', v)} />
            </Field>
            <Field label="描述">
              <Input value={form.description} onChange={v => set('description', v)} />
            </Field>
            <Field label="类型">
              <div className="grid grid-cols-3 gap-2">
                {(['builtin', 'http', 'script'] as Skill['type'][]).map(t => {
                  const meta = SKILL_TYPE_META[t];
                  const Icon = meta.icon;
                  const active = form.type === t;
                  return (
                    <button
                      key={t}
                      onClick={() => set('type', t)}
                      className={`press flex items-center gap-2 px-3 py-3 rounded-2xl border text-xs font-black uppercase tracking-widest transition-all ${
                        active
                          ? 'border-primary-500/40 bg-primary-500/10 text-white shadow-[0_0_25px_rgba(34,197,94,0.18)]'
                          : 'border-white/[0.08] bg-white/[0.03] text-slate-400 hover:bg-white/[0.06] hover:text-slate-200'
                      }`}
                    >
                      <Icon size={13} className={active ? meta.color : 'text-slate-500'} />
                      <span>{meta.label}</span>
                    </button>
                  );
                })}
              </div>
            </Field>

            {form.type === 'http' && (
              <>
                <Field label="URL">
                  <Input
                    value={form.config.url || ''}
                    onChange={v => set('config', { ...form.config, url: v })}
                    placeholder="https://api.example.com/endpoint"
                  />
                </Field>
                <Field label="方法">
                  <select
                    value={form.config.method || 'GET'}
                    onChange={e => set('config', { ...form.config, method: e.target.value })}
                    className="w-full px-5 py-3.5 rounded-2xl border border-white/10 bg-slate-950/40 text-slate-200 text-sm focus:outline-none focus:border-primary-500/50 transition-all"
                  >
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                  </select>
                </Field>
              </>
            )}

            {form.type === 'script' && (
              <Field label="代码">
                <textarea
                  value={form.config.code || ''}
                  onChange={e => set('config', { ...form.config, code: e.target.value })}
                  className="w-full px-5 py-3.5 rounded-2xl border border-white/10 bg-slate-950/40 text-slate-200 placeholder-slate-600 text-sm font-mono h-40 focus:outline-none focus:border-primary-500/50 focus:bg-slate-900/60 transition-all resize-none"
                />
              </Field>
            )}

            <Field label="参数 Schema (JSON)">
              <textarea
                value={JSON.stringify(form.parameters, null, 2)}
                onChange={e => { try { set('parameters', JSON.parse(e.target.value)); } catch { /* ignore */ } }}
                className="w-full px-5 py-3.5 rounded-2xl border border-white/10 bg-slate-950/40 text-slate-200 placeholder-slate-600 text-sm font-mono h-40 focus:outline-none focus:border-primary-500/50 focus:bg-slate-900/60 transition-all resize-none"
              />
            </Field>
          </div>

          <div className="sticky bottom-0 flex justify-end gap-3 px-7 py-5 bg-slate-950/80 backdrop-blur-xl border-t border-white/[0.06]">
            <button
              onClick={onClose}
              className="press px-5 py-2.5 text-xs font-black uppercase tracking-widest bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 hover:text-white rounded-xl transition-all"
            >
              取消
            </button>
            <button
              onClick={() => onSave(form)}
              className="press px-6 py-2.5 text-xs font-black uppercase tracking-widest bg-gradient-to-r from-primary-500 to-accent-500 text-white rounded-xl shadow-[0_10px_25px_-8px_rgba(34,197,94,0.6)] hover:shadow-[0_15px_30px_-8px_rgba(34,197,94,0.7)] transition-all"
            >
              <span className="inline-flex items-center gap-1.5">保存 <ChevronRight size={12} /></span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-black text-slate-500 uppercase tracking-widest mb-2 ml-1">{label}</label>
      {children}
    </div>
  );
}

function Input({
  value, onChange, placeholder, type = 'text',
}: { value: string; onChange: (v: string) => void; placeholder?: string; type?: string }) {
  return (
    <input
      type={type}
      value={value}
      placeholder={placeholder}
      onChange={e => onChange(e.target.value)}
      className="w-full px-5 py-3.5 rounded-2xl border border-white/10 bg-slate-950/40 text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-primary-500/50 focus:bg-slate-900/60 transition-all"
    />
  );
}
