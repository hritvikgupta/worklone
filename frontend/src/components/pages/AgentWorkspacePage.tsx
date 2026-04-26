import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronsLeft,
  ChevronsRight,
  ListChecks,
  Loader2,
  Plus,
} from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  CHAT_AUTH_EXPIRED_ERROR,
  ChatSession,
  createEmployeeChatSession,
  getEmployeeChatSessionMessages,
  listEmployeeChatSessions,
  resumeEmployeeChat,
  streamEmployeeChatEvents,
} from '@/lib/api';
import { getEmployee, updateEmployee, EmployeeWithDetails } from '@/src/api/employees';
import { EmployeePanel, EmployeeFormData } from '@/src/components/EmployeePanel';
import { FullMessenger } from '@/components/ui/chat/layouts';
import type { ChatMessageData, ChatUser } from '@/components/ui/chat/types';
import type { SidebarConversation } from '@/components/ui/chat/layouts';
import { useAuth } from '@/src/contexts/AuthContext';
import { useEmployeePresence } from '@/src/hooks/usePresence';

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

function toConfigForm(employee: EmployeeWithDetails): EmployeeFormData {
  return {
    name: employee.employee.name,
    role: employee.employee.role,
    avatar_url: employee.employee.avatar_url,
    cover_url: employee.employee.cover_url || '',
    description: employee.employee.description,
    system_prompt: employee.employee.system_prompt,
    model: employee.employee.model,
    provider: employee.employee.provider || '',
    temperature: employee.employee.temperature,
    max_tokens: employee.employee.max_tokens,
    tools: employee.tools.filter((tool) => tool.is_enabled).map((tool) => tool.tool_name),
    skills: employee.skills.map((skill) => ({
      skill_name: skill.skill_name,
      category: skill.category,
      proficiency_level: skill.proficiency_level,
      description: skill.description,
    })),
    memory: employee.employee.memory || [],
  };
}

export function AgentWorkspacePage() {
  const navigate = useNavigate();
  const { agentId } = useParams<{ agentId: string }>();
  const employeeId = agentId || '';
  const { logout, user } = useAuth();

  const currentUser: ChatUser = {
    id: user?.id || 'user-1',
    name: user?.name || 'Current User',
    avatar: user?.avatar_url || `https://i.pravatar.cc/150?u=${user?.id || 'current'}`,
  };

  const [employee, setEmployee] = useState<EmployeeWithDetails | null>(null);
  const [loadingEmployee, setLoadingEmployee] = useState(true);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState('');
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activePlan, setActivePlan] = useState<ChatMessageData['plan']>();
  const [collapsedPlans, setCollapsedPlans] = useState<Record<string, boolean>>({});
  const [pendingResume, setPendingResume] = useState<{
    employeeId: string;
    sessionId: string;
    askType: string;
  } | null>(null);
  const [isResuming, setIsResuming] = useState(false);
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);

  const isStreamingRef = useRef(false);
  const pendingNewAssistantRef = useRef<{ id: string; senderName: string } | null>(null);
  const configFormData = useMemo(() => (employee ? toConfigForm(employee) : null), [employee]);
  const { isBusy, busyIn } = useEmployeePresence([employeeId], user?.id);

  const refreshEmployee = async () => {
    if (!employeeId) return;
    const detail = await getEmployee(employeeId);
    setEmployee(detail);
  };

  const fetchSessions = async () => {
    if (!employeeId) return;
    try {
      const list = await listEmployeeChatSessions(employeeId);
      setSessions(list);
      if (!activeSessionId && list.length > 0) {
        const firstSessionId = list[0].id;
        setActiveSessionId(firstSessionId);
        void fetchMessages(firstSessionId);
      } else if (list.length === 0) {
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    }
  };

  const fetchMessages = async (sessionId: string) => {
    if (!employee || !employeeId || !sessionId) return;
    try {
      const history = await getEmployeeChatSessionMessages(employeeId, sessionId);
      const mappedMessages: ChatMessageData[] = history.map((msg, idx) => ({
        id: `msg-${idx}-${Date.now()}`,
        senderId: msg.role === 'user' ? currentUser.id : employeeId,
        senderName: msg.role === 'user' ? currentUser.name : employee.employee.name,
        text: msg.content,
        timestamp: new Date(msg.created_at),
        status: 'read',
      }));
      setMessages(mappedMessages);
      setActivePlan(undefined);
      setPendingResume(null);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  };

  const handleStartNewSession = async () => {
    if (!employeeId || !employee) return;
    try {
      const newSession = await createEmployeeChatSession(employeeId, 'New Chat', employee.employee.model);
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      setMessages([]);
      setActivePlan(undefined);
    } catch (error) {
      console.error('Failed to create new session:', error);
    }
  };

  const handleSwitchSession = (sessionId: string) => {
    setActiveSessionId(sessionId);
    void fetchMessages(sessionId);
  };

  const handlePlanDecision = async (approved: boolean) => {
    if (!pendingResume) return;
    const captured = pendingResume;
    setPendingResume(null);
    setIsResuming(true);
    const userMsg: ChatMessageData = {
      id: `user-${Date.now()}`,
      senderId: currentUser.id,
      senderName: currentUser.name,
      text: approved ? 'Approved' : 'Rejected',
      timestamp: new Date(),
      status: 'read',
    };
    const next = pendingNewAssistantRef.current;
    pendingNewAssistantRef.current = null;
    setMessages((prev) => {
      const newMsgs: ChatMessageData[] = [userMsg];
      if (next) {
        newMsgs.push({ id: next.id, senderId: employeeId, senderName: next.senderName, text: '', timestamp: new Date(), status: 'sending', activities: [] });
      }
      return [...prev, ...newMsgs];
    });
    setActivePlan((prev) => {
      if (!prev) return prev;
      return { ...prev, status: approved ? 'approved' : 'proposed' };
    });
    try {
      await resumeEmployeeChat(captured.employeeId, {
        approved,
        message: approved ? 'Approved' : 'Rejected',
        session_id: captured.sessionId,
      });
    } catch (e) {
      console.error('Failed to resume:', e);
    } finally {
      setIsResuming(false);
    }
  };

  const handleResumeWithInput = async (text: string) => {
    if (!pendingResume || pendingResume.employeeId !== employeeId) return;
    const captured = pendingResume;
    setPendingResume(null);
    const userMsg: ChatMessageData = {
      id: `user-${Date.now()}`,
      senderId: currentUser.id,
      senderName: currentUser.name,
      text,
      timestamp: new Date(),
      status: 'read',
    };
    const next = pendingNewAssistantRef.current;
    pendingNewAssistantRef.current = null;
    setMessages((prev) => {
      const newMsgs: ChatMessageData[] = [userMsg];
      if (next) {
        newMsgs.push({ id: next.id, senderId: employeeId, senderName: next.senderName, text: '', timestamp: new Date(), status: 'sending', activities: [] });
      }
      return [...prev, ...newMsgs];
    });
    try {
      await resumeEmployeeChat(captured.employeeId, {
        approved: true,
        message: text,
        session_id: captured.sessionId,
      });
    } catch (e) {
      console.error('Failed to resume with input:', e);
    }
  };

  const handleSend = async (text: string) => {
    if (!employeeId || !employee) return;

    let sessionId = activeSessionId;

    if (!sessionId) {
      try {
        const newSession = await createEmployeeChatSession(employeeId, 'New Chat', employee.employee.model);
        sessionId = newSession.id;
        setActiveSessionId(sessionId);
        setSessions((prev) => [newSession, ...(prev || [])]);
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

    setMessages((prev) => [...prev, userMessage]);

    setIsLoading(true);
    isStreamingRef.current = true;

    const assistantMessageId = `assistant-${Date.now()}`;
    let currentAssistantId = assistantMessageId;
    const assistantMessage: ChatMessageData = {
      id: assistantMessageId,
      senderId: employeeId,
      senderName: employee.employee.name,
      text: '',
      timestamp: new Date(),
      status: 'sending',
      activities: [],
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      const history = messages.map((m) => ({
        role: m.senderId === currentUser.id ? 'user' : 'assistant',
        content: m.text || '',
      }));

      let answerBuffer = '';
      let thinkingBuffer = '';
      let activities: NonNullable<ChatMessageData['activities']> = [];
      let toolsCompletedSinceLastThink = 0;

      const advancePlanTask = (toStatus: 'in_progress' | 'done') => {
        setActivePlan((prev) => {
          if (!prev || prev.status === 'proposed' || prev.status === 'completed') return prev;
          if (toStatus === 'in_progress') {
            const firstTodo = prev.tasks.findIndex((t) => t.status === 'todo');
            if (firstTodo < 0 || prev.tasks.some((t) => t.status === 'in_progress')) return prev;
            const nextTasks = prev.tasks.map((t, i) => i === firstTodo ? { ...t, status: 'in_progress' } : t);
            return { ...prev, tasks: nextTasks };
          } else {
            const inProg = prev.tasks.findIndex((t) => t.status === 'in_progress');
            if (inProg < 0) return prev;
            const nextTasks = prev.tasks.map((t, i) => i === inProg ? { ...t, status: 'done' } : t);
            const nextTodo = nextTasks.findIndex((t) => t.status === 'todo');
            if (nextTodo >= 0) nextTasks[nextTodo] = { ...nextTasks[nextTodo], status: 'in_progress' };
            const allDone = nextTasks.every((t) => t.status === 'done');
            return { ...prev, status: allDone ? 'completed' : 'running', tasks: nextTasks };
          }
        });
      };

      const stream = streamEmployeeChatEvents(employeeId, {
        message: text,
        conversation_history: history,
        model: employee.employee.model,
        session_id: sessionId,
      });

      for await (const event of stream) {
        if (event.type === 'content_token') {
          const token = event.token || '';
          if (token) {
            answerBuffer += token;
          }
          setMessages((prev) =>
            prev.map((m) =>
              m.id === currentAssistantId
                ? {
                    ...m,
                    text: answerBuffer,
                    status: 'sending',
                  }
                : m,
            ),
          );
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
          setActivePlan(planData);
          continue;
        }

        if (event.type === 'thinking') {
          const thought = event.content || '';
          if (thought) {
            if (toolsCompletedSinceLastThink > 0) {
              advancePlanTask('done');
            } else {
              advancePlanTask('in_progress');
            }
            toolsCompletedSinceLastThink = 0;
            thinkingBuffer += `${thought}\n\n`;
            answerBuffer = '';
            activities = activities.map((a) =>
              a.type === 'thinking' && a.status === 'running' ? { ...a, status: 'done' } : a,
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
          activities = activities.map((a) =>
            a.type === 'thinking' && a.status === 'running' ? { ...a, status: 'done' } : a,
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
              setActivePlan((prev) => ({
                mode: prev?.mode || 'multi_step',
                reason: prev?.reason || '',
                message: prev?.message || '',
                status: prev?.status || 'proposed',
                tasks: data.tasks.map((task: any, i: number) => ({
                  task_id: String(task.task_id || `task-${i + 1}`),
                  order: task.order || i + 1,
                  title: task.title || `Step ${i + 1}`,
                  description: task.description || '',
                  status: task.status || 'todo',
                  priority: task.priority || 'medium',
                })),
              }));
            }
            if (data?.task_id && data.status) {
              setActivePlan((prev) => {
                if (!prev) return prev;
                const nextTasks = prev.tasks.map((t) =>
                  t.task_id === data.task_id ? { ...t, status: String(data.status) } : t,
                );
                return {
                  ...prev,
                  status: nextTasks.every((t) => t.status === 'done') ? 'completed' : prev.status,
                  tasks: nextTasks,
                };
              });
            }
          }

          const idx = [...activities]
            .reverse()
            .findIndex(
              (a) => a.type === 'tool' && a.label === humanizeToken(event.tool || 'tool') && a.status === 'running',
            );
          if (idx >= 0) {
            const realIdx = activities.length - 1 - idx;
            activities[realIdx] = {
              ...activities[realIdx],
              status: event.success === false ? 'error' : 'done',
              detail: event.success === false ? event.message || event.output || 'Tool failed' : undefined,
            };
          }
          if (event.success !== false && event.tool !== 'manage_tasks') {
            toolsCompletedSinceLastThink++;
          }
        } else if (event.type === 'confirmation_required') {
          const confirmMsg = event.message || 'Waiting for your approval to continue.';
          const askType = event.ask_type || 'approval';
          if (event.plan) {
            setActivePlan((prev) => ({
              mode: (event.plan as any)?.mode || prev?.mode || 'multi_step',
              reason: (event.plan as any)?.reason || prev?.reason || '',
              message: confirmMsg,
              status: 'proposed',
              tasks: prev?.tasks || [],
            }));
          }
          // Finalize the current assistant bubble with the question text
          const doneActivities = activities.map((a) => (a.status === 'running' ? { ...a, status: 'done' } : a));
          const finishedId = currentAssistantId;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === finishedId ? { ...m, text: confirmMsg, activities: doneActivities, status: 'read' } : m,
            ),
          );
          // Prepare next phase bubble (added to state by handlePlanDecision/handleResumeWithInput)
          const nextId = `assistant-${Date.now()}-r`;
          currentAssistantId = nextId;
          pendingNewAssistantRef.current = { id: nextId, senderName: employee.employee.name };
          // Reset buffers
          answerBuffer = '';
          activities = [];
          thinkingBuffer = '';
          toolsCompletedSinceLastThink = 0;
          setIsLoading(false);
          setPendingResume({
            employeeId,
            sessionId,
            askType,
          });
        } else if (event.type === 'task_started') {
          const taskId = event.task_id || '';
          setActivePlan((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              status: 'running',
              tasks: prev.tasks.map((t) => (t.task_id === taskId ? { ...t, status: 'in_progress' } : t)),
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
          activities = activities.map((a) => (a.status === 'running' ? { ...a, status: 'done' } : a));
          answerBuffer = event.content || answerBuffer;
          // Auto-complete any tasks the agent didn't explicitly mark done
          // (happens when agent uses execute_workflow, run_task_async, or skips complete_task)
          setActivePlan((prev) => {
            if (!prev) return prev;
            const nextTasks = prev.tasks.map((t) =>
              t.status === 'todo' || t.status === 'in_progress'
                ? { ...t, status: 'done' }
                : t
            );
            return { ...prev, status: 'completed', tasks: nextTasks };
          });
        } else if (event.type === 'error') {
          activities = activities.map((a) =>
            a.status === 'running' ? { ...a, status: 'error', detail: event.message } : a,
          );
          answerBuffer += `\nError: ${event.message}`;
        }

        setMessages((prev) =>
          prev.map((m) =>
            m.id === currentAssistantId
              ? {
                  ...m,
                  text: answerBuffer,
                  thinking: thinkingBuffer || undefined,
                  activities: [...activities],
                }
              : m,
          ),
        );
      }
    } catch (error) {
      console.error('Chat error:', error);
      if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
      }
    } finally {
      setIsLoading(false);
      isStreamingRef.current = false;

      setMessages((prev) =>
        prev.map((m) => {
          if (m.id === userMessage.id) return { ...m, status: 'read' };
          if (m.id === currentAssistantId) return { ...m, status: 'read' };
          return m;
        }),
      );
    }
  };

  const handleSaveConfig = async (form: EmployeeFormData) => {
    if (!employeeId) return;
    setIsSavingConfig(true);
    try {
      await updateEmployee(employeeId, form);
      await refreshEmployee();
    } catch (error) {
      console.error('Failed to save employee config:', error);
    } finally {
      setIsSavingConfig(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    if (!employeeId) return;

    async function load() {
      setLoadingEmployee(true);
      try {
        const detail = await getEmployee(employeeId);
        if (cancelled) return;
        setEmployee(detail);
        const sessionList = await listEmployeeChatSessions(employeeId);
        if (cancelled) return;
        setSessions(sessionList);
        if (sessionList.length > 0) {
          setActiveSessionId(sessionList[0].id);
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load employee workspace:', error);
          setEmployee(null);
          setSessions([]);
        }
      } finally {
        if (!cancelled) setLoadingEmployee(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [employeeId]);

  useEffect(() => {
    if (!employeeId || !employee) return;
    if (sessions.length === 0) {
      void fetchSessions();
      return;
    }
    if (!activeSessionId && sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
    }
  }, [employeeId, employee, sessions.length]);

  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }
    void fetchMessages(activeSessionId);
  }, [activeSessionId, employeeId, employee?.employee.name]);

  if (!employeeId) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
        Missing employee id.
      </div>
    );
  }

  if (loadingEmployee) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        Loading workspace...
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
        Employee not found.
      </div>
    );
  }

  const isPlanCollapsed = collapsedPlans[employeeId] ?? false;
  const conversations: SidebarConversation[] = [
    {
      id: employeeId,
      title: employee.employee.name,
      lastMessage: employee.employee.role,
      presence: 'online',
    },
  ];

  const paneBusy = !!employeeId && isBusy(employeeId);
  const paneBusyCtx = busyIn(employeeId);
  const busyLabel = paneBusyCtx
    ? `${employee.employee.name} is busy on ${paneBusyCtx.kind}${paneBusyCtx.run_id ? ` · ${paneBusyCtx.run_id}` : ''} — please wait`
    : `${employee.employee.name} is busy — please wait`;
  const hasInputPending = pendingResume?.employeeId === employeeId && pendingResume.askType === 'input';
  const isComposerDisabled = (paneBusy || isLoading) && !hasInputPending;

  const headerActions = (
    <div className="flex items-center gap-2">
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-muted-foreground hover:text-foreground"
        onClick={() => setRightPanelOpen((prev) => !prev)}
        aria-label={rightPanelOpen ? 'Close right panel' : 'Open right panel'}
      >
        {rightPanelOpen ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
      </Button>
    </div>
  );

  const planPanel = activePlan ? (
    <div className="shrink-0 border-t border-[var(--chat-border)] bg-[var(--chat-bg-main)]">
      <div className="mx-auto max-w-3xl px-3 py-1.5">
        <div className="rounded-xl border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] overflow-hidden shadow-sm">
          <div
            className={cn(
              'flex items-center justify-between gap-2 px-2.5 py-2',
              !isPlanCollapsed && 'border-b border-[var(--chat-border)]',
            )}
          >
            <div className="flex min-w-0 items-center gap-2.5">
              <ListChecks className="h-4 w-4 shrink-0 text-[var(--chat-text-secondary)]" />
              <div className="min-w-0">
                <div className="truncate text-[13px] font-medium leading-4 text-[var(--chat-text-primary)]">
                  {activePlan.tasks.filter((task) => task.status === 'done').length} of {activePlan.tasks.length}{' '}
                  tasks completed
                </div>
                <div className="truncate text-[11px] leading-4 text-[var(--chat-text-tertiary)] mt-0.5">
                  {activePlan.message || activePlan.reason || 'Agent-generated execution plan'}
                </div>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <div className="rounded-full border border-[var(--chat-border)] px-2 py-0.5 text-[11px] text-[var(--chat-text-secondary)]">
                {activePlan.status === 'approved'
                  ? 'Approved'
                  : activePlan.status === 'running'
                    ? 'Running'
                    : activePlan.status === 'completed'
                      ? 'Completed'
                      : 'Needs approval'}
              </div>
              <button
                type="button"
                onClick={() => setCollapsedPlans((prev) => ({ ...prev, [employeeId]: !isPlanCollapsed }))}
                className="inline-flex h-7 w-7 items-center justify-center rounded-md text-[var(--chat-text-secondary)] hover:bg-[var(--chat-accent-soft)]"
                aria-label={isPlanCollapsed ? 'Expand task plan' : 'Collapse task plan'}
              >
                <ChevronDown className={cn('h-4 w-4 transition-transform', !isPlanCollapsed && 'rotate-180')} />
              </button>
            </div>
          </div>

          {!isPlanCollapsed && (
            <div className="max-h-40 space-y-1.5 overflow-y-auto px-2.5 py-2 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
              {activePlan.tasks.map((task, index) => (
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
                    <div
                      className={cn(
                        'text-[12px] leading-5',
                        task.status === 'done'
                          ? 'text-[var(--chat-text-tertiary)] line-through'
                          : 'text-[var(--chat-text-secondary)]',
                      )}
                    >
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

          {pendingResume && pendingResume.employeeId === employeeId && pendingResume.askType === 'input' && (
            <div className="flex items-center gap-2 border-t border-[var(--chat-border)] px-2.5 py-2 text-[11px] text-[var(--chat-text-secondary)]">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-amber-500" />
              Type your response in the message box below
            </div>
          )}

          {pendingResume &&
            pendingResume.employeeId === employeeId &&
            pendingResume.askType === 'approval' &&
            activePlan.status !== 'approved' &&
            activePlan.status !== 'running' &&
            activePlan.status !== 'completed' && (
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

  const composerBanner = paneBusy ? (
    <div className="shrink-0 border-t border-amber-200 bg-amber-50 px-3 py-1.5 text-[11px] font-medium text-amber-800">
      <div className="mx-auto flex max-w-3xl items-center gap-2">
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-amber-500" />
        <span>{busyLabel}</span>
      </div>
    </div>
  ) : null;

  const composerSlot = (
    <>
      {composerBanner}
      {planPanel}
    </>
  );

  return (
    <div className="h-full min-h-0 overflow-hidden bg-white">
      <div className={cn('h-full min-h-0 grid', rightPanelOpen ? 'grid-cols-[280px_minmax(0,1fr)_420px]' : 'grid-cols-[280px_minmax(0,1fr)]')}>
        <aside className="border-r border-border h-full min-h-0 flex flex-col bg-white overflow-hidden">
          <div className="p-4 border-b border-border space-y-3">
            <Button variant="ghost" className="w-full justify-start gap-2" onClick={() => navigate('/agents')}>
              <ChevronLeft className="h-4 w-4" />
              Go back
            </Button>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Employee</p>
              <h2 className="font-semibold truncate">{employee.employee.name}</h2>
            </div>
            <Button className="w-full gap-2" variant="outline" onClick={() => void handleStartNewSession()}>
              <Plus className="h-4 w-4" />
              New Session
            </Button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-3 space-y-2">
            {sessions.length === 0 ? (
              <div className="text-xs text-muted-foreground px-2 py-3">No chats yet</div>
            ) : (
              sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => handleSwitchSession(session.id)}
                  className={cn(
                    'w-full text-left rounded-lg border px-3 py-2.5 transition-colors',
                    activeSessionId === session.id ? 'border-primary bg-primary/5' : 'border-border bg-background hover:bg-muted/60',
                  )}
                >
                  <div className="text-sm font-medium truncate">{session.title || 'Untitled Chat'}</div>
                </button>
              ))
            )}
          </div>
        </aside>

        <main className="h-full min-h-0 min-w-0 relative bg-white overflow-hidden flex flex-col">
          <div className="min-h-0 flex-1 h-full w-full overflow-hidden">
            <div className="flex h-full min-h-0 w-full overflow-hidden [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden [--chat-bg-app:#f8fafc] [--chat-bg-sidebar:#f8fafc] [--chat-bg-main:#ffffff] [--chat-bg-header:rgba(255,255,255,0.95)] [--chat-bg-composer:rgba(255,255,255,0.96)] [--chat-bubble-outgoing:#334155] [--chat-bubble-outgoing-text:#f8fafc] [--chat-bubble-incoming:#f1f5f9] [--chat-bubble-incoming-text:#0f172a] [--chat-text-primary:#0f172a] [--chat-text-secondary:#475569] [--chat-text-tertiary:#64748b] [--chat-border:rgba(15,23,42,0.08)] [--chat-border-strong:rgba(15,23,42,0.12)] [--chat-accent:#334155] [--chat-accent-soft:rgba(51,65,85,0.08)] dark:[--chat-bg-app:#0b1220] dark:[--chat-bg-sidebar:#0f172a] dark:[--chat-bg-main:#0b1220] dark:[--chat-bg-header:rgba(15,23,42,0.9)] dark:[--chat-bg-composer:rgba(15,23,42,0.92)] dark:[--chat-bubble-outgoing:#334155] dark:[--chat-bubble-outgoing-text:#f8fafc] dark:[--chat-bubble-incoming:#1e293b] dark:[--chat-bubble-incoming-text:#e2e8f0] dark:[--chat-text-primary:#e2e8f0] dark:[--chat-text-secondary:#cbd5e1] dark:[--chat-text-tertiary:#94a3b8] dark:[--chat-border:rgba(148,163,184,0.22)] dark:[--chat-border-strong:rgba(148,163,184,0.34)] dark:[--chat-accent:#64748b] dark:[--chat-accent-soft:rgba(148,163,184,0.16)]">
              <div className="flex h-full min-h-0 w-full shrink-0 flex-col overflow-hidden border-r border-[var(--chat-border-strong)] bg-[var(--chat-bg-main)]">
                <div className="min-h-0 flex-1">
                  <FullMessenger
                    currentUser={currentUser}
                    conversations={conversations}
                    activeConversationId={employeeId}
                    onSelectConversation={() => {}}
                    messages={messages}
                    onSend={(text) => {
                      if (hasInputPending) {
                        void handleResumeWithInput(text);
                      } else if (!paneBusy && !isLoading) {
                        void handleSend(text);
                      }
                    }}
                    composerDisabled={isComposerDisabled}
                    composerPlaceholder={isComposerDisabled ? busyLabel : hasInputPending ? 'Type your response…' : undefined}
                    title="Employees"
                    theme="lunar"
                    className="h-full w-full"
                    headerActions={headerActions}
                    beforeComposer={composerSlot}
                    conversationStyle="tabs"
                    hideConversationTabs
                    messagesClassName="px-2"
                    composerClassName="px-2 py-1"
                    hideHeaderIdentity
                  />
                </div>
              </div>
            </div>
          </div>
        </main>

        {rightPanelOpen && (
          <aside className="h-full min-h-0 min-w-0 overflow-hidden bg-white flex flex-col">
            <EmployeePanel
              open={Boolean(configFormData)}
              onClose={() => {}}
              employee={configFormData}
              onSave={handleSaveConfig}
              isSaving={isSavingConfig}
              mode="inline"
            />
          </aside>
        )}
      </div>
    </div>
  );
}
