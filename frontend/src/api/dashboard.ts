const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export interface DashboardStat {
  title: string;
  value: string;
  description: string;
  trend: string;
}

export interface DashboardActivity {
  id: string;
  source: string;
  sourceType: string;
  message: string;
  time: string;
  color: string;
}

export interface EmployeeUsage {
  employee_id: string;
  name: string;
  role: string;
  model: string;
  avatar_url: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_tokens_formatted: string;
  total_cost: number;
  total_cost_formatted: string;
  total_run_seconds: number;
  total_run_time_formatted: string;
  total_calls: number;
  tasks_completed: number;
  sprint_runs_completed: number;
  team_runs_completed: number;
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

export async function getDashboardStats(): Promise<DashboardStat[]> {
  const data = await request<{ stats: DashboardStat[] }>('/api/dashboard/stats');
  return data.stats;
}

export async function getDashboardActivity(): Promise<DashboardActivity[]> {
  const data = await request<{ activities: DashboardActivity[] }>('/api/dashboard/activity');
  return data.activities;
}

export async function getDashboardUsage(): Promise<EmployeeUsage[]> {
  const data = await request<{ employees: EmployeeUsage[] }>('/api/dashboard/usage');
  return data.employees;
}
