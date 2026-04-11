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

export interface ChatResponse {
  response: string;
  success: boolean;
  error?: string;
}

export interface ChatStreamEvent {
  type: 'thinking' | 'tool_start' | 'tool_result' | 'final' | 'error';
  cycle?: number;
  content?: string;
  output?: string;
  message?: string;
  tool?: string;
  input?: Record<string, unknown>;
  success?: boolean;
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

export interface VercelSkillListItem {
  id: string;
  name: string;
  source: string;
  owner: string;
  installs_label: string;
  installs_count: number;
}

export interface VercelSkillDetail {
  id: string;
  owner: string;
  source: string;
  name: string;
  install_command: string;
  summary_html: string;
  skill_html: string;
  repository: string;
  weekly_installs: string;
  github_stars: string;
  first_seen: string;
  trust: {
    gen_agent: string;
    socket: string;
    snyk: string;
  };
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
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      
      // Process SSE format
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            return;
          }
          if (data.startsWith('[ERROR]')) {
            throw new Error(data.slice(8).trim());
          }
          try {
            const parsed = JSON.parse(data) as ChatStreamEvent;
            if (parsed && typeof parsed.type === 'string') {
              yield parsed;
              continue;
            }
          } catch {
            // Backward compatibility for any plain-text chunks.
          }
          yield { type: 'thinking', content: data };
        }
      }
    }
  } catch (error) {
    console.error('Error streaming chat message:', error);
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
    throw new Error(`Failed to load markdown file (${response.status})`);
  }
  return response.json();
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

export async function listVercelSkills(): Promise<VercelSkillListItem[]> {
  const response = await fetch(`${BACKEND_URL}/api/skills/vercel`, {
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to load Vercel skills (${response.status})`);
  }
  const data = await response.json();
  return data.skills || [];
}

export async function getVercelSkillDetail(source: string, skillName: string): Promise<VercelSkillDetail> {
  const response = await fetch(`${BACKEND_URL}/api/skills/vercel/${encodeURIComponent(source)}/${encodeURIComponent(skillName)}`, {
    headers: authHeaders(),
  });
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw new Error(`Failed to load skill detail (${response.status})`);
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
