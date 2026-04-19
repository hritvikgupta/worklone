import { API_BASE } from './_base'

export interface LLMProvider {
  id: string
  name: string
}

export interface ModelOption {
  id: string
  name: string
}

export interface LLMSettings {
  provider: string
  default_model: string
  has_api_key: boolean
  provider_keys: Record<string, boolean>
}

export interface ProviderSettings {
  provider: string
  default_model: string
  has_api_key: boolean
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('auth_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function listLLMProviders(): Promise<LLMProvider[]> {
  const res = await fetch(`${API_BASE}/settings/llm/providers`)
  if (!res.ok) throw new Error('Failed to load providers')
  const data = await res.json()
  return data.providers
}

export async function getLLMSettings(): Promise<LLMSettings> {
  const res = await fetch(`${API_BASE}/settings/llm`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to load LLM settings')
  return res.json()
}

export async function getProviderSettings(provider: string): Promise<ProviderSettings> {
  const res = await fetch(`${API_BASE}/settings/llm/provider/${provider}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to load provider settings')
  return res.json()
}

export async function saveLLMSettings(payload: {
  provider: string
  api_key: string
  default_model: string
}): Promise<void> {
  const res = await fetch(`${API_BASE}/settings/llm`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error('Failed to save LLM settings')
}

export async function fetchModelsForProvider(provider: string, apiKey?: string): Promise<ModelOption[]> {
  const params = new URLSearchParams({ provider })
  if (apiKey) params.set('api_key', apiKey)
  const res = await fetch(`${API_BASE}/employees/models/catalog?${params}`, { headers: authHeaders() })
  if (!res.ok) return []
  const data = await res.json()
  return (data.models || []).map((m: any) => ({ id: m.id, name: m.name || m.id }))
}

export async function changePassword(payload: {
  current_password: string
  new_password: string
}): Promise<void> {
  const res = await fetch(`${API_BASE}/settings/password`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to change password')
  }
}
