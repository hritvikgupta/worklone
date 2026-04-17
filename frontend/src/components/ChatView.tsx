import React, { useState, useEffect, useRef } from 'react';
import { FullMessenger } from '@/components/ui/chat/layouts';
import type { ChatMessageData, ChatUser } from '@/components/ui/chat/types';
import type { SidebarConversation } from '@/components/ui/chat/layouts';
import { Plus, History, ChevronDown, ListChecks, CheckCircle2, AlertCircle, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import {
  CHAT_AUTH_EXPIRED_ERROR,
  createEmployeeChatSession,
  getEmployeeChatSessionMessages,
  listEmployeeChatSessions,
  streamEmployeeChatEvents,
  resumeEmployeeChat,
  ChatSession,
} from '@/lib/api';
import { listEmployees, EmployeeDetail } from '@/src/api/employees';
import { useAuth } from '@/src/contexts/AuthContext';

function humanizeToken(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function stripMarkdown(text: string): string {
  return text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/[*_~>#-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function truncateLabel(text: string, maxLength = 92): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1).trimEnd()}…`;
}

function summarizeThinkingLabel(text: string): string {
  const cleaned = stripMarkdown(text);
  if (!cleaned) return 'Reasoning through the next step';
  const firstSentence = cleaned.split(/(?<=[.!?])\s+/)[0] || cleaned;
  return truncateLabel(firstSentence);
}

function summarizeToolMeta(input?: Record<string, unknown>): string | undefined {
  if (!input) return undefined;

  const parts: string[] = [];
  const action = typeof input.action === 'string' ? humanizeToken(input.action) : null;
  const owner = typeof input.owner === 'string' ? input.owner : null;
  const repo = typeof input.repo === 'string' ? input.repo : null;
  const projectKey = typeof input.project_key === 'string' ? input.project_key : null;
  const issueType = typeof input.issue_type === 'string' ? humanizeToken(input.issue_type) : null;

  if (action) parts.push(action);
  if (owner && repo) {
    parts.push(`${owner}/${repo}`);
  } else if (owner) {
    parts.push(owner);
  } else if (repo) {
    parts.push(repo);
  }
  if (projectKey) parts.push(projectKey);
  if (issueType) parts.push(issueType);

  return parts.length > 0 ? truncateLabel(parts.join(' · '), 72) : undefined;
}

export function ChatView() {
  const { logout, user } = useAuth();
  
  const currentUser: ChatUser = {
    id: user?.id || 'user-1',
    name: user?.name || 'Current User',
    avatar: user?.avatar_url || `https://i.pravatar.cc/150?u=${user?.id || 'current'}`,
  };

  const [employees, setEmployees] = useState<EmployeeDetail[]>([]);
  const [chatPanes, setChatPanes] = useState<Array<{ id: string; employeeId: string }>>([
    { id: 'pane-1', employeeId: '' }
  ]);
  const [sessions, setSessions] = useState<Record<string, ChatSession[]>>({});
  const [activeSessionId, setActiveSessionId] = useState<Record<string, string>>({});
  const [messages, setMessages] = useState<Record<string, ChatMessageData[]>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [activePlans, setActivePlans] = useState<Record<string, ChatMessageData['plan']>>({});
  const [collapsedPlans, setCollapsedPlans] = useState<Record<string, boolean>>({});
  const [pendingResume, setPendingResume] = useState<{
    employeeId: string;
    sessionId: string;
    askType: string;
  } | null>(null);
  const [isResuming, setIsResuming] = useState(false);

  const isStreamingRef = useRef(false);

  useEffect(() => {
    async function fetchEmployees() {
      try {
        const data = await listEmployees();
        setEmployees(data);
        if (data.length === 0) return;
        setChatPanes((prev) => {
          if (prev.some((pane) => pane.employeeId)) return prev;
          return data.slice(0, Math.min(3, data.length)).map((employee, index) => ({
            id: `pane-${index + 1}`,
            employeeId: employee.id,
          }));
        });
      } catch (error) {
        console.error('Failed to fetch employees:', error);
      }
    }
    fetchEmployees();
  }, []);

  const fetchSessionsForEmployee = async (employeeId: string) => {
    if (!employeeId) return;
    try {
      const sessionList = await listEmployeeChatSessions(employeeId);
      setSessions((prev) => ({ ...prev, [employeeId]: sessionList }));

      if (!activeSessionId[employeeId] && sessionList.length > 0) {
        const firstSessionId = sessionList[0].id;
        setActiveSessionId((prev) => ({ ...prev, [employeeId]: firstSessionId }));
        void fetchMessages(employeeId, firstSessionId);
      } else if (sessionList.length === 0) {
        setMessages((prev) => ({ ...prev, [employeeId]: [] }));
      }
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    }
  };

  useEffect(() => {
    for (const pane of chatPanes) {
      if (pane.employeeId && sessions[pane.employeeId] === undefined) {
        void fetchSessionsForEmployee(pane.employeeId);
      }
    }
  }, [chatPanes, sessions]);

  const fetchMessages = async (employeeId: string, sessionId: string) => {
    try {
      const history = await getEmployeeChatSessionMessages(employeeId, sessionId);
      const mappedMessages: ChatMessageData[] = history.map((msg, idx) => ({
        id: `msg-${idx}-${Date.now()}`,
        senderId: msg.role === 'user' ? currentUser.id : employeeId,
        senderName: msg.role === 'user' ? currentUser.name : (employees.find(e => e.id === employeeId)?.name || 'Agent'),
        text: msg.content,
        timestamp: new Date(msg.created_at),
        status: 'read',
      }));
      setMessages(prev => ({ ...prev, [employeeId]: mappedMessages }));
      setActivePlans(prev => ({ ...prev, [employeeId]: undefined })); // Reset plan on session load
      setPendingResume(null);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  };

  const handleSelectConversation = (paneId: string, employeeId: string) => {
    setChatPanes((prev) =>
      prev.map((pane) => (pane.id === paneId ? { ...pane, employeeId } : pane))
    );
    if (activeSessionId[employeeId]) {
      void fetchMessages(employeeId, activeSessionId[employeeId]);
    } else {
      void fetchSessionsForEmployee(employeeId);
    }
  };

  const handleStartNewSession = async (employeeId: string) => {
    if (!employeeId) return;
    const activeEmployee = employees.find(e => e.id === employeeId);
    if (!activeEmployee) return;

    try {
      const newSession = await createEmployeeChatSession(employeeId, 'New Chat', activeEmployee.model);
      setSessions(prev => ({
        ...prev,
        [employeeId]: [newSession, ...(prev[employeeId] || [])]
      }));
      setActiveSessionId(prev => ({ ...prev, [employeeId]: newSession.id }));
      setMessages(prev => ({ ...prev, [employeeId]: [] }));
      setActivePlans(prev => ({ ...prev, [employeeId]: undefined }));
    } catch (error) {
      console.error('Failed to create new session:', error);
    }
  };

  const handleSwitchSession = (employeeId: string, sessionId: string) => {
    setActiveSessionId(prev => ({ ...prev, [employeeId]: sessionId }));
    void fetchMessages(employeeId, sessionId);
  };

  const handlePlanDecision = async (approved: boolean) => {
    if (!pendingResume) return;
    setIsResuming(true);
    try {
      await resumeEmployeeChat(pendingResume.employeeId, {
        approved,
        message: approved ? 'Approved' : 'Rejected',
        session_id: pendingResume.sessionId,
      });
      setActivePlans(prev => {
        const plan = prev[pendingResume.employeeId];
        if (!plan) return prev;
        return { ...prev, [pendingResume.employeeId]: { ...plan, status: approved ? 'approved' : 'proposed' } };
      });
    } catch (e) {
      console.error('Failed to resume:', e);
    } finally {
      setPendingResume(null);
      setIsResuming(false);
    }
  };

  const handleSend = async (employeeId: string, text: string) => {
    if (!employeeId) return;
    const activeEmployee = employees.find(e => e.id === employeeId);
    if (!activeEmployee) return;

    let sessionId = activeSessionId[employeeId];
    
    if (!sessionId) {
      try {
        const newSession = await createEmployeeChatSession(employeeId, 'New Chat', activeEmployee.model);
        sessionId = newSession.id;
        setActiveSessionId(prev => ({ ...prev, [employeeId]: sessionId }));
        setSessions(prev => ({
          ...prev,
          [employeeId]: [newSession, ...(prev[employeeId] || [])]
        }));
      } catch (error) {
        console.error('Failed to create session on send:', error);
        return;
      }
    }

    const userMessage: ChatMessageData = {
      id: `user-${Date.now()}`,
      senderId: currentUser.id,
      senderName: currentUser.name,
      text,
      timestamp: new Date(),
      status: 'sending',
    };

    setMessages(prev => ({
      ...prev,
      [employeeId]: [...(prev[employeeId] || []), userMessage]
    }));

    setIsLoading(true);
    isStreamingRef.current = true;

    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessageData = {
      id: assistantMessageId,
      senderId: employeeId,
      senderName: activeEmployee.name,
      text: '',
      timestamp: new Date(),
      status: 'sending',
      activities: [],
    };

    setMessages(prev => ({
      ...prev,
      [employeeId]: [...(prev[employeeId] || []), assistantMessage]
    }));

    try {
      const history = (messages[employeeId] || []).map(m => ({
        role: m.senderId === currentUser.id ? 'user' : 'assistant',
        content: m.text || ''
      }));

      let answerBuffer = '';
      let thinkingBuffer = '';
      let activities: NonNullable<ChatMessageData['activities']> = [];
      
      const stream = streamEmployeeChatEvents(employeeId, {
        message: text,
        conversation_history: history,
        model: activeEmployee.model,
        session_id: sessionId,
      });

      for await (const event of stream) {
        if (event.type === 'content_token') {
          const token = event.token || '';
          if (token) {
            answerBuffer += token;
          }
          setMessages(prev => {
            const convoMessages = prev[employeeId] || [];
            return {
              ...prev,
              [employeeId]: convoMessages.map(m =>
                m.id === assistantMessageId ? {
                  ...m,
                  text: answerBuffer,
                  status: 'sending',
                } : m
              )
            };
          });
          continue;
        }

        if (event.type === 'plan_created') {
          const planData = {
            mode: event.mode || 'multi_step',
            reason: event.reason || '',
            message: event.message || '',
            status: 'proposed' as const,
            tasks: (event.tasks || []).map((task: any, i: number) => ({
              task_id: String(task.task_id || `task-${i + 1}`),
              order: task.order || i + 1,
              title: task.title || `Step ${i + 1}`,
              description: task.description || '',
              status: task.status || 'todo',
              priority: task.priority || 'medium',
            })),
          };
          setActivePlans(prev => ({ ...prev, [employeeId]: planData }));
          continue;
        }

        if (event.type === 'thinking') {
          const thought = event.content || '';
          if (thought) {
            thinkingBuffer += `${thought}\n\n`;
            answerBuffer = '';
            activities = activities.map(a =>
              a.type === 'thinking' && a.status === 'running' ? { ...a, status: 'done' } : a
            );
            activities = [
              ...activities,
              {
                id: `thinking-${event.cycle || 0}-${Date.now()}`,
                type: 'thinking',
                label: summarizeThinkingLabel(thought),
                status: 'running',
              },
            ];
          }
        } else if (event.type === 'tool_start') {
          activities = activities.map(a =>
            a.type === 'thinking' && a.status === 'running' ? { ...a, status: 'done' } : a
          );
          activities = [
            ...activities,
            {
              id: `tool-${event.tool || 'tool'}-${event.cycle || 0}-${Date.now()}`,
              type: 'tool',
              label: humanizeToken(event.tool || 'tool'),
              meta: summarizeToolMeta(event.input),
              status: 'running',
            },
          ];
        } else if (event.type === 'tool_result') {
          if (event.tool === 'manage_tasks') {
            const action = typeof event.input?.action === 'string' ? event.input.action : '';
            const data = event.data as Record<string, any>;
            if (action === 'create_plan' && Array.isArray(data?.tasks)) {
               setActivePlans(prev => ({
                 ...prev,
                 [employeeId]: {
                   mode: prev[employeeId]?.mode || 'multi_step',
                   reason: prev[employeeId]?.reason || '',
                   message: prev[employeeId]?.message || '',
                   status: prev[employeeId]?.status || 'proposed',
                   tasks: data.tasks.map((task: any, i: number) => ({
                     task_id: String(task.task_id || `task-${i + 1}`),
                     order: task.order || i + 1,
                     title: task.title || `Step ${i + 1}`,
                     description: task.description || '',
                     status: task.status || 'todo',
                     priority: task.priority || 'medium',
                   })),
                 }
               }));
            }
            if (data?.task_id && data.status) {
              setActivePlans(prev => {
                const plan = prev[employeeId];
                if (!plan) return prev;
                const nextTasks = plan.tasks.map(t => 
                  t.task_id === data.task_id ? { ...t, status: String(data.status) } : t
                );
                return {
                  ...prev,
                  [employeeId]: {
                    ...plan,
                    status: nextTasks.every(t => t.status === 'done') ? 'completed' : plan.status,
                    tasks: nextTasks
                  }
                };
              });
            }
          }
          
          const idx = [...activities].reverse().findIndex(a => a.type === 'tool' && a.label === humanizeToken(event.tool || 'tool') && a.status === 'running');
          if (idx >= 0) {
            const realIdx = activities.length - 1 - idx;
            activities[realIdx] = {
              ...activities[realIdx],
              status: event.success === false ? 'error' : 'done',
              detail: event.success === false ? (event.message || event.output || 'Tool failed') : undefined,
            };
          }
        } else if (event.type === 'confirmation_required') {
          const confirmMsg = event.message || 'Waiting for your approval to continue.';
          const askType = event.ask_type || 'approval';
          // Update plan with the ask_user message as description
          if (event.plan) {
            setActivePlans(prev => ({
              ...prev,
              [employeeId]: {
                mode: (event.plan as any)?.mode || prev[employeeId]?.mode || 'multi_step',
                reason: (event.plan as any)?.reason || prev[employeeId]?.reason || '',
                message: confirmMsg,
                status: 'proposed',
                tasks: prev[employeeId]?.tasks || [],
              },
            }));
          }
          // Show the agent's question as the answer bubble
          answerBuffer = confirmMsg;
          activities = activities.map(a => a.status === 'running' ? { ...a, status: 'done' } : a);
          setIsLoading(false);
          setPendingResume({
            employeeId,
            sessionId: sessionId,
            askType,
          });
        } else if (event.type === 'task_started') {
          const taskId = event.task_id || '';
          setActivePlans(prev => {
             const plan = prev[employeeId];
             if (!plan) return prev;
             return {
               ...prev,
               [employeeId]: {
                 ...plan,
                 status: 'running',
                 tasks: plan.tasks.map(t => t.task_id === taskId ? { ...t, status: 'in_progress' } : t)
               }
             };
          });
          activities = [
            ...activities,
            {
              id: `bg-task-${taskId}-${Date.now()}`,
              type: 'tool',
              label: `Background task: ${truncateLabel(event.task_title || taskId, 60)}`,
              meta: 'Async',
              status: 'running',
            },
          ];
        } else if (event.type === 'final') {
          setPendingResume(null);
          activities = activities.map(a => a.status === 'running' ? { ...a, status: 'done' } : a);
          answerBuffer = event.content || answerBuffer;
        } else if (event.type === 'error') {
          activities = activities.map(a => a.status === 'running' ? { ...a, status: 'error', detail: event.message } : a);
          answerBuffer += `\nError: ${event.message}`;
        }

        // Update UI state
        setMessages(prev => {
          const convoMessages = prev[employeeId] || [];
          return {
            ...prev,
            [employeeId]: convoMessages.map(m => 
              m.id === assistantMessageId ? { 
                ...m, 
                text: answerBuffer,
                thinking: thinkingBuffer || undefined,
                activities: [...activities] 
              } : m
            )
          };
        });
      }
    } catch (error) {
      console.error('Chat error:', error);
      if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
      }
    } finally {
      setIsLoading(false);
      isStreamingRef.current = false;
      
      setMessages(prev => {
        const convoMessages = prev[employeeId] || [];
        return {
          ...prev,
          [employeeId]: convoMessages.map(m => {
            if (m.id === userMessage.id) return { ...m, status: 'read' };
            if (m.id === assistantMessageId) return { ...m, status: 'read' };
            return m;
          })
        };
      });
    }
  };

  const addPaneForEmployee = async (employeeId: string) => {
    if (!employeeId) return;
    const employee = employees.find((item) => item.id === employeeId);
    if (!employee) return;

    try {
      let sessionList = sessions[employeeId];
      if (!sessionList) {
        sessionList = await listEmployeeChatSessions(employeeId);
        setSessions((prev) => ({ ...prev, [employeeId]: sessionList || [] }));
      }

      const latestSession = sessionList?.[0];
      const currentSession = activeSessionId[employeeId];

      if (!latestSession || (currentSession && currentSession === latestSession.id)) {
        const newSession = await createEmployeeChatSession(employeeId, 'New Chat', employee.model);
        setSessions((prev) => ({
          ...prev,
          [employeeId]: [newSession, ...(prev[employeeId] || [])],
        }));
        setActiveSessionId((prev) => ({ ...prev, [employeeId]: newSession.id }));
        setMessages((prev) => ({ ...prev, [employeeId]: [] }));
        setActivePlans((prev) => ({ ...prev, [employeeId]: undefined }));
      } else {
        setActiveSessionId((prev) => ({ ...prev, [employeeId]: latestSession.id }));
        void fetchMessages(employeeId, latestSession.id);
      }
    } catch (error) {
      console.error('Failed to prepare session for added chat pane:', error);
      return;
    }

    setChatPanes((prev) => ([
      ...prev,
      { id: `pane-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, employeeId },
    ]));
  };

  const removePane = (paneId: string) => {
    setChatPanes((prev) => (prev.length <= 1 ? prev : prev.filter((pane) => pane.id !== paneId)));
  };

  return (
    <div className="flex-1 h-full w-full overflow-hidden">
      <div className="flex h-full overflow-x-auto overflow-y-hidden [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
        {chatPanes.map((pane) => {
          const employeeId = pane.employeeId;
          const activeEmployee = employees.find((employee) => employee.id === employeeId);
          const currentSessions = sessions[employeeId] || [];
          const currentSessionId = activeSessionId[employeeId];
          const selectedPlan = activePlans[employeeId];
          const isPlanCollapsed = collapsedPlans[employeeId] ?? false;
          const paneConversations: SidebarConversation[] = activeEmployee ? [{
            id: activeEmployee.id,
            title: activeEmployee.name,
            lastMessage: activeEmployee.role,
            presence: 'online',
          }] : [];

          const headerActions = (
            <div className="flex items-center gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className="inline-flex h-7 items-center gap-1 rounded-md border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] px-2 text-[11px] font-medium text-[var(--chat-text-primary)] transition-colors hover:bg-[var(--chat-accent-soft)]"
                  >
                    <History className="h-3.5 w-3.5" />
                    <span>Sessions</span>
                    <ChevronDown className="h-3 w-3 opacity-50" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-64">
                  <DropdownMenuLabel>
                    {activeEmployee ? `${activeEmployee.name}'s Sessions` : 'Sessions'}
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => void handleStartNewSession(employeeId)}>
                    <Plus className="mr-2 h-4 w-4" />
                    New Session
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  {currentSessions.length === 0 ? (
                    <DropdownMenuItem disabled>No sessions yet</DropdownMenuItem>
                  ) : (
                    currentSessions.map((session) => (
                      <DropdownMenuItem
                        key={session.id}
                        onClick={() => handleSwitchSession(employeeId, session.id)}
                        className="flex items-center justify-between"
                      >
                        <span className="truncate">{session.title || 'Untitled Session'}</span>
                        {currentSessionId === session.id && (
                          <span className="text-[10px] font-bold text-[var(--chat-accent)] uppercase">Active</span>
                        )}
                      </DropdownMenuItem>
                    ))
                  )}
                </DropdownMenuContent>
              </DropdownMenu>

              <button
                onClick={() => void handleStartNewSession(employeeId)}
                className="flex size-7 items-center justify-center rounded-md bg-[var(--chat-accent)] text-white transition-transform active:scale-95"
                title="New Session"
              >
                <Plus className="size-3.5" />
              </button>

              <button
                type="button"
                onClick={() => removePane(pane.id)}
                disabled={chatPanes.length <= 1}
                className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] text-[var(--chat-text-secondary)] hover:bg-[var(--chat-accent-soft)] disabled:opacity-40"
                aria-label="Close pane"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          );

          const planPanel = selectedPlan ? (
            <div className="shrink-0 border-t border-[var(--chat-border)] bg-[var(--chat-bg-main)]">
              <div className="mx-auto max-w-3xl px-3 py-1.5">
                <div className="rounded-xl border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] overflow-hidden shadow-sm">
                  <div className={cn(
                    "flex items-center justify-between gap-2 px-2.5 py-2",
                    !isPlanCollapsed && "border-b border-[var(--chat-border)]"
                  )}>
                    <div className="flex min-w-0 items-center gap-2.5">
                      <ListChecks className="h-4 w-4 shrink-0 text-[var(--chat-text-secondary)]" />
                      <div className="min-w-0">
                        <div className="truncate text-[13px] font-medium leading-4 text-[var(--chat-text-primary)]">
                          {selectedPlan.tasks.filter((task) => task.status === 'done').length} of {selectedPlan.tasks.length} tasks completed
                        </div>
                        <div className="truncate text-[11px] leading-4 text-[var(--chat-text-tertiary)] mt-0.5">
                          {selectedPlan.message || selectedPlan.reason || 'Agent-generated execution plan'}
                        </div>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <div className="rounded-full border border-[var(--chat-border)] px-2 py-0.5 text-[11px] text-[var(--chat-text-secondary)]">
                        {selectedPlan.status === 'approved' ? 'Approved' : selectedPlan.status === 'running' ? 'Running' : selectedPlan.status === 'completed' ? 'Completed' : 'Needs approval'}
                      </div>
                      <button
                        type="button"
                        onClick={() => setCollapsedPlans((prev) => ({ ...prev, [employeeId]: !isPlanCollapsed }))}
                        className="inline-flex h-7 w-7 items-center justify-center rounded-md text-[var(--chat-text-secondary)] hover:bg-[var(--chat-accent-soft)]"
                        aria-label={isPlanCollapsed ? 'Expand task plan' : 'Collapse task plan'}
                      >
                        <ChevronDown className={cn("h-4 w-4 transition-transform", !isPlanCollapsed && "rotate-180")} />
                      </button>
                    </div>
                  </div>

                  {!isPlanCollapsed && (
                    <div className="max-h-40 space-y-1.5 overflow-y-auto px-2.5 py-2 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
                      {selectedPlan.tasks.map((task, index) => (
                        <div key={task.task_id} className="flex items-start gap-2.5">
                          <div className="pt-0.5">
                            {task.status === 'done' ? (
                              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                            ) : task.status === 'in_progress' ? (
                              <span className="mt-0.5 block h-3 w-3 rounded-full border-2 border-amber-400 border-t-transparent animate-spin" />
                            ) : task.status === 'blocked' || task.status === 'cancelled' ? (
                              <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
                            ) : (
                              <span className="mt-1 block h-3 w-3 rounded-full border border-[var(--chat-text-tertiary)]" />
                            )}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className={cn("text-[12px] leading-5", task.status === 'done' ? "text-[var(--chat-text-tertiary)] line-through" : "text-[var(--chat-text-secondary)]")}>
                              {index + 1}. {task.title}
                            </div>
                            {task.description && (
                              <div className="mt-0.5 text-[11px] leading-[18px] text-[var(--chat-text-tertiary)]">
                                {task.description}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {pendingResume && pendingResume.employeeId === employeeId && pendingResume.askType === 'approval' && selectedPlan.status !== 'approved' && selectedPlan.status !== 'running' && selectedPlan.status !== 'completed' && (
                    <div className="flex items-center justify-end gap-2 border-t border-[var(--chat-border)] px-2.5 py-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => void handlePlanDecision(false)}
                        disabled={isResuming}
                        className="h-8 px-3 text-[11px]"
                      >
                        Reject
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => void handlePlanDecision(true)}
                        disabled={isResuming}
                        className="h-8 px-3 text-[11px]"
                      >
                        {isResuming ? 'Approving…' : 'Approve plan'}
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : null;

          return (
            <div
              key={pane.id}
              className="flex h-full min-h-0 w-[460px] shrink-0 flex-col overflow-hidden border-r border-r-[#e8edf3] bg-[var(--chat-bg-app)]"
            >
              <div className="min-h-0 flex-1">
                <FullMessenger
                  currentUser={currentUser}
                  conversations={paneConversations}
                  activeConversationId={employeeId}
                  onSelectConversation={() => {}}
                  messages={messages[employeeId] || []}
                  onSend={(text) => void handleSend(employeeId, text)}
                  title="Employees"
                  theme="lunar"
                  className="h-full w-full [--chat-bg-app:#f8fafc] [--chat-bg-sidebar:#f8fafc] [--chat-bg-main:#ffffff] [--chat-bg-header:rgba(255,255,255,0.95)] [--chat-bg-composer:rgba(255,255,255,0.96)] [--chat-bubble-outgoing:#334155] [--chat-bubble-outgoing-text:#f8fafc] [--chat-bubble-incoming:#f1f5f9] [--chat-bubble-incoming-text:#0f172a] [--chat-text-primary:#0f172a] [--chat-text-secondary:#475569] [--chat-text-tertiary:#64748b] [--chat-border:rgba(15,23,42,0.08)] [--chat-border-strong:rgba(15,23,42,0.12)] [--chat-accent:#334155] [--chat-accent-soft:rgba(51,65,85,0.08)]"
                  headerActions={headerActions}
                  beforeComposer={planPanel}
                  conversationStyle="tabs"
                  hideConversationTabs
                  messagesClassName="px-2"
                  composerClassName="px-2 py-1"
                />
              </div>
            </div>
          );
        })}
        <div className="flex h-full min-h-0 w-[460px] shrink-0 items-center justify-center border-r border-r-[#e8edf3] bg-[var(--chat-bg-app)]">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-xl border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] px-4 py-3 text-[14px] font-semibold text-[var(--chat-text-primary)] transition-colors hover:bg-[var(--chat-accent-soft)]"
              >
                <Plus className="h-4 w-4" />
                <span>Add Chat</span>
                <ChevronDown className="h-3.5 w-3.5 opacity-60" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="center" className="w-64">
              <DropdownMenuLabel>Select Employee</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {employees.length === 0 ? (
                <DropdownMenuItem disabled>No employees available</DropdownMenuItem>
              ) : (
                employees.map((employee) => (
                  <DropdownMenuItem
                    key={employee.id}
                    onClick={() => void addPaneForEmployee(employee.id)}
                  >
                    {employee.name}
                  </DropdownMenuItem>
                ))
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </div>
  );
}
