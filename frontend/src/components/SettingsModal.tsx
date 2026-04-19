import React, { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { X, Key, Cpu, Lock, Eye, EyeOff, Check, Loader2, ChevronDown, Search } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  listLLMProviders,
  getLLMSettings,
  getProviderSettings,
  saveLLMSettings,
  changePassword,
  fetchModelsForProvider,
  LLMProvider,
  ModelOption,
} from '@/src/api/settings'

type Tab = 'general' | 'llm'

interface Props {
  open: boolean
  onClose: () => void
}

export function SettingsModal({ open, onClose }: Props) {
  const [tab, setTab] = useState<Tab>('general')

  // LLM state
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [selectedProvider, setSelectedProvider] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [defaultModel, setDefaultModel] = useState('')
  const [liveModels, setLiveModels] = useState<ModelOption[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [modelPickerOpen, setModelPickerOpen] = useState(false)
  const [modelQuery, setModelQuery] = useState('')
  const [llmSaving, setLlmSaving] = useState(false)
  const [llmSaved, setLlmSaved] = useState(false)
  const [llmError, setLlmError] = useState('')
  const [hasExistingKey, setHasExistingKey] = useState(false)
  const [providerKeys, setProviderKeys] = useState<Record<string, boolean>>({})

  // Password state
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [pwSaved, setPwSaved] = useState(false)
  const [pwError, setPwError] = useState('')

  useEffect(() => {
    if (!open) return
    setApiKey('')
    listLLMProviders().then(setProviders).catch(() => {})
    getLLMSettings()
      .then((s) => {
        setSelectedProvider(s.provider || '')
        setDefaultModel(s.default_model || '')
        setHasExistingKey(s.has_api_key)
        setProviderKeys(s.provider_keys || {})
      })
      .catch(() => {})
  }, [open])

  // When provider changes: update key status + load saved model for that provider
  useEffect(() => {
    if (!selectedProvider || !open) return
    setApiKey('')
    setHasExistingKey(providerKeys[selectedProvider] ?? false)
    getProviderSettings(selectedProvider)
      .then((s) => {
        setDefaultModel(s.default_model || '')
        setHasExistingKey(s.has_api_key)
        setProviderKeys((prev) => ({ ...prev, [selectedProvider]: s.has_api_key }))
      })
      .catch(() => {})
  }, [selectedProvider]) // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch live models whenever provider or api_key changes
  useEffect(() => {
    if (!selectedProvider) { setLiveModels([]); return }
    setModelsLoading(true)
    setLiveModels([])
    fetchModelsForProvider(selectedProvider, apiKey || undefined)
      .then(setLiveModels)
      .catch(() => setLiveModels([]))
      .finally(() => setModelsLoading(false))
  }, [selectedProvider, apiKey])

  const filteredProviderModels = liveModels.filter((m) =>
    m.id.toLowerCase().includes(modelQuery.trim().toLowerCase()) ||
    m.name.toLowerCase().includes(modelQuery.trim().toLowerCase())
  )

  const handleSaveLLM = async () => {
    setLlmError('')
    if (!selectedProvider) { setLlmError('Select a provider'); return }
    if (!apiKey && !hasExistingKey) { setLlmError('Enter your API key'); return }
    if (!defaultModel) { setLlmError('Select a default model'); return }
    setLlmSaving(true)
    try {
      await saveLLMSettings({ provider: selectedProvider, api_key: apiKey, default_model: defaultModel })
      setLlmSaved(true)
      setApiKey('')
      setHasExistingKey(true)
      setProviderKeys((prev) => ({ ...prev, [selectedProvider]: true }))
      setTimeout(() => setLlmSaved(false), 2500)
    } catch (e: any) {
      setLlmError(e.message || 'Failed to save')
    } finally {
      setLlmSaving(false)
    }
  }

  const handleChangePassword = async () => {
    setPwError('')
    if (!currentPw) { setPwError('Enter your current password'); return }
    if (newPw.length < 6) { setPwError('New password must be at least 6 characters'); return }
    if (newPw !== confirmPw) { setPwError('Passwords do not match'); return }
    setPwSaving(true)
    try {
      await changePassword({ current_password: currentPw, new_password: newPw })
      setPwSaved(true)
      setCurrentPw(''); setNewPw(''); setConfirmPw('')
      setTimeout(() => setPwSaved(false), 2500)
    } catch (e: any) {
      setPwError(e.message || 'Failed to change password')
    } finally {
      setPwSaving(false)
    }
  }

  const modal = (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
            className="relative w-full max-w-2xl bg-background border border-border rounded-2xl shadow-2xl flex overflow-hidden"
            style={{ minHeight: 420 }}
          >
            {/* Left sidebar */}
            <div className="w-44 border-r border-border bg-muted/30 flex flex-col p-3 gap-1 shrink-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-2 mb-1 mt-1">Settings</p>
              {([
                { id: 'general', label: 'General', icon: Lock },
                { id: 'llm', label: 'LLM Config', icon: Cpu },
              ] as { id: Tab; label: string; icon: any }[]).map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setTab(id)}
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left',
                    tab === id
                      ? 'bg-background text-foreground shadow-sm border border-border'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  )}
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  {label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <h2 className="text-sm font-semibold">
                  {tab === 'general' ? 'General' : 'LLM Configuration'}
                </h2>
                <button onClick={onClose} className="h-7 w-7 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {tab === 'general' && (
                  <div className="space-y-5">
                    <div>
                      <h3 className="text-sm font-semibold mb-1">Change Password</h3>
                      <p className="text-xs text-muted-foreground mb-4">Update your account password.</p>
                      <div className="space-y-3">
                        <div className="space-y-1.5">
                          <Label className="text-xs">Current Password</Label>
                          <Input type="password" value={currentPw} onChange={e => setCurrentPw(e.target.value)} placeholder="••••••••" className="h-9 text-sm" />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">New Password</Label>
                          <Input type="password" value={newPw} onChange={e => setNewPw(e.target.value)} placeholder="••••••••" className="h-9 text-sm" />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">Confirm New Password</Label>
                          <Input type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)} placeholder="••••••••" className="h-9 text-sm" onKeyDown={e => e.key === 'Enter' && handleChangePassword()} />
                        </div>
                        {pwError && <p className="text-xs text-destructive">{pwError}</p>}
                        <Button onClick={handleChangePassword} disabled={pwSaving} size="sm" className="w-full h-9">
                          {pwSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : pwSaved ? <Check className="w-3.5 h-3.5 mr-1.5 text-emerald-400" /> : null}
                          {pwSaved ? 'Password Updated' : 'Update Password'}
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                {tab === 'llm' && (
                  <div className="space-y-5">
                    <div>
                      <h3 className="text-sm font-semibold mb-1">LLM Provider</h3>
                      <p className="text-xs text-muted-foreground mb-4">
                        Configure your AI provider. This key is used for all agents — employees, workflows, skill generation, and prompt creation.
                      </p>
                      <div className="space-y-4">
                        <div className="space-y-1.5">
                          <Label className="text-xs">Provider</Label>
                          <Select value={selectedProvider} onValueChange={v => { setSelectedProvider(v); setModelQuery('') }}>
                            <SelectTrigger className="h-9 text-sm">
                              <SelectValue placeholder="Select a provider…" />
                            </SelectTrigger>
                            <SelectContent>
                              {providers.map(p => (
                                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-1.5">
                          <Label className="text-xs">API Key</Label>
                          <div className="relative">
                            <Input
                              type={showKey ? 'text' : 'password'}
                              value={apiKey}
                              onChange={e => setApiKey(e.target.value)}
                              placeholder={hasExistingKey ? '••••••••  (saved — enter new to replace)' : 'sk-…'}
                              className="h-9 text-sm pr-9"
                              autoComplete="new-password"
                              data-form-type="other"
                            />
                            <button
                              type="button"
                              onClick={() => setShowKey(s => !s)}
                              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                            >
                              {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                          {hasExistingKey && !apiKey && (
                            <p className="text-[11px] text-emerald-500 flex items-center gap-1">
                              <Check className="w-3 h-3" /> API key saved
                            </p>
                          )}
                        </div>

                        <div className="space-y-1.5">
                          <Label className="text-xs">Default Model</Label>
                          <Popover open={modelPickerOpen} onOpenChange={setModelPickerOpen}>
                            <PopoverTrigger
                              disabled={!selectedProvider}
                              className={cn(
                                "h-9 w-full rounded-lg border border-input bg-transparent px-3 text-sm",
                                "flex items-center justify-between text-left disabled:cursor-not-allowed disabled:opacity-50"
                              )}
                              onClick={() => setModelQuery(defaultModel)}
                            >
                              <span className={cn("truncate font-mono text-[12px]", !defaultModel && "font-sans text-sm text-muted-foreground")}>
                                {defaultModel || (selectedProvider ? 'Select or type a model…' : 'Select a provider first')}
                              </span>
                              <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                            </PopoverTrigger>
                            <PopoverContent
                              align="start"
                              sideOffset={6}
                              className="z-[90] w-[min(640px,calc(100vw-2rem))] p-2"
                            >
                              <div className="space-y-2">
                                <div className="relative">
                                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                                  <Input
                                    value={modelQuery}
                                    onChange={(e) => setModelQuery(e.target.value)}
                                    placeholder="Search models or type custom model id..."
                                    className="h-8 pl-8 text-xs font-mono"
                                  />
                                </div>
                                <div className="max-h-56 overflow-y-auto rounded-md border border-border">
                                  {modelsLoading && (
                                    <div className="flex items-center gap-2 px-2.5 py-3 text-xs text-muted-foreground">
                                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Fetching live models…
                                    </div>
                                  )}
                                  {!modelsLoading && filteredProviderModels.map((m) => (
                                    <button
                                      key={m.id}
                                      type="button"
                                      onClick={() => {
                                        setDefaultModel(m.id)
                                        setModelQuery(m.id)
                                        setModelPickerOpen(false)
                                      }}
                                      className={cn(
                                        "w-full text-left px-2.5 py-2 text-[12px] font-mono hover:bg-accent",
                                        defaultModel === m.id && "bg-accent"
                                      )}
                                    >
                                      {m.id}
                                    </button>
                                  ))}
                                  {!modelsLoading && filteredProviderModels.length === 0 && (
                                    <div className="px-2.5 py-2 text-xs text-muted-foreground">
                                      {selectedProvider ? (apiKey || hasExistingKey ? 'No models found.' : 'Enter API key to load models.') : 'Select a provider first.'}
                                    </div>
                                  )}
                                </div>
                                {modelQuery.trim() && (
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    className="w-full h-8 text-xs justify-start"
                                    onClick={() => {
                                      const customModel = modelQuery.trim()
                                      setDefaultModel(customModel)
                                      setModelPickerOpen(false)
                                    }}
                                  >
                                    Use custom model: <span className="ml-1 font-mono">{modelQuery.trim()}</span>
                                  </Button>
                                )}
                              </div>
                            </PopoverContent>
                          </Popover>
                          <p className="text-[11px] text-muted-foreground">Applied to all AI features: employees, workflows, and generation.</p>
                        </div>

                        {llmError && <p className="text-xs text-destructive">{llmError}</p>}
                        <Button onClick={handleSaveLLM} disabled={llmSaving} size="sm" className="w-full h-9">
                          {llmSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : llmSaved ? <Check className="w-3.5 h-3.5 mr-1.5 text-emerald-400" /> : <Key className="w-3.5 h-3.5 mr-1.5" />}
                          {llmSaved ? 'Saved!' : 'Save LLM Settings'}
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )

  if (typeof document === 'undefined') return null
  return createPortal(modal, document.body)
}
