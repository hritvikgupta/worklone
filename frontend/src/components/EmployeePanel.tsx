import React, { useState, useEffect, useCallback } from 'react';
import { X, Plus, Trash2, Save, Loader2, Sparkles, Paperclip, Mic, Send, BookOpen, FileText, Check, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item';
import { cn } from '@/lib/utils';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getToolsCatalog, EmployeeModelOption, ProviderInfo } from '@/src/api/employees';
import { listLLMProviders, fetchModelsForProvider } from '@/src/api/settings';
import { ModelSelect } from '@/src/components/ModelSelect';
import { FileTree } from '@/src/components/FileTree';
import { ScrollArea } from '@/components/ui/scroll-area';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { listPublicSkills, type PublicSkillListItem, getPublicSkillDetail, type PublicSkillDetail, getMarkdownTree, type MarkdownTreeNode } from '@/lib/api';
import { getIntegrations, getOAuthUrl, type IntegrationStatus } from '@/lib/auth-api';
import { IntegrationIcon, resolveIntegrationIdFromTool } from '@/src/components/IntegrationIcon';
import { useAuth } from '../contexts/AuthContext';

interface EmployeePanelProps {
  open: boolean;
  onClose: () => void;
  employee?: EmployeeFormData | null;
  onSave: (data: EmployeeFormData) => Promise<void>;
  isSaving?: boolean;
  mode?: 'modal' | 'inline';
}

export interface EmployeeFormData {
  name: string;
  role: string;
  avatar_url: string;
  cover_url?: string;
  description: string;
  system_prompt: string;
  model: string;
  provider: string;
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

function toToolDisplayName(rawName: string): string {
  const withoutSuffix = rawName.replace(/tool$/i, "");
  const spaced = withoutSuffix
    .replace(/_/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .trim();
  if (!spaced) return rawName;
  return spaced
    .split(/\s+/)
    .map((w) => (w.length === 0 ? w : w[0].toUpperCase() + w.slice(1).toLowerCase()))
    .join(" ");
}

function ToolIcon({ tool, label }: { tool: AvailableTool; label: string }) {
  const providerId = resolveIntegrationIdFromTool(tool);
  return (
    <IntegrationIcon id={providerId} name={label} className="h-8 w-8" />
  );
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
const AVATAR_URL_OPTIONS = [
  '/employees/men_1.png',
  '/employees/men_2.png',
  '/employees/men_3.png',
  '/employees/men_4.png',
  '/employees/men_5.png',
  '/employees/men_6.png',
  '/employees/men_7.png',
  '/employees/women_1.png',
  '/employees/women_2.png',
  '/employees/women_3.png',
  '/employees/women_4.png',
  '/employees/women_5.png',
  '/employees/women_6.png',
  '/employees/women_7.png',
  '/employees/women_8.png',
];

function avatarLabel(url: string): string {
  const base = url.split('/').pop() || url;
  return base.replace(/\.[^.]+$/, '').replace(/_/g, ' ');
}

const emptyForm: EmployeeFormData = {
  name: '',
  role: '',
  avatar_url: '',
  cover_url: '',
  description: '',
  system_prompt: '',
  model: 'openai/gpt-4o',
  provider: '',
  temperature: 0.7,
  max_tokens: 4096,
  tools: [],
  skills: [],
  memory: [],
};

export function EmployeePanel({ open, onClose, employee, onSave, isSaving, mode = 'modal' }: EmployeePanelProps) {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState<EmployeeFormData>(emptyForm);
  const [savedSignature, setSavedSignature] = useState<string | null>(null);
  const [showSavedHint, setShowSavedHint] = useState(false);
  const [activeTab, setActiveTab] = useState<'profile' | 'tools' | 'skills' | 'memory'>('profile');
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
  const [toolSearch, setToolSearch] = useState('');
  const [publicSkillSearch, setPublicSkillSearch] = useState('');
  const [integrationMap, setIntegrationMap] = useState<Record<string, IntegrationStatus>>({});
  const [deploymentMode, setDeploymentMode] = useState<'cloud' | 'self_hosted'>('self_hosted');
  const [connectingIntegration, setConnectingIntegration] = useState<string | null>(null);

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
        const models = await fetchModelsForProvider(selectedProvider);
        if (!cancelled) setAvailableModels(models.map(m => ({ id: m.id, name: m.name, description: '', context_length: 0 })));
      } catch (error) {
        if (!cancelled) setModelsError(error instanceof Error ? error.message : 'Failed to load models');
      } finally {
        if (!cancelled) setModelsLoading(false);
      }
    }

    async function loadProviders() {
      setProvidersLoading(true);
      try {
        const providers = await listLLMProviders();
        if (!cancelled) {
          const mapped = providers.map(p => ({ id: p.id, name: p.name, description: p.name, available: true }));
          setAvailableProviders(mapped);
          if (!selectedProvider && mapped.length > 0) setSelectedProvider(mapped[0].id);
        }
      } catch (error) {
        console.error('Failed to load providers:', error);
      } finally {
        if (!cancelled) setProvidersLoading(false);
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

      getMarkdownTree('agent')
        .then((treeData) => {
          if (!cancelled) {
            setAgentFiles(mapMarkdownNodesToFileItems(treeData));
          }
        })
        .catch(() => {});
    }

    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    let cancelled = false;
    if (!open || !token) return;

    getIntegrations(token)
      .then((data) => {
        if (cancelled) return;
        const nextMap: Record<string, IntegrationStatus> = {};
        for (const integration of data.integrations || []) {
          nextMap[integration.id] = integration;
        }
        setIntegrationMap(nextMap);
        setDeploymentMode(data.deployment_mode);
      })
      .catch(() => {
        if (!cancelled) {
          setIntegrationMap({});
          setDeploymentMode('self_hosted');
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, token]);

  useEffect(() => {
    if (employee) {
      const savedProvider = employee.provider || '';
      setForm({
        name: employee.name || '',
        role: employee.role || '',
        avatar_url: employee.avatar_url || '',
        cover_url: (employee as any).cover_url || '',
        description: employee.description || '',
        system_prompt: employee.system_prompt || '',
        model: employee.model || 'openai/gpt-4o',
        provider: savedProvider,
        temperature: employee.temperature ?? 0.7,
        max_tokens: employee.max_tokens ?? 4096,
        tools: employee.tools || [],
        skills: employee.skills || [],
        memory: employee.memory || [],
      });

      if (savedProvider) {
        setSelectedProvider(savedProvider);
      } else if (employee.model) {
        const modelPrefix = employee.model.split('/')[0].toLowerCase();
        setSelectedProvider(['minimaxai', 'meta'].includes(modelPrefix) ? 'nvidia' : 'openrouter');
      }
    } else {
      setForm(emptyForm);
      setSelectedProvider('openrouter');
    }
  }, [employee, open]);

  useEffect(() => {
    if (!open) {
      setSavedSignature(null);
      setShowSavedHint(false);
    }
  }, [open]);

  // Reload models when provider changes
  useEffect(() => {
    if (open) {
      setModelsLoading(true);
      setModelsError(null);
      fetchModelsForProvider(selectedProvider)
        .then((models) => setAvailableModels(models.map(m => ({ id: m.id, name: m.name, description: '', context_length: 0 }))))
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

  const MAX_TOOLS_PER_EMPLOYEE = 10;

  const toggleTool = (toolName: string) => {
    setForm((prev) => {
      const isSelected = prev.tools.includes(toolName);
      if (!isSelected && prev.tools.length >= MAX_TOOLS_PER_EMPLOYEE) {
        return prev;
      }
      return {
        ...prev,
        tools: isSelected
          ? prev.tools.filter((t) => t !== toolName)
          : [...prev.tools, toolName],
      };
    });
  };

  const handleConnectIntegration = async (providerId: string) => {
    const integration = integrationMap[providerId];
    if (!integration) {
      navigate('/integrations');
      return;
    }

    const needsCredentials =
      deploymentMode === 'self_hosted'
      && integration.client_credentials_required
      && !integration.has_client_credentials;
    if (integration.auth_type === 'api_key' || needsCredentials) {
      navigate('/integrations');
      return;
    }

    if (!token) {
      navigate('/integrations');
      return;
    }

    setConnectingIntegration(providerId);
    try {
      const authUrl = await getOAuthUrl(token, providerId, window.location.origin);
      if (authUrl) {
        window.location.href = authUrl;
      } else {
        navigate('/integrations');
      }
    } catch {
      navigate('/integrations');
    } finally {
      setConnectingIntegration(null);
    }
  };

  const addSkill = () => {
    if (!newSkill.skill_name.trim()) return;
    setForm((prev) => ({
      ...prev,
      skills: [...prev.skills, { ...newSkill, proficiency_level: 50 }],
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
    setSavedSignature(JSON.stringify(form));
    setShowSavedHint(true);
    window.setTimeout(() => setShowSavedHint(false), 2500);
  };

  const modelOptions = !form.model || availableModels.some((model) => model.id === form.model)
    ? availableModels
    : [{ id: form.model, name: form.model, description: 'Currently selected model', context_length: 0 }, ...availableModels];
  const selectedAvatarValue = AVATAR_URL_OPTIONS.includes(form.avatar_url) ? form.avatar_url : '';
  const isSaved = savedSignature !== null && savedSignature === JSON.stringify(form);
  const toolQuery = toolSearch.toLowerCase();
  const filteredTools = availableTools
    .filter((tool) => {
      const displayName = toToolDisplayName(tool.name).toLowerCase();
      return (
        displayName.includes(toolQuery) ||
        (tool.runtime_name || '').toLowerCase().includes(toolQuery) ||
        tool.name.toLowerCase().includes(toolQuery) ||
        tool.description.toLowerCase().includes(toolQuery) ||
        tool.category.toLowerCase().includes(toolQuery)
      );
    })
    .sort((a, b) => toToolDisplayName(a.name).localeCompare(toToolDisplayName(b.name)));
  const selectedTools = filteredTools.filter((tool) => form.tools.includes(tool.name));
  const unselectedTools = filteredTools.filter((tool) => !form.tools.includes(tool.name));
  const resolveConnectProviderId = (tool: AvailableTool): string | null => {
    const primary = resolveIntegrationIdFromTool(tool);
    const raw = `${tool.name} ${(tool.runtime_name || '')}`.toLowerCase();
    const candidates = [primary];

    if (primary === 'gmail' || raw.includes('gmail')) candidates.unshift('google');
    if (primary.startsWith('google_')) candidates.push('google');
    if (primary === 'x') candidates.push('twitter');

    for (const candidate of candidates) {
      if (candidate && integrationMap[candidate]) return candidate;
    }
    return null;
  };

  return (
    <AnimatePresence>
      {open && (
        <div className={mode === 'modal' ? "fixed inset-0 z-50 flex justify-end p-4 sm:p-6 lg:p-8" : "h-full min-h-0"}>
          {mode === 'modal' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              onClick={onClose}
              className="absolute inset-0 bg-background/80 backdrop-blur-sm"
              style={{
                backgroundImage: 'radial-gradient(circle, var(--border) 1px, transparent 1px)',
                backgroundSize: '24px 24px'
              }}
            />
          )}

          <motion.div
            initial={mode === 'modal' ? { opacity: 0, x: 50, scale: 0.98 } : undefined}
            animate={mode === 'modal' ? { opacity: 1, x: 0, scale: 1 } : undefined}
            exit={mode === 'modal' ? { opacity: 0, x: 50, scale: 0.98 } : undefined}
            transition={mode === 'modal' ? { type: 'spring', damping: 25, stiffness: 300 } : undefined}
            className={mode === 'modal'
              ? "relative w-full max-w-lg h-full bg-background rounded-2xl border border-border shadow-2xl flex flex-col overflow-hidden"
              : "relative w-full h-full min-h-0 bg-white border-l border-border flex flex-col overflow-hidden"}
          >
            <div className={cn("flex items-center justify-between p-4 border-b border-border", mode === 'modal' ? "bg-background" : "bg-white")}>
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
              {mode === 'modal' ? (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  onClick={onClose}
                >
                  <X className="h-4 w-4" />
                </Button>
              ) : (
                <div className="w-8 h-8" />
              )}
            </div>

            <div className={cn("min-h-0 flex-1 overflow-y-auto", mode === 'modal' ? "bg-muted/20" : "bg-white")}>
              <div className="p-6">
                {activeTab === 'profile' && (
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-muted-foreground">Name</Label>
                      <input
                        type="text"
                        value={form.name}
                        onChange={(e) => updateField('name', e.target.value)}
                        placeholder="Employee name"
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring h-11 shadow-sm"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-muted-foreground">Role</Label>
                      <input
                        type="text"
                        value={form.role}
                        onChange={(e) => updateField('role', e.target.value)}
                        placeholder="e.g. Senior Backend Engineer"
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring h-11 shadow-sm"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-muted-foreground">Avatar URL</Label>
                      <Select
                        value={selectedAvatarValue}
                        onValueChange={(value) => updateField('avatar_url', value)}
                      >
                        <SelectTrigger className="h-11 bg-background">
                          {form.avatar_url ? (
                            <div className="flex items-center gap-2 min-w-0">
                              <img src={form.avatar_url} alt="Selected avatar" className="h-6 w-6 rounded-full object-cover border border-border" />
                              <span className="truncate">{avatarLabel(form.avatar_url)}</span>
                            </div>
                          ) : (
                            <SelectValue placeholder="Select an avatar..." />
                          )}
                        </SelectTrigger>
                        <SelectContent>
                          {AVATAR_URL_OPTIONS.map((url) => (
                            <SelectItem key={url} value={url}>
                              <div className="flex items-center gap-2">
                                <img src={url} alt={avatarLabel(url)} className="h-6 w-6 rounded-full object-cover border border-border" />
                                <span>{avatarLabel(url)}</span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
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
                        provider={deploymentMode === 'cloud' ? 'openrouter' : selectedProvider}
                        {...(deploymentMode !== 'cloud' && {
                          onProviderChange: (provider: string) => {
                            setSelectedProvider(provider);
                            updateField('model', '');
                            updateField('provider', provider);
                          },
                          availableProviders,
                        })}
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
                          min="256"
                          max="16384"
                          step="256"
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
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs text-muted-foreground">Configure the capabilities and tools accessible to this employee.</p>
                        <span className={cn(
                          "text-[11px] font-semibold uppercase tracking-wider shrink-0",
                          form.tools.length >= MAX_TOOLS_PER_EMPLOYEE ? "text-destructive" : "text-muted-foreground"
                        )}>
                          {form.tools.length}/{MAX_TOOLS_PER_EMPLOYEE}
                        </span>
                      </div>
                      {form.tools.length >= MAX_TOOLS_PER_EMPLOYEE && (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                          Tool limit reached. Remove a tool before adding another.
                        </div>
                      )}
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
                    <div className="space-y-4 min-w-0">
                      {selectedTools.length > 0 && (
                        <div className="space-y-2">
                          <div className="text-[11px] font-semibold uppercase tracking-wider text-primary">
                            Selected Tools ({selectedTools.length})
                          </div>
                          <ItemGroup className="gap-2 min-w-0">
                            {selectedTools.map((tool) => {
                              const isSelected = true;
                              const displayName = toToolDisplayName(tool.name);
                              const connectProviderId = resolveConnectProviderId(tool);
                              const integration = connectProviderId ? integrationMap[connectProviderId] : undefined;
                              const showConnect = Boolean(connectProviderId && integration && !integration.connected);
                              return (
                                <Item
                                  key={tool.name}
                                  asChild
                                  variant="outline"
                                  size="sm"
                                  className={cn(
                                    "w-full min-w-0 rounded-xl p-3 transition-all",
                                    isSelected
                                      ? "border-primary bg-primary/5 shadow-sm"
                                      : "border-border/60 bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground"
                                  )}
                                >
                                  <button
                                    type="button"
                                    onClick={() => toggleTool(tool.name)}
                                    className="w-full text-left"
                                  >
                                    <div className="flex w-full items-center justify-between">
                                      <div className="flex items-center gap-3 min-w-0">
                                        <ItemMedia className="size-8">
                                          <ToolIcon tool={tool} label={displayName} />
                                        </ItemMedia>
                                        <ItemContent className="min-w-0 gap-0">
                                          <ItemTitle className="truncate text-sm font-semibold text-foreground">{displayName}</ItemTitle>
                                        </ItemContent>
                                      </div>
                                      {showConnect ? (
                                        <ItemActions>
                                          <Button
                                            type="button"
                                            size="sm"
                                            variant="outline"
                                            className="h-7 px-2.5 text-[11px]"
                                            disabled={connectingIntegration === connectProviderId}
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              if (connectProviderId) void handleConnectIntegration(connectProviderId);
                                            }}
                                          >
                                            {connectingIntegration === connectProviderId ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Connect'}
                                          </Button>
                                        </ItemActions>
                                      ) : (
                                        isSelected && <Check className="h-4 w-4 text-primary" />
                                      )}
                                    </div>
                                  </button>
                                </Item>
                              );
                            })}
                          </ItemGroup>
                        </div>
                      )}
                      <div className="space-y-2">
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Available Tools ({unselectedTools.length})
                        </div>
                        <ItemGroup className="gap-2 min-w-0">
                          {unselectedTools.map((tool) => {
                            const displayName = toToolDisplayName(tool.name);
                            const connectProviderId = resolveConnectProviderId(tool);
                            const integration = connectProviderId ? integrationMap[connectProviderId] : undefined;
                            const showConnect = Boolean(connectProviderId && integration && !integration.connected);
                            const atCap = form.tools.length >= MAX_TOOLS_PER_EMPLOYEE;
                            return (
                              <Item
                                key={tool.name}
                                asChild
                                variant="outline"
                                size="sm"
                                className={cn(
                                  "w-full min-w-0 rounded-xl p-3 transition-all",
                                  atCap
                                    ? "border-border/40 bg-background/40 text-muted-foreground/50 cursor-not-allowed"
                                    : "border-border/60 bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground"
                                )}
                              >
                                <button
                                  type="button"
                                  onClick={() => toggleTool(tool.name)}
                                  disabled={atCap}
                                  className="w-full text-left disabled:cursor-not-allowed"
                                >
                                  <div className="flex w-full items-center justify-between">
                                    <div className="flex items-center gap-3 min-w-0">
                                      <ItemMedia className="size-8">
                                        <ToolIcon tool={tool} label={displayName} />
                                      </ItemMedia>
                                      <ItemContent className="min-w-0 gap-0">
                                        <ItemTitle className="truncate text-sm font-semibold text-foreground">{displayName}</ItemTitle>
                                      </ItemContent>
                                    </div>
                                    {showConnect && (
                                      <ItemActions>
                                        <Button
                                          type="button"
                                          size="sm"
                                          variant="outline"
                                          className="h-7 px-2.5 text-[11px]"
                                          disabled={connectingIntegration === connectProviderId}
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            if (connectProviderId) void handleConnectIntegration(connectProviderId);
                                          }}
                                        >
                                          {connectingIntegration === connectProviderId ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Connect'}
                                        </Button>
                                      </ItemActions>
                                    )}
                                  </div>
                                </button>
                              </Item>
                            );
                          })}
                        </ItemGroup>
                      </div>
                      {!toolsLoading && filteredTools.length === 0 && (
                        <div className="rounded-lg border border-border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
                          No tools match "{toolSearch}".
                        </div>
                      )}
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
                              <div className="flex items-center gap-2">
                                <div className="min-w-0 flex-1">
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
                                    <SelectTrigger className="h-10 w-full bg-background">
                                      <SelectValue placeholder="Select a public skill..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <div className="sticky top-0 z-10 border-b border-border bg-popover p-2">
                                        <div className="relative">
                                          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                                          <input
                                            type="text"
                                            value={publicSkillSearch}
                                            onChange={(e) => setPublicSkillSearch(e.target.value)}
                                            onKeyDown={(e) => {
                                              e.stopPropagation();
                                            }}
                                            placeholder="Search public skills..."
                                            className="h-8 w-full rounded-md border border-border bg-background pl-8 pr-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
                                          />
                                        </div>
                                      </div>
                                      {publicSkills
                                        .filter((s) => !form.skills.some((fs) => fs.skill_name === s.slug))
                                        .filter((s) => {
                                          const q = publicSkillSearch.trim().toLowerCase();
                                          if (!q) return true;
                                          return (
                                            s.title.toLowerCase().includes(q) ||
                                            s.category.toLowerCase().includes(q) ||
                                            s.description.toLowerCase().includes(q)
                                          );
                                        })
                                        .map((s) => (
                                          <SelectItem key={s.slug} value={s.slug}>
                                            {s.title}
                                          </SelectItem>
                                        ))}
                                      {publicSkills
                                        .filter((s) => !form.skills.some((fs) => fs.skill_name === s.slug))
                                        .filter((s) => {
                                          const q = publicSkillSearch.trim().toLowerCase();
                                          if (!q) return true;
                                          return (
                                            s.title.toLowerCase().includes(q) ||
                                            s.category.toLowerCase().includes(q) ||
                                            s.description.toLowerCase().includes(q)
                                          );
                                        }).length === 0 && (
                                        <div className="px-3 py-2 text-xs text-muted-foreground">
                                          No matching skills found
                                        </div>
                                      )}
                                    </SelectContent>
                                  </Select>
                                </div>
                                <Button
                                  size="sm"
                                  onClick={addSkill}
                                  disabled={!newSkill.skill_name.trim()}
                                  className="h-10 shrink-0 gap-1.5 px-3.5"
                                >
                                  <Plus className="h-3.5 w-3.5" />
                                  Attach to Employee
                                </Button>
                              </div>
                            </div>
                          {newSkill.skill_name && (
                              <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground leading-relaxed italic">
                                {newSkill.description}
                              </div>
                            )}
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

            <div className={cn(
              "p-4 border-t border-border flex items-center justify-end gap-3 shadow-[0_-4px_10px_-5px_rgba(0,0,0,0.05)]",
              mode === 'modal' ? "bg-background" : "bg-white"
            )}>
              {showSavedHint && (
                <span className="mr-auto text-xs font-medium text-emerald-600">Saved</span>
              )}
              {mode === 'modal' && (
                <Button variant="outline" onClick={onClose} disabled={isSaving}>
                  Cancel
                </Button>
              )}
              <Button
                onClick={handleSave}
                disabled={isSaving || !form.name.trim() || isSaved}
                className="gap-2 px-6"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : isSaved ? (
                  <>
                    <Check className="h-4 w-4" />
                    Saved
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

          {/* Skill Detail Sidebar */}
          <AnimatePresence>
            {mode === 'modal' && selectedSkillSlug && (() => {
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
        </div>
      )}
    </AnimatePresence>
  );
}
