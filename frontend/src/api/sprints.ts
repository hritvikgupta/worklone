import { BACKEND_URL } from '../../lib/api';

export interface Sprint {
  id: string;
  name: string;
  goal: string;
  start_date: string;
  end_date: string;
  status: string;
  created_at: string;
}

export interface Column {
  id: string;
  sprint_id: string;
  name: string;
  order_index: number;
}

export interface TaskMessage {
  id: string;
  task_id: string;
  sender_id: string;
  sender_name: string;
  sender_type: string;
  message_type: string;
  content: string;
  created_at: string;
}

export interface SprintRunStep {
  id: string;
  run_id: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done' | 'blocked' | 'cancelled' | string;
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface SprintRun {
  id: string;
  task_id: string;
  employee_id: string;
  employee_name: string;
  status: 'running' | 'done' | 'failed' | string;
  summary: string;
  error: string;
  created_at: string;
  updated_at: string;
  steps: SprintRunStep[];
}

export interface Task {
  id: string;
  sprint_id: string;
  column_id: string;
  title: string;
  requirements: string;
  description: string;
  priority: string;
  employee_id: string;
  created_at: string;
  updated_at: string;
  messages: TaskMessage[];
  runs: SprintRun[];
}

export interface SprintData {
  sprint: Sprint;
  columns: Column[];
  tasks: Task[];
}

export async function getActiveSprint(): Promise<SprintData> {
  const res = await fetch(`${BACKEND_URL}/api/sprints/active`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
  });
  if (!res.ok) {
    if (res.status === 404) {
        throw new Error("No active sprint found");
    }
    throw new Error('Failed to fetch active sprint');
  }
  return res.json();
}

export async function createTask(sprintId: string, data: { title: string; column_id: string; requirements?: string; description?: string; priority?: string; employee_id?: string }): Promise<{ task_id: string }> {
  const res = await fetch(`${BACKEND_URL}/api/sprints/${sprintId}/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create task');
  return res.json();
}

export async function updateTaskColumn(taskId: string, columnId: string): Promise<void> {
  const res = await fetch(`${BACKEND_URL}/api/sprints/tasks/${taskId}/column`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
    body: JSON.stringify({ column_id: columnId }),
  });
  if (!res.ok) throw new Error('Failed to update task column');
}

export async function updateTaskDetails(taskId: string, data: { title: string; description: string; requirements: string }): Promise<void> {
  const res = await fetch(`${BACKEND_URL}/api/sprints/tasks/${taskId}/details`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update task details');
}

export async function updateTaskAssignment(taskId: string, employeeId: string): Promise<void> {
  const res = await fetch(`${BACKEND_URL}/api/sprints/tasks/${taskId}/assignment`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
    body: JSON.stringify({ employee_id: employeeId }),
  });
  if (!res.ok) throw new Error('Failed to update task assignment');
}

export async function runTask(sprintId: string, taskId: string): Promise<{ run_id: string; status: string }> {
  const res = await fetch(`${BACKEND_URL}/api/sprints/${sprintId}/tasks/${taskId}/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(body || 'Failed to start task run');
  }
  return res.json();
}

export async function addTaskMessage(taskId: string, data: { content: string; sender_id?: string; sender_name?: string; sender_type?: string; message_type?: string }): Promise<{ message_id: string }> {
  const res = await fetch(`${BACKEND_URL}/api/sprints/tasks/${taskId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to add message');
  return res.json();
}
