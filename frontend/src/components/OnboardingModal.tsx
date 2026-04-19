import React, { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'motion/react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Check, ChevronDown, Eye, EyeOff, Key, Loader2, Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getOnboardingStatus, saveOnboardingProfile } from '@/src/api/onboarding'
import {
  listLLMProviders,
  getLLMSettings,
  getProviderSettings,
  saveLLMSettings,
  fetchModelsForProvider,
  LLMProvider,
  ModelOption,
} from '@/src/api/settings'

interface Props {
  open: boolean
  onCompleted: () => void
}

const COMPANY_TYPES = [
  { value: 'startup', label: 'Startup' },
  { value: 'smb', label: 'SMB' },
  { value: 'enterprise', label: 'Enterprise' },
  { value: 'agency', label: 'Agency' },
  { value: 'consultancy', label: 'Consultancy' },
  { value: 'nonprofit', label: 'Non-profit' },
  { value: 'government', label: 'Government' },
  { value: 'education', label: 'Education' },
  { value: 'other', label: 'Other' },
]

export function OnboardingModal({ open, onCompleted }: Props) {
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(true)

  const [profession, setProfession] = useState('')
  const [companyDescription, setCompanyDescription] = useState('')
  const [companyType, setCompanyType] = useState('')
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileError, setProfileError] = useState('')

  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [selectedProvider, setSelectedProvider] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [defaultModel, setDefaultModel] = useState('')
  const [hasExistingKey, setHasExistingKey] = useState(false)
  const [providerKeys, setProviderKeys] = useState<Record<string, boolean>>({})
  const [liveModels, setLiveModels] = useState<ModelOption[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [modelPickerOpen, setModelPickerOpen] = useState(false)
  const [modelQuery, setModelQuery] = useState('')
  const [llmSaving, setLlmSaving] = useState(false)
  const [llmError, setLlmError] = useState('')

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setStep(1)
    setProfileError('')
    setLlmError('')
    setApiKey('')
    Promise.all([
      getOnboardingStatus(),
      listLLMProviders().catch(() => [] as LLMProvider[]),
      getLLMSettings().catch(() => null),
    ])
      .then(([onboarding, llmProviders, llmSettings]) => {
        if (onboarding?.onboarded) {
          onCompleted()
          return
        }
        setProfession(onboarding?.profile?.profession || '')
        setCompanyDescription(onboarding?.profile?.company_description || '')
        setCompanyType(onboarding?.profile?.company_type || '')
        setProviders(llmProviders || [])
        if (llmSettings) {
          setSelectedProvider(llmSettings.provider || '')
          setDefaultModel(llmSettings.default_model || '')
          setHasExistingKey(llmSettings.has_api_key)
          setProviderKeys(llmSettings.provider_keys || {})
        }
      })
      .finally(() => setLoading(false))
  }, [open, onCompleted])

  useEffect(() => {
    if (!open || !selectedProvider) return
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

  useEffect(() => {
    if (!open || !selectedProvider) {
      setLiveModels([])
      return
    }
    setModelsLoading(true)
    fetchModelsForProvider(selectedProvider, apiKey || undefined)
      .then(setLiveModels)
      .catch(() => setLiveModels([]))
      .finally(() => setModelsLoading(false))
  }, [open, selectedProvider, apiKey])

  const filteredProviderModels = liveModels.filter((m) =>
    m.id.toLowerCase().includes(modelQuery.trim().toLowerCase()) ||
    m.name.toLowerCase().includes(modelQuery.trim().toLowerCase())
  )

  const handleNextProfile = async () => {
    setProfileError('')
    if (!profession.trim()) {
      setProfileError('Profession is required')
      return
    }
    if (!companyType) {
      setProfileError('Company type is required')
      return
    }
    if (!companyDescription.trim()) {
      setProfileError('Company description is required')
      return
    }
    setProfileSaving(true)
    try {
      await saveOnboardingProfile({
        profession: profession.trim(),
        company_type: companyType,
        company_description: companyDescription.trim(),
      })
      setStep(2)
    } catch (e: any) {
      setProfileError(e.message || 'Failed to save profile')
    } finally {
      setProfileSaving(false)
    }
  }

  const handleFinish = async () => {
    setLlmError('')
    if (!selectedProvider) {
      setLlmError('Select a provider')
      return
    }
    if (!apiKey && !hasExistingKey) {
      setLlmError('Enter your API key')
      return
    }
    if (!defaultModel) {
      setLlmError('Select a default model')
      return
    }
    setLlmSaving(true)
    try {
      await saveLLMSettings({
        provider: selectedProvider,
        api_key: apiKey,
        default_model: defaultModel,
      })
      onCompleted()
    } catch (e: any) {
      setLlmError(e.message || 'Failed to save LLM settings')
    } finally {
      setLlmSaving(false)
    }
  }

  const modal = (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
            className="relative w-full max-w-2xl bg-background border border-border rounded-2xl shadow-2xl overflow-hidden"
          >
            <div className="px-6 py-4 border-b border-border flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold">Complete your workspace onboarding</h2>
              </div>
              <p className="text-xs text-muted-foreground">Step {step} of 2</p>
            </div>

            <div className="p-6">
              {loading ? (
                <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading onboarding…
                </div>
              ) : (
                <>
                  {step === 1 && (
                    <div className="space-y-4">
                      <div className="space-y-1.5">
                        <Label className="text-xs">Profession</Label>
                        <Input
                          value={profession}
                          onChange={(e) => setProfession(e.target.value)}
                          placeholder="e.g. Product Manager, Founder, Engineer"
                          className="h-9 text-sm"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label className="text-xs">Company Type</Label>
                        <Select value={companyType} onValueChange={setCompanyType}>
                          <SelectTrigger className="h-9 text-sm">
                            <SelectValue placeholder="Select company type..." />
                          </SelectTrigger>
                          <SelectContent>
                            {COMPANY_TYPES.map((item) => (
                              <SelectItem key={item.value} value={item.value}>
                                {item.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-1.5">
                        <Label className="text-xs">Company Description</Label>
                        <textarea
                          value={companyDescription}
                          onChange={(e) => setCompanyDescription(e.target.value)}
                          placeholder="Describe what your company does and your main workflows."
                          rows={5}
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        />
                      </div>

                      {profileError && <p className="text-xs text-destructive">{profileError}</p>}

                      <div className="pt-1">
                        <Button onClick={handleNextProfile} disabled={profileSaving} className="h-9 w-full">
                          {profileSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null}
                          Next
                        </Button>
                      </div>
                    </div>
                  )}

                  {step === 2 && (
                    <div className="space-y-4">
                      <div className="space-y-1.5">
                        <Label className="text-xs">LLM Provider</Label>
                        <Select value={selectedProvider} onValueChange={v => { setSelectedProvider(v); setModelQuery('') }}>
                          <SelectTrigger className="h-9 text-sm">
                            <SelectValue placeholder="Select a provider…" />
                          </SelectTrigger>
                          <SelectContent>
                            {providers.map((p) => (
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
                            onClick={() => setShowKey((s) => !s)}
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
                          <PopoverContent align="start" sideOffset={6} className="z-[130] w-[min(640px,calc(100vw-2rem))] p-2">
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
                      </div>

                      {llmError && <p className="text-xs text-destructive">{llmError}</p>}

                      <div className="pt-1 grid grid-cols-2 gap-2">
                        <Button type="button" variant="outline" className="h-9" onClick={() => setStep(1)}>
                          Back
                        </Button>
                        <Button onClick={handleFinish} disabled={llmSaving} className="h-9">
                          {llmSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <Key className="w-3.5 h-3.5 mr-1.5" />}
                          Complete Setup
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )

  if (typeof document === 'undefined') return null
  return createPortal(modal, document.body)
}
