import { API_BASE } from './_base'

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('auth_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export interface OnboardingProfile {
  profession: string
  company_description: string
  company_type: string
}

export interface OnboardingStatus {
  onboarded: boolean
  profile: OnboardingProfile
}

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  const res = await fetch(`${API_BASE}/settings/onboarding`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to load onboarding status')
  return res.json()
}

export async function saveOnboardingProfile(payload: OnboardingProfile): Promise<void> {
  const res = await fetch(`${API_BASE}/settings/onboarding`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to save onboarding profile')
  }
}

