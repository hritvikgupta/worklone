import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Send, Sparkles, FileText, ListChecks, X, Paperclip, Mic, ChevronDown, Users, Brain, Wrench, CheckCircle2, AlertCircle, History, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  CHAT_AUTH_EXPIRED_ERROR,
  createEmployeeChatSession,
  getEmployeeChatSessionMessages,
  listEmployeeChatSessions,
  streamChatEvents,
  streamEmployeeChatEvents,
  resumeEmployeeChat,
  ChatSession,
  ChatSessionMessage,
} from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { getEmployee, listEmployees } from '@/src/api/employees';
import { useAuth } from '../contexts/AuthContext';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  type?: 'text' | 'prd' | 'backlog';
  thinking?: string;
  activities?: ActivityItem[];
}

interface ActivityItem {
  id: string;
  type: 'thinking' | 'tool';
  label: string;
  meta?: string;
  status: 'running' | 'done' | 'error';
  detail?: string;
}

interface PlanTaskItem {
  task_id: string;
  order?: number;
  title: string;
  description?: string;
  status: string;
  priority?: string;
}

interface ActivePlan {
  mode: string;
  reason?: string;
  message?: string;
  status: 'proposed' | 'approved' | 'running' | 'completed' | 'rejected';
  tasks: PlanTaskItem[];
}

interface AIAssistantProps {
  onClose?: () => void;
}

interface AssistantTarget {
  id: string;
  name: string;
  role?: string;
  type: 'katy' | 'employee';
  model?: string;
}

const KATY_MODEL = 'z-ai/glm-5.1';
const KATY_GREETING = "Hello! I'm Katy. I can help you write PRDs, prioritize your backlog, or brainstorm features. What's on your mind today?";

function buildEmployeeGreeting(target: AssistantTarget): string {
  return `Hello! I'm ${target.name}${target.role ? `, your ${target.role}` : ''}. What would you like me to help with?`;
}

function normalizeMarkdown(text: string): string {
  return text
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
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

function humanizeToken(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
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

function buildFallbackActivity(thinking?: string): ActivityItem[] {
  if (!thinking) return [];
  return [
    {
      id: 'thinking-fallback',
      type: 'thinking',
      label: summarizeThinkingLabel(thinking),
      status: 'done',
    },
  ];
}

function buildPendingActivity(): ActivityItem[] {
  return [
    {
      id: 'pending-intake',
      type: 'thinking',
      label: 'Mapping the request and choosing the first move',
      status: 'running',
    },
    {
      id: 'pending-context',
      type: 'tool',
      label: 'Preparing the next lookup',
      meta: 'Warmup',
      status: 'running',
    },
  ];
}

function buildInitialMessages(target: AssistantTarget): Message[] {
  return [
    {
      role: 'assistant',
      content: target.type === 'katy' ? KATY_GREETING : buildEmployeeGreeting(target),
    },
  ];
}

function mapSessionMessages(history: ChatSessionMessage[]): Message[] {
  return history.map((msg) => ({
    role: msg.role,
    content: msg.content,
    thinking: msg.thinking || undefined,
  }));
}

function formatSessionOptionLabel(session: ChatSession): string {
  const title = (session.title || 'Untitled session').trim();
  const timestamp = session.last_message_at || session.updated_at || session.created_at;
  if (!timestamp) return truncateLabel(title, 42);
  const date = new Date(timestamp);
  const dateLabel = Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  return truncateLabel(dateLabel ? `${title} · ${dateLabel}` : title, 42);
}

function normalizePlanTasks(tasks?: ActivePlan['tasks'] | Array<Record<string, unknown>>): PlanTaskItem[] {
  return (tasks || []).map((task, index) => ({
    task_id: String(task.task_id || `task-${index + 1}`),
    order: typeof task.order === 'number' ? task.order : index + 1,
    title: String(task.title || `Step ${index + 1}`),
    description: typeof task.description === 'string' ? task.description : '',
    status: typeof task.status === 'string' ? task.status : 'todo',
    priority: typeof task.priority === 'string' ? task.priority : 'medium',
  }));
}

function planStatusLabel(status: ActivePlan['status']): string {
  if (status === 'approved') return 'Approved';
  if (status === 'running') return 'Running';
  if (status === 'completed') return 'Completed';
  if (status === 'rejected') return 'Rejected';
  return 'Needs approval';
}

export function AIAssistant({ onClose }: AIAssistantProps) {
  const { logout } = useAuth();
  const [assistantTargets, setAssistantTargets] = useState<AssistantTarget[]>([
    { id: 'katy', name: 'Katy', role: 'Product Manager', type: 'katy', model: KATY_MODEL },
  ]);
  const [selectedAssistantId, setSelectedAssistantId] = useState('katy');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: KATY_GREETING }
  ]);
  const [input, setInput] = useState('');
  const [composerRows, setComposerRows] = useState(2);
  const [isLoading, setIsLoading] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [pendingResume, setPendingResume] = useState<{
    employeeId: string;
    sessionId: string;
    askType: string;
    options?: string[];
  } | null>(null);
  const [employeeSessionIds, setEmployeeSessionIds] = useState<Record<string, string>>({});
  const [employeeSessions, setEmployeeSessions] = useState<Record<string, ChatSession[]>>({});
  const [employeePlans, setEmployeePlans] = useState<Record<string, ActivePlan | null>>({});
  const [collapsedPlans, setCollapsedPlans] = useState<Record<string, boolean>>({});
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const isStreamingRef = useRef(false);
  const activeAssistantIndexRef = useRef<number | null>(null);

  const selectedAssistant = useMemo(
    () => assistantTargets.find((target) => target.id === selectedAssistantId) || assistantTargets[0],
    [assistantTargets, selectedAssistantId],
  );
  const selectedPlan = selectedAssistant?.type === 'employee'
    ? employeePlans[selectedAssistant.id] || null
    : null;
  const isPlanCollapsed = selectedAssistant?.type === 'employee'
    ? collapsedPlans[selectedAssistant.id] || false
    : false;

  useEffect(() => {
    const viewport = scrollRef.current?.querySelector('[data-slot="scroll-area-viewport"]') as HTMLDivElement | null;
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [messages, isLoading]);

  useEffect(() => {
    let cancelled = false;

    async function loadEmployees() {
      try {
        const employees = await listEmployees();
        if (cancelled) return;
        setAssistantTargets([
          { id: 'katy', name: 'Katy', role: 'Product Manager', type: 'katy', model: KATY_MODEL },
          ...employees.map((employee) => ({
            id: employee.id,
            name: employee.name,
            role: employee.role,
            type: 'employee' as const,
            model: employee.model,
          })),
        ]);
      } catch (error) {
        console.error('Failed to load assistant targets:', error);
      }
    }

    loadEmployees();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedAssistant) return;
    setMessages(buildInitialMessages(selectedAssistant));
    setIsLoading(false);
    setIsResuming(false);
    setPendingResume(null);
  }, [selectedAssistantId]);

  useEffect(() => {
    let cancelled = false;

    async function refreshSelectedEmployeeTarget(employeeId: string) {
      try {
        const details = await getEmployee(employeeId);
        if (cancelled) return;
        setAssistantTargets((prev) =>
          prev.map((target) =>
            target.id === employeeId && target.type === 'employee'
              ? {
                  ...target,
                  name: details.employee.name,
                  role: details.employee.role,
                  model: details.employee.model,
                }
              : target
          )
        );
      } catch (error) {
        console.error('Failed to refresh selected employee:', error);
      }
    }

    async function syncEmployeeHistory(target: AssistantTarget) {
      if (target.type !== 'employee') return;
      setIsHistoryLoading(true);
      try {
        const sessions = await listEmployeeChatSessions(target.id);
        if (cancelled) return;
        setEmployeeSessions((prev) => ({ ...prev, [target.id]: sessions }));

        const rememberedSessionId = employeeSessionIds[target.id];
        const nextSessionId = rememberedSessionId && sessions.some((session) => session.id === rememberedSessionId)
          ? rememberedSessionId
          : sessions[0]?.id;

        if (!nextSessionId) {
          if (!isStreamingRef.current) {
            setMessages(buildInitialMessages(target));
          }
          return;
        }

        setEmployeeSessionIds((prev) => ({
          ...prev,
          [target.id]: nextSessionId,
        }));

        setIsSessionLoading(true);
        const history = await getEmployeeChatSessionMessages(target.id, nextSessionId);
        if (cancelled) return;
        if (!isStreamingRef.current) {
          setMessages(history.length > 0 ? mapSessionMessages(history) : buildInitialMessages(target));
        }
      } catch (error) {
        console.error('Failed to load employee sessions:', error);
        if (!cancelled) {
          if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
            logout();
            return;
          }
          if (!isStreamingRef.current) {
            setMessages(buildInitialMessages(target));
          }
        }
      } finally {
        if (!cancelled) {
          setIsHistoryLoading(false);
          setIsSessionLoading(false);
        }
      }
    }

    if (!selectedAssistant) return;
    if (selectedAssistant.type === 'katy') {
      setIsHistoryLoading(false);
      setIsSessionLoading(false);
      return;
    }

    void refreshSelectedEmployeeTarget(selectedAssistant.id);
    syncEmployeeHistory(selectedAssistant);
    return () => {
      cancelled = true;
    };
  }, [selectedAssistantId, logout]);

  const openEmployeeSession = async (employeeId: string, sessionId: string) => {
    const assistant = assistantTargets.find((target) => target.id === employeeId && target.type === 'employee');
    if (!assistant) return;

    setPendingResume(null);
    setInput('');
    setComposerRows(2);
    setIsSessionLoading(true);
    try {
      const history = await getEmployeeChatSessionMessages(employeeId, sessionId);
      setEmployeeSessionIds((prev) => ({
        ...prev,
        [employeeId]: sessionId,
      }));
      setMessages(history.length > 0 ? mapSessionMessages(history) : buildInitialMessages(assistant));
    } catch (error) {
      console.error('Failed to load employee chat history:', error);
      if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
        return;
      }
      setMessages(buildInitialMessages(assistant));
    } finally {
      setIsSessionLoading(false);
    }
  };

  const handleStartNewEmployeeSession = (employeeId: string) => {
    const assistant = assistantTargets.find((target) => target.id === employeeId && target.type === 'employee');
    if (!assistant) return;

    setPendingResume(null);
    setInput('');
    setComposerRows(2);
    setEmployeeSessionIds((prev) => {
      const next = { ...prev };
      delete next[employeeId];
      return next;
    });
    setEmployeePlans((prev) => ({ ...prev, [employeeId]: null }));
    setMessages(buildInitialMessages(assistant));
  };

  const handlePlanDecision = async (approved: boolean) => {
    if (!pendingResume || selectedAssistant?.type !== 'employee') return;
    const decisionMessage = approved ? 'Approved' : 'Rejected';
    setIsResuming(true);
    setIsLoading(true);
    setEmployeePlans((prev) => ({
      ...prev,
      [selectedAssistant.id]: prev[selectedAssistant.id]
        ? { ...prev[selectedAssistant.id]!, status: approved ? 'approved' : 'rejected' }
        : prev[selectedAssistant.id],
    }));
    setMessages((prev) => {
      const next = [
        ...prev,
        { role: 'user' as const, content: decisionMessage },
        {
          role: 'assistant' as const,
          content: '',
          thinking: undefined,
          activities: buildPendingActivity(),
        },
      ];
      activeAssistantIndexRef.current = next.length - 1;
      return next;
    });
    try {
      await resumeEmployeeChat(pendingResume.employeeId, {
        session_id: pendingResume.sessionId,
        approved,
        message: decisionMessage,
        input: { response: decisionMessage },
      });
      setPendingResume(null);
    } catch (error) {
      console.error('Plan decision failed:', error);
      setIsLoading(false);
      if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
        return;
      }
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry — I could not submit your plan decision. The agent session may have expired.',
        },
      ]);
    } finally {
      setIsResuming(false);
    }
  };

  const togglePlanCollapsed = () => {
    if (selectedAssistant?.type !== 'employee') return;
    setCollapsedPlans((prev) => ({
      ...prev,
      [selectedAssistant.id]: !(prev[selectedAssistant.id] || false),
    }));
  };

  const handleSend = async () => {
    const messageToSend = input.trim();
    if (!messageToSend) return;

    // Human-in-the-loop: resuming a paused employee ReAct loop
    if (pendingResume && selectedAssistant?.type === 'employee') {
      const approved = /^(yes|y|approve|ok|go|confirm|sure|do it|proceed)/i.test(messageToSend);
      setMessages((prev) => {
        const next = [
          ...prev,
          { role: 'user' as const, content: messageToSend },
          {
            role: 'assistant' as const,
            content: '',
            thinking: undefined,
            activities: buildPendingActivity(),
          },
        ];
        activeAssistantIndexRef.current = next.length - 1;
        return next;
      });
      setInput('');
      setComposerRows(2);
      setIsResuming(true);
      setIsLoading(true);
      try {
        await resumeEmployeeChat(pendingResume.employeeId, {
          session_id: pendingResume.sessionId,
          approved,
          message: messageToSend,
          input: { response: messageToSend },
        });
        setPendingResume(null);
      } catch (error) {
        console.error('Resume failed:', error);
        setIsLoading(false);
        if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
          logout();
          return;
        }
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: 'Sorry — I could not resume the paused run. The agent session may have expired.',
          },
        ]);
        setPendingResume(null);
      } finally {
        setIsResuming(false);
      }
      return;
    }

    const userMessage: Message = { role: 'user', content: messageToSend };
    setInput('');
    setComposerRows(2);
    setIsLoading(true);
    isStreamingRef.current = true;
    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        role: 'assistant',
        content: '',
        thinking: undefined,
        activities: buildPendingActivity(),
      },
    ]);
    activeAssistantIndexRef.current = messages.length + 1;

    try {
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      let thinkingBuffer = '';
      let answerBuffer = '';
      let activities: ActivityItem[] = [];
      let employeeSessionId: string | null = null;

      if (selectedAssistant?.type === 'employee') {
        employeeSessionId = employeeSessionIds[selectedAssistant.id] || null;
        if (!employeeSessionId) {
          const session = await createEmployeeChatSession(selectedAssistant.id, 'New Chat', selectedAssistant.model);
          employeeSessionId = session.id;
          setEmployeeSessionIds((prev) => ({
            ...prev,
            [selectedAssistant.id]: session.id,
          }));
          setEmployeeSessions((prev) => ({
            ...prev,
            [selectedAssistant.id]: [session, ...(prev[selectedAssistant.id] || [])],
          }));
        }
      }

      const updateAssistantMessage = (nextContent: string, nextThinking?: string, nextActivities?: ActivityItem[]) => {
        setMessages((prev) =>
          prev.map((msg, idx) =>
            idx === activeAssistantIndexRef.current
              ? {
                  ...msg,
                  content: nextContent,
                  thinking: nextThinking,
                  activities: nextActivities ?? msg.activities,
                  type: nextContent.toLowerCase().includes('prd') || nextContent.toLowerCase().includes('requirements') ? 'prd' : 'text',
                }
              : msg
          )
        );
      };

      const stream = selectedAssistant?.type === 'employee'
        ? streamEmployeeChatEvents(selectedAssistant.id, {
            message: messageToSend,
            conversation_history: conversationHistory,
            model: selectedAssistant.model,
            session_id: employeeSessionId || undefined,
          })
        : streamChatEvents({
            message: messageToSend,
            conversation_history: conversationHistory,
            model: KATY_MODEL,
          });

      for await (const event of stream) {
        if (event.type === 'plan_created' && selectedAssistant?.type === 'employee') {
          setEmployeePlans((prev) => ({
            ...prev,
            [selectedAssistant.id]: {
              mode: event.mode || 'multi_step',
              reason: event.reason || '',
              message: event.message || '',
              status: 'proposed',
              tasks: normalizePlanTasks(event.tasks),
            },
          }));
          continue;
        }

        if (event.type === 'thinking') {
          const thought = event.content || '';
          if (thought) {
            thinkingBuffer += `${thought}\n\n`;
            activities = activities.map((activity) =>
              activity.type === 'thinking' && activity.status === 'running'
                ? { ...activity, status: 'done' }
                : activity
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
          updateAssistantMessage(
            normalizeMarkdown(answerBuffer),
            normalizeMarkdown(thinkingBuffer) || undefined,
            [...activities]
          );
          continue;
        }

        if (event.type === 'tool_start') {
          activities = activities.map((a) =>
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
          updateAssistantMessage(
            normalizeMarkdown(answerBuffer),
            normalizeMarkdown(thinkingBuffer) || undefined,
            [...activities]
          );
          continue;
        }

        if (event.type === 'tool_result') {
          if (selectedAssistant?.type === 'employee' && event.tool === 'manage_tasks') {
            const action = typeof event.input?.action === 'string' ? event.input.action : '';
            const data = event.data && typeof event.data === 'object' ? event.data as Record<string, unknown> : null;

            if (action === 'create_plan' && Array.isArray(data?.tasks)) {
              setEmployeePlans((prev) => ({
                ...prev,
                [selectedAssistant.id]: {
                  mode: prev[selectedAssistant.id]?.mode || 'multi_step',
                  reason: prev[selectedAssistant.id]?.reason || '',
                  message: prev[selectedAssistant.id]?.message || '',
                  status: prev[selectedAssistant.id]?.status || 'proposed',
                  tasks: normalizePlanTasks(data.tasks as Array<Record<string, unknown>>),
                },
              }));
            }

            if (data?.task_id && typeof data.task_id === 'string' && typeof data.status === 'string') {
              setEmployeePlans((prev) => {
                const currentPlan = prev[selectedAssistant.id];
                if (!currentPlan) return prev;
                const nextTasks = currentPlan.tasks.map((task) =>
                  task.task_id === data.task_id
                    ? { ...task, status: String(data.status) }
                    : task
                );
                const allDone = nextTasks.length > 0 && nextTasks.every((task) => task.status === 'done');
                const nextStatus = allDone
                  ? 'completed'
                  : data.status === 'in_progress'
                  ? 'running'
                  : currentPlan.status;
                return {
                  ...prev,
                  [selectedAssistant.id]: {
                    ...currentPlan,
                    status: nextStatus,
                    tasks: nextTasks,
                  },
                };
              });
            }
          }

          const idx = [...activities].reverse().findIndex((a) => a.type === 'tool' && a.label === humanizeToken(event.tool || 'tool') && a.status === 'running');
          if (idx >= 0) {
            const realIdx = activities.length - 1 - idx;
            activities[realIdx] = {
              ...activities[realIdx],
              status: event.success === false ? 'error' : 'done',
              detail: event.success === false ? (event.message || event.output || 'Tool failed') : undefined,
            };
          }
          updateAssistantMessage(
            normalizeMarkdown(answerBuffer),
            normalizeMarkdown(thinkingBuffer) || undefined,
            [...activities]
          );
          continue;
        }

        if (event.type === 'confirmation_required' && selectedAssistant?.type === 'employee') {
          const confirmMsg = event.message || 'Waiting for your approval to continue.';
          const askType = event.ask_type || 'approval';
          const isPlanApproval = Boolean(event.plan);
          setIsLoading(false);
          if (event.plan) {
            setEmployeePlans((prev) => ({
              ...prev,
              [selectedAssistant.id]: {
                mode: event.plan?.mode || prev[selectedAssistant.id]?.mode || 'multi_step',
                reason: event.plan?.reason || prev[selectedAssistant.id]?.reason || '',
                message: confirmMsg,
                status: 'proposed',
                tasks: normalizePlanTasks(event.plan?.tasks as Array<Record<string, unknown>> | undefined),
              },
            }));
          }
          activities = activities.map((a) =>
            a.status === 'running' ? { ...a, status: 'done' } : a
          );
          activities = [
            ...activities,
            {
              id: `confirm-${Date.now()}`,
              type: 'thinking',
              label: `Paused — ${truncateLabel(stripMarkdown(confirmMsg), 80)}`,
              status: 'running',
            },
          ];
          if (!isPlanApproval) {
            const hint = '\n\n*Reply in the composer to continue (e.g. "yes" / "no" / your choice).*';
            const optionLines = askType === 'choice' && event.options?.length
              ? '\n\n' + event.options.map((o, i) => `${i + 1}. ${o}`).join('\n')
              : '';
            answerBuffer = `${answerBuffer ? answerBuffer + '\n\n---\n\n' : ''}**${confirmMsg}**${optionLines}${hint}`;
          }
          updateAssistantMessage(
            normalizeMarkdown(answerBuffer),
            normalizeMarkdown(thinkingBuffer) || undefined,
            [...activities]
          );
          setPendingResume({
            employeeId: selectedAssistant.id,
            sessionId: employeeSessionId || employeeSessionIds[selectedAssistant.id] || 'default',
            askType,
            options: event.options,
          });
          continue;
        }

        if (event.type === 'task_started') {
          const taskId = event.task_id || '';
          const title = event.task_title || event.instructions || taskId || 'task';
          if (selectedAssistant?.type === 'employee') {
            setEmployeePlans((prev) => {
              const currentPlan = prev[selectedAssistant.id];
              if (!currentPlan) return prev;
              return {
                ...prev,
                [selectedAssistant.id]: {
                  ...currentPlan,
                  status: 'running',
                  tasks: currentPlan.tasks.map((task) =>
                    task.task_id === taskId
                      ? { ...task, status: 'in_progress' }
                      : task
                  ),
                },
              };
            });
          }
          activities = [
            ...activities,
            {
              id: `bg-task-${taskId}-${Date.now()}`,
              type: 'tool',
              label: `Background task: ${truncateLabel(title, 60)}`,
              meta: 'Async',
              status: 'running',
            },
          ];
          thinkingBuffer += `Started background task **${title}**.\n\n`;
          updateAssistantMessage(
            normalizeMarkdown(answerBuffer),
            normalizeMarkdown(thinkingBuffer) || undefined,
            [...activities]
          );
          continue;
        }

        if (event.type === 'final') {
          if (selectedAssistant?.type === 'employee') {
            setEmployeePlans((prev) => {
              const currentPlan = prev[selectedAssistant.id];
              if (!currentPlan) return prev;
              const allDone = currentPlan.tasks.length > 0 && currentPlan.tasks.every((task) => task.status === 'done');
              return {
                ...prev,
                [selectedAssistant.id]: {
                  ...currentPlan,
                  status: allDone ? 'completed' : currentPlan.status,
                },
              };
            });
          }
          activities = activities.map((a) =>
            a.status === 'running' ? { ...a, status: 'done' } : a
          );
          answerBuffer = event.content || '';
          updateAssistantMessage(
            normalizeMarkdown(answerBuffer),
            normalizeMarkdown(thinkingBuffer) || undefined,
            [...activities]
          );
          continue;
        }

        if (event.type === 'error') {
          const errText = event.message || 'Unknown streaming error';
          activities = activities.map((a) =>
            a.status === 'running' ? { ...a, status: 'error', detail: errText } : a
          );
          updateAssistantMessage(
            `Error: ${errText}`,
            normalizeMarkdown(thinkingBuffer) || undefined,
            [...activities]
          );
          break;
        }
      }

      const finalContent = normalizeMarkdown(answerBuffer);
      const finalThinking = normalizeMarkdown(thinkingBuffer);
      updateAssistantMessage(finalContent, finalThinking || undefined, [...activities]);

      if (!finalContent) {
        updateAssistantMessage(
          'I completed the run but did not receive a final response message. Please try again.',
          finalThinking || undefined,
          [...activities]
        );
      }
    } catch (error) {
      console.error('Chat error:', error);
      if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
        return;
      }
      setMessages((prev) =>
        prev.map((msg, idx) =>
          idx === activeAssistantIndexRef.current
            ? {
                ...msg,
                content: 'Sorry, I encountered an error processing your request. Please make sure the backend server is running.',
                thinking: msg.thinking || undefined,
              }
            : msg
        )
      );
    } finally {
      isStreamingRef.current = false;
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      <div className="p-4 border-b border-border bg-background sticky top-0 z-10">
        <div className="min-w-0">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-foreground" />
              <h2 className="text-sm font-bold text-foreground">Talk</h2>
            </div>
            <div className="flex items-center gap-1">
              {selectedAssistant?.type === 'employee' && (
                <>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <button
                        type="button"
                        disabled={isHistoryLoading || isSessionLoading}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-foreground transition-colors hover:bg-muted/60 disabled:cursor-not-allowed disabled:text-muted-foreground"
                        aria-label="Open session history"
                      >
                        <History className="h-4 w-4" />
                      </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-64">
                      <DropdownMenuLabel>
                        {isHistoryLoading ? 'Loading sessions...' : `${selectedAssistant.name} sessions`}
                      </DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => handleStartNewEmployeeSession(selectedAssistant.id)}>
                        <Plus className="mr-2 h-4 w-4" />
                        New session
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      {(employeeSessions[selectedAssistant.id] || []).length === 0 ? (
                        <DropdownMenuItem disabled>No past sessions</DropdownMenuItem>
                      ) : (
                        (employeeSessions[selectedAssistant.id] || []).map((session) => (
                          <DropdownMenuItem
                            key={session.id}
                            onClick={() => {
                              void openEmployeeSession(selectedAssistant.id, session.id);
                            }}
                            className="flex items-center justify-between gap-3"
                          >
                            <span className="truncate">{formatSessionOptionLabel(session)}</span>
                            {employeeSessionIds[selectedAssistant.id] === session.id && (
                              <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                                Open
                              </span>
                            )}
                          </DropdownMenuItem>
                        ))
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                  <button
                    type="button"
                    onClick={() => handleStartNewEmployeeSession(selectedAssistant.id)}
                    disabled={isSessionLoading || isLoading}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-foreground transition-colors hover:bg-muted/60 disabled:cursor-not-allowed disabled:text-muted-foreground"
                    aria-label="Start new session"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </>
              )}
              {onClose && (
                <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 text-muted-foreground hover:bg-muted/50">
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
          <div className="relative max-w-[260px]">
            <select
              value={selectedAssistantId}
              onChange={(e) => setSelectedAssistantId(e.target.value)}
              className="h-10 w-full appearance-none rounded-xl border border-border bg-card pl-3 pr-10 text-sm font-medium text-foreground shadow-sm outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-ring"
            >
              {assistantTargets.map((target) => (
                <option key={target.id} value={target.id}>
                  {target.name}{target.role ? ` · ${target.role}` : ''}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          </div>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        <div ref={scrollRef} className="min-h-0 flex-1">
        <ScrollArea className="h-full px-4">
          <div className="space-y-6 py-6">
            {isSessionLoading && selectedAssistant?.type === 'employee' && (
              <div className="rounded-lg border border-border bg-card px-4 py-3 text-xs text-muted-foreground shadow-sm">
                Loading chat history...
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={cn(
                "flex gap-3",
                msg.role === 'user' ? "flex-row-reverse" : ""
              )}>
                <div className={cn(
                  "w-6 h-6 rounded flex items-center justify-center shrink-0 mt-0.5",
                  msg.role === 'assistant' ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                )}>
                  {msg.role === 'assistant' ? <Sparkles className="w-3 h-3" /> : <div className="text-[9px] font-bold">U</div>}
                </div>
                <div className={cn(
                  "max-w-[90%] text-xs leading-relaxed",
                  msg.role === 'assistant' ? "text-foreground" : "bg-primary text-primary-foreground px-3 py-2 rounded-xl shadow-sm"
                )}>
                  {msg.role === 'assistant' ? (
                    <div className="space-y-3">
                      {(msg.activities?.length || msg.thinking) && (
                        <div className="space-y-1.5">
                          {(msg.activities && msg.activities.length > 0 ? msg.activities : buildFallbackActivity(msg.thinking)).map((activity) => (
                            <div key={activity.id} className="space-y-1">
                              <div className="flex items-center justify-between gap-3 text-[11px] leading-5">
                                <div className="flex min-w-0 items-center gap-2 text-muted-foreground">
                                  {activity.type === 'thinking' ? (
                                    <Brain className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                                  ) : (
                                    <Wrench className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                                  )}
                                  <span className="truncate">{activity.label}</span>
                                  {activity.meta && (
                                    <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                                      {activity.meta}
                                    </span>
                                  )}
                                </div>
                                <div className="shrink-0 text-[11px]">
                                  {activity.status === 'done' && (
                                    <span className="inline-flex items-center gap-1 text-emerald-600">
                                      <CheckCircle2 className="w-3 h-3" />
                                      Done
                                    </span>
                                  )}
                                  {activity.status === 'running' && (
                                    <span className="inline-flex items-center gap-1 text-muted-foreground">
                                      <span className="flex items-center gap-0.5">
                                        <span className="h-1.5 w-1.5 rounded-full bg-muted animate-pulse" />
                                        <span className="h-1.5 w-1.5 rounded-full bg-muted animate-pulse [animation-delay:120ms]" />
                                        <span className="h-1.5 w-1.5 rounded-full bg-muted animate-pulse [animation-delay:240ms]" />
                                      </span>
                                      Live
                                    </span>
                                  )}
                                  {activity.status === 'error' && (
                                    <span className="inline-flex items-center gap-1 text-amber-600">
                                      <AlertCircle className="w-3 h-3" />
                                      Error
                                    </span>
                                  )}
                                </div>
                              </div>
                              {activity.status === 'error' && activity.detail && (
                                <div className="pl-5 text-[11px] leading-5 text-amber-700/90">
                                  {truncateLabel(stripMarkdown(activity.detail), 160)}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {msg.type === 'prd' ? (
                        <div className="bg-card border border-border rounded-lg p-4 space-y-3 shadow-sm">
                          <div className="flex items-center gap-2 pb-2 border-b border-border">
                            <FileText className="w-3 h-3 text-muted-foreground" />
                            <span className="font-bold uppercase tracking-widest text-[9px] text-muted-foreground">PRD Draft</span>
                          </div>
                          <div className="max-w-none text-[13px] leading-6 text-foreground space-y-3 [&_p]:my-2 [&_ul]:my-2 [&_ol]:my-2 [&_li]:my-0.5 [&_pre]:my-3 [&_blockquote]:my-3">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                p: ({ children }) => <p className="whitespace-pre-wrap leading-6">{children}</p>,
                                ul: ({ children }) => <ul className="list-disc pl-5 space-y-1">{children}</ul>,
                                ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1">{children}</ol>,
                                li: ({ children }) => <li className="leading-6">{children}</li>,
                                table: ({ children }) => (
                                  <div className="my-3 overflow-x-auto rounded-lg border border-border">
                                    <table className="min-w-full border-collapse text-[12px]">{children}</table>
                                  </div>
                                ),
                                thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
                                th: ({ children }) => <th className="border-b border-border px-3 py-2 text-left font-medium text-foreground">{children}</th>,
                                td: ({ children }) => <td className="border-b border-border px-3 py-2 align-top">{children}</td>,
                                code: ({ children, ...props }) =>
                                  props.node?.position?.start.line === props.node?.position?.end.line ? (
                                    <code className="rounded bg-muted px-1.5 py-0.5 text-[12px] font-mono">{children}</code>
                                  ) : (
                                    <code className="block overflow-x-auto rounded-lg bg-primary p-3 text-[12px] font-mono text-muted-foreground">{children}</code>
                                  ),
                                blockquote: ({ children }) => <blockquote className="border-l-4 border-border pl-4 italic text-muted-foreground">{children}</blockquote>,
                              }}
                            >
                              {normalizeMarkdown(msg.content)}
                            </ReactMarkdown>
                          </div>
                        </div>
                      ) : (
                        <div className="max-w-none text-[13px] leading-6 text-foreground space-y-3 [&_p]:my-2 [&_ul]:my-2 [&_ol]:my-2 [&_li]:my-0.5 [&_pre]:my-3 [&_blockquote]:my-3">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              p: ({ children }) => <p className="whitespace-pre-wrap leading-6">{children}</p>,
                              ul: ({ children }) => <ul className="list-disc pl-5 space-y-1">{children}</ul>,
                              ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1">{children}</ol>,
                              li: ({ children }) => <li className="leading-6">{children}</li>,
                              table: ({ children }) => (
                                <div className="my-3 overflow-x-auto rounded-lg border border-border">
                                  <table className="min-w-full border-collapse text-[12px]">{children}</table>
                                </div>
                              ),
                              thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
                              th: ({ children }) => <th className="border-b border-border px-3 py-2 text-left font-medium text-foreground">{children}</th>,
                              td: ({ children }) => <td className="border-b border-border px-3 py-2 align-top">{children}</td>,
                              code: ({ children, ...props }) =>
                                props.node?.position?.start.line === props.node?.position?.end.line ? (
                                  <code className="rounded bg-muted px-1.5 py-0.5 text-[12px] font-mono">{children}</code>
                                ) : (
                                  <code className="block overflow-x-auto rounded-lg bg-primary p-3 text-[12px] font-mono text-muted-foreground">{children}</code>
                                ),
                              blockquote: ({ children }) => <blockquote className="border-l-4 border-border pl-4 italic text-muted-foreground">{children}</blockquote>,
                            }}
                          >
                            {normalizeMarkdown(msg.content)}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
        </div>

        <div className="shrink-0 border-t border-border bg-background p-4">
          {selectedAssistant?.type === 'employee' && selectedPlan && (
            <div className="mb-2 overflow-hidden rounded-xl border border-border bg-primary text-muted-foreground shadow-sm">
              <div className={cn(
                "flex items-center justify-between gap-3 px-3 py-2.5",
                !isPlanCollapsed && "border-b border-white/10"
              )}>
                <div className="flex min-w-0 items-center gap-2.5">
                  <ListChecks className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <div className="min-w-0">
                    <div className="truncate text-[13px] font-medium leading-4">
                      {selectedPlan.tasks.filter((task) => task.status === 'done').length} out of {selectedPlan.tasks.length} tasks completed
                    </div>
                    <div className="truncate text-[11px] leading-4 text-muted-foreground">
                      {selectedPlan.message || selectedPlan.reason || 'Agent-generated execution plan'}
                    </div>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <div className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] text-muted-foreground">
                    {planStatusLabel(selectedPlan.status)}
                  </div>
                  <button
                    type="button"
                    onClick={togglePlanCollapsed}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-card/10 hover:text-white"
                    aria-label={isPlanCollapsed ? 'Expand task plan' : 'Collapse task plan'}
                  >
                    <ChevronDown className={cn("h-4 w-4 transition-transform", !isPlanCollapsed && "rotate-180")} />
                  </button>
                </div>
              </div>

              {!isPlanCollapsed && (
              <div className="max-h-44 space-y-2.5 overflow-y-auto px-3 py-2.5">
                {selectedPlan.tasks.map((task, index) => (
                  <div key={task.task_id} className="flex items-start gap-2.5">
                    <div className="pt-0.5">
                      {task.status === 'done' ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      ) : task.status === 'in_progress' ? (
                        <span className="mt-0.5 block h-3 w-3 rounded-full border-2 border-amber-300 border-t-transparent animate-spin" />
                      ) : task.status === 'blocked' || task.status === 'cancelled' ? (
                        <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
                      ) : (
                        <span className="mt-1 block h-3 w-3 rounded-full border border-border" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className={cn("text-[12px] leading-5", task.status === 'done' ? "text-muted-foreground line-through" : "text-muted-foreground")}>
                        {index + 1}. {task.title}
                      </div>
                      {task.description && (
                        <div className="mt-0.5 text-[11px] leading-[18px] text-muted-foreground">
                          {task.description}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              )}

              {pendingResume && pendingResume.askType === 'approval' && (
                <div className="flex items-center justify-end gap-2 border-t border-white/10 px-3 py-2.5">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => void handlePlanDecision(false)}
                    disabled={isResuming}
                    className="h-8 border-white/10 bg-transparent px-3 text-[11px] text-muted-foreground hover:bg-card/10 hover:text-white"
                  >
                    Reject
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => void handlePlanDecision(true)}
                    disabled={isResuming}
                    className="h-8 bg-card px-3 text-[11px] text-foreground hover:bg-muted"
                  >
                    Approve plan
                  </Button>
                </div>
              )}
            </div>
          )}

          <div className="relative bg-card border border-border rounded-xl p-3 shadow-sm focus-within:border-ring transition-colors">
            <textarea
              placeholder={
                pendingResume
                  ? `${selectedAssistant?.name || 'Agent'} is paused — reply to continue (yes / no / your answer)...`
                  : selectedAssistant?.type === 'employee'
                  ? `Message ${selectedAssistant.name}...`
                  : 'Ask Katy anything...'
              }
              value={input}
              rows={composerRows}
              onChange={(e) => {
                setInput(e.target.value);
                const lineCount = e.target.value.split('\n').length;
                setComposerRows(Math.max(2, Math.min(6, lineCount)));
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              className="max-h-36 min-h-[44px] w-full resize-none overflow-y-auto border-none bg-transparent py-1 text-xs text-foreground shadow-none outline-none focus:outline-none focus:ring-0 placeholder:text-muted-foreground"
            />
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-border">
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground">
                  <Paperclip className="w-3 h-3" />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground">
                  <Mic className="w-3 h-3" />
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  onClick={handleSend}
                  disabled={(isLoading && !pendingResume) || isResuming || !input.trim()}
                  size="icon"
                  className="bg-primary text-primary-foreground hover:bg-primary/80 h-7 w-7 rounded-lg transition-all active:scale-95"
                >
                  <Send className="w-3 h-3" />
                </Button>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5 mt-3">
            {[
              { label: 'Draft PRD', icon: FileText, text: "Draft a PRD for a new dark mode feature" },
              { label: 'Prioritize', icon: ListChecks, text: "Prioritize my current backlog" },
            ].map((btn) => (
              <button 
                key={btn.label}
                onClick={() => setInput(btn.text)}
                className="flex items-center gap-1 px-2 py-0.5 rounded border border-border bg-card text-[10px] font-medium text-muted-foreground hover:bg-muted hover:border-border transition-all shadow-sm"
              >
                <btn.icon className="w-2.5 h-2.5" />
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
