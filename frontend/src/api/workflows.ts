import { BACKEND_URL, requestJson, throwIfErrorResponse } from '../../lib/api';

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
  task_count: number;
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

export interface WorkflowTask {
  id: string;
  description: string;
  status: string;
  result: string;
  error: string;
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
  execution_time: number;
}

export interface WorkflowDetail extends WorkflowSummary {
  variables: Record<string, unknown>;
  is_published: boolean;
  triggers: WorkflowTrigger[];
  tasks: WorkflowTask[];
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  return requestJson<T>(path, options, 'The workflow request could not be completed.');
}

export async function generateWorkflow(prompt: string, model?: string): Promise<{ success: boolean; workflow_id: string }> {
  return request<{ success: boolean; workflow_id: string }>('/api/workflows/generate', {
    method: 'POST',
    body: JSON.stringify({ 
      prompt, 
      model: model || "qwen/qwen3-max-thinking",
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      current_time: new Date().toISOString()
    }),
  });
}

/**
 * Execute a workflow manually.
 *
 * Now enqueues a dispatch job and returns immediately. Live progress arrives
 * via socket.io `run.progress` / `run.completed` events — the caller should
 * subscribe to those keyed by the returned run id (currently the job id until
 * the worker assigns one). See `subscribeToWorkflowRun` below.
 */
export async function executeWorkflow(
  workflowId: string,
  onEvent?: (event: Record<string, unknown>) => void,
): Promise<{ success: boolean; job_id?: string; status?: string }> {
  const res = await fetch(`${BACKEND_URL}/api/workflows/${workflowId}/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
  });
  await throwIfErrorResponse(res, 'The workflow execution could not be started.');
  const data = await res.json().catch(() => ({} as any));

  const jobId: string | undefined = data.job_id;
  if (!jobId) return { success: true };

  // Wait for completion using socket.io events — falls back to polling the
  // dispatch job if the socket is unavailable so callers still resolve.
  const done = await new Promise<boolean>(async (resolve) => {
    const { io } = await import('socket.io-client');
    const { SOCKET_URL } = await import('./_base');
    const socket = io(SOCKET_URL, { path: '/socket.io', transports: ['websocket', 'polling'] });

    const handleProgress = (evt: any) => {
      if (evt?.job_id !== jobId) return;
      if (onEvent && evt?.data) onEvent(evt.data);
    };
    const handleCompleted = (evt: any) => {
      if (evt?.job_id !== jobId) return;
      const ok = evt?.status === 'completed';
      cleanup();
      resolve(ok);
    };
    const cleanup = () => {
      socket.off('run.progress', handleProgress);
      socket.off('run.completed', handleCompleted);
      socket.disconnect();
    };
    socket.on('run.progress', handleProgress);
    socket.on('run.completed', handleCompleted);

    // Fallback timeout — give up after 10 min.
    setTimeout(() => { cleanup(); resolve(false); }, 10 * 60 * 1000);
  });

  return { success: done, job_id: jobId, status: data.status };
}

export async function updateWorkflow(workflowId: string, updates: { name?: string; description?: string; schedule?: string; timezone?: string; tasks?: Partial<WorkflowTask>[] }): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/api/workflows/${workflowId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

export async function deleteWorkflow(workflowId: string): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/api/workflows/${workflowId}`, {
    method: 'DELETE',
  });
}

export interface PausedExecution {
  id: string;
  workflow_id: string;
  execution_id: string;
  owner_id: string;
  execution_snapshot: Record<string, unknown>;
  pause_points: Array<{
    block_id?: string;
    block_name?: string;
    prompt?: string;
    input_fields?: string[];
    timeout_minutes?: number;
    timestamp?: number;
  }>;
  total_pause_count: number;
  resumed_count: number;
  status: string;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
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

export async function listPausedExecutions(workflowId: string): Promise<PausedExecution[]> {
  const data = await request<{ success: boolean; paused: PausedExecution[] }>(`/api/workflows/${workflowId}/paused`);
  return data.paused || [];
}

export async function resumePausedExecution(pauseId: string, input: Record<string, unknown>): Promise<{ execution_id: string; status: string; output: Record<string, unknown> }> {
  const data = await request<{ success: boolean; execution_id: string; status: string; output: Record<string, unknown> }>(
    `/api/workflows/paused/${pauseId}/resume`,
    {
      method: 'POST',
      body: JSON.stringify({ input }),
    }
  );
  return {
    execution_id: data.execution_id,
    status: data.status,
    output: data.output,
  };
}

export async function cancelPausedExecution(pauseId: string): Promise<void> {
  await request<{ success: boolean }>(`/api/workflows/paused/${pauseId}/cancel`, {
    method: 'POST',
  });
}
