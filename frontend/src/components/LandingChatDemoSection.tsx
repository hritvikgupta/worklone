import React, { useState, useEffect, useRef } from 'react';
import { FullMessenger } from '@/components/ui/chat/layouts';
import type { ChatMessageData, ChatUser, TypingUser } from '@/components/ui/chat/types';
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

// Helper functions from ChatView
function humanizeToken(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function truncateLabel(text: string, maxLength = 92): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1).trimEnd()}…`;
}

// Dummy data
const DUMMY_USER: ChatUser = {
  id: 'user-1',
  name: 'Current User',
  avatar: '/employees/men_1.png',
};

const DUMMY_EMPLOYEES = [
  { id: 'emp-1', name: 'Alice (Engineer)', role: 'Software Engineer', avatar: '/employees/women_1.png' },
  { id: 'emp-2', name: 'Bob (Product)', role: 'Product Manager', avatar: '/employees/men_2.png' },
  { id: 'emp-3', name: 'Charlie (Design)', role: 'Product Designer', avatar: '/employees/men_3.png' },
];

const DUMMY_SESSIONS = {
  'emp-1': [{ id: 'sess-1', title: 'Implement new auth flow' }],
  'emp-2': [{ id: 'sess-2', title: 'Q3 Roadmap Planning' }],
  'emp-3': [{ id: 'sess-3', title: 'Landing page redesign' }],
};

const DUMMY_MESSAGES: Record<string, ChatMessageData[]> = {
  'emp-1': [
    { id: 'msg-1', senderId: 'user-1', senderName: 'Current User', senderAvatar: '/employees/men_1.png', text: 'Can you implement the new auth flow?', timestamp: new Date(Date.now() - 1200000), status: 'read' },
    { id: 'msg-2', senderId: 'emp-1', senderName: 'Alice (Engineer)', senderAvatar: '/employees/women_1.png', text: 'I am analyzing the requirements.', timestamp: new Date(Date.now() - 600000), status: 'read', activities: [{ id: 'act-1', type: 'thinking', label: 'Reasoning through the next step', status: 'done' }] },
    { id: 'msg-2-1', senderId: 'emp-1', senderName: 'Alice (Engineer)', senderAvatar: '/employees/women_1.png', text: 'I have set up the initial OAuth provider configuration.', timestamp: new Date(Date.now() - 300000), status: 'read' },
  ],
  'emp-2': [
    { id: 'msg-3', senderId: 'user-1', senderName: 'Current User', senderAvatar: '/employees/men_1.png', text: 'Let us prepare for Q3.', timestamp: new Date(Date.now() - 3000000), status: 'read' },
    { id: 'msg-4', senderId: 'emp-2', senderName: 'Bob (Product)', senderAvatar: '/employees/men_2.png', text: 'Looking at our backlog.', timestamp: new Date(Date.now() - 1500000), status: 'read' },
    { id: 'msg-4-1', senderId: 'emp-2', senderName: 'Bob (Product)', senderAvatar: '/employees/men_2.png', text: 'I\'ve outlined the top 3 priorities for the next sprint.', timestamp: new Date(Date.now() - 800000), status: 'read' },
  ],
  'emp-3': [
    { id: 'msg-5', senderId: 'user-1', senderName: 'Current User', senderAvatar: '/employees/men_1.png', text: 'We need to refresh the landing page.', timestamp: new Date(Date.now() - 5000000), status: 'read' },
    { id: 'msg-6', senderId: 'emp-3', senderName: 'Charlie (Design)', senderAvatar: '/employees/men_3.png', text: 'I will start drafting some wireframes.', timestamp: new Date(Date.now() - 2500000), status: 'read' },
    { id: 'msg-6-1', senderId: 'user-1', senderName: 'Current User', senderAvatar: '/employees/men_1.png', text: 'Make sure to include the new product screenshots.', timestamp: new Date(Date.now() - 1000000), status: 'read' },
  ],
};

const DUMMY_PLANS: Record<string, ChatMessageData['plan']> = {
  'emp-1': {
    mode: 'multi_step',
    reason: 'To complete the auth flow implementation.',
    message: 'I have created a plan for the new auth flow.',
    status: 'running',
    tasks: [
      { task_id: 't-1', order: 1, title: 'Setup OAuth provider', description: '', status: 'done', priority: 'high' },
      { task_id: 't-2', order: 2, title: 'Update login UI', description: '', status: 'in_progress', priority: 'high' },
    ],
  }
};

export function LandingChatDemoSection() {
  const currentUser = DUMMY_USER;
  const sectionRef = useRef<HTMLElement>(null);
  const [isInView, setIsInView] = useState(false);

  const [employees] = useState(DUMMY_EMPLOYEES);
  // Show exactly 2 panes in the landing demo
  const [chatPanes, setChatPanes] = useState<Array<{ id: string; employeeId: string }>>([
    { id: 'pane-1', employeeId: 'emp-1' },
    { id: 'pane-2', employeeId: 'emp-2' },
  ]);
  const [sessions] = useState(DUMMY_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState<Record<string, string>>({
    'emp-1': 'sess-1',
    'emp-2': 'sess-2',
    'emp-3': 'sess-3',
  });
  const [messages, setMessages] = useState<Record<string, ChatMessageData[]>>(DUMMY_MESSAGES);
  const [activePlans] = useState(DUMMY_PLANS);
  const [collapsedPlans, setCollapsedPlans] = useState<Record<string, boolean>>({});
  const [typingState, setTypingState] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        setIsInView(entries[0].isIntersecting);
      },
      { threshold: 0.3 }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!isInView) {
      // Reset state when out of view so it can animate again when scrolled back into view
      setMessages(DUMMY_MESSAGES);
      setTypingState({});
      return;
    }

    // Sequence of fake live events to make the chats animate concurrently
    const timers: NodeJS.Timeout[] = [];

    // All start typing at roughly the same time (T+1s to T+1.5s)
    timers.push(setTimeout(() => setTypingState(p => ({ ...p, 'emp-1': true })), 1000));
    timers.push(setTimeout(() => setTypingState(p => ({ ...p, 'emp-2': true })), 1200));
    timers.push(setTimeout(() => setTypingState(p => ({ ...p, 'emp-3': true })), 1500));

    // Alice sends message
    timers.push(setTimeout(() => {
      setTypingState(p => ({ ...p, 'emp-1': false }));
      setMessages(p => ({
        ...p,
        'emp-1': [...(p['emp-1'] || []), {
          id: `msg-sim-${Date.now()}-1`,
          senderId: 'emp-1',
          senderName: 'Alice (Engineer)',
          senderAvatar: '/employees/women_1.png',
          text: 'Just pushed the final commits for the auth flow. It is 100% complete.',
          timestamp: new Date(),
          status: 'read',
        }]
      }));
    }, 3500));

    // Bob sends message
    timers.push(setTimeout(() => {
      setTypingState(p => ({ ...p, 'emp-2': false }));
      setMessages(p => ({
        ...p,
        'emp-2': [...(p['emp-2'] || []), {
          id: `msg-sim-${Date.now()}-2`,
          senderId: 'emp-2',
          senderName: 'Bob (Product)',
          senderAvatar: '/employees/men_2.png',
          text: 'Excellent. I have updated the Q3 roadmap to reflect the completed auth epic.',
          timestamp: new Date(),
          status: 'read',
        }]
      }));
    }, 4500));

    // Charlie sends message
    timers.push(setTimeout(() => {
      setTypingState(p => ({ ...p, 'emp-3': false }));
      setMessages(p => ({
        ...p,
        'emp-3': [...(p['emp-3'] || []), {
          id: `msg-sim-${Date.now()}-3`,
          senderId: 'emp-3',
          senderName: 'Charlie (Design)',
          senderAvatar: '/employees/men_3.png',
          text: 'Here are the new wireframes for the landing page redesign! 🎨',
          timestamp: new Date(),
          status: 'read',
          activities: [
            { id: `thinking-sim`, type: 'thinking', label: 'Generating design alternatives', status: 'done' }
          ]
        }]
      }));
    }, 5500));
    
    // Charlie types again
    timers.push(setTimeout(() => setTypingState(p => ({ ...p, 'emp-3': true })), 7000));
    // Charlie sends again
    timers.push(setTimeout(() => {
      setTypingState(p => ({ ...p, 'emp-3': false }));
      setMessages(p => ({
        ...p,
        'emp-3': [...(p['emp-3'] || []), {
          id: `msg-sim-${Date.now()}-4`,
          senderId: 'emp-3',
          senderName: 'Charlie (Design)',
          senderAvatar: '/employees/men_3.png',
          text: 'Let me know if you want any changes to the hero section layout.',
          timestamp: new Date(),
          status: 'read'
        }]
      }));
    }, 9000));

    // Alice starts typing again
    timers.push(setTimeout(() => setTypingState(p => ({ ...p, 'emp-1': true })), 8000));
    // Alice sends message
    timers.push(setTimeout(() => {
      setTypingState(p => ({ ...p, 'emp-1': false }));
      setMessages(p => ({
        ...p,
        'emp-1': [...(p['emp-1'] || []), {
          id: `msg-sim-${Date.now()}-5`,
          senderId: 'emp-1',
          senderName: 'Alice (Engineer)',
          senderAvatar: '/employees/women_1.png',
          text: 'I will start looking at the next ticket on the sprint board now.',
          timestamp: new Date(),
          status: 'read',
          activities: [
            { id: `tool-sim-jira`, type: 'tool', label: 'Jira', meta: 'Move ticket to Done', status: 'done' }
          ]
        }]
      }));
    }, 10500));

    // Bob starts typing again
    timers.push(setTimeout(() => setTypingState(p => ({ ...p, 'emp-2': true })), 9500));
    // Bob sends message
    timers.push(setTimeout(() => {
      setTypingState(p => ({ ...p, 'emp-2': false }));
      setMessages(p => ({
        ...p,
        'emp-2': [...(p['emp-2'] || []), {
          id: `msg-sim-${Date.now()}-6`,
          senderId: 'emp-2',
          senderName: 'Bob (Product)',
          senderAvatar: '/employees/men_2.png',
          text: 'Also I will ping the marketing team to align on the release notes.',
          timestamp: new Date(),
          status: 'read',
        }]
      }));
    }, 12000));

    return () => timers.forEach(clearTimeout);
  }, [isInView]);

  const handleSend = (employeeId: string, text: string) => {
    if (!employeeId || !text.trim()) return;

    const userMessage: ChatMessageData = {
      id: `user-${Date.now()}`,
      senderId: currentUser.id,
      senderName: currentUser.name,
      text,
      timestamp: new Date(),
      status: 'read',
    };

    setMessages(prev => ({
      ...prev,
      [employeeId]: [...(prev[employeeId] || []), userMessage]
    }));

    // Simulate agent typing then replying
    setTypingState(p => ({ ...p, [employeeId]: true }));
    setTimeout(() => {
      const activeEmployee = employees.find(e => e.id === employeeId);
      const assistantMessage: ChatMessageData = {
        id: `assistant-${Date.now()}`,
        senderId: employeeId,
        senderName: activeEmployee?.name || 'Agent',
        text: 'I will take care of that right away.',
        timestamp: new Date(),
        status: 'read',
        activities: [
          { id: `thinking-${Date.now()}`, type: 'thinking', label: 'Evaluating request', status: 'done' }
        ]
      };
      setTypingState(p => ({ ...p, [employeeId]: false }));
      setMessages(prev => ({
        ...prev,
        [employeeId]: [...(prev[employeeId] || []), assistantMessage]
      }));
    }, 1500);
  };

  const removePane = (paneId: string) => {
    setChatPanes((prev) => (prev.length <= 1 ? prev : prev.filter((pane) => pane.id !== paneId)));
  };

  return (
    <section ref={sectionRef} className="border-t border-zinc-200/70 bg-white py-16 sm:py-24">
      <div className="mx-auto w-full max-w-7xl px-6 sm:px-8 lg:px-10">
        <div className="grid gap-0 overflow-hidden rounded-[30px] border border-zinc-200 bg-white lg:grid-cols-[0.64fr_1.36fr]">
          <div className="flex items-center border-b border-zinc-300/70 p-8 sm:p-12 lg:border-b-0 lg:border-r lg:p-16">
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
                Multi-Employee Workspace
              </div>
              <h2 className="mt-4 text-[24px] font-medium leading-[1.15] tracking-tight text-zinc-900 sm:text-[30px]">
                Coordinate AI employee chats
                <span className="block text-zinc-500">inside one shared workspace</span>
              </h2>
              <p className="mt-4 max-w-md text-[15px] leading-7 text-zinc-600">
                Keep teams aligned with concurrent execution, unified context, and clear handoffs.
              </p>
            </div>
          </div>

          <div className="relative overflow-hidden bg-white p-4 sm:p-8">
            <div className="absolute inset-0 z-0 pointer-events-none">
              <img src="/bgothers.png" alt="" className="h-full w-full object-cover object-center" />
            </div>

            <div className="relative z-10 h-[650px] overflow-hidden rounded-[24px] border border-zinc-200 bg-white shadow-[0_12px_28px_rgba(24,24,27,0.06)]">
              <div className="flex h-full overflow-x-auto overflow-y-hidden [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden [--chat-bg-app:#f6f4f3] [--chat-bg-sidebar:#f5f3f2] [--chat-bg-main:#fbfbfa] [--chat-bg-header:rgba(251,251,250,0.96)] [--chat-bg-composer:rgba(251,251,250,0.98)] [--chat-bubble-outgoing:#4b5563] [--chat-bubble-outgoing-text:#f9fafb] [--chat-bubble-incoming:#ece9e7] [--chat-bubble-incoming-text:#1f2937] [--chat-text-primary:#1f2937] [--chat-text-secondary:#4b5563] [--chat-text-tertiary:#6b7280] [--chat-border:rgba(31,41,55,0.09)] [--chat-border-strong:rgba(31,41,55,0.14)] [--chat-accent:#4b5563] [--chat-accent-soft:rgba(75,85,99,0.09)] dark:[--chat-bg-app:#0b1220] dark:[--chat-bg-sidebar:#0f172a] dark:[--chat-bg-main:#0b1220] dark:[--chat-bg-header:rgba(15,23,42,0.9)] dark:[--chat-bg-composer:rgba(15,23,42,0.92)] dark:[--chat-bubble-outgoing:#334155] dark:[--chat-bubble-outgoing-text:#f8fafc] dark:[--chat-bubble-incoming:#1e293b] dark:[--chat-bubble-incoming-text:#e2e8f0] dark:[--chat-text-primary:#e2e8f0] dark:[--chat-text-secondary:#cbd5e1] dark:[--chat-text-tertiary:#94a3b8] dark:[--chat-border:rgba(148,163,184,0.22)] dark:[--chat-border-strong:rgba(148,163,184,0.34)] dark:[--chat-accent:#64748b] dark:[--chat-accent-soft:rgba(148,163,184,0.16)]">
                {chatPanes.map((pane) => {
                  const employeeId = pane.employeeId;
                  const activeEmployee = employees.find((employee) => employee.id === employeeId);
                  const currentSessions = sessions[employeeId as keyof typeof sessions] || [];
                  const currentSessionId = activeSessionId[employeeId];
                  const selectedPlan = activePlans[employeeId as keyof typeof activePlans];
                  const isPlanCollapsed = collapsedPlans[employeeId] ?? false;
                  const isTyping = typingState[employeeId] ?? false;

                  const paneConversations: SidebarConversation[] = activeEmployee ? [{
                    id: activeEmployee.id,
                    title: activeEmployee.name,
                    avatar: activeEmployee.avatar,
                    lastMessage: activeEmployee.role,
                    presence: 'online',
                  }] : [];

                  const paneTypingUsers: TypingUser[] = isTyping && activeEmployee ? [{
                    id: activeEmployee.id,
                    name: activeEmployee.name,
                    avatar: activeEmployee.avatar,
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
                          <DropdownMenuItem>
                            <Plus className="mr-2 h-4 w-4" />
                            New Session
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          {currentSessions.length === 0 ? (
                            <DropdownMenuItem disabled>No sessions yet</DropdownMenuItem>
                          ) : (
                            currentSessions.map((session) => (
                              <DropdownMenuItem key={session.id} className="flex items-center justify-between">
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
                        type="button"
                        className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] text-[var(--chat-text-primary)] transition-colors hover:bg-[var(--chat-accent-soft)]"
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
                        <div className="overflow-hidden rounded-xl border border-[var(--chat-border-strong)] bg-[var(--chat-bg-sidebar)] shadow-sm">
                          <div className={cn(
                            'flex items-center justify-between gap-2 px-2.5 py-2',
                            !isPlanCollapsed && 'border-b border-[var(--chat-border)]'
                          )}>
                            <div className="flex min-w-0 items-center gap-2.5">
                              <ListChecks className="h-4 w-4 shrink-0 text-[var(--chat-text-secondary)]" />
                              <div className="min-w-0">
                                <div className="truncate text-[13px] font-medium leading-4 text-[var(--chat-text-primary)]">
                                  {selectedPlan.tasks.filter((task) => task.status === 'done').length} of {selectedPlan.tasks.length} tasks completed
                                </div>
                                <div className="mt-0.5 truncate text-[11px] leading-4 text-[var(--chat-text-tertiary)]">
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
                                <ChevronDown className={cn('h-4 w-4 transition-transform', !isPlanCollapsed && 'rotate-180')} />
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
                                      <span className="mt-0.5 block h-3 w-3 animate-spin rounded-full border-2 border-amber-400 border-t-transparent" />
                                    ) : task.status === 'blocked' || task.status === 'cancelled' ? (
                                      <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
                                    ) : (
                                      <span className="mt-1 block h-3 w-3 rounded-full border border-[var(--chat-text-tertiary)]" />
                                    )}
                                  </div>
                                  <div className="min-w-0 flex-1">
                                    <div className={cn('text-[12px] leading-5', task.status === 'done' ? 'text-[var(--chat-text-tertiary)] line-through' : 'text-[var(--chat-text-secondary)]')}>
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
                        </div>
                      </div>
                    </div>
                  ) : null;

                  return (
                    <div
                      key={pane.id}
                      style={{ '--header-avatar': activeEmployee?.avatar ? `url(${activeEmployee.avatar})` : 'none' } as React.CSSProperties}
                      className="flex h-full min-h-0 min-w-[300px] flex-1 shrink-0 flex-col overflow-hidden border-r border-[var(--chat-border-strong)] bg-[var(--chat-bg-main)] [&_.chat-bubble]:px-3 [&_.chat-bubble]:py-1.5 [&_.chat-bubble_p]:text-[13.5px] [&_.chat-bubble_p]:leading-[1.4] [&_.chat-message-group]:text-[13px] [&_header_.size-10.rounded-full]:!bg-[image:var(--header-avatar)] [&_header_.size-10.rounded-full]:!bg-cover [&_header_.size-10.rounded-full]:!bg-center [&_header_.size-10.rounded-full]:!text-transparent"
                    >
                      <div className="min-h-0 flex-1">
                        <FullMessenger
                          currentUser={currentUser}
                          conversations={paneConversations}
                          activeConversationId={employeeId}
                          onSelectConversation={() => {}}
                          messages={messages[employeeId] || []}
                          typingUsers={paneTypingUsers}
                          onSend={(text) => handleSend(employeeId, text)}
                          title="Employees"
                          theme="lunar"
                          className="h-full w-full"
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
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
