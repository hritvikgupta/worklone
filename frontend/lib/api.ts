/**
 * API client for communicating with the backend
 */

/// <reference types="vite/client" />

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
export const CHAT_AUTH_EXPIRED_ERROR = 'CHAT_AUTH_EXPIRED';

export interface BackendErrorShape {
  code: string;
  message: string;
  retryable: boolean;
  details?: Record<string, unknown>;
}

export class BackendApiError extends Error {
  code: string;
  retryable: boolean;
  status?: number;
  details?: Record<string, unknown>;

  constructor(
    message: string,
    options?: {
      code?: string;
      retryable?: boolean;
      status?: number;
      details?: Record<string, unknown>;
    }
  ) {
    super(message);
    this.name = 'BackendApiError';
    this.code = options?.code || 'UNKNOWN_ERROR';
    this.retryable = options?.retryable ?? false;
    this.status = options?.status;
    this.details = options?.details;
  }
}

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
  error?: BackendErrorShape;
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

export function isBackendApiError(error: unknown): error is BackendApiError {
  return error instanceof BackendApiError;
}

export function getErrorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  if (error instanceof BackendApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function readJsonSafe(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return null;
  }
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export function errorMessageForCode(code: string, fallback: string): string {
  switch (code) {
    case 'PROVIDER_TIMEOUT':
      return 'The service is taking too long to respond. Try again in a moment.';
    case 'PROVIDER_REQUEST_FAILED':
      return 'The service is busy right now. Try again shortly.';
    case 'INVALID_PROVIDER_RESPONSE':
      return 'The service returned an invalid response. Try again.';
    case 'PROVIDER_UNAVAILABLE':
      return 'This service is not configured right now.';
    case 'EMPLOYEE_CHAT_FAILED':
    case 'KATY_CHAT_FAILED':
      return 'The chat service could not complete the request.';
    case 'EMPLOYEE_CHAT_STREAM_FAILED':
    case 'KATY_CHAT_STREAM_FAILED':
      return 'The chat stream stopped unexpectedly.';
    case 'WORKFLOW_EXECUTION_FAILED':
      return 'The workflow execution failed.';
    case 'WORKFLOW_GENERATION_FAILED':
      return 'The workflow generator could not complete the request.';
    case 'WORKFLOW_LIST_FAILED':
      return 'Workflows could not be loaded right now.';
    case 'MODEL_CATALOG_UNAVAILABLE':
      return 'The model catalog could not be loaded right now.';
    case 'AUTH_INVALID_CREDENTIALS':
      return 'Invalid email or password.';
    case 'AUTH_EMAIL_IN_USE':
      return 'That email is already in use.';
    case 'AUTH_PASSWORD_TOO_SHORT':
      return 'Password must be at least 6 characters.';
    default:
      return fallback;
  }
}

export async function parseBackendError(response: Response, fallbackMessage: string): Promise<BackendApiError> {
  const data = await readJsonSafe(response);

  if (data && typeof data === 'object') {
    const record = data as Record<string, unknown>;
    const nestedError = record.error;
    if (nestedError && typeof nestedError === 'object') {
      const err = nestedError as Record<string, unknown>;
      const code = typeof err.code === 'string' ? err.code : 'API_ERROR';
      const message = typeof err.message === 'string' ? err.message : errorMessageForCode(code, fallbackMessage);
      const retryable = typeof err.retryable === 'boolean' ? err.retryable : response.status >= 500;
      const details = err.details && typeof err.details === 'object' ? (err.details as Record<string, unknown>) : undefined;
      return new BackendApiError(errorMessageForCode(code, message), {
        code,
        retryable,
        status: response.status,
        details,
      });
    }

    const code = typeof record.error_code === 'string' ? record.error_code : undefined;
    const message =
      typeof record.error === 'string'
        ? record.error
        : typeof record.detail === 'string'
          ? record.detail
          : fallbackMessage;
    if (code || typeof record.error === 'string' || typeof record.detail === 'string') {
      return new BackendApiError(errorMessageForCode(code || 'API_ERROR', message), {
        code: code || 'API_ERROR',
        retryable: typeof record.retryable === 'boolean' ? record.retryable : response.status >= 500,
        status: response.status,
      });
    }
  }

  const text = await response.text().catch(() => '');
  return new BackendApiError(text || fallbackMessage, {
    code: 'HTTP_ERROR',
    retryable: response.status >= 500,
    status: response.status,
  });
}

export async function throwIfErrorResponse(response: Response, fallbackMessage: string): Promise<void> {
  if (response.status === 401) {
    throw new Error(CHAT_AUTH_EXPIRED_ERROR);
  }
  if (!response.ok) {
    throw await parseBackendError(response, fallbackMessage);
  }
}

export async function requestJson<T>(
  path: string,
  options?: RequestInit,
  fallbackMessage = 'Request failed.'
): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    headers: { ...authHeaders(), ...options?.headers },
    ...options,
  });
  await throwIfErrorResponse(response, fallbackMessage);
  return response.json();
}

/**
 * Send a message to Katy and get a response
 */
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  try {
    const data = await requestJson<ChatResponse>(
      '/api/chat/',
      {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(request),
      },
      'The chat service could not complete the request.'
    );
    return data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
}

export async function sendEmployeeChatMessage(employeeId: string, request: EmployeeChatRequest): Promise<ChatResponse> {
  try {
    const data = await requestJson<ChatResponse>(
      `/api/employees/${employeeId}/chat`,
      {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(request),
      },
      'The employee chat service could not complete the request.'
    );
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

    await throwIfErrorResponse(response, 'The chat stream could not be started.');

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
  await throwIfErrorResponse(response, 'The employee chat could not be resumed.');
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

    await throwIfErrorResponse(response, 'The employee chat stream could not be started.');

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
  await throwIfErrorResponse(response, 'Chat sessions could not be loaded.');
  const data = await response.json();
  return data.sessions || [];
}

export async function createChatSession(title = 'New Chat', model?: string): Promise<ChatSession> {
  const response = await fetch(`${BACKEND_URL}/api/chat/sessions`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ title, model }),
  });
  await throwIfErrorResponse(response, 'The chat session could not be created.');
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
  await throwIfErrorResponse(response, 'The employee chat session could not be created.');
  const data = await response.json();
  return data.session;
}

export async function listEmployeeChatSessions(employeeId: string): Promise<ChatSession[]> {
  const response = await fetch(`${BACKEND_URL}/api/employees/${employeeId}/chat/sessions`, {
    headers: authHeaders(),
  });
  await throwIfErrorResponse(response, 'Employee chat sessions could not be loaded.');
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
  await throwIfErrorResponse(response, 'Employee chat messages could not be loaded.');
  const data = await response.json();
  return data.messages || [];
}

export async function getChatSessionMessages(sessionId: string): Promise<ChatSessionMessage[]> {
  const response = await fetch(`${BACKEND_URL}/api/chat/sessions/${sessionId}/messages`, {
    headers: authHeaders(),
  });
  await throwIfErrorResponse(response, 'Chat messages could not be loaded.');
  const data = await response.json();
  return data.messages || [];
}

export async function getMarkdownTree(scope: 'agent' | 'shared'): Promise<MarkdownTreeNode[]> {
  const response = await fetch(`${BACKEND_URL}/api/files/tree?scope=${scope}`, {
    headers: authHeaders(),
  });
  await throwIfErrorResponse(response, 'Files could not be loaded.');
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
  await throwIfErrorResponse(response, 'The file could not be loaded.');
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
  await throwIfErrorResponse(response, 'The file could not be uploaded.');
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
  await throwIfErrorResponse(response, 'The file could not be loaded.');
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
  await throwIfErrorResponse(response, 'The file could not be saved.');
  return response.json();
}

export async function listPublicSkills(): Promise<PublicSkillListItem[]> {
  const response = await fetch(`${BACKEND_URL}/api/skills/public`, {
    headers: authHeaders(),
  });
  await throwIfErrorResponse(response, 'Public skills could not be loaded.');
  const data = await response.json();
  return data.skills || [];
}

export async function getPublicSkillDetail(slug: string): Promise<PublicSkillDetail> {
  const response = await fetch(`${BACKEND_URL}/api/skills/public/${encodeURIComponent(slug)}`, {
    headers: authHeaders(),
  });
  await throwIfErrorResponse(response, 'The public skill could not be loaded.');
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
  await throwIfErrorResponse(response, 'The public skill could not be created.');
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
