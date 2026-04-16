/**
 * API client for communicating with the backend
 */

/// <reference types="vite/client" />

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
export const CHAT_AUTH_EXPIRED_ERROR = 'CHAT_AUTH_EXPIRED';

export interface ChatRequest {
  message: string;
  user_id?: string;
  conversation_history?: Array<{role: string; content: string}>;
  model?: string;
  session_id?: string;
}

export interface EmployeeChatRequest {
  message: string;
  conversation_history?: Array<{role: string; content: string}>;
  model?: string;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  success: boolean;
  error?: string;
}

export interface ChatStreamEvent {
  type:
    | 'thinking'
    | 'tool_start'
    | 'tool_result'
    | 'plan_created'
    | 'final'
    | 'error'
    | 'confirmation_required'
    | 'task_started'
    | 'content_token';
  cycle?: number;
  content?: string;
  token?: string;
  output?: string;
  message?: string;
  tool?: string;
  input?: Record<string, unknown>;
  success?: boolean;
  data?: unknown;
  // confirmation_required fields
  ask_type?: 'approval' | 'choice' | 'input' | string;
  options?: string[];
  plan?: {
    mode?: 'multi_step' | 'background' | 'direct' | string;
    reason?: string;
    context_summary?: string;
    status?: string;
    tasks?: Array<{
      task_id?: string;
      order?: number;
      title?: string;
      description?: string;
      status?: string;
      priority?: string;
    }>;
  };
  // plan_created fields
  mode?: 'multi_step' | 'background' | 'direct' | string;
  reason?: string;
  context_summary?: string;
  tasks?: Array<{
    task_id?: string;
    order?: number;
    title?: string;
    description?: string;
    status?: string;
    priority?: string;
  }>;
  // task_started fields
  task_id?: string;
  task_title?: string;
  instructions?: string;
}

export interface EmployeeChatResumePayload {
  session_id?: string;
  approved?: boolean;
  message?: string;
  input?: Record<string, unknown>;
}

export interface ChatSession {
  id: string;
  title: string;
  model?: string | null;
  created_at: string;
  updated_at: string;
  last_message?: string | null;
  last_message_role?: string | null;
  last_message_at?: string | null;
}

export interface ChatSessionMessage {
  role: 'user' | 'assistant';
  content: string;
  thinking?: string | null;
  model?: string | null;
  created_at: string;
}

export interface MarkdownTreeNode {
  type: 'file' | 'folder';
  name: string;
  path: string;
  children?: MarkdownTreeNode[];
}

export interface MarkdownFileContent {
  scope: 'agent' | 'shared';
  root_name: string;
  path: string;
  name: string;
  content: string;
}

export interface PublicSkillListItem {
  id: string;
  slug: string;
  title: string;
  description: string;
  category: string;
  employee_role: string;
  suggested_tools: string[];
  source_model: string;
  created_at: string;
  updated_at: string;
}

export interface PublicSkillDetail extends PublicSkillListItem {
  skill_markdown: string;
  notes: string;
}

function parseSseBufferChunk(buffer: string): {
  events: ChatStreamEvent[];
  remaining: string;
  done: boolean;
} {
  const events: ChatStreamEvent[] = [];
  const lines = buffer.split('\n');
  const remaining = lines.pop() || '';

  for (const line of lines) {
    if (!line.startsWith('data: ')) continue;

    const data = line.slice(6);
    if (data === '[DONE]') {
      return { events, remaining: '', done: true };
    }
    if (data.startsWith('[ERROR]')) {
      throw new Error(data.slice(8).trim());
    }
    try {
      const parsed = JSON.parse(data) as ChatStreamEvent;
      if (parsed && typeof parsed.type === 'string') {
        events.push(parsed);
        continue;
      }
    } catch {
      // Backward compatibility for plain-text chunks.
    }
    events.push({ type: 'thinking', content: data });
  }

  return { events, remaining, done: false };
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

/**
 * Send a message to Katy and get a response
 */
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/chat/`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(request),
    });

    if (response.status === 401) {
      throw new Error(CHAT_AUTH_EXPIRED_ERROR);
    }
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
}

export async function sendEmployeeChatMessage(employeeId: string, request: EmployeeChatRequest): Promise<ChatResponse> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/employees/${employeeId}/chat`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(request),
    });

    if (response.status === 401) {
      throw new Error(CHAT_AUTH_EXPIRED_ERROR);
    }
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error sending employee chat message:', error);
    throw error;
  }
}

/**
 * Stream Katy's response using Server-Sent Events
 */
export async function* streamChatEvents(request: ChatRequest): AsyncGenerator<ChatStreamEvent, void, unknown> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/chat/stream`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(request),
    });

    if (response.status === 401) {
      throw new Error(CHAT_AUTH_EXPIRED_ERROR);
    }
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        buffer += decoder.decode();
      } else {
        buffer += decoder.decode(value, { stream: true });
      }

      const parsedChunk = parseSseBufferChunk(buffer);
      buffer = parsedChunk.remaining;
      for (const event of parsedChunk.events) {
        yield event;
      }
      if (parsedChunk.done || done) {
        if (buffer.trim()) {
          const trailingChunk = parseSseBufferChunk(`${buffer}\n`);
          for (const event of trailingChunk.events) {
            yield event;
          }
        }
        return;
      }
    }
  } catch (error) {
    console.error('Error streaming chat message:', error);
    throw error;
  }
}

export async function resumeEmployeeChat(
  employeeId: string,
  payload: EmployeeChatResumePayload
): Promise<{ success: boolean }> {
  const response = await fetch(
    `${BACKEND_URL}/api/employees/${employeeId}/chat/resume`,
    {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    }
  );
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to resume employee chat (${response.status})`);
  }
  return response.json();
}

export async function* streamEmployeeChatEvents(
  employeeId: string,
  request: EmployeeChatRequest
): AsyncGenerator<ChatStreamEvent, void, unknown> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/employees/${employeeId}/chat/stream`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(request),
    });

    if (response.status === 401) {
      throw new Error(CHAT_AUTH_EXPIRED_ERROR);
    }
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        buffer += decoder.decode();
      } else {
        buffer += decoder.decode(value, { stream: true });
      }

      const parsedChunk = parseSseBufferChunk(buffer);
      buffer = parsedChunk.remaining;
      for (const event of parsedChunk.events) {
        yield event;
      }
      if (parsedChunk.done || done) {
        if (buffer.trim()) {
          const trailingChunk = parseSseBufferChunk(`${buffer}\n`);
          for (const event of trailingChunk.events) {
            yield event;
          }
        }
        return;
      }
    }
  } catch (error) {
    console.error('Error streaming employee chat message:', error);
    throw error;
  }
}

export async function listChatSessions(): Promise<ChatSession[]> {
  const response = await fetch(`${BACKEND_URL}/api/chat/sessions`, {
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to list sessions (${response.status})`);
  }
  const data = await response.json();
  return data.sessions || [];
}

export async function createChatSession(title = 'New Chat', model?: string): Promise<ChatSession> {
  const response = await fetch(`${BACKEND_URL}/api/chat/sessions`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ title, model }),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to create session (${response.status})`);
  }
  const data = await response.json();
  return data.session;
}

export async function createEmployeeChatSession(
  employeeId: string,
  title = 'New Chat',
  model?: string
): Promise<ChatSession> {
  const response = await fetch(`${BACKEND_URL}/api/employees/${employeeId}/chat/sessions`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ title, model }),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to create employee session (${response.status})`);
  }
  const data = await response.json();
  return data.session;
}

export async function listEmployeeChatSessions(employeeId: string): Promise<ChatSession[]> {
  const response = await fetch(`${BACKEND_URL}/api/employees/${employeeId}/chat/sessions`, {
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to list employee sessions (${response.status})`);
  }
  const data = await response.json();
  return data.sessions || [];
}

export async function getEmployeeChatSessionMessages(
  employeeId: string,
  sessionId: string
): Promise<ChatSessionMessage[]> {
  const response = await fetch(
    `${BACKEND_URL}/api/employees/${employeeId}/chat/sessions/${sessionId}/messages`,
    {
      headers: authHeaders(),
    }
  );
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to load employee session messages (${response.status})`);
  }
  const data = await response.json();
  return data.messages || [];
}

export async function getChatSessionMessages(sessionId: string): Promise<ChatSessionMessage[]> {
  const response = await fetch(`${BACKEND_URL}/api/chat/sessions/${sessionId}/messages`, {
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to load session messages (${response.status})`);
  }
  const data = await response.json();
  return data.messages || [];
}

export async function getMarkdownTree(scope: 'agent' | 'shared'): Promise<MarkdownTreeNode[]> {
  const response = await fetch(`${BACKEND_URL}/api/files/tree?scope=${scope}`, {
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to load markdown tree (${response.status})`);
  }
  const data = await response.json();
  return data.tree || [];
}

export async function getMarkdownContent(
  scope: 'agent' | 'shared',
  path: string
): Promise<MarkdownFileContent> {
  const response = await fetch(
    `${BACKEND_URL}/api/files/content?scope=${scope}&path=${encodeURIComponent(path)}`,
    {
      headers: authHeaders(),
    }
  );
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to load file (${response.status})`);
  }
  return response.json();
}

export async function uploadFile(
  scope: 'agent' | 'shared',
  file: File
): Promise<MarkdownFileContent> {
  const formData = new FormData();
  formData.append('file', file);
  
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${BACKEND_URL}/api/files/upload?scope=${scope}`, {
    method: 'POST',
    headers, // Don't set Content-Type, let browser set it with boundary
    body: formData,
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to upload file (${response.status})`);
  }
  return response.json();
}

export function getRawFileUrl(scope: string, path: string): string {
  const url = new URL(`${BACKEND_URL}/api/files/raw`);
  url.searchParams.append('scope', scope);
  url.searchParams.append('path', path);
  
  // We need to pass the token in the URL for iframe/object tags since we can't send headers
  // A better approach is to fetch it via JS and create an object URL, 
  // but for a quick iframe integration, this is a common workaround if the backend supports it,
  // OR we can just fetch it as blob and create object URL in the component.
  // We will do the blob approach in the component to avoid token in URL.
  return url.toString();
}

export async function fetchRawFileBlob(scope: string, path: string): Promise<Blob> {
  const response = await fetch(
    `${BACKEND_URL}/api/files/raw?scope=${scope}&path=${encodeURIComponent(path)}`,
    {
      headers: authHeaders(),
    }
  );
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to load raw file (${response.status})`);
  }
  return response.blob();
}

export async function updateMarkdownContent(
  scope: 'agent' | 'shared',
  path: string,
  content: string
): Promise<MarkdownFileContent> {
  const response = await fetch(`${BACKEND_URL}/api/files/content`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({ scope, path, content }),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to update markdown file (${response.status})`);
  }
  return response.json();
}

export async function listPublicSkills(): Promise<PublicSkillListItem[]> {
  const response = await fetch(`${BACKEND_URL}/api/skills/public`, {
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to load public skills (${response.status})`);
  }
  const data = await response.json();
  return data.skills || [];
}

export async function getPublicSkillDetail(slug: string): Promise<PublicSkillDetail> {
  const response = await fetch(`${BACKEND_URL}/api/skills/public/${encodeURIComponent(slug)}`, {
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to load public skill detail (${response.status})`);
  }
  const data = await response.json();
  return data.skill;
}

export interface CreatePublicSkillRequest {
  title: string;
  description: string;
  employee_role?: string;
}

export async function createPublicSkill(request: CreatePublicSkillRequest): Promise<PublicSkillListItem> {
  const response = await fetch(`${BACKEND_URL}/api/skills/public`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(request),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to create public skill (${response.status})`);
  }
  const data = await response.json();
  return data.skill;
}

/**
 * Health check
 */
export async function checkHealth(): Promise<{status: string; version: string}> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error checking health:', error);
    throw error;
  }
}
