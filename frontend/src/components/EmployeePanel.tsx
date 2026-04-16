import React, { useState, useEffect, useCallback } from 'react';
import { X, Plus, Trash2, Save, Loader2, Sparkles, Paperclip, Mic, Send, BookOpen, FileText } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getModelsCatalog, getToolsCatalog, EmployeeModelOption, getAvailableProviders, ProviderInfo } from '@/src/api/employees';
import { ModelSelect } from '@/src/components/ModelSelect';
import { FileTree } from '@/src/components/FileTree';
import { ScrollArea } from '@/components/ui/scroll-area';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { listPublicSkills, type PublicSkillListItem, getPublicSkillDetail, type PublicSkillDetail, getMarkdownTree, type MarkdownTreeNode } from '@/lib/api';

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
  memory: string[];
}

interface AvailableTool {
  name: string;
  runtime_name?: string;
  description: string;
  category: string;
}

export interface FileItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  children?: FileItem[];
}

export function mapMarkdownNodesToFileItems(nodes: MarkdownTreeNode[]): FileItem[] {
  return nodes.map((node) => ({
    id: node.path,
    name: node.name,
    type: node.type,
    children: node.children ? mapMarkdownNodesToFileItems(node.children) : undefined,
  }));
}

const SKILL_CATEGORIES = ['research', 'coding', 'devops', 'analytics', 'communication', 'product', 'design', 'sales', 'finance'];

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
  memory: [],
};

export function EmployeePanel({ open, onClose, employee, onSave, isSaving }: EmployeePanelProps) {
  const [form, setForm] = useState<EmployeeFormData>(emptyForm);
  const [activeTab, setActiveTab] = useState<'profile' | 'tools' | 'skills'>('profile');
  const [newSkill, setNewSkill] = useState({ skill_name: '', category: 'research', description: '' });
  const [availableTools, setAvailableTools] = useState<AvailableTool[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState<string | null>(null);
  const [availableModels, setAvailableModels] = useState<EmployeeModelOption[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>('openrouter');
  const [availableProviders, setAvailableProviders] = useState<ProviderInfo[]>([]);
  const [providersLoading, setProvidersLoading] = useState(false);
  const [publicSkills, setPublicSkills] = useState<PublicSkillListItem[]>([]);
  const [publicSkillsLoading, setPublicSkillsLoading] = useState(false);
  const [selectedSkillSlug, setSelectedSkillSlug] = useState<string | null>(null);
  const [selectedSkillDetail, setSelectedSkillDetail] = useState<PublicSkillDetail | null>(null);
  const [availableSkillSlugs, setAvailableSkillSlugs] = useState<string[]>([]);
  const [agentFiles, setAgentFiles] = useState<FileItem[]>([]);

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

    async function loadModels() {
      setModelsLoading(true);
      setModelsError(null);
      try {
        const models = await getModelsCatalog(selectedProvider);
        if (!cancelled) {
          setAvailableModels(models);
        }
      } catch (error) {
        if (!cancelled) {
          setModelsError(error instanceof Error ? error.message : 'Failed to load models');
        }
      } finally {
        if (!cancelled) {
          setModelsLoading(false);
        }
      }
    }

    async function loadProviders() {
      setProvidersLoading(true);
      try {
        const providers = await getAvailableProviders();
        if (!cancelled) {
          setAvailableProviders(providers);
          // Auto-select first available provider
          const available = providers.find(p => p.available);
          if (available && !cancelled) {
            setSelectedProvider(available.id);
          }
        }
      } catch (error) {
        console.error('Failed to load providers:', error);
      } finally {
        if (!cancelled) {
          setProvidersLoading(false);
        }
      }
    }

    if (open) {
      loadTools();
      loadProviders();
      loadModels();

      // Load public skills for the dropdown
      setPublicSkillsLoading(true);
      listPublicSkills()
        .then((skills) => {
          if (!cancelled) {
            setPublicSkills(skills);
          }
        })
        .catch(() => {})
        .finally(() => {
          if (!cancelled) setPublicSkillsLoading(false);
        });
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
        memory: employee.memory || [],
      });
      
      // Detect provider from saved model name
      if (employee.model) {
        const modelPrefix = employee.model.split('/')[0].toLowerCase();
        if (['minimaxai', 'meta'].includes(modelPrefix)) {
          setSelectedProvider('nvidia');
        } else {
          setSelectedProvider('openrouter');
        }
      }
    } else {
      setForm(emptyForm);
      setSelectedProvider('openrouter');
    }
  }, [employee, open]);

  // Reload models when provider changes
  useEffect(() => {
    if (open) {
      setModelsLoading(true);
      setModelsError(null);
      getModelsCatalog(selectedProvider)
        .then((models) => setAvailableModels(models))
        .catch((error) => setModelsError(error instanceof Error ? error.message : 'Failed to load models'))
        .finally(() => setModelsLoading(false));
    }
  }, [selectedProvider, open]);

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
    setNewSkill({ skill_name: '', category: 'research', description: '' });
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

  const modelOptions = availableModels.some((model) => model.id === form.model)
    ? availableModels
    : [{ id: form.model, name: form.model, description: 'Currently selected model', context_length: 0 }, ...availableModels];

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
            className="fixed inset-0 z-40 bg-background/30 backdrop-blur-sm"
          />

          {/* Slide Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            className="fixed right-0 top-0 z-50 h-full w-[80%] max-w-6xl bg-card shadow-2xl"
          >
            <div className="relative flex h-full flex-col overflow-hidden">
              {/* Panel Header */}
              <div className="flex items-center justify-between border-b border-border px-6 py-4">
                <div>
                  <h2 className="text-lg font-semibold text-foreground">
                    {employee ? 'Edit Employee' : 'Create Employee'}
                  </h2>
                  <p className="text-sm text-muted-foreground">
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
              <div className="flex border-b border-border px-6">
                {(['profile', 'tools', 'skills', 'memory'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`border-b-2 px-4 py-2.5 text-sm font-medium capitalize transition-colors ${
                      activeTab === tab
                        ? 'border-primary text-foreground'
                        : 'border-transparent text-muted-foreground hover:text-foreground'
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
                      <label className="mb-1.5 block text-sm font-medium text-foreground">
                        Name <span className="text-destructive">*</span>
                      </label>
                      <input
                        type="text"
                        value={form.name}
                        onChange={(e) => updateField('name', e.target.value)}
                        placeholder="e.g. Katy, Sam, Mira"
                        className="w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                    </div>

                    {/* Role */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-foreground">
                        Role <span className="text-destructive">*</span>
                      </label>
                      <input
                        type="text"
                        value={form.role}
                        onChange={(e) => updateField('role', e.target.value)}
                        placeholder="e.g. Product Manager, Data Analyst"
                        className="w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                    </div>

                    {/* Avatar URL */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-foreground">
                        Avatar URL
                      </label>
                      <input
                        type="text"
                        value={form.avatar_url}
                        onChange={(e) => updateField('avatar_url', e.target.value)}
                        placeholder="https://api.dicebear.com/7.x/avataaars/svg?seed=katy"
                        className="w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                    </div>

                    {/* Description */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-foreground">
                        Description
                      </label>
                      <textarea
                        value={form.description}
                        onChange={(e) => updateField('description', e.target.value)}
                        placeholder="Brief description of what this employee does..."
                        rows={3}
                        className="w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                    </div>

                    <Separator />

                    {/* Model */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-foreground">
                        LLM Model
                      </label>
                      <ModelSelect
                        value={form.model}
                        onChange={(value) => updateField('model', value)}
                        models={modelOptions}
                        loading={modelsLoading}
                        error={modelsError}
                        provider={selectedProvider}
                        onProviderChange={(provider) => {
                          setSelectedProvider(provider);
                          // Clear current model when switching providers
                          updateField('model', '');
                        }}
                        availableProviders={availableProviders}
                      />
                      {modelsLoading && (
                        <p className="mt-1.5 text-[11px] text-muted-foreground">Loading models...</p>
                      )}
                    </div>

                    {/* Temperature & Max Tokens */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="mb-1.5 block text-sm font-medium text-foreground">
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
                          <span className="w-12 text-center text-sm font-mono text-foreground">
                            {form.temperature.toFixed(1)}
                          </span>
                        </div>
                      </div>
                      <div>
                        <label className="mb-1.5 block text-sm font-medium text-foreground">
                          Max Tokens
                        </label>
                        <input
                          type="number"
                          value={form.max_tokens}
                          onChange={(e) => updateField('max_tokens', parseInt(e.target.value, 10))}
                          min="256"
                          max="16384"
                          step="256"
                          className="w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
                        />
                      </div>
                    </div>

                    <Separator />

                    {/* System Prompt */}
                    <div>
                      <div className="mb-1.5 flex items-center justify-between">
                        <label className="text-sm font-medium text-foreground">
                          System Prompt
                        </label>
                        <Badge variant="secondary" className="gap-1 text-[10px] bg-emerald-500/10 text-emerald-400">
                          <Sparkles className="h-3 w-3" />
                          Persona Definition
                        </Badge>
                      </div>
                      <textarea
                        value={form.system_prompt}
                        onChange={(e) => updateField('system_prompt', e.target.value)}
                        placeholder={`You are {name}, a {role}. Your responsibilities include...`}
                        rows={12}
                        className="w-full rounded-lg border border-border px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
                      />
                      <p className="mt-1.5 text-[11px] text-muted-foreground">
                        Define the persona, responsibilities, and behavior rules for this employee.
                      </p>
                    </div>
                  </div>
                )}

                {activeTab === 'tools' && (
                  <div className="w-full max-w-none space-y-4 text-left">
                    <p className="text-sm text-muted-foreground">
                      Select which tools this employee can access. Tools give the employee the ability to interact with external systems.
                    </p>
                    {toolsError && (
                      <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                        {toolsError}
                      </div>
                    )}
                    {toolsLoading && (
                      <div className="flex items-center gap-2 rounded-lg border border-border bg-muted px-4 py-3 text-sm text-muted-foreground">
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
                                ? 'border-primary bg-primary/5'
                                : 'border-border bg-card hover:bg-muted'
                            }`}
                          >
                            <div>
                              <div className="flex items-center gap-2">
                                <div className="text-sm font-medium text-foreground">{tool.name}</div>
                                <Badge variant="secondary" className="text-[10px] capitalize">
                                  {tool.category.replace(/_/g, ' ')}
                                </Badge>
                              </div>
                              <div className="text-xs text-muted-foreground">{tool.description}</div>
                            </div>
                            <Badge
                              variant="secondary"
                              className={`text-[10px] ${
                                isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                              }`}
                            >
                              {isSelected ? 'Enabled' : 'Disabled'}
                            </Badge>
                          </button>
                        );
                      })}
                    </div>
                    {!toolsLoading && !toolsError && availableTools.length === 0 && (
                      <div className="rounded-lg border border-border bg-muted px-4 py-3 text-sm text-muted-foreground">
                        No tools available.
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'skills' && (
                  <div className="w-full max-w-none space-y-6 text-left">
                    <div>
                      <p className="text-sm text-muted-foreground">
                        Skills represent high-level capabilities assigned from the public skills library. They are shown on the dashboard and help categorize what the employee does.
                      </p>
                    </div>

                    {/* Add Skill from Public Library */}
                    <div className="rounded-lg border border-border bg-muted p-4 space-y-3">
                      <div className="flex items-center gap-2">
                        <Plus className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium text-foreground">Add Skill from Library</span>
                      </div>
                      {publicSkillsLoading ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Loading public skills...
                        </div>
                      ) : (
                        <>
                          <Select
                            value={newSkill.skill_name}
                            onValueChange={(value) => {
                              const skill = publicSkills.find((s) => s.slug === value);
                              if (skill) {
                                setNewSkill({
                                  skill_name: skill.slug,
                                  category: skill.category,
                                  description: skill.description,
                                });
                              }
                            }}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select a public skill..." />
                            </SelectTrigger>
                            <SelectContent className="w-auto min-w-[320px]">
                              {publicSkills
                                .filter((s) => !form.skills.some((fs) => fs.skill_name === s.slug))
                                .map((s) => (
                                  <SelectItem key={s.slug} value={s.slug}>
                                    {s.title} — {s.category}
                                  </SelectItem>
                                ))}
                            </SelectContent>
                          </Select>
                          {newSkill.skill_name && (
                            <div className="text-xs text-muted-foreground">{newSkill.description}</div>
                          )}
                          <Button
                            size="sm"
                            onClick={addSkill}
                            disabled={!newSkill.skill_name.trim()}
                            className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/80"
                          >
                            <Plus className="h-3.5 w-3.5" />
                            Add Skill
                          </Button>
                        </>
                      )}
                    </div>

                    {/* Skills List */}
                    {form.skills.length > 0 ? (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium text-foreground">Assigned Skills ({form.skills.length})</h4>
                        {form.skills.map((skill, index) => (
                          <div
                            key={index}
                            className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3"
                          >
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedSkillSlug(skill.skill_name);
                                setSelectedSkillDetail(null);
                                getPublicSkillDetail(skill.skill_name)
                                  .then((d) => setSelectedSkillDetail(d))
                                  .catch(() => {});
                              }}
                              className="flex flex-1 items-center gap-2 text-left"
                            >
                              <BookOpen className="h-4 w-4 text-muted-foreground" />
                              <span className="text-sm font-medium text-foreground">{skill.skill_name}</span>
                              <Badge variant="secondary" className="text-[10px] capitalize">
                                {skill.category}
                              </Badge>
                            </button>
                            <button
                              type="button"
                              onClick={() => removeSkill(index)}
                              className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex flex-col items-start justify-center rounded-lg border-2 border-border border-border py-12 pl-4 text-left">
                        <p className="text-sm text-muted-foreground">No skills assigned yet</p>
                        <p className="mt-1 text-xs text-muted-foreground">Add skills from the public library above</p>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'memory' && (
                  <div className="w-full max-w-none space-y-6 text-left">
                    <div className="space-y-1">
                      <h3 className="text-lg font-medium text-foreground">Memory Files</h3>
                      <p className="text-sm text-muted-foreground">
                        Select files and folders to index into this employee's memory.
                      </p>
                    </div>

                    <div className="border border-border/60 rounded-2xl bg-background overflow-hidden shadow-sm">
                      <div className="p-4 border-b border-border bg-muted/30 flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Agent Files Browser</span>
                        <Badge variant="secondary" className="bg-primary/10 text-primary border-none">{form.memory.length} Selected</Badge>
                      </div>
                      <ScrollArea className="h-[400px] p-4">
                        <FileTree
                          items={agentFiles}
                          selectedFiles={form.memory}
                          onToggle={toggleFile}
                        />
                      </ScrollArea>
                    </div>

                    {form.memory.length > 0 && (
                      <div className="mt-6 p-4 rounded-xl border border-primary/20 bg-primary/5">
                        <label className="text-xs font-bold uppercase tracking-widest text-primary mb-2 block">Attached to Memory</label>
                        <div className="flex flex-wrap gap-2">
                          {form.memory.map((fid) => (
                            <Badge key={fid} variant="secondary" className="gap-1.5 px-2 py-1 bg-background border-border text-foreground">
                              <FileText className="w-3 h-3 text-muted-foreground" />
                              {fid.split('/').pop() || fid}
                              <button type="button" onClick={() => toggleFile(fid)} className="hover:text-destructive text-muted-foreground transition-colors ml-1">
                                <X className="w-3 h-3" />
                              </button>
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 p-6">
                <div className="pointer-events-auto mx-auto w-full max-w-3xl">
                  <div className="relative rounded-xl border border-border bg-card p-3 shadow-sm transition-colors focus-within:border-ring">
                    <textarea
                      placeholder="Chat with this employee..."
                      disabled
                      rows={2}
                      className="min-h-[52px] w-full resize-none border-none bg-transparent py-1 text-sm text-foreground outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-100"
                    />
                    <div className="mt-2 flex items-center justify-between border-t border-border pt-2">
                      <div className="flex items-center gap-1">
                        <span className="rounded-md border border-border bg-muted px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                          Chat panel
                        </span>
                        <Button variant="ghost" size="icon" disabled className="h-8 w-8 text-muted-foreground">
                          <Paperclip className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" disabled className="h-8 w-8 text-muted-foreground">
                          <Mic className="h-4 w-4" />
                        </Button>
                      </div>
                      <Button
                        size="icon"
                        disabled
                        className="h-8 w-8 rounded-lg bg-primary text-primary-foreground hover:bg-primary disabled:opacity-100"
                      >
                        <Send className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Skill Detail Sidebar */}
          <AnimatePresence>
            {selectedSkillSlug && (() => {
              const ps = publicSkills.find((s) => s.slug === selectedSkillSlug);
              const assignedSkill = form.skills.find((s) => s.skill_name === selectedSkillSlug);
              if (!ps && !assignedSkill) return null;

              return (
                <>
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => { setSelectedSkillSlug(null); setSelectedSkillDetail(null); }}
                    className="fixed inset-0 z-[55] bg-background/20 backdrop-blur-[1px]"
                  />
                  <motion.div
                    initial={{ x: 32, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 32, opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 340, damping: 30 }}
                    className="fixed inset-y-4 right-4 z-[60] w-[min(480px,calc(100vw-2rem))] rounded-2xl border border-border bg-card shadow-2xl"
                  >
                    <div className="flex h-full min-h-0 flex-col">
                      <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-5">
                        <div className="min-w-0">
                          <div className="truncate text-[14px] font-semibold text-foreground">
                            {ps?.title || assignedSkill?.skill_name}
                          </div>
                          <div className="text-[12px] text-muted-foreground">{ps?.category || assignedSkill?.category}</div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => { setSelectedSkillSlug(null); setSelectedSkillDetail(null); }}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>

                      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
                        <div className="space-y-6">
                          <section className="space-y-3">
                            <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Overview</div>
                            <div className="rounded-xl border border-border bg-muted p-4 text-[14px] leading-6 text-foreground">
                              {ps?.description || assignedSkill?.description}
                            </div>
                          </section>

                          {selectedSkillDetail?.skill_markdown ? (
                            <section>
                              <div className="mb-3 text-[12px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">SKILL.md</div>
                              <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                                h1: (p) => <h1 className="text-[20px] font-semibold text-foreground mb-3 mt-4 first:mt-0" {...p} />,
                                h2: (p) => <h2 className="text-[16px] font-semibold text-foreground mb-2 mt-4" {...p} />,
                                h3: (p) => <h3 className="text-[14px] font-semibold text-foreground mb-2 mt-3" {...p} />,
                                p: (p) => <p className="mb-3 text-[13px] leading-6 text-foreground" {...p} />,
                                ul: (p) => <ul className="mb-3 list-disc pl-5 text-[13px] leading-6 text-foreground space-y-1" {...p} />,
                                ol: (p) => <ol className="mb-3 list-decimal pl-5 text-[13px] leading-6 text-foreground space-y-1" {...p} />,
                                li: (p) => <li className="pl-1" {...p} />,
                                code: (p) => <code className="rounded bg-muted px-1 py-0.5 text-[12px] text-foreground" {...p} />,
                                pre: (p) => <pre className="mb-3 overflow-x-auto rounded-lg border border-border bg-muted p-3 text-[12px]" {...p} />,
                                strong: (p) => <strong className="font-semibold text-foreground" {...p} />,
                                hr: () => null,
                              }}>
                                {selectedSkillDetail.skill_markdown}
                              </ReactMarkdown>
                            </section>
                          ) : null}

                          {ps && (
                            <section className="space-y-3">
                              <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Suggested Tools</div>
                              <div className="flex flex-wrap gap-2">
                                {ps.suggested_tools.length > 0 ? ps.suggested_tools.map((tool) => (
                                  <span key={tool} className="rounded-full border border-border bg-muted px-2.5 py-1 text-[12px] text-foreground">
                                    {tool}
                                  </span>
                                )) : (
                                  <span className="text-[14px] text-muted-foreground">No suggested tools</span>
                                )}
                              </div>
                            </section>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </>
              );
            })()}
          </AnimatePresence>
        </>
      )}
    </AnimatePresence>
  );
}
