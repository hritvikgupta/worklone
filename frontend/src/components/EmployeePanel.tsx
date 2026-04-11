import React, { useState, useEffect, useCallback } from 'react';
import { X, Plus, Trash2, Save, Loader2, Sparkles, Paperclip, Mic, Send } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { getToolsCatalog } from '@/src/api/employees';

interface EmployeePanelProps {
  open: boolean;
  onClose: () => void;
  employee?: EmployeeFormData | null;
  onSave: (data: EmployeeFormData) => Promise<void>;
  isSaving?: boolean;
}

export interface EmployeeFormData {
  name: string;
  role: string;
  avatar_url: string;
  description: string;
  system_prompt: string;
  model: string;
  temperature: number;
  max_tokens: number;
  tools: string[];
  skills: { skill_name: string; category: string; proficiency_level: number; description: string }[];
}

interface AvailableTool {
  name: string;
  runtime_name?: string;
  description: string;
  category: string;
}

const SKILL_CATEGORIES = ['research', 'coding', 'devops', 'analytics', 'communication', 'product', 'design', 'sales', 'finance'];

const MODEL_OPTIONS = [
  'openai/gpt-4o',
  'anthropic/claude-sonnet-4-20250514',
  'anthropic/claude-3.5-sonnet',
  'google/gemini-2.5-pro',
  'minimax/minimax-m2',
  'deepseek/deepseek-chat',
  'x-ai/grok-3',
];

const emptyForm: EmployeeFormData = {
  name: '',
  role: '',
  avatar_url: '',
  description: '',
  system_prompt: '',
  model: 'openai/gpt-4o',
  temperature: 0.7,
  max_tokens: 4096,
  tools: [],
  skills: [],
};

export function EmployeePanel({ open, onClose, employee, onSave, isSaving }: EmployeePanelProps) {
  const [form, setForm] = useState<EmployeeFormData>(emptyForm);
  const [activeTab, setActiveTab] = useState<'profile' | 'tools' | 'skills'>('profile');
  const [newSkill, setNewSkill] = useState({ skill_name: '', category: 'research', proficiency_level: 50, description: '' });
  const [availableTools, setAvailableTools] = useState<AvailableTool[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadTools() {
      setToolsLoading(true);
      setToolsError(null);
      try {
        const tools = await getToolsCatalog();
        if (!cancelled) {
          setAvailableTools(tools);
        }
      } catch (error) {
        if (!cancelled) {
          setToolsError(error instanceof Error ? error.message : 'Failed to load tools');
        }
      } finally {
        if (!cancelled) {
          setToolsLoading(false);
        }
      }
    }

    if (open) {
      loadTools();
    }

    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    if (employee) {
      setForm({
        name: employee.name || '',
        role: employee.role || '',
        avatar_url: employee.avatar_url || '',
        description: employee.description || '',
        system_prompt: employee.system_prompt || '',
        model: employee.model || 'openai/gpt-4o',
        temperature: employee.temperature ?? 0.7,
        max_tokens: employee.max_tokens ?? 4096,
        tools: employee.tools || [],
        skills: employee.skills || [],
      });
    } else {
      setForm(emptyForm);
    }
  }, [employee, open]);

  const updateField = <K extends keyof EmployeeFormData>(key: K, value: EmployeeFormData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const toggleTool = (toolName: string) => {
    setForm((prev) => ({
      ...prev,
      tools: prev.tools.includes(toolName)
        ? prev.tools.filter((t) => t !== toolName)
        : [...prev.tools, toolName],
    }));
  };

  const addSkill = () => {
    if (!newSkill.skill_name.trim()) return;
    setForm((prev) => ({
      ...prev,
      skills: [...prev.skills, { ...newSkill }],
    }));
    setNewSkill({ skill_name: '', category: 'research', proficiency_level: 50, description: '' });
  };

  const removeSkill = (index: number) => {
    setForm((prev) => ({
      ...prev,
      skills: prev.skills.filter((_, i) => i !== index),
    }));
  };

  const handleSave = async () => {
    await onSave(form);
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
          />

          {/* Slide Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            className="fixed right-0 top-0 z-50 h-full w-[80%] max-w-6xl bg-white shadow-2xl"
          >
            <div className="relative flex h-full flex-col overflow-hidden">
              {/* Panel Header */}
              <div className="flex items-center justify-between border-b border-zinc-200 px-6 py-4">
                <div>
                  <h2 className="text-lg font-semibold text-zinc-900">
                    {employee ? 'Edit Employee' : 'Create Employee'}
                  </h2>
                  <p className="text-sm text-zinc-500">
                    {employee ? 'Update persona, tools, and capabilities' : 'Define a new AI employee'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onClose}
                    className="gap-1.5 text-xs"
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSave}
                    disabled={isSaving || !form.name.trim()}
                    className="gap-1.5 text-xs bg-zinc-950 text-white hover:bg-zinc-800"
                  >
                    {isSaving ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Save className="h-3.5 w-3.5" />
                    )}
                    {isSaving ? 'Saving...' : 'Save Employee'}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                    className="h-8 w-8 p-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-zinc-200 px-6">
                {(['profile', 'tools', 'skills'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`border-b-2 px-4 py-2.5 text-sm font-medium capitalize transition-colors ${
                      activeTab === tab
                        ? 'border-zinc-950 text-zinc-950'
                        : 'border-transparent text-zinc-500 hover:text-zinc-700'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* Scrollable Content */}
              <div className="flex-1 overflow-y-auto px-6 py-5 pb-56">
                {activeTab === 'profile' && (
                  <div className="w-full max-w-none space-y-6 text-left">
                    {/* Name */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-zinc-700">
                        Name <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={form.name}
                        onChange={(e) => updateField('name', e.target.value)}
                        placeholder="e.g. Katy, Sam, Mira"
                        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950"
                      />
                    </div>

                    {/* Role */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-zinc-700">
                        Role <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={form.role}
                        onChange={(e) => updateField('role', e.target.value)}
                        placeholder="e.g. Product Manager, Data Analyst"
                        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950"
                      />
                    </div>

                    {/* Avatar URL */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-zinc-700">
                        Avatar URL
                      </label>
                      <input
                        type="text"
                        value={form.avatar_url}
                        onChange={(e) => updateField('avatar_url', e.target.value)}
                        placeholder="https://api.dicebear.com/7.x/avataaars/svg?seed=katy"
                        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950"
                      />
                    </div>

                    {/* Description */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-zinc-700">
                        Description
                      </label>
                      <textarea
                        value={form.description}
                        onChange={(e) => updateField('description', e.target.value)}
                        placeholder="Brief description of what this employee does..."
                        rows={3}
                        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950"
                      />
                    </div>

                    <Separator />

                    {/* Model */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-zinc-700">
                        LLM Model
                      </label>
                      <select
                        value={form.model}
                        onChange={(e) => updateField('model', e.target.value)}
                        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950"
                      >
                        {MODEL_OPTIONS.map((m) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    </div>

                    {/* Temperature & Max Tokens */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="mb-1.5 block text-sm font-medium text-zinc-700">
                          Temperature
                        </label>
                        <div className="flex items-center gap-3">
                          <input
                            type="range"
                            min="0"
                            max="2"
                            step="0.1"
                            value={form.temperature}
                            onChange={(e) => updateField('temperature', parseFloat(e.target.value))}
                            className="flex-1"
                          />
                          <span className="w-12 text-center text-sm font-mono text-zinc-700">
                            {form.temperature.toFixed(1)}
                          </span>
                        </div>
                      </div>
                      <div>
                        <label className="mb-1.5 block text-sm font-medium text-zinc-700">
                          Max Tokens
                        </label>
                        <input
                          type="number"
                          value={form.max_tokens}
                          onChange={(e) => updateField('max_tokens', parseInt(e.target.value, 10))}
                          min="256"
                          max="16384"
                          step="256"
                          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950"
                        />
                      </div>
                    </div>

                    <Separator />

                    {/* System Prompt */}
                    <div>
                      <div className="mb-1.5 flex items-center justify-between">
                        <label className="text-sm font-medium text-zinc-700">
                          System Prompt
                        </label>
                        <Badge variant="secondary" className="gap-1 text-[10px] bg-emerald-500/10 text-emerald-600">
                          <Sparkles className="h-3 w-3" />
                          Persona Definition
                        </Badge>
                      </div>
                      <textarea
                        value={form.system_prompt}
                        onChange={(e) => updateField('system_prompt', e.target.value)}
                        placeholder={`You are {name}, a {role}. Your responsibilities include...`}
                        rows={12}
                        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm font-mono text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950"
                      />
                      <p className="mt-1.5 text-[11px] text-zinc-400">
                        Define the persona, responsibilities, and behavior rules for this employee.
                      </p>
                    </div>
                  </div>
                )}

                {activeTab === 'tools' && (
                  <div className="w-full max-w-none space-y-4 text-left">
                    <p className="text-sm text-zinc-500">
                      Select which tools this employee can access. Tools give the employee the ability to interact with external systems.
                    </p>
                    {toolsError && (
                      <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                        {toolsError}
                      </div>
                    )}
                    {toolsLoading && (
                      <div className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-500">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading tools...
                      </div>
                    )}
                    <div className="grid gap-2">
                      {availableTools.map((tool) => {
                        const isSelected = form.tools.includes(tool.name);
                        return (
                          <button
                            key={tool.name}
                            type="button"
                            onClick={() => toggleTool(tool.name)}
                            className={`flex items-center justify-between rounded-lg border px-4 py-3 text-left transition-all ${
                              isSelected
                                ? 'border-zinc-950 bg-zinc-950/5'
                                : 'border-zinc-200 bg-white hover:bg-zinc-50'
                            }`}
                          >
                            <div>
                              <div className="flex items-center gap-2">
                                <div className="text-sm font-medium text-zinc-900">{tool.name}</div>
                                <Badge variant="secondary" className="text-[10px] capitalize">
                                  {tool.category.replace(/_/g, ' ')}
                                </Badge>
                              </div>
                              <div className="text-xs text-zinc-500">{tool.description}</div>
                            </div>
                            <Badge
                              variant="secondary"
                              className={`text-[10px] ${
                                isSelected ? 'bg-zinc-950 text-white' : 'bg-zinc-100 text-zinc-500'
                              }`}
                            >
                              {isSelected ? 'Enabled' : 'Disabled'}
                            </Badge>
                          </button>
                        );
                      })}
                    </div>
                    {!toolsLoading && !toolsError && availableTools.length === 0 && (
                      <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-500">
                        No tools available.
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'skills' && (
                  <div className="w-full max-w-none space-y-6 text-left">
                    <div>
                      <p className="text-sm text-zinc-500">
                        Skills represent high-level capabilities. They are shown on the dashboard and help categorize what the employee does.
                      </p>
                    </div>

                    {/* Add Skill Form */}
                    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 space-y-3">
                      <div className="flex items-center gap-2">
                        <Plus className="h-4 w-4 text-zinc-500" />
                        <span className="text-sm font-medium text-zinc-700">Add Skill</span>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <input
                          type="text"
                          value={newSkill.skill_name}
                          onChange={(e) => setNewSkill((p) => ({ ...p, skill_name: e.target.value }))}
                          placeholder="Skill name (e.g. Roadmapping)"
                          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950"
                        />
                        <select
                          value={newSkill.category}
                          onChange={(e) => setNewSkill((p) => ({ ...p, category: e.target.value }))}
                          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950"
                        >
                          {SKILL_CATEGORIES.map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-zinc-500">Proficiency</span>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="5"
                          value={newSkill.proficiency_level}
                          onChange={(e) => setNewSkill((p) => ({ ...p, proficiency_level: parseInt(e.target.value, 10) }))}
                          className="flex-1"
                        />
                        <span className="w-10 text-center text-sm font-mono text-zinc-700">
                          {newSkill.proficiency_level}%
                        </span>
                      </div>
                      <input
                        type="text"
                        value={newSkill.description}
                        onChange={(e) => setNewSkill((p) => ({ ...p, description: e.target.value }))}
                        placeholder="Brief description"
                        className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950"
                      />
                      <Button
                        size="sm"
                        onClick={addSkill}
                        disabled={!newSkill.skill_name.trim()}
                        className="gap-1.5 bg-zinc-950 text-white hover:bg-zinc-800"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        Add Skill
                      </Button>
                    </div>

                    {/* Skills List */}
                    {form.skills.length > 0 ? (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium text-zinc-700">Assigned Skills ({form.skills.length})</h4>
                        {form.skills.map((skill, index) => (
                          <div
                            key={index}
                            className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-4 py-3"
                          >
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-zinc-900">{skill.skill_name}</span>
                                <Badge variant="secondary" className="text-[10px] capitalize">
                                  {skill.category}
                                </Badge>
                              </div>
                              {skill.description && (
                                <div className="mt-0.5 text-xs text-zinc-500">{skill.description}</div>
                              )}
                              <div className="mt-2 h-1.5 w-full max-w-[200px] rounded-full bg-zinc-100">
                                <div
                                  className="h-full rounded-full bg-zinc-950 transition-all"
                                  style={{ width: `${skill.proficiency_level}%` }}
                                />
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => removeSkill(index)}
                              className="ml-3 rounded p-1 text-zinc-400 hover:bg-rose-50 hover:text-rose-500 transition-colors"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex flex-col items-start justify-center rounded-lg border-2 border-dashed border-zinc-200 py-12 pl-4 text-left">
                        <p className="text-sm text-zinc-400">No skills assigned yet</p>
                        <p className="mt-1 text-xs text-zinc-400">Add skills using the form above</p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 p-6">
                <div className="pointer-events-auto mx-auto w-full max-w-3xl">
                  <div className="relative rounded-xl border border-zinc-200 bg-white p-3 shadow-sm transition-colors focus-within:border-zinc-400">
                    <textarea
                      placeholder="Chat with this employee..."
                      disabled
                      rows={2}
                      className="min-h-[52px] w-full resize-none border-none bg-transparent py-1 text-sm text-[#37352f] outline-none placeholder:text-zinc-400 disabled:cursor-not-allowed disabled:opacity-100"
                    />
                    <div className="mt-2 flex items-center justify-between border-t border-zinc-100 pt-2">
                      <div className="flex items-center gap-1">
                        <span className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
                          Chat panel
                        </span>
                        <Button variant="ghost" size="icon" disabled className="h-8 w-8 text-zinc-400">
                          <Paperclip className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" disabled className="h-8 w-8 text-zinc-400">
                          <Mic className="h-4 w-4" />
                        </Button>
                      </div>
                      <Button
                        size="icon"
                        disabled
                        className="h-8 w-8 rounded-lg bg-zinc-900 text-white hover:bg-zinc-900 disabled:opacity-100"
                      >
                        <Send className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
