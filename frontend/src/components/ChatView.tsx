import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Send, Sparkles, User, Paperclip, Mic, Maximize2, Eraser, FileText, MessageSquare, MessageSquarePlus, Wrench, CheckCircle2, AlertCircle, Brain, Github, ListChecks, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  streamChatEvents,
  CHAT_AUTH_EXPIRED_ERROR,
  createChatSession,
  getChatSessionMessages,
  listChatSessions,
  type ChatSession,
} from '@/lib/api';
import { ModelDropdown, AVAILABLE_MODELS } from '@/components/ModelDropdown';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { useAuth } from '../contexts/AuthContext';

interface Message {
  role: 'user' | 'assistant';
  content: string;
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

export function ChatView() {
  const { logout } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [input, setInput] = useState('');
  const [hasStarted, setHasStarted] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [selectedModel, setSelectedModel] = useState(AVAILABLE_MODELS[0].value);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  const handleAuthExpired = () => {
    logout();
  };

  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const data = await listChatSessions();
      setSessions(data);
    } catch (error) {
      if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
        handleAuthExpired();
      }
    } finally {
      setSessionsLoading(false);
    }
  };

  useEffect(() => {
    if (hasStarted) {
      loadSessions();
    }
  }, [hasStarted]);

  const startNewChat = async () => {
    try {
      const session = await createChatSession('New Chat', selectedModel);
      setActiveSessionId(session.id);
      setMessages([]);
      setHasStarted(true);
      await loadSessions();
    } catch (error) {
      if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
        handleAuthExpired();
      }
    }
  };

  const openSession = async (sessionId: string) => {
    try {
      const history = await getChatSessionMessages(sessionId);
      setActiveSessionId(sessionId);
      setMessages(
        history.map((msg) => ({
          role: msg.role,
          content: msg.content,
          thinking: msg.thinking || undefined,
        }))
      );
      setHasStarted(true);
    } catch (error) {
      if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
        handleAuthExpired();
      }
    }
  };

  const handleSend = async () => {
    const messageToSend = input.trim();
    if (!messageToSend) return;

    let sessionId = activeSessionId;
    if (!sessionId) {
      try {
        const session = await createChatSession('New Chat', selectedModel);
        sessionId = session.id;
        setActiveSessionId(session.id);
      } catch (error) {
        if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
          handleAuthExpired();
          return;
        }
        return;
      }
    }

    const userMsg: Message = { role: 'user', content: messageToSend };
    setMessages(prev => [
      ...prev,
      userMsg,
      {
        role: 'assistant',
        content: '',
        thinking: undefined,
        activities: buildPendingActivity(),
      },
    ]);
    const assistantIndex = messages.length + 1;
    setInput('');
    setHasStarted(true);
    setIsThinking(true);

    try {
      // Convert message history to API format
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      let thinkingBuffer = '';
      let answerBuffer = '';
      let activities: ActivityItem[] = [];

      const updateAssistantMessage = (nextContent: string, nextThinking?: string, nextActivities?: ActivityItem[]) => {
        setMessages((prev) =>
          prev.map((msg, idx) =>
            idx === assistantIndex
              ? {
                  ...msg,
                  content: nextContent,
                  thinking: nextThinking,
                  activities: nextActivities ?? msg.activities,
                }
              : msg
          )
        );
      };

      for await (const event of streamChatEvents({
        message: messageToSend,
        conversation_history: conversationHistory,
        model: selectedModel,
        session_id: sessionId,
      })) {
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
          thinkingBuffer += `Using **${event.tool || 'tool'}**...\n\n`;
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
          if (event.success === false) {
            thinkingBuffer += `**${event.tool || 'Tool'}** returned an error. Katy is adjusting and continuing.\n\n`;
          } else {
            thinkingBuffer += `Completed **${event.tool || 'tool'}**.\n\n`;
          }
          const idx = [...activities].reverse().findIndex((a) => a.type === 'tool' && a.label === (event.tool || 'tool') && a.status === 'running');
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

        if (event.type === 'final') {
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
          "I completed the run but did not receive a final response message. Please try again.",
          finalThinking || undefined
        );
      }
    } catch (error) {
      console.error('Chat error:', error);
      if (error instanceof Error && error.message === CHAT_AUTH_EXPIRED_ERROR) {
        handleAuthExpired();
        return;
      }
      setMessages((prev) =>
        prev.map((msg, idx) =>
          idx === assistantIndex
            ? {
                ...msg,
                content: "Sorry, I encountered an error. Please ensure the backend server is running.",
                thinking: msg.thinking || undefined,
              }
            : msg
        )
      );
    } finally {
      setIsThinking(false);
      await loadSessions();
    }
  };

  return (
    <div className="h-full flex flex-col bg-white relative overflow-hidden">
      {/* Background Pattern */}
      {!hasStarted && (
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none">
          <div className="absolute inset-0" style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
        </div>
      )}

      <AnimatePresence mode="wait">
        {!hasStarted ? (
          <motion.div 
            key="initial"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="flex-1 flex flex-col items-center justify-center p-6 max-w-2xl mx-auto w-full"
          >
            <div className="w-16 h-16 bg-zinc-900 rounded-2xl flex items-center justify-center mb-8 shadow-xl">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold text-[#37352f] mb-4 tracking-tight">How can I help you, Katy?</h1>
            <p className="text-zinc-500 text-center mb-12 leading-relaxed">
              I'm your AI product partner. Ask me to draft a PRD, prioritize your backlog, 
              or brainstorm new features for your roadmap.
            </p>
            
            <div className="w-full relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-zinc-200 to-zinc-100 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200" />
              <div className="relative bg-white border border-zinc-200 rounded-xl p-4 shadow-sm">
                <textarea
                  placeholder="Ask anything..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  className="w-full bg-transparent border-none focus:ring-0 outline-none focus:outline-none shadow-none resize-none text-sm min-h-[44px] py-1 text-[#37352f] placeholder:text-zinc-400"
                />
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-zinc-50">
                  <div className="flex items-center gap-2">
                    <ModelDropdown value={selectedModel} onChange={setSelectedModel} />
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-zinc-900">
                      <Paperclip className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-zinc-900">
                      <Mic className="w-4 h-4" />
                    </Button>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider">
                      {input.length} characters
                    </span>
                    <Button 
                      onClick={handleSend}
                      disabled={!input.trim()}
                      className="bg-zinc-900 text-white hover:bg-zinc-800 h-9 px-4 rounded-lg flex items-center gap-2 transition-all active:scale-95"
                    >
                      <span className="text-xs font-bold">Send</span>
                      <Send className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-8 w-full">
              {[
                { label: 'List my repos...', icon: Github, text: 'List my 5 most recently updated GitHub repositories' },
                { label: 'Prioritize features...', icon: ListChecks, text: 'Help me prioritize my backlog using RICE framework' },
                { label: 'Draft a PRD...', icon: FileText, text: 'Draft a PRD for a new dark mode feature' },
                { label: 'Define metrics...', icon: TrendingUp, text: 'What success metrics should I track for my MVP?' },
              ].map((item) => (
                <button
                  key={item.label}
                  onClick={() => setInput(item.text)}
                  className="flex items-center gap-3 p-3 rounded-xl border border-zinc-100 bg-zinc-50/50 hover:bg-white hover:border-zinc-200 hover:shadow-sm transition-all text-left group"
                >
                  <div className="w-8 h-8 rounded-lg bg-white border border-zinc-100 flex items-center justify-center group-hover:border-zinc-200">
                    <item.icon className="w-4 h-4 text-zinc-500" />
                  </div>
                  <span className="text-xs font-medium text-zinc-600 group-hover:text-zinc-900">{item.label}</span>
                </button>
              ))}
            </div>
          </motion.div>
        ) : (
          <motion.div 
            key="chat"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex-1 flex min-h-0"
          >
            {hasStarted && (
              <aside className="w-72 border-r border-zinc-100 bg-zinc-50/40 flex flex-col">
                <div className="p-4 border-b border-zinc-100">
                  <Button
                    onClick={startNewChat}
                    className="w-full bg-zinc-900 text-white hover:bg-zinc-800 h-9 text-xs font-bold"
                  >
                    <MessageSquarePlus className="w-3.5 h-3.5 mr-1.5" />
                    New Chat
                  </Button>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                  {sessionsLoading ? (
                    <div className="text-xs text-zinc-400 px-2 py-3">Loading chats...</div>
                  ) : sessions.length === 0 ? (
                    <div className="text-xs text-zinc-400 px-2 py-3">No chats yet.</div>
                  ) : (
                    sessions.map((session) => (
                      <button
                        key={session.id}
                        onClick={() => openSession(session.id)}
                        className={cn(
                          "w-full text-left rounded-lg px-3 py-2 border transition-colors",
                          activeSessionId === session.id
                            ? "bg-white border-zinc-300"
                            : "bg-transparent border-transparent hover:bg-white hover:border-zinc-200"
                        )}
                      >
                        <div className="text-xs font-semibold text-zinc-800 truncate">
                          {session.title || 'New Chat'}
                        </div>
                        <div className="text-[11px] text-zinc-500 truncate mt-0.5">
                          {session.last_message || 'No messages yet'}
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </aside>
            )}

            <div className="flex-1 flex flex-col min-h-0">
              <div className="flex-1 overflow-y-auto" ref={scrollRef}>
                <div className="max-w-3xl mx-auto w-full py-12 px-6 space-y-8">
                  {messages.map((msg, i) => (
                    <div key={i} className="space-y-4">
                      <div className={cn(
                        "flex gap-4",
                        msg.role === 'user' ? "flex-row-reverse" : ""
                      )}>
                        <div className={cn(
                          "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-sm",
                          msg.role === 'assistant' ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-500"
                        )}>
                          {msg.role === 'assistant' ? <Sparkles className="w-4 h-4" /> : <User className="w-4 h-4" />}
                        </div>
                        <div className="flex flex-col gap-1 max-w-[85%]">
                          <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest px-1">
                            {msg.role === 'assistant' ? 'Katy' : 'You'}
                          </span>
                          
                          {msg.role === 'assistant' && (msg.activities?.length || msg.thinking) && (
                            <div className="mb-3 space-y-1.5">
                              {(msg.activities && msg.activities.length > 0 ? msg.activities : buildFallbackActivity(msg.thinking)).map((activity) => (
                                <div key={activity.id} className="space-y-1">
                                  <div className="flex items-center justify-between gap-4 text-[12.5px] leading-5">
                                    <div className="flex min-w-0 items-center gap-2.5 text-zinc-500">
                                      {activity.type === 'thinking' ? (
                                        <Brain className="w-3.5 h-3.5 shrink-0 text-zinc-400" />
                                      ) : (
                                        <Wrench className="w-3.5 h-3.5 shrink-0 text-zinc-400" />
                                      )}
                                      <span className="truncate text-zinc-500">{activity.label}</span>
                                      {activity.meta && (
                                        <span className="shrink-0 rounded-full bg-zinc-50 px-2 py-0.5 font-mono text-[11px] text-zinc-400">
                                          {activity.meta}
                                        </span>
                                      )}
                                    </div>
                                    <div className="shrink-0 text-[12px]">
                                      {activity.status === 'done' && (
                                        <span className="inline-flex items-center gap-1 text-emerald-600">
                                          <CheckCircle2 className="w-3.5 h-3.5" />
                                          Done
                                        </span>
                                      )}
                                      {activity.status === 'running' && (
                                        <span className="inline-flex items-center gap-1 text-zinc-400">
                                          <span className="flex items-center gap-0.5">
                                            <span className="h-1.5 w-1.5 rounded-full bg-zinc-300 animate-pulse" />
                                            <span className="h-1.5 w-1.5 rounded-full bg-zinc-300 animate-pulse [animation-delay:120ms]" />
                                            <span className="h-1.5 w-1.5 rounded-full bg-zinc-300 animate-pulse [animation-delay:240ms]" />
                                          </span>
                                          Live
                                        </span>
                                      )}
                                      {activity.status === 'error' && (
                                        <span className="inline-flex items-center gap-1 text-amber-600">
                                          <AlertCircle className="w-3.5 h-3.5" />
                                          Error
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                  {activity.status === 'error' && activity.detail && (
                                    <div className="pl-6 text-[12px] leading-5 text-amber-700/90">
                                      {truncateLabel(stripMarkdown(activity.detail), 180)}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}

                          <div className={cn(
                            "text-sm leading-relaxed",
                            msg.role === 'user' ? "text-[#37352f]" : "text-[#37352f]"
                          )}>
                            {msg.role === 'assistant' ? (
                              <div className="max-w-none text-[14px] leading-6 text-zinc-700 space-y-3 [&_p]:my-2 [&_ul]:my-2 [&_ol]:my-2 [&_li]:my-0.5 [&_pre]:my-3 [&_blockquote]:my-3">
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm]}
                                  components={{
                                    p: ({ children }) => <p className="whitespace-pre-wrap leading-6">{children}</p>,
                                    ul: ({ children }) => <ul className="list-disc pl-6 space-y-1">{children}</ul>,
                                    ol: ({ children }) => <ol className="list-decimal pl-6 space-y-1">{children}</ol>,
                                    li: ({ children }) => <li className="leading-6">{children}</li>,
                                    table: ({ children }) => (
                                      <div className="my-4 overflow-x-auto rounded-lg border border-zinc-200">
                                        <table className="min-w-full border-collapse text-[13px]">{children}</table>
                                      </div>
                                    ),
                                    thead: ({ children }) => <thead className="bg-zinc-50">{children}</thead>,
                                    th: ({ children }) => (
                                      <th className="border-b border-zinc-200 px-3 py-2 text-left font-medium text-zinc-700">
                                        {children}
                                      </th>
                                    ),
                                    td: ({ children }) => <td className="border-b border-zinc-100 px-3 py-2 align-top">{children}</td>,
                                    code: ({ inline, children }) =>
                                      inline ? (
                                        <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-[12px] font-mono">{children}</code>
                                      ) : (
                                        <code className="block overflow-x-auto rounded-lg bg-zinc-950 p-3 text-[12px] font-mono text-zinc-100">
                                          {children}
                                        </code>
                                      ),
                                    blockquote: ({ children }) => (
                                      <blockquote className="border-l-4 border-zinc-300 pl-4 italic text-zinc-600">
                                        {children}
                                      </blockquote>
                                    ),
                                  }}
                                >
                                  {normalizeMarkdown(msg.content)}
                                </ReactMarkdown>
                              </div>
                            ) : (
                              msg.content
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                  
                </div>
              </div>

              <div className="p-6 bg-white border-t border-zinc-100">
              <div className="max-w-3xl mx-auto w-full">
                <div className="relative bg-white border border-zinc-200 rounded-xl p-4 shadow-sm focus-within:border-zinc-400 transition-colors">
                  <textarea
                    placeholder="Ask Katy anything..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                    className="w-full bg-transparent border-none focus:ring-0 outline-none focus:outline-none shadow-none resize-none text-sm min-h-[44px] py-1 text-[#37352f] placeholder:text-zinc-400"
                  />
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-zinc-50">
                    <div className="flex items-center gap-1">
                      <ModelDropdown value={selectedModel} onChange={setSelectedModel} />
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-zinc-900">
                        <Paperclip className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-zinc-900">
                        <Mic className="w-4 h-4" />
                      </Button>
                      <div className="h-4 w-[1px] bg-zinc-100 mx-1" />
                      <Button variant="ghost" size="sm" className="h-8 px-2 text-[10px] font-bold text-zinc-400 hover:text-zinc-900 uppercase tracking-wider flex items-center gap-1.5">
                        <Eraser className="w-3 h-3" />
                        Clean history
                      </Button>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-50 text-[10px] font-medium text-zinc-400">
                        <span className="px-1 py-0.5 rounded bg-white border border-zinc-200">Shift + ↵</span>
                        <span>for newline</span>
                      </div>
                      <Button 
                        onClick={handleSend}
                        disabled={!input.trim() || isThinking}
                        size="icon"
                        className="bg-zinc-900 text-white hover:bg-zinc-800 h-8 w-8 rounded-lg transition-all active:scale-95"
                      >
                        <Send className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Quick Suggestions Pills */}
                <div className="flex flex-wrap gap-2 mt-3">
                  {[
                    { label: 'List my repos...', text: 'List my 5 most recently updated GitHub repositories' },
                    { label: 'Prioritize features...', text: 'Help me prioritize my backlog using RICE framework' },
                    { label: 'Draft a PRD...', text: 'Draft a PRD for a new dark mode feature' },
                    { label: 'Define metrics...', text: 'What success metrics should I track for my MVP?' },
                  ].map((suggestion) => (
                    <button
                      key={suggestion.label}
                      onClick={() => setInput(suggestion.text)}
                      className="px-3 py-1.5 rounded-full border border-zinc-200 bg-white text-xs text-zinc-500 hover:bg-zinc-50 hover:border-zinc-300 hover:text-zinc-700 transition-all shadow-sm"
                    >
                      {suggestion.label}
                    </button>
                  ))}
                </div>
              </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
