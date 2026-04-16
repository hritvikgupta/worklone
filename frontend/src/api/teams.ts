import { Team } from '../types';
import { BACKEND_URL, CHAT_AUTH_EXPIRED_ERROR } from '../../lib/api';

export interface TeamRunMember {
  id: string;
  employee_id: string;
  employee_name: string;
  employee_role: string;
  assigned_task: string;
  task_status: 'assigned' | 'in_progress' | 'done' | 'blocked';
  result: string;
}

export interface TeamRun {
  id: string;
  team_id: string;
  conversation_id: string;
  goal: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  members: TeamRunMember[];
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function listTeams(): Promise<Team[]> {
  const response = await fetch(`${BACKEND_URL}/api/teams`, {
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to list teams (${response.status})`);
  }
  const data = await response.json();
  return data.teams || [];
}

export async function getTeam(teamId: string): Promise<Team> {
  const response = await fetch(`${BACKEND_URL}/api/teams/${teamId}`, {
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to get team (${response.status})`);
  }
  const data = await response.json();
  return {
    ...data.team,
    members: data.members || [],
    edges: data.edges || [],
    runs: data.runs || []
  };
}

export async function createTeam(teamData: Omit<Team, 'id' | 'createdAt'>): Promise<Team> {
  const response = await fetch(`${BACKEND_URL}/api/teams`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(teamData),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to create team (${response.status})`);
  }
  const data = await response.json();
  return {
    ...data.team,
    members: data.members || [],
    edges: data.edges || []
  };
}

export async function updateTeam(teamId: string, teamData: Omit<Team, 'id' | 'createdAt'>): Promise<Team> {
  const response = await fetch(`${BACKEND_URL}/api/teams/${teamId}`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(teamData),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to update team (${response.status})`);
  }
  const data = await response.json();
  return {
    ...data.team,
    members: data.members || [],
    edges: data.edges || []
  };
}

export async function deleteTeam(teamId: string): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/api/teams/${teamId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to delete team (${response.status})`);
  }
}

export async function startRun(
  teamId: string,
  goal: string,
  memberTasks: Record<string, string>
): Promise<{ run_id: string; conversation_id: string }> {
  const payload = { goal, member_tasks: memberTasks };
  console.log('[startRun] payload:', JSON.stringify(payload));
  const response = await fetch(`${BACKEND_URL}/api/teams/${teamId}/runs`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (response.status === 401) throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  if (!response.ok) {
    const errBody = await response.json().catch(() => ({}));
    console.error('[startRun] error:', errBody);
    throw new Error(errBody.detail || `Failed to start run (${response.status})`);
  }
  const data = await response.json();
  return { run_id: data.run_id, conversation_id: data.run?.conversation_id || '' };
}

export async function getRun(teamId: string, runId: string): Promise<TeamRun> {
  const response = await fetch(`${BACKEND_URL}/api/teams/${teamId}/runs/${runId}`, {
    headers: authHeaders(),
  });
  if (response.status === 401) throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  if (!response.ok) throw new Error(`Failed to get run (${response.status})`);
  const data = await response.json();
  return { ...data.run, members: data.members || [] };
}

export async function listRuns(teamId: string): Promise<TeamRun[]> {
  const response = await fetch(`${BACKEND_URL}/api/teams/${teamId}/runs`, {
    headers: authHeaders(),
  });
  if (response.status === 401) throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  if (!response.ok) throw new Error(`Failed to list runs (${response.status})`);
  const data = await response.json();
  return data.runs || [];
}
