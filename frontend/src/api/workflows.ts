const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  status: string;
  schedule: string;
  owner: string;
  owner_id: string;
  owner_type: string;
  created_at: string;
  updated_at: string;
  handoff_actor_type: string;
  handoff_actor_id: string;
  handoff_actor_name: string;
  handoff_at: string | null;
  created_by_actor_type: string;
  created_by_actor_id: string;
  created_by_actor_name: string;
  trigger_count: number;
  block_count: number;
}

export interface WorkflowTrigger {
  id: string;
  trigger_type: string;
  name: string;
  config: Record<string, unknown>;
  enabled: boolean;
  webhook_path: string;
  cron_expression: string;
  schedule_preset: string;
  timezone: string;
  last_triggered_at: string | null;
  next_run_at: string | null;
  failed_count: number;
}

export interface WorkflowBlock {
  id: string;
  name: string;
  block_type: string;
  description: string;
  tool_name: string;
  model: string;
  system_prompt: string;
  code: string;
  url: string;
  method: string;
  condition: string;
  params: Record<string, unknown>;
  config: Record<string, unknown>;
  status: string;
  error: string;
  execution_time: number;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
}

export interface WorkflowConnection {
  id: string;
  from_block_id: string;
  to_block_id: string;
  condition: string;
  from_handle: string;
  to_handle: string;
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  owner_id: string;
  status: string;
  trigger_type: string;
  trigger_input: Record<string, unknown>;
  output: Record<string, unknown>;
  error: string;
  started_at: string;
  completed_at: string | null;
  block_results: Record<string, unknown>;
  execution_time: number;
}

export interface WorkflowDetail extends WorkflowSummary {
  variables: Record<string, unknown>;
  is_published: boolean;
  triggers: WorkflowTrigger[];
  blocks: WorkflowBlock[];
  connections: WorkflowConnection[];
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

export async function listWorkflows(): Promise<WorkflowSummary[]> {
  const data = await request<{ success: boolean; workflows: WorkflowSummary[]; error?: string }>('/api/workflows');
  if (!data.success) throw new Error(data.error || 'Failed to load workflows');
  return data.workflows;
}

export async function getWorkflow(workflowId: string): Promise<{ workflow: WorkflowDetail; executions: WorkflowExecution[] }> {
  const data = await request<{ success: boolean; workflow?: WorkflowDetail; executions?: WorkflowExecution[]; error?: string }>(`/api/workflows/${workflowId}`);
  if (!data.success || !data.workflow) throw new Error(data.error || 'Workflow not found');
  return {
    workflow: data.workflow,
    executions: data.executions || [],
  };
}
