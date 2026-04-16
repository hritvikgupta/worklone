import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2, Save, Loader2, Sparkles, Paperclip, Mic, Send, BookOpen, Check, Search, FileText } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { getModelsCatalog, getToolsCatalog, EmployeeModelOption, getAvailableProviders, ProviderInfo } from '@/src/api/employees';
import { ModelSelect } from '@/src/components/ModelSelect';
import { FileTree } from '@/src/components/FileTree';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { EmployeeFormData } from '@/src/components/EmployeePanel';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { listPublicSkills, type PublicSkillListItem, getPublicSkillDetail, type PublicSkillDetail, getMarkdownTree, type MarkdownTreeNode } from '@/lib/api';

interface EmployeeConfigPanelProps {
  open: boolean;
  onClose: () => void;
  employee: EmployeeFormData | null;
  onSave: (data: EmployeeFormData) => Promise<void>;
  isSaving?: boolean;
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

export function EmployeeConfigPanel({
  open,
  onClose,
  employee,
  onSave,
  isSaving,
}: EmployeeConfigPanelProps) {
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
  const [toolSearch, setToolSearch] = useState('');
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
      setPublicSkillsLoading(true);
      listPublicSkills()
        .then((skills) => { if (!cancelled) setPublicSkills(skills); })
        .catch(() => {})
        .finally(() => { if (!cancelled) setPublicSkillsLoading(false); });
      
      getMarkdownTree('agent')
        .then((treeData) => { if (!cancelled) setAgentFiles(mapMarkdownNodesToFileItems(treeData)); })
        .catch(() => {});
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

  const toggleFile = (id: string) => {
    setForm((prev) => ({
      ...prev,
      memory: prev.memory.includes(id)
        ? prev.memory.filter((fid) => fid !== id)
        : [...prev.memory, id],
    }));
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

  const modelOptions = availableModels.some((model) => model.id === form.model)
    ? availableModels
    : [{ id: form.model, name: form.model, description: 'Currently selected model', context_length: 0 }, ...availableModels];

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end p-4 sm:p-6 lg:p-8">
          {/* Backdrop with dotted grid */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            style={{
              backgroundImage: 'radial-gradient(circle, var(--border) 1px, transparent 1px)',
              backgroundSize: '24px 24px'
            }}
            onClick={onClose}
          />

          {/* Floating Slide-over Panel (Right Aligned) */}
          <motion.div
            initial={{ opacity: 0, x: 50, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 50, scale: 0.98 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="relative w-full max-w-lg h-full bg-background rounded-2xl border border-border shadow-2xl flex flex-col overflow-hidden"
          >
            {/* Header / Tabs Area */}
            <div className="flex items-center justify-between p-4 border-b border-border bg-background">
              <div className="flex items-center gap-4">
                <div className="flex items-center bg-muted/50 p-1 rounded-full border border-border/50">
                  {(['profile', 'tools', 'skills', 'memory'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={cn(
                        "px-4 py-1.5 text-sm font-medium rounded-full transition-all capitalize",
                        activeTab === tab 
                          ? "bg-background text-foreground shadow-sm" 
                          : "text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {tab}
                    </button>
                  ))}
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground hover:text-foreground"
                onClick={onClose}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto bg-muted/20">
              <div className="p-6">
                {activeTab === 'profile' && (
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-muted-foreground">Name</Label>
                      <input
                        type="text"
                        value={form.name}
                        onChange={(e) => updateField('name', e.target.value)}
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring h-11 shadow-sm"
                        placeholder="Employee name"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-muted-foreground">Role</Label>
                      <input
                        type="text"
                        value={form.role}
                        onChange={(e) => updateField('role', e.target.value)}
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring h-11 shadow-sm"
                        placeholder="e.g. Senior Backend Engineer"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-muted-foreground">Avatar URL</Label>
                      <input
                        type="text"
                        value={form.avatar_url}
                        onChange={(e) => updateField('avatar_url', e.target.value)}
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring h-11 shadow-sm"
                        placeholder="https://..."
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-muted-foreground">Description</Label>
                      <textarea
                        value={form.description}
                        onChange={(e) => updateField('description', e.target.value)}
                        rows={3}
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring resize-none shadow-sm"
                        placeholder="A brief bio or description"
                      />
                    </div>

                    <Separator className="bg-border/50" />

                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-muted-foreground">LLM Model</Label>
                      <ModelSelect
                        value={form.model}
                        onChange={(value) => updateField('model', value)}
                        models={modelOptions}
                        loading={modelsLoading}
                        error={modelsError}
                        provider={selectedProvider}
                        onProviderChange={(provider) => {
                          setSelectedProvider(provider);
                          updateField('model', '');
                        }}
                        availableProviders={availableProviders}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label className="text-sm font-medium text-muted-foreground">Temperature</Label>
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
                          <span className="w-10 text-right text-xs font-mono text-foreground">
                            {form.temperature.toFixed(1)}
                          </span>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label className="text-sm font-medium text-muted-foreground">Max Tokens</Label>
                        <input
                          type="number"
                          value={form.max_tokens}
                          onChange={(e) => updateField('max_tokens', parseInt(e.target.value, 10))}
                          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring h-10 shadow-sm"
                        />
                      </div>
                    </div>

                    <Separator className="bg-border/50" />

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm font-medium text-muted-foreground">System Prompt</Label>
                        <Badge variant="outline" className="text-[10px] bg-emerald-500/5 text-emerald-600 border-emerald-500/20">
                          Persona Definition
                        </Badge>
                      </div>
                      <textarea
                        value={form.system_prompt}
                        onChange={(e) => updateField('system_prompt', e.target.value)}
                        rows={12}
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring shadow-sm"
                        placeholder="Define the employee's instructions..."
                      />
                    </div>
                  </div>
                )}

                {activeTab === 'tools' && (
                  <div className="space-y-4">
                    <div className="flex flex-col gap-3">
                      <p className="text-xs text-muted-foreground">Configure the capabilities and tools accessible to this employee.</p>
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <input
                          type="text"
                          placeholder="Search tools..."
                          value={toolSearch}
                          onChange={(e) => setToolSearch(e.target.value)}
                          className="w-full rounded-lg border border-border bg-background pl-9 pr-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring h-10 shadow-sm"
                        />
                      </div>
                    </div>

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
                      {availableTools
                        .filter((tool) => 
                          tool.name.toLowerCase().includes(toolSearch.toLowerCase()) ||
                          tool.description.toLowerCase().includes(toolSearch.toLowerCase()) ||
                          tool.category.toLowerCase().includes(toolSearch.toLowerCase())
                        )
                        .map((tool) => {
                        const isSelected = form.tools.includes(tool.name);
                        return (
                          <button
                            key={tool.name}
                            type="button"
                            onClick={() => toggleTool(tool.name)}
                            className={cn(
                              "flex flex-col gap-1 rounded-xl border p-4 text-left transition-all",
                              isSelected 
                                ? "border-primary bg-primary/5 shadow-sm" 
                                : "border-border/60 bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground"
                            )}
                          >
                            <div className="flex items-center justify-between">
                              <div className="text-sm font-semibold text-foreground">{tool.name}</div>
                              {isSelected && <Check className="h-4 w-4 text-primary" />}
                            </div>
                            <div className="text-xs leading-relaxed opacity-70">{tool.description}</div>
                            <div className="mt-2 flex items-center gap-2">
                              <Badge variant="outline" className="text-[9px] uppercase tracking-wider px-1.5 py-0">
                                {tool.category.replace(/_/g, ' ')}
                              </Badge>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {activeTab === 'skills' && (
                  <div className="space-y-6">
                    <Card className="border-border/60 shadow-sm overflow-hidden">
                      <CardHeader className="bg-muted/30 pb-3">
                        <div className="flex items-center gap-2">
                          <Plus className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm font-bold uppercase tracking-wider text-foreground">Add Skill from Library</span>
                        </div>
                      </CardHeader>
                      <CardContent className="p-4 space-y-4">
                        {publicSkillsLoading ? (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Loading public skills...
                          </div>
                        ) : (
                          <>
                            <div className="space-y-2">
                              <Label className="text-xs font-medium text-muted-foreground">Select a public skill</Label>
                              <Select
                                value={newSkill.skill_name}
                                onValueChange={(value) => {
                                  const skill = publicSkills.find((s) => s.slug === value);
                                  if (skill) setNewSkill({ skill_name: skill.slug, category: skill.category, description: skill.description });
                                }}
                              >
                                <SelectTrigger className="h-10 bg-background">
                                  <SelectValue placeholder="Select a public skill..." />
                                </SelectTrigger>
                                <SelectContent>
                                  {publicSkills.filter((s) => !form.skills.some((fs) => fs.skill_name === s.slug)).map((s) => (
                                    <SelectItem key={s.slug} value={s.slug}>
                                      <div className="flex flex-col gap-0.5">
                                        <span className="font-medium">{s.title}</span>
                                        <span className="text-[10px] text-muted-foreground uppercase">{s.category}</span>
                                      </div>
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            {newSkill.skill_name && (
                              <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground leading-relaxed italic">
                                {newSkill.description}
                              </div>
                            )}
                            <Button 
                              size="sm" 
                              onClick={addSkill} 
                              disabled={!newSkill.skill_name.trim()} 
                              className="w-full h-9 gap-2"
                            >
                              <Plus className="h-4 w-4" />
                              Attach to Employee
                            </Button>
                          </>
                        )}
                      </CardContent>
                    </Card>

                    <div className="space-y-3">
                      <Label className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
                        Assigned Skills ({form.skills.length})
                      </Label>
                      {form.skills.length > 0 ? (
                        <div className="space-y-2">
                          {form.skills.map((skill, index) => (
                            <div 
                              key={index} 
                              className="flex items-center justify-between rounded-xl border border-border/60 bg-background p-3 shadow-sm hover:border-primary/30 transition-all"
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
                                className="flex flex-1 items-center gap-3 text-left min-w-0"
                              >
                                <div className="h-8 w-8 rounded-lg bg-primary/5 flex items-center justify-center shrink-0">
                                  <BookOpen className="h-4 w-4 text-primary" />
                                </div>
                                <div className="min-w-0">
                                  <p className="text-sm font-semibold text-foreground truncate">{skill.skill_name}</p>
                                  <Badge variant="outline" className="text-[9px] uppercase tracking-wider h-4 px-1 border-none bg-muted text-muted-foreground">
                                    {skill.category}
                                  </Badge>
                                </div>
                              </button>
                              <Button 
                                variant="ghost" 
                                size="icon" 
                                onClick={() => removeSkill(index)} 
                                className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 py-10 bg-background/50">
                          <p className="text-xs text-muted-foreground">No skills assigned yet</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {activeTab === 'memory' && (
                  <div className="space-y-6 text-left">
                    <Card className="border-border/60 shadow-sm overflow-hidden">
                      <CardHeader className="bg-muted/30 pb-3">
                        <div className="flex items-center gap-2">
                          <Paperclip className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm font-bold uppercase tracking-wider text-foreground">Memory Files</span>
                        </div>
                      </CardHeader>
                      <CardContent className="p-4 space-y-4">
                        <p className="text-xs text-muted-foreground">
                          Select files and folders to index into this employee's memory.
                        </p>
                      </CardContent>
                    </Card>

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
                        <Label className="text-xs font-bold uppercase tracking-widest text-primary mb-2 block">Attached to Memory</Label>
                        <div className="flex flex-wrap gap-2">
                          {form.memory.map((fid) => (
                            <Badge key={fid} variant="secondary" className="gap-1.5 px-2 py-1 bg-background border-border">
                              <FileText className="w-3 h-3 text-muted-foreground" />
                              {fid.split('/').pop() || fid}
                              <button type="button" onClick={() => toggleFile(fid)} className="hover:text-destructive">
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
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-border bg-background flex items-center justify-end gap-3 shadow-[0_-4px_10px_-5px_rgba(0,0,0,0.05)]">
              <Button variant="outline" onClick={onClose} disabled={isSaving}>
                Cancel
              </Button>
              <Button
                onClick={() => onSave(form)}
                disabled={isSaving || !form.name.trim()}
                className="gap-2 px-6"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </motion.div>

          <AnimatePresence>
            {selectedSkillSlug && (() => {
              const ps = publicSkills.find((s) => s.slug === selectedSkillSlug);
              const assignedSkill = form.skills.find((s) => s.skill_name === selectedSkillSlug);
              if (!ps && !assignedSkill) return null;
              return (
                <>
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    onClick={() => { setSelectedSkillSlug(null); setSelectedSkillDetail(null); }} className="fixed inset-0 z-[55] bg-background/20 backdrop-blur-[1px]" />
                  <motion.div initial={{ x: 32, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 32, opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 340, damping: 30 }}
                    className="fixed inset-y-4 right-4 z-[60] w-[min(480px,calc(100vw-2rem))] rounded-2xl border border-border bg-card shadow-2xl">
                    <div className="flex h-full min-h-0 flex-col">
                      <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-5">
                        <div className="min-w-0">
                          <div className="truncate text-[14px] font-semibold text-foreground">{ps?.title || assignedSkill?.skill_name}</div>
                          <div className="text-[12px] text-muted-foreground">{ps?.category || assignedSkill?.category}</div>
                        </div>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => { setSelectedSkillSlug(null); setSelectedSkillDetail(null); }}>
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
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </>
              );
            })()}
          </AnimatePresence>
        </div>
      )}
    </AnimatePresence>
  );
}
