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

export interface Issue {
  id: string;
  title: string;
  description: string;
  status: IssueStatus;
  assigneeId?: string;
  agentId?: string;
  priority: 'low' | 'medium' | 'high';
  tags: string[];
  createdAt: string;
  fileChanges?: string[];
  comments: IssueComment[];
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
