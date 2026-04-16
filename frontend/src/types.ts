export type AgentStatus = 'idle' | 'working' | 'blocked' | 'offline';

export interface Agent {
  id: string;
  name: string;
  role?: string;
  avatar: string;
  status: AgentStatus;
  description: string;
  systemPrompt: string;
  currentTask?: string;
  skills: string[];
  model: string;
}

export type IssueStatus = string;

export interface IssueComment {
  id: string;
  authorId: string;
  authorName: string;
  authorAvatar?: string;
  content: string;
  timestamp: string;
  type: 'user' | 'agent' | 'system';
}

export interface IssueRunStep {
  id: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done' | 'blocked' | 'cancelled' | string;
  updatedAt: string;
}

export interface IssueRun {
  id: string;
  status: 'running' | 'done' | 'failed' | string;
  employeeName: string;
  summary: string;
  error: string;
  createdAt: string;
  updatedAt: string;
  steps: IssueRunStep[];
}

export interface Issue {
  id: string;
  title: string;
  description: string;
  requirements?: string;
  status: IssueStatus;
  assigneeId?: string;
  agentId?: string;
  priority: 'low' | 'medium' | 'high';
  tags: string[];
  createdAt: string;
  fileChanges?: string[];
  comments: IssueComment[];
  runs?: IssueRun[];
}

export interface Activity {
  id: string;
  agentId: string;
  type: 'work_started' | 'code_pushed' | 'blocker_reported' | 'status_updated' | 'skill_learned';
  message: string;
  timestamp: string;
  issueId?: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  category: 'coding' | 'testing' | 'devops' | 'research';
  level: number;
}

export interface TeamMember {
  id: string;
  name: string;
  role: string;
  avatar?: string;
  task?: string;
}

export interface TeamEdge {
  from: string;
  to: string;
}

export interface TeamRunMember {
  id: string;
  run_id: string;
  employee_id: string;
  employee_name: string;
  employee_role: string;
  assigned_task: string;
  task_status: 'assigned' | 'in_progress' | 'done' | 'blocked';
  result: string;
  created_at: string;
  updated_at: string;
}

export interface TeamRun {
  id: string;
  team_id: string;
  owner_id: string;
  conversation_id: string;
  goal: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  members?: TeamRunMember[];
}

export interface Team {
  id: string;
  name: string;
  goal: string;
  topology: string;
  projectType: string;
  deadline: string;
  members: TeamMember[];
  attachedFiles: string[];
  edges: TeamEdge[];
  sequenceOrder: string[];
  broadcasterId: string;
  createdAt: string;
  runs?: TeamRun[];
}
