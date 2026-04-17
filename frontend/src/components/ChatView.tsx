import React, { useState, useEffect, useRef } from 'react';
import { FullMessenger } from '@/components/ui/chat/layouts';
import type { ChatMessageData, ChatUser } from '@/components/ui/chat/types';
import type { SidebarConversation } from '@/components/ui/chat/layouts';
import { Plus, History, ChevronDown, ListChecks, CheckCircle2, AlertCircle } from 'lucide-react';
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
  const [activeEmployeeId, setActiveEmployeeId] = useState<string>('');
  const [sessions, setSessions] = useState<Record<string, ChatSession[]>>({});
  const [activeSessionId, setActiveSessionId] = useState<Record<string, string>>({});
  const [messages, setMessages] = useState<Record<string, ChatMessageData[]>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [activePlans, setActivePlans] = useState<Record<string, ChatMessageData['plan']>>({});
  const [isPlanCollapsed, setIsPlanCollapsed] = useState(false);
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
        if (data.length > 0 && !activeEmployeeId) {
          setActiveEmployeeId(data[0].id);
        }
      } catch (error) {
        console.error('Failed to fetch employees:', error);
      }
    }
    fetchEmployees();
  }, []);

  useEffect(() => {
    if (!activeEmployeeId) return;

    async function fetchSessions() {
      try {
        const sessionList = await listEmployeeChatSessions(activeEmployeeId);
        setSessions(prev => ({ ...prev, [activeEmployeeId]: sessionList }));
        
        if (!activeSessionId[activeEmployeeId] && sessionList.length > 0) {
          const firstSessionId = sessionList[0].id;
          setActiveSessionId(prev => ({ ...prev, [activeEmployeeId]: firstSessionId }));
          void fetchMessages(activeEmployeeId, firstSessionId);
        } else if (sessionList.length === 0) {
          setMessages(prev => ({ ...prev, [activeEmployeeId]: [] }));
        }
      } catch (error) {
        console.error('Failed to fetch sessions:', error);
      }
    }
    
    fetchSessions();
  }, [activeEmployeeId]);

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

  const handleSelectConversation = (id: string) => {
    setActiveEmployeeId(id);
    if (activeSessionId[id]) {
      void fetchMessages(id, activeSessionId[id]);
    }
  };

  const handleStartNewSession = async () => {
    if (!activeEmployeeId) return;
    const activeEmployee = employees.find(e => e.id === activeEmployeeId);
    if (!activeEmployee) return;

    try {
      const newSession = await createEmployeeChatSession(activeEmployeeId, 'New Chat', activeEmployee.model);
      setSessions(prev => ({
        ...prev,
        [activeEmployeeId]: [newSession, ...(prev[activeEmployeeId] || [])]
      }));
      setActiveSessionId(prev => ({ ...prev, [activeEmployeeId]: newSession.id }));
      setMessages(prev => ({ ...prev, [activeEmployeeId]: [] }));
      setActivePlans(prev => ({ ...prev, [activeEmployeeId]: undefined }));
    } catch (error) {
      console.error('Failed to create new session:', error);
    }
  };

  const handleSwitchSession = (sessionId: string) => {
    setActiveSessionId(prev => ({ ...prev, [activeEmployeeId]: sessionId }));
    void fetchMessages(activeEmployeeId, sessionId);
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

  const handleSend = async (text: string) => {
    if (!activeEmployeeId) return;
    const activeEmployee = employees.find(e => e.id === activeEmployeeId);
    if (!activeEmployee) return;

    let sessionId = activeSessionId[activeEmployeeId];
    
    if (!sessionId) {
      try {
        const newSession = await createEmployeeChatSession(activeEmployeeId, 'New Chat', activeEmployee.model);
        sessionId = newSession.id;
        setActiveSessionId(prev => ({ ...prev, [activeEmployeeId]: sessionId }));
        setSessions(prev => ({
          ...prev,
          [activeEmployeeId]: [newSession, ...(prev[activeEmployeeId] || [])]
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
      [activeEmployeeId]: [...(prev[activeEmployeeId] || []), userMessage]
    }));

    setIsLoading(true);
    isStreamingRef.current = true;

    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessageData = {
      id: assistantMessageId,
      senderId: activeEmployeeId,
      senderName: activeEmployee.name,
      text: '',
      timestamp: new Date(),
      status: 'sending',
      activities: [],
    };

    setMessages(prev => ({
      ...prev,
      [activeEmployeeId]: [...(prev[activeEmployeeId] || []), assistantMessage]
    }));

    try {
      const history = (messages[activeEmployeeId] || []).map(m => ({
        role: m.senderId === currentUser.id ? 'user' : 'assistant',
        content: m.text || ''
      }));

      let answerBuffer = '';
      let thinkingBuffer = '';
      let activities: NonNullable<ChatMessageData['activities']> = [];
      
      const stream = streamEmployeeChatEvents(activeEmployeeId, {
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
            const convoMessages = prev[activeEmployeeId] || [];
            return {
              ...prev,
              [activeEmployeeId]: convoMessages.map(m =>
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
          setActivePlans(prev => ({ ...prev, [activeEmployeeId]: planData }));
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
                 [activeEmployeeId]: {
                   mode: prev[activeEmployeeId]?.mode || 'multi_step',
                   reason: prev[activeEmployeeId]?.reason || '',
                   message: prev[activeEmployeeId]?.message || '',
                   status: prev[activeEmployeeId]?.status || 'proposed',
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
                const plan = prev[activeEmployeeId];
                if (!plan) return prev;
                const nextTasks = plan.tasks.map(t => 
                  t.task_id === data.task_id ? { ...t, status: String(data.status) } : t
                );
                return {
                  ...prev,
                  [activeEmployeeId]: {
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
              [activeEmployeeId]: {
                mode: (event.plan as any)?.mode || prev[activeEmployeeId]?.mode || 'multi_step',
                reason: (event.plan as any)?.reason || prev[activeEmployeeId]?.reason || '',
                message: confirmMsg,
                status: 'proposed',
                tasks: prev[activeEmployeeId]?.tasks || [],
              },
            }));
          }
          // Show the agent's question as the answer bubble
          answerBuffer = confirmMsg;
          activities = activities.map(a => a.status === 'running' ? { ...a, status: 'done' } : a);
          setIsLoading(false);
          setPendingResume({
            employeeId: activeEmployeeId,
            sessionId: sessionId,
            askType,
          });
        } else if (event.type === 'task_started') {
          const taskId = event.task_id || '';
          setActivePlans(prev => {
             const plan = prev[activeEmployeeId];
             if (!plan) return prev;
             return {
               ...prev,
               [activeEmployeeId]: {
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
          const convoMessages = prev[activeEmployeeId] || [];
          return {
            ...prev,
            [activeEmployeeId]: convoMessages.map(m => 
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
        const convoMessages = prev[activeEmployeeId] || [];
        return {
          ...prev,
          [activeEmployeeId]: convoMessages.map(m => {
            if (m.id === userMessage.id) return { ...m, status: 'read' };
            if (m.id === assistantMessageId) return { ...m, status: 'read' };
            return m;
          })
        };
      });
    }
  };

  const conversations: SidebarConversation[] = employees.map(e => ({
    id: e.id,
    title: e.name,
    lastMessage: e.role,
    presence: 'online',
  }));

  const activeEmployee = employees.find(e => e.id === activeEmployeeId);
  const currentSessions = sessions[activeEmployeeId] || [];
  const currentSessionId = activeSessionId[activeEmployeeId];

  const headerActions = (
    <div className="flex items-center gap-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] px-2.5 text-[12px] font-medium text-[var(--chat-text-primary)] transition-colors hover:bg-[var(--chat-accent-soft)]"
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
          <DropdownMenuItem onClick={handleStartNewSession}>
            <Plus className="mr-2 h-4 w-4" />
            New Session
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          {currentSessions.length === 0 ? (
            <DropdownMenuItem disabled>No sessions yet</DropdownMenuItem>
          ) : (
            currentSessions.map((s) => (
              <DropdownMenuItem
                key={s.id}
                onClick={() => handleSwitchSession(s.id)}
                className="flex items-center justify-between"
              >
                <span className="truncate">{s.title || 'Untitled Session'}</span>
                {currentSessionId === s.id && (
                  <span className="text-[10px] font-bold text-[var(--chat-accent)] uppercase">Active</span>
                )}
              </DropdownMenuItem>
            ))
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <button
        onClick={handleStartNewSession}
        className="flex size-8 items-center justify-center rounded-lg bg-[var(--chat-accent)] text-white transition-transform active:scale-95"
        title="New Session"
      >
        <Plus className="size-4" />
      </button>
    </div>
  );

  const selectedPlan = activePlans[activeEmployeeId];

  const planPanel = selectedPlan ? (
    <div className="shrink-0 border-t border-[var(--chat-border)] bg-[var(--chat-bg-main)]">
      <div className="mx-auto max-w-3xl px-4 py-2">
        <div className="rounded-xl border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] overflow-hidden shadow-sm">
          <div className={cn(
            "flex items-center justify-between gap-3 px-3 py-2.5",
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
                onClick={() => setIsPlanCollapsed(!isPlanCollapsed)}
                className="inline-flex h-7 w-7 items-center justify-center rounded-md text-[var(--chat-text-secondary)] hover:bg-[var(--chat-accent-soft)]"
                aria-label={isPlanCollapsed ? 'Expand task plan' : 'Collapse task plan'}
              >
                <ChevronDown className={cn("h-4 w-4 transition-transform", !isPlanCollapsed && "rotate-180")} />
              </button>
            </div>
          </div>

          {!isPlanCollapsed && (
          <div className="max-h-52 space-y-2 overflow-y-auto px-3 py-2.5">
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

          {pendingResume && pendingResume.askType === 'approval' && selectedPlan.status !== 'approved' && selectedPlan.status !== 'running' && selectedPlan.status !== 'completed' && (
            <div className="flex items-center justify-end gap-2 border-t border-[var(--chat-border)] px-3 py-2.5">
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
    <div className="flex-1 h-full w-full overflow-hidden flex">
      <FullMessenger
        currentUser={currentUser}
        conversations={conversations}
        activeConversationId={activeEmployeeId}
        onSelectConversation={handleSelectConversation}
        messages={messages[activeEmployeeId] || []}
        onSend={handleSend}
        title="Employees"
        theme="lunar"
        className="w-full h-full"
        headerActions={headerActions}
        beforeComposer={planPanel}
      />
    </div>
  );
}
