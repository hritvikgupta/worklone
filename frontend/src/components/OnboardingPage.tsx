import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { Check, ChevronDown, Eye, EyeOff, Key, Loader2, Search } from 'lucide-react'
import { saveOnboardingProfile } from '@/src/api/onboarding'
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

export function OnboardingPage({ onCompleted }: Props) {
  const navigate = useNavigate()
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
    setLoading(true)
    Promise.all([
      listLLMProviders().catch(() => [] as LLMProvider[]),
      getLLMSettings().catch(() => null),
    ])
      .then(([llmProviders, llmSettings]) => {
        setProviders(llmProviders || [])
        if (llmSettings) {
          setSelectedProvider(llmSettings.provider || '')
          setDefaultModel(llmSettings.default_model || '')
          setHasExistingKey(llmSettings.has_api_key)
          setProviderKeys(llmSettings.provider_keys || {})
        }
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedProvider) return
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
    if (!selectedProvider) {
      setLiveModels([])
      return
    }
    setModelsLoading(true)
    fetchModelsForProvider(selectedProvider, apiKey || undefined)
      .then(setLiveModels)
      .catch(() => setLiveModels([]))
      .finally(() => setModelsLoading(false))
  }, [selectedProvider, apiKey])

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
      navigate('/chat', { replace: true })
    } catch (e: any) {
      setLlmError(e.message || 'Failed to save LLM settings')
    } finally {
      setLlmSaving(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-background">
      <div className="flex flex-1 items-center justify-center p-6 lg:p-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-xl"
        >
          <div className="w-full border border-border rounded-2xl overflow-hidden bg-card shadow-sm">
            <div className="px-6 py-5 border-b border-border flex items-center justify-between">
              <div>
                <h1 className="text-xl font-semibold text-foreground">Complete your workspace onboarding</h1>
              </div>
              <p className="text-muted-foreground text-sm">Step {step} of 2</p>
            </div>

            <div className="px-6 py-6">
              {loading ? (
                <div className="h-40 flex items-center justify-center text-muted-foreground text-sm">
                  <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading setup...
                </div>
              ) : (
                <>
                  {step === 1 && (
                    <div className="space-y-4">
                      <div className="space-y-1.5">
                        <Label className="text-sm text-foreground">Profession</Label>
                        <Input
                          value={profession}
                          onChange={(e) => setProfession(e.target.value)}
                          placeholder="e.g. Engineer, Product Manager, Founder"
                          className="h-10 text-sm"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label className="text-sm text-foreground">Company Type</Label>
                        <Select value={companyType} onValueChange={setCompanyType}>
                          <SelectTrigger className="h-10 text-sm max-w-[280px]">
                            <SelectValue placeholder="Select company type..." />
                          </SelectTrigger>
                          <SelectContent className="z-[200]">
                            {COMPANY_TYPES.map((item) => (
                              <SelectItem key={item.value} value={item.value}>
                                {item.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-1.5">
                        <Label className="text-sm text-foreground">Company Description</Label>
                        <textarea
                          value={companyDescription}
                          onChange={(e) => setCompanyDescription(e.target.value)}
                          placeholder="Describe what your company does and your main workflows."
                          rows={6}
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        />
                      </div>

                      {profileError && (
                        <div className="p-3 rounded-md border border-destructive/30 bg-destructive/10 text-destructive text-sm">{profileError}</div>
                      )}

                      <Button onClick={handleNextProfile} disabled={profileSaving} className="w-full h-10 text-sm">
                        {profileSaving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                        Next
                      </Button>
                    </div>
                  )}

                  {step === 2 && (
                    <div className="space-y-4">
                      <div className="space-y-1.5">
                        <Label className="text-sm text-foreground">LLM Provider</Label>
                        <Select value={selectedProvider} onValueChange={v => { setSelectedProvider(v); setModelQuery('') }}>
                          <SelectTrigger className="h-10 text-sm">
                            <SelectValue placeholder="Select a provider..." />
                          </SelectTrigger>
                          <SelectContent className="z-[200]">
                            {providers.map((p) => (
                              <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-1.5">
                        <Label className="text-sm text-foreground">API Key</Label>
                        <div className="relative">
                          <Input
                            type={showKey ? 'text' : 'password'}
                            value={apiKey}
                            onChange={e => setApiKey(e.target.value)}
                            placeholder={hasExistingKey ? '••••••••  (saved — enter new to replace)' : 'sk-...'}
                            className="h-10 text-sm pr-10"
                            autoComplete="new-password"
                            data-form-type="other"
                          />
                          <button
                            type="button"
                            onClick={() => setShowKey((s) => !s)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                          >
                            {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                        {hasExistingKey && !apiKey && (
                          <p className="text-xs text-emerald-600 flex items-center gap-1">
                            <Check className="w-3 h-3" /> API key saved
                          </p>
                        )}
                      </div>

                      <div className="space-y-1.5">
                        <Label className="text-sm text-foreground">Default Model</Label>
                        <Popover open={modelPickerOpen} onOpenChange={setModelPickerOpen}>
                          <PopoverTrigger
                            disabled={!selectedProvider}
                            className={cn(
                              "h-10 w-full rounded-md border border-input bg-background px-3 text-sm",
                              "flex items-center justify-between text-left disabled:cursor-not-allowed disabled:opacity-50"
                            )}
                            onClick={() => setModelQuery(defaultModel)}
                          >
                            <span className={cn("truncate font-mono text-xs", !defaultModel && "font-sans text-sm text-muted-foreground")}>
                              {defaultModel || (selectedProvider ? 'Select or type a model...' : 'Select a provider first')}
                            </span>
                            <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                          </PopoverTrigger>
                          <PopoverContent align="start" sideOffset={6} className="z-[220] w-[min(640px,calc(100vw-2rem))] p-2">
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
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Fetching live models...
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

                      {llmError && (
                        <div className="p-3 rounded-md border border-destructive/30 bg-destructive/10 text-destructive text-sm">{llmError}</div>
                      )}

                      <div className="grid grid-cols-2 gap-3 pt-1">
                        <Button type="button" variant="outline" className="h-10" onClick={() => setStep(1)}>
                          Back
                        </Button>
                        <Button onClick={handleFinish} disabled={llmSaving} className="h-10">
                          {llmSaving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Key className="w-4 h-4 mr-2" />}
                          Complete Setup
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </motion.div>
      </div>

      <div className="hidden lg:block relative flex-1 bg-zinc-950">
        <img
          src="/login.jpg"
          alt="Onboarding background"
          className="absolute inset-0 h-full w-full object-cover opacity-90"
        />
      </div>
    </div>
  )
}
