import { Team } from '../types';
import { BACKEND_URL, requestJson } from '../../lib/api';

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
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function listTeams(): Promise<Team[]> {
  const data = await requestJson<{ teams: Team[] }>('/api/teams', { headers: authHeaders() }, 'Teams could not be loaded.');
  return data.teams || [];
}

export async function getTeam(teamId: string): Promise<Team> {
  const data = await requestJson<any>(`/api/teams/${teamId}`, { headers: authHeaders() }, 'The team could not be loaded.');
  return {
    ...data.team,
    members: data.members || [],
    edges: data.edges || [],
    runs: data.runs || []
  };
}

export async function createTeam(teamData: Omit<Team, 'id' | 'createdAt'>): Promise<Team> {
  const data = await requestJson<any>('/api/teams', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(teamData),
  }, 'The team could not be created.');
  return {
    ...data.team,
    members: data.members || [],
    edges: data.edges || []
  };
}

export async function updateTeam(teamId: string, teamData: Omit<Team, 'id' | 'createdAt'>): Promise<Team> {
  const data = await requestJson<any>(`/api/teams/${teamId}`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(teamData),
  }, 'The team could not be updated.');
  return {
    ...data.team,
    members: data.members || [],
    edges: data.edges || []
  };
}

export async function deleteTeam(teamId: string): Promise<void> {
  await requestJson<{ success: boolean }>(`/api/teams/${teamId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  }, 'The team could not be deleted.');
}

export async function startRun(
  teamId: string,
  goal: string,
  memberTasks: Record<string, string>
): Promise<{ run_id: string; conversation_id: string }> {
  const payload = { goal, member_tasks: memberTasks };
  console.log('[startRun] payload:', JSON.stringify(payload));
  const data = await requestJson<any>(`/api/teams/${teamId}/runs`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  }, 'The team run could not be started.');
  return { run_id: data.run_id, conversation_id: data.run?.conversation_id || '' };
}

export async function getRun(teamId: string, runId: string): Promise<TeamRun> {
  const data = await requestJson<any>(`/api/teams/${teamId}/runs/${runId}`, { headers: authHeaders() }, 'The team run could not be loaded.');
  return { ...data.run, members: data.members || [] };
}

export async function listRuns(teamId: string): Promise<TeamRun[]> {
  const data = await requestJson<any>(`/api/teams/${teamId}/runs`, { headers: authHeaders() }, 'Team runs could not be loaded.');
  return data.runs || [];
}
