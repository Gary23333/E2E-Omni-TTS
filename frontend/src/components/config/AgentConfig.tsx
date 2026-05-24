import { useState } from 'react';
import {
  Plus, Trash2, Edit3, Users, X, Check, Bot, Sparkles, Settings2,
  Layers, ChevronRight, Volume2, BookOpen, Zap,
} from 'lucide-react';
import { useAgentStore } from '../../stores/agentStore';
import type { Agent, AgentGroup } from '../../types';

export function AgentConfig() {
  const {
    agents, groups,
    createAgent, updateAgent, deleteAgent,
    createGroup, updateGroup, deleteGroup,
  } = useAgentStore();

  const [tab, setTab] = useState<'agents' | 'groups'>('agents');
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [editingGroup, setEditingGroup] = useState<AgentGroup | null>(null);

  const defaultAgent: Agent = {
    id: '', name: '新客服', role: 'general',
    systemPrompt: '你是一个专业的客服助手，语气友好、专业。',
    voiceDescriptor: '(A warm young woman)',
    temperature: 0.7, maxTokens: 1024,
    enabledToolIds: [], ragEnabled: false, enabled: true,
  };

  const defaultGroup: AgentGroup = {
    id: '', name: '新客服组', description: '',
    agentIds: [], defaultAgentId: '',
    routerPrompt:
      '你是客服路由代理。根据用户消息判断应该由哪个客服处理。\n可用客服列表：\n{agent_list}\n\n用户消息：{user_message}\n\n请返回JSON格式：{"agent_id":"xxx","confidence":0.9,"reason":"原因"}',
    collaborationRules: [],
  };

  return (
    <div className="h-full flex flex-col text-slate-200">
      {/* Header */}
      <div className="px-10 py-8 border-b border-white/[0.06] bg-white/[0.02] backdrop-blur-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="absolute -inset-1.5 bg-gradient-to-tr from-primary-500 to-accent-400 rounded-2xl blur opacity-30" />
              <div className="relative w-14 h-14 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center text-primary-400 shadow-2xl">
                <Users size={26} />
              </div>
            </div>
            <div>
              <h2 className="text-2xl font-black tracking-tight uppercase italic">
                <span className="text-gradient-modern">客服编排</span>
              </h2>
              <p className="text-xs text-slate-500 mt-1.5 font-medium uppercase tracking-widest">
                Agent Roster · Routing · Collaboration
              </p>
            </div>
          </div>

          {/* Tab Switcher */}
          <div className="flex items-center gap-1.5 p-1.5 rounded-2xl bg-slate-900/60 border border-white/[0.06] shadow-inner">
            <TabPill
              active={tab === 'agents'}
              onClick={() => setTab('agents')}
              icon={<Bot size={14} />}
              label={`客服 · ${agents.length}`}
            />
            <TabPill
              active={tab === 'groups'}
              onClick={() => setTab('groups')}
              icon={<Layers size={14} />}
              label={`客服组 · ${groups.length}`}
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-10 custom-scrollbar bg-slate-950/20">
        <div className="max-w-5xl mx-auto">
          {tab === 'agents' && (
            <div className="space-y-4">
              <CreateButton label="添加客服" onClick={() => setEditingAgent({ ...defaultAgent })} />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {agents.map(agent => (
                  <AgentCard
                    key={agent.id}
                    agent={agent}
                    onEdit={() => setEditingAgent({ ...agent })}
                    onDelete={() => deleteAgent(agent.id)}
                  />
                ))}
              </div>

              {agents.length === 0 && <EmptyState icon={<Users size={36} />} text="暂无客服，点击上方按钮创建第一个 Agent" />}
            </div>
          )}

          {tab === 'groups' && (
            <div className="space-y-4">
              <CreateButton label="添加客服组" onClick={() => setEditingGroup({ ...defaultGroup })} />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {groups.map(group => (
                  <GroupCard
                    key={group.id}
                    group={group}
                    agents={agents}
                    onEdit={() => setEditingGroup({ ...group })}
                    onDelete={() => deleteGroup(group.id)}
                  />
                ))}
              </div>

              {groups.length === 0 && <EmptyState icon={<Layers size={36} />} text="暂无客服组，点击上方按钮创建" />}
            </div>
          )}
        </div>

        {editingAgent && (
          <AgentEditModal
            agent={editingAgent}
            onSave={a => {
              if (a.id) updateAgent(a.id, a);
              else createAgent(a);
              setEditingAgent(null);
            }}
            onClose={() => setEditingAgent(null)}
          />
        )}

        {editingGroup && (
          <GroupEditModal
            group={editingGroup}
            agents={agents}
            onSave={g => {
              if (g.id) updateGroup(g.id, g);
              else createGroup(g);
              setEditingGroup(null);
            }}
            onClose={() => setEditingGroup(null)}
          />
        )}
      </div>
    </div>
  );
}

/* -------- Cards -------- */

function AgentCard({
  agent, onEdit, onDelete,
}: { agent: Agent; onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="group glass-card glass-card-glow rounded-[1.75rem] p-5 relative overflow-hidden">
      <div className="flex items-start gap-4">
        <div className="relative shrink-0">
          <div className={`absolute -inset-1 rounded-2xl blur opacity-20 ${agent.enabled ? 'bg-gradient-to-tr from-primary-500 to-accent-500' : 'bg-slate-700'} group-hover:opacity-40 transition`} />
          <div className="relative w-12 h-12 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center">
            <Bot size={22} className={agent.enabled ? 'text-primary-400' : 'text-slate-600'} />
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-black text-base text-white tracking-tight truncate">{agent.name}</h4>
            <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              {agent.role}
            </span>
            {!agent.enabled && (
              <span className="px-2 py-0.5 rounded-full bg-slate-800 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                Off
              </span>
            )}
          </div>

          <p className="text-xs text-slate-400 mt-2 leading-relaxed line-clamp-2">{agent.systemPrompt}</p>

          <div className="flex items-center gap-3 mt-3 text-[10px] font-bold uppercase tracking-widest">
            <Stat icon={<Sparkles size={11} />} label="Temp" value={agent.temperature.toFixed(1)} />
            <Stat icon={<Volume2 size={11} />} label="Voice" value={agent.voiceDescriptor ? '已配置' : '默认'} />
            {agent.ragEnabled && <Stat icon={<BookOpen size={11} />} label="RAG" value="开启" highlight />}
            {agent.enabledToolIds.length > 0 && (
              <Stat icon={<Zap size={11} />} label="Tools" value={String(agent.enabledToolIds.length)} highlight />
            )}
          </div>
        </div>

        <div className="flex flex-col gap-1.5 shrink-0">
          <button
            onClick={onEdit}
            className="press p-2 rounded-xl bg-white/[0.04] hover:bg-white/10 text-slate-400 hover:text-white transition-all"
          >
            <Edit3 size={16} />
          </button>
          <button
            onClick={onDelete}
            className="press p-2 rounded-xl bg-white/[0.04] hover:bg-red-500/20 text-slate-400 hover:text-red-300 transition-all"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function GroupCard({
  group, agents, onEdit, onDelete,
}: { group: AgentGroup; agents: Agent[]; onEdit: () => void; onDelete: () => void }) {
  const memberAgents = agents.filter(a => group.agentIds.includes(a.id));
  return (
    <div className="group glass-card glass-card-glow rounded-[1.75rem] p-5 relative overflow-hidden">
      <div className="flex items-start gap-4">
        <div className="relative shrink-0">
          <div className="absolute -inset-1 rounded-2xl blur opacity-20 bg-gradient-to-tr from-accent-500 to-primary-500 group-hover:opacity-40 transition" />
          <div className="relative w-12 h-12 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center">
            <Layers size={22} className="text-accent-400" />
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-black text-base text-white tracking-tight truncate">{group.name}</h4>
            <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              {group.agentIds.length} agents
            </span>
          </div>
          {group.description && (
            <p className="text-xs text-slate-400 mt-2 leading-relaxed line-clamp-2">{group.description}</p>
          )}

          <div className="flex flex-wrap gap-1.5 mt-3">
            {memberAgents.slice(0, 5).map(a => (
              <span
                key={a.id}
                className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[10px] font-bold text-slate-300"
              >
                {a.name}
              </span>
            ))}
            {memberAgents.length > 5 && (
              <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[10px] font-bold text-slate-500">
                +{memberAgents.length - 5}
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-1.5 shrink-0">
          <button
            onClick={onEdit}
            className="press p-2 rounded-xl bg-white/[0.04] hover:bg-white/10 text-slate-400 hover:text-white transition-all"
          >
            <Edit3 size={16} />
          </button>
          <button
            onClick={onDelete}
            className="press p-2 rounded-xl bg-white/[0.04] hover:bg-red-500/20 text-slate-400 hover:text-red-300 transition-all"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

/* -------- Modals -------- */

function AgentEditModal({
  agent, onSave, onClose,
}: { agent: Agent; onSave: (a: Agent) => void; onClose: () => void }) {
  const [form, setForm] = useState(agent);
  const set = <K extends keyof Agent>(key: K, val: Agent[K]) =>
    setForm(f => ({ ...f, [key]: val }));

  return (
    <ModalShell
      title={agent.id ? '编辑客服' : '添加客服'}
      onClose={onClose}
      onSave={() => onSave(form)}
    >
      <Field label="名称">
        <Input value={form.name} onChange={v => set('name', v)} />
      </Field>
      <Field label="角色">
        <Input value={form.role} onChange={v => set('role', v)} placeholder="如 general / sales / support" />
      </Field>
      <Field label="系统提示词">
        <Textarea value={form.systemPrompt} onChange={v => set('systemPrompt', v)} rows={5} />
      </Field>
      <Field label="声音描述 (VoxCPM2)">
        <Input value={form.voiceDescriptor} onChange={v => set('voiceDescriptor', v)} placeholder="(A warm young woman)" />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Temperature">
          <Input type="number" step="0.1" min="0" max="2" value={String(form.temperature)} onChange={v => set('temperature', +v)} />
        </Field>
        <Field label="Max Tokens">
          <Input type="number" min="1" value={String(form.maxTokens)} onChange={v => set('maxTokens', +v)} />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <ToggleCard
          label="启用 RAG"
          desc="允许调用知识库"
          checked={form.ragEnabled}
          onChange={v => set('ragEnabled', v)}
        />
        <ToggleCard
          label="启用此 Agent"
          desc="可被路由分配"
          checked={form.enabled}
          onChange={v => set('enabled', v)}
        />
      </div>
    </ModalShell>
  );
}

function GroupEditModal({
  group, agents, onSave, onClose,
}: { group: AgentGroup; agents: Agent[]; onSave: (g: AgentGroup) => void; onClose: () => void }) {
  const [form, setForm] = useState(group);
  const set = <K extends keyof AgentGroup>(key: K, val: AgentGroup[K]) =>
    setForm(f => ({ ...f, [key]: val }));

  const toggleAgent = (id: string) => {
    setForm(f => ({
      ...f,
      agentIds: f.agentIds.includes(id) ? f.agentIds.filter(a => a !== id) : [...f.agentIds, id],
    }));
  };

  return (
    <ModalShell
      title={group.id ? '编辑客服组' : '添加客服组'}
      onClose={onClose}
      onSave={() => onSave(form)}
    >
      <Field label="组名称">
        <Input value={form.name} onChange={v => set('name', v)} />
      </Field>
      <Field label="描述">
        <Input value={form.description} onChange={v => set('description', v)} />
      </Field>

      <Field label="选择客服">
        <div className="space-y-1.5 max-h-56 overflow-y-auto custom-scrollbar pr-1">
          {agents.length === 0 && (
            <div className="px-4 py-3 text-xs text-slate-500 italic rounded-xl bg-white/[0.03] border border-white/[0.06]">
              请先添加客服，再来配置客服组。
            </div>
          )}
          {agents.map(a => {
            const active = form.agentIds.includes(a.id);
            return (
              <label
                key={a.id}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all border ${
                  active
                    ? 'bg-primary-500/10 border-primary-500/30'
                    : 'bg-white/[0.03] border-white/[0.06] hover:bg-white/[0.05]'
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-md flex items-center justify-center border transition-all ${
                    active ? 'bg-gradient-to-tr from-primary-500 to-accent-500 border-transparent' : 'border-white/20 bg-slate-900/40'
                  }`}
                >
                  {active && <Check size={12} className="text-white" />}
                </div>
                <input
                  type="checkbox"
                  checked={active}
                  onChange={() => toggleAgent(a.id)}
                  className="sr-only"
                />
                <span className="text-sm font-bold text-slate-200">{a.name}</span>
                <span className="ml-auto text-[10px] font-bold uppercase tracking-widest text-slate-500">{a.role}</span>
              </label>
            );
          })}
        </div>
      </Field>

      {form.agentIds.length > 0 && (
        <Field label="默认客服">
          <select
            value={form.defaultAgentId}
            onChange={e => set('defaultAgentId', e.target.value)}
            className="w-full px-5 py-3.5 rounded-2xl border border-white/10 bg-slate-950/40 text-slate-200 text-sm focus:outline-none focus:border-primary-500/50 transition-all"
          >
            <option value="">请选择...</option>
            {form.agentIds.map(id => {
              const a = agents.find(ag => ag.id === id);
              return a ? <option key={id} value={id}>{a.name}</option> : null;
            })}
          </select>
        </Field>
      )}

      <Field label="路由提示词">
        <Textarea value={form.routerPrompt} onChange={v => set('routerPrompt', v)} rows={5} />
      </Field>
    </ModalShell>
  );
}

/* -------- Shared bits -------- */

function TabPill({
  active, onClick, icon, label,
}: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`press flex items-center gap-2 px-4 py-2 text-xs font-black rounded-xl transition-all duration-300 ${
        active
          ? 'bg-white text-slate-950 shadow-[0_8px_20px_-6px_rgba(255,255,255,0.25)]'
          : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
      }`}
    >
      {icon}
      <span className="tracking-wider uppercase">{label}</span>
    </button>
  );
}

function CreateButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="press group inline-flex items-center gap-2.5 px-5 py-3 rounded-2xl bg-gradient-to-r from-primary-500 to-accent-500 text-white text-sm font-black shadow-[0_15px_30px_-10px_rgba(34,197,94,0.5)] hover:shadow-[0_20px_40px_-10px_rgba(34,197,94,0.7)] hover:-translate-y-0.5 transition-all duration-300"
    >
      <div className="w-6 h-6 rounded-lg bg-white/20 flex items-center justify-center group-hover:rotate-90 transition-transform duration-500">
        <Plus size={14} strokeWidth={3} />
      </div>
      <span className="tracking-wider uppercase">{label}</span>
    </button>
  );
}

function Stat({
  icon, label, value, highlight,
}: { icon: React.ReactNode; label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`flex items-center gap-1.5 ${highlight ? 'text-primary-400' : 'text-slate-500'}`}>
      {icon}
      <span>{label}</span>
      <span className={`${highlight ? 'text-primary-300' : 'text-slate-300'} tabular-nums`}>{value}</span>
    </div>
  );
}

function EmptyState({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="text-center py-16">
      <div className="w-20 h-20 mx-auto mb-5 rounded-3xl bg-slate-900 border border-white/10 flex items-center justify-center text-slate-500">
        {icon}
      </div>
      <p className="text-slate-500 text-sm font-medium">{text}</p>
    </div>
  );
}

function ModalShell({
  title, onClose, onSave, children,
}: { title: string; onClose: () => void; onSave: () => void; children: React.ReactNode }) {
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
              <h3 className="text-lg font-black text-white tracking-tight">{title}</h3>
            </div>
            <button
              onClick={onClose}
              className="press p-2 rounded-xl bg-white/[0.04] hover:bg-white/10 text-slate-400 hover:text-white transition-all"
            >
              <X size={18} />
            </button>
          </div>

          <div className="px-7 py-6 space-y-5">{children}</div>

          <div className="sticky bottom-0 flex justify-end gap-3 px-7 py-5 bg-slate-950/80 backdrop-blur-xl border-t border-white/[0.06]">
            <button
              onClick={onClose}
              className="press px-5 py-2.5 text-xs font-black uppercase tracking-widest bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 hover:text-white rounded-xl transition-all"
            >
              取消
            </button>
            <button
              onClick={onSave}
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
      <label className="block text-[11px] font-black text-slate-500 uppercase tracking-widest mb-2 ml-1">
        {label}
      </label>
      {children}
    </div>
  );
}

function Input(props: Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'value'> & { onChange: (v: string) => void; value: string }) {
  const { onChange, ...rest } = props;
  return (
    <input
      {...rest}
      onChange={e => onChange(e.target.value)}
      className="w-full px-5 py-3.5 rounded-2xl border border-white/10 bg-slate-950/40 text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-primary-500/50 focus:bg-slate-900/60 transition-all"
    />
  );
}

function Textarea({
  value, onChange, rows = 4,
}: { value: string; onChange: (v: string) => void; rows?: number }) {
  return (
    <textarea
      value={value}
      rows={rows}
      onChange={e => onChange(e.target.value)}
      className="w-full px-5 py-3.5 rounded-2xl border border-white/10 bg-slate-950/40 text-slate-200 placeholder-slate-600 text-sm focus:outline-none focus:border-primary-500/50 focus:bg-slate-900/60 transition-all resize-none"
    />
  );
}

function ToggleCard({
  label, desc, checked, onChange,
}: { label: string; desc: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center justify-between p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-all cursor-pointer">
      <div className="flex flex-col">
        <span className="text-sm font-bold text-slate-200">{label}</span>
        <span className="text-[10px] text-slate-500 font-medium mt-0.5">{desc}</span>
      </div>
      <div className={`relative w-11 h-6 rounded-full transition-colors duration-300 ${checked ? 'bg-primary-500 shadow-[0_0_15px_rgba(34,197,94,0.5)]' : 'bg-slate-700'}`}>
        <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform duration-300 ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        className="sr-only"
      />
    </label>
  );
}
