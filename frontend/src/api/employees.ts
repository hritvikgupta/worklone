import { EmployeeFormData } from '@/src/components/EmployeePanel';

const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export interface EmployeeDetail {
  id: string;
  name: string;
  role: string;
  avatar_url: string;
  status: string;
  description: string;
  system_prompt: string;
  model: string;
  is_active: boolean;
  temperature: number;
  max_tokens: number;
  memory: string[];
  created_at: string;
  updated_at: string;
}

export interface EmployeeTool {
  id: string;
  tool_name: string;
  is_enabled: boolean;
  config: Record<string, unknown>;
  created_at: string;
}

export interface EmployeeSkill {
  id: string;
  skill_name: string;
  category: string;
  proficiency_level: number;
  description: string;
  created_at: string;
}

export interface EmployeeTask {
  id: string;
  task_title: string;
  task_description: string;
  status: string;
  priority: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface EmployeeActivity {
  id: string;
  activity_type: string;
  message: string;
  task_id: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

export interface EmployeeWithDetails {
  employee: EmployeeDetail;
  tools: EmployeeTool[];
  skills: EmployeeSkill[];
  tasks: EmployeeTask[];
  activity: EmployeeActivity[];
}

export interface EmployeeModelOption {
  id: string;
  name: string;
  description: string;
  context_length: number;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function listEmployees(): Promise<EmployeeDetail[]> {
  const data = await request<{ success: boolean; employees: EmployeeDetail[]; error?: string }>('/api/employees');
  if (!data.success) throw new Error(data.error);
  return data.employees;
}

export async function getEmployee(employeeId: string): Promise<EmployeeWithDetails> {
  const data = await request<{ success: boolean; error?: string; employee?: EmployeeDetail; tools?: EmployeeTool[]; skills?: EmployeeSkill[]; tasks?: EmployeeTask[]; activity?: EmployeeActivity[] }>(`/api/employees/${employeeId}`);
  if (!data.success || !data.employee) throw new Error(data.error || 'Employee not found');
  return {
    employee: data.employee,
    tools: data.tools || [],
    skills: data.skills || [],
    tasks: data.tasks || [],
    activity: data.activity || [],
  };
}

export async function createEmployee(form: EmployeeFormData): Promise<EmployeeDetail> {
  const data = await request<{ success: boolean; employee: EmployeeDetail; error?: string }>('/api/employees', {
    method: 'POST',
    body: JSON.stringify({
      name: form.name,
      role: form.role,
      avatar_url: form.avatar_url,
      description: form.description,
      system_prompt: form.system_prompt,
      model: form.model,
      temperature: form.temperature,
      max_tokens: form.max_tokens,
      tools: form.tools,
      skills: form.skills,
      memory: form.memory || [],
    }),
  });
  if (!data.success) throw new Error(data.error);
  return data.employee;
}

export async function updateEmployee(employeeId: string, form: Partial<EmployeeFormData>): Promise<EmployeeDetail> {
  const body: Record<string, unknown> = {};
  if (form.name !== undefined) body.name = form.name;
  if (form.role !== undefined) body.role = form.role;
  if (form.avatar_url !== undefined) body.avatar_url = form.avatar_url;
  if (form.description !== undefined) body.description = form.description;
  if (form.system_prompt !== undefined) body.system_prompt = form.system_prompt;
  if (form.model !== undefined) body.model = form.model;
  if (form.temperature !== undefined) body.temperature = form.temperature;
  if (form.max_tokens !== undefined) body.max_tokens = form.max_tokens;
  if (form.is_active !== undefined) body.is_active = form.is_active;
  if (form.tools !== undefined) body.tools = form.tools;
  if (form.skills !== undefined) body.skills = form.skills;
  if (form.memory !== undefined) body.memory = form.memory;

  const data = await request<{ success: boolean; employee: EmployeeDetail; error?: string }>(`/api/employees/${employeeId}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
  if (!data.success) throw new Error(data.error);
  return data.employee;
}

export async function deleteEmployee(employeeId: string): Promise<void> {
  await request<{ success: boolean }>(`/api/employees/${employeeId}`, {
    method: 'DELETE',
  });
}

export async function updateEmployeeMemory(employeeId: string, memory: string[]): Promise<EmployeeDetail> {
  const data = await request<{ success: boolean; employee: EmployeeDetail; error?: string }>(`/api/employees/${employeeId}/memory`, {
    method: 'PUT',
    body: JSON.stringify({ memory }),
  });
  if (!data.success) throw new Error(data.error);
  return data.employee;
}

export async function getToolsCatalog(): Promise<{ name: string; description: string; category: string }[]> {
  const data = await request<{ success: boolean; tools: { name: string; runtime_name?: string; description: string; category: string }[] }>('/api/employees/tools/catalog');
  return data.tools;
}

export async function getModelsCatalog(provider: string = 'openrouter'): Promise<EmployeeModelOption[]> {
  const data = await request<{ success: boolean; models: EmployeeModelOption[]; error?: string }>(`/api/employees/models/catalog?provider=${provider}`);
  if (!data.success) throw new Error(data.error || 'Failed to load models');
  return data.models;
}

export interface ProviderInfo {
  id: string;
  name: string;
  description: string;
  available: boolean;
  message?: string;
}

export async function getAvailableProviders(): Promise<ProviderInfo[]> {
  const data = await request<{ providers: ProviderInfo[] }>('/api/employees/models/providers');
  return data.providers;
}

export interface GeneratedPromptResult {
  role: string;
  system_prompt: string;
  tools: string[];
  skills: { skill_name: string; category: string; proficiency_level: number; description: string }[];
}

export async function generateEmployeePrompt(
  name: string,
  description: string,
): Promise<GeneratedPromptResult> {
  const data = await request<{ success: boolean; role: string; system_prompt: string; tools: string[]; skills: GeneratedPromptResult['skills'] }>(
    '/api/employees/generate-prompt',
    {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    },
  );
  return {
    role: data.role,
    system_prompt: data.system_prompt,
    tools: data.tools,
    skills: data.skills,
  };
}
