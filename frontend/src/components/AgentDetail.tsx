import React from 'react';
import { Agent } from '@/src/types';
import { useEmployeePresence } from '@/src/hooks/usePresence';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  X, 
  Bot, 
  Terminal, 
  History, 
  Code, 
  ChevronLeft,
  Cpu,
  Activity as ActivityIcon,
  Layers,
  Settings,
  ShieldCheck,
  Clock,
  PauseCircle,
  PlayCircle,
  CheckCircle2,
  AlertCircle,
  ArrowUpRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmployeeTool, EmployeeSkill, EmployeeTask, EmployeeActivity } from '@/src/api/employees';

interface AgentDetailProps {
  agent: Agent;
  onBack: () => void;
  onConfigure?: () => void;
  onCoverUpdate?: (coverUrl: string) => Promise<void> | void;
  tools?: EmployeeTool[];
  skills?: EmployeeSkill[];
  tasks?: EmployeeTask[];
  activity?: EmployeeActivity[];
}

function normalizeSystemPrompt(text: string): string {
  return text
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n(#{1,6}\s)/g, '\n\n$1')
    .replace(/([^\n])\n(#{1,6}\s)/g, '$1\n\n$2')
    .replace(/\n([-*+]\s)/g, '\n\n$1')
    .replace(/([^\n])\n([-*+]\s)/g, '$1\n\n$2')
    .replace(/\n(\d+\.\s)/g, '\n\n$1')
    .replace(/([^\n])\n(\d+\.\s)/g, '$1\n\n$2')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

const markdownComponents = {
  h1: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 className={cn('mb-6 text-[28px] font-semibold tracking-tight text-foreground', className)} {...props} />
  ),
  h2: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 className={cn('mt-8 mb-4 text-[22px] font-semibold tracking-tight text-foreground', className)} {...props} />
  ),
  h3: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 className={cn('mt-6 mb-3 text-[17px] font-semibold text-foreground', className)} {...props} />
  ),
  p: ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className={cn('mb-4 text-[15px] leading-7 text-foreground', className)} {...props} />
  ),
  ul: ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul className={cn('mb-5 list-disc space-y-2 pl-6 text-[15px] leading-7 text-foreground', className)} {...props} />
  ),
  ol: ({ className, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol className={cn('mb-5 list-decimal space-y-2 pl-6 text-[15px] leading-7 text-foreground', className)} {...props} />
  ),
  li: ({ className, ...props }: React.HTMLAttributes<HTMLLIElement>) => (
    <li className={cn('pl-1 marker:text-muted-foreground', className)} {...props} />
  ),
  strong: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <strong className={cn('font-semibold text-foreground', className)} {...props} />
  ),
  em: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <em className={cn('italic text-foreground', className)} {...props} />
  ),
  code: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <code className={cn('rounded bg-muted px-1.5 py-0.5 text-[0.92em] text-foreground', className)} {...props} />
  ),
  pre: ({ className, ...props }: React.HTMLAttributes<HTMLPreElement>) => (
    <pre className={cn('mb-6 overflow-x-auto rounded-xl border border-border bg-muted p-4 text-[13px] leading-6 text-foreground', className)} {...props} />
  ),
  blockquote: ({ className, ...props }: React.HTMLAttributes<HTMLQuoteElement>) => (
    <blockquote className={cn('mb-5 border-l-2 border-border pl-4 italic text-muted-foreground', className)} {...props} />
  ),
  hr: ({ className, ...props }: React.HTMLAttributes<HTMLHRElement>) => (
    <hr className={cn('my-8 border-border', className)} {...props} />
  ),
};

export function AgentDetail({ agent, onBack, onConfigure, onCoverUpdate, tools = [], skills = [], tasks = [], activity = [] }: AgentDetailProps) {
  const { statuses, busyIn } = useEmployeePresence([agent.id]);
  const livePresence = {
    status: (statuses[agent.id]?.status as Agent['status']) || agent.status,
    busyIn: busyIn(agent.id),
  };
  const [selectedActivity, setSelectedActivity] = React.useState<EmployeeActivity | null>(null);
  const [showFullPrompt, setShowFullPrompt] = React.useState(false);
  const [isUploadingCover, setIsUploadingCover] = React.useState(false);
  const [coverError, setCoverError] = React.useState<string | null>(null);
  const coverInputRef = React.useRef<HTMLInputElement | null>(null);
  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'working': return 'bg-blue-400';
      case 'idle': return 'bg-emerald-400';
      case 'blocked': return 'bg-rose-400';
      case 'offline': return 'bg-slate-300';
      default: return 'bg-slate-300';
    }
  };

  const activeTask = tasks.find((task) => task.status === 'in_progress')
    || tasks.find((task) => task.status === 'blocked')
    || null;
  const visibleTasks = tasks
    .filter((task) => task.status === 'in_progress' || task.status === 'blocked')
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 4);
  const latestPausedActivity = activity.find((entry) => entry.activity_type === 'workflow_paused');
  const latestResumedActivity = activity.find((entry) => entry.activity_type === 'workflow_resumed');
  const latestApprovalActivity =
    latestPausedActivity
      && (!latestResumedActivity || new Date(latestPausedActivity.timestamp).getTime() > new Date(latestResumedActivity.timestamp).getTime())
      ? latestPausedActivity
      : null;
  const taskById = new Map(tasks.map((task) => [task.id, task]));

  const formatActivityType = (type: string) =>
    type
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());

  const describeActivity = (entry: EmployeeActivity) => {
    const linkedTask = entry.task_id ? taskById.get(entry.task_id) : null;
    const base = linkedTask?.task_title || entry.message;
    const detail = linkedTask?.task_description || '';
    return { base, detail, linkedTask };
  };

  const taskStatusBadge = (status: string) => {
    if (status === 'in_progress') return 'bg-amber-50 text-amber-700 border-amber-200';
    if (status === 'blocked' || status === 'cancelled') return 'bg-rose-50 text-rose-700 border-rose-200';
    if (status === 'done') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    return 'bg-muted text-muted-foreground border-border';
  };

  const taskStatusIcon = (status: string) => {
    if (status === 'in_progress') return <PlayCircle className="w-4 h-4 text-amber-500" />;
    if (status === 'blocked') return <AlertCircle className="w-4 h-4 text-rose-500" />;
    if (status === 'done') return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
    return <Clock className="w-4 h-4 text-muted-foreground" />;
  };

  const historyMarker = (status?: string | null) => {
    if (status === 'done') {
      return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
    }
    if (status === 'in_progress') {
      return <PlayCircle className="h-4 w-4 text-amber-500" />;
    }
    if (status === 'blocked' || status === 'cancelled') {
      return <AlertCircle className="h-4 w-4 text-rose-500" />;
    }
    return <div className="h-2.5 w-2.5 rounded-full border-2 border-primary bg-background transition-transform group-hover:scale-125" />;
  };

  const handleCoverFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setCoverError(null);
    setIsUploadingCover(true);
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => reject(new Error("Failed to read image"));
        reader.readAsDataURL(file);
      });
      await onCoverUpdate?.(dataUrl);
    } catch (err) {
      setCoverError(err instanceof Error ? err.message : "Failed to upload cover image");
    } finally {
      setIsUploadingCover(false);
      event.target.value = '';
    }
  };

  const normalizedPrompt = normalizeSystemPrompt(agent.systemPrompt || '');
  const promptParagraphs = normalizedPrompt
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean);
  const promptPreview = promptParagraphs.slice(0, 2).join('\n\n');

  return (
    <div className="mx-auto w-full max-w-7xl animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6">
          <Card className="overflow-hidden border-border pt-0 pb-0 gap-0">
            <div
              className="relative h-36 bg-gradient-to-r from-zinc-200 via-zinc-100 to-zinc-200"
              style={agent.cover ? { backgroundImage: `url(${agent.cover})`, backgroundSize: 'cover', backgroundPosition: 'center' } : undefined}
            >
              <div className="absolute inset-0 bg-black/10" />
              <div className="absolute right-3 top-3 z-10">
                <input
                  ref={coverInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleCoverFileChange}
                />
                <Button
                  variant="secondary"
                  size="sm"
                  className="h-8 bg-white/90 text-xs hover:bg-white"
                  disabled={isUploadingCover}
                  onClick={() => coverInputRef.current?.click()}
                >
                  {isUploadingCover ? 'Uploading...' : 'Change Cover'}
                </Button>
              </div>
            </div>
            <CardContent className="relative px-6 pb-6 pt-0">
              <div className="flex items-start justify-between gap-4">
                <div className="relative -mt-12">
                  <Avatar className="h-24 w-24 rounded-full border-2 border-background shadow-sm">
                    <AvatarImage src={agent.avatar} alt={agent.name} />
                    <AvatarFallback className="text-2xl">{agent.name[0]}</AvatarFallback>
                  </Avatar>
                  <div
                    className={cn(
                      'absolute -bottom-1 -right-1 h-4 w-4 rounded-full border-2 border-background',
                      getStatusColor(livePresence.status as Agent['status']),
                    )}
                  />
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={onBack}>
                    <ChevronLeft className="h-4 w-4" />
                    Back
                  </Button>
                  <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={onConfigure}>
                    <Settings className="h-4 w-4" />
                    Configure
                  </Button>
                </div>
              </div>

              <div className="mt-3 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-3xl font-semibold tracking-tight">{agent.name}</h1>
                  <Badge variant="secondary" className="font-mono text-[10px]">
                    {agent.model}
                  </Badge>
                  <Badge variant="outline" className="capitalize">
                    {livePresence.status}
                  </Badge>
                </div>
                {agent.role && <div className="text-lg text-muted-foreground">{agent.role}</div>}
                {agent.description && (
                  <p className="max-w-3xl text-sm leading-6 text-foreground/90">{agent.description}</p>
                )}
                <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Cpu className="h-4 w-4" />
                    {skills.length} skills
                  </span>
                  <span>•</span>
                  <span>{tools.length} tools</span>
                  {livePresence.busyIn?.run_id && (
                    <>
                      <span>•</span>
                      <span className="font-mono text-xs">{livePresence.busyIn.run_id}</span>
                    </>
                  )}
                </div>
                {coverError && <div className="text-xs text-rose-600">{coverError}</div>}
              </div>
            </CardContent>
          </Card>

          {/* Left Feed: Overview & Prompt */}
          <div className="space-y-6">
          {/* Current Task Section */}
          <section className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-widest">
              <Terminal className="w-4 h-4" />
              Active Context
            </div>
            {latestApprovalActivity && (
              <Card className="border-amber-200 bg-amber-50/70 shadow-sm">
                <CardContent className="flex items-start gap-3 p-4">
                  <PauseCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-amber-900">Waiting for approval</div>
                    <p className="mt-1 text-sm leading-relaxed text-amber-800/90">
                      {latestApprovalActivity.message}
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
            {activeTask ? (
              <Card className="border-border shadow-sm bg-secondary/5">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between mb-1">
                    <div />
                    <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Updated {new Date(activeTask.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <CardTitle className="text-lg">{activeTask.task_title}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {activeTask.task_description || 'No task description provided.'}
                  </p>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className={cn("text-[10px] capitalize", taskStatusBadge(activeTask.status))}>
                      {activeTask.status.replace('_', ' ')}
                    </Badge>
                    <Badge variant="secondary" className="text-[10px] capitalize bg-secondary/50">
                      {activeTask.priority}
                    </Badge>
                    {activeTask.tags.map(tag => (
                      <Badge key={tag} variant="secondary" className="text-[10px] bg-secondary/50">
                        #{tag}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="h-32 flex flex-col items-center justify-center border-2 border-border border-border rounded-xl text-muted-foreground bg-secondary/5">
                <p className="text-sm italic">No active task assigned</p>
                <p className="mt-1 text-xs">The employee is not currently executing or waiting on a task.</p>
              </div>
            )}
            {visibleTasks.length > 0 && (
              <div className="grid gap-3">
                {visibleTasks.map((task) => (
                  <div key={task.id} className="flex items-start gap-3 rounded-xl border border-border bg-card px-4 py-3 shadow-sm">
                    <div className="pt-0.5">{taskStatusIcon(task.status)}</div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-3">
                        <div className="truncate text-sm font-medium text-foreground">{task.task_title}</div>
                        <Badge variant="outline" className={cn("shrink-0 text-[10px] capitalize", taskStatusBadge(task.status))}>
                          {task.status.replace('_', ' ')}
                        </Badge>
                      </div>
                      {task.task_description && (
                        <div className="mt-1 text-xs leading-5 text-muted-foreground">
                          {task.task_description}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Prompt Section */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-widest">
                <Code className="w-4 h-4" />
                System Instructions
              </div>
              <Badge variant="outline" className="text-[9px] border-emerald-500/20 text-emerald-600 bg-emerald-500/5 gap-1">
                <ShieldCheck className="w-3 h-3" />
                Verified Persona
              </Badge>
            </div>
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-b from-zinc-100/70 to-transparent rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
              <div className="rounded-xl border border-border bg-card p-6 text-sm leading-relaxed text-foreground shadow-sm overflow-hidden">
                <div className="mb-4 flex items-center gap-2 border-b border-border pb-2 text-xs text-muted-foreground">
                  <span className="text-foreground">system</span>
                  <span>prompt.md</span>
                </div>
                <div className="max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {promptPreview || normalizedPrompt}
                  </ReactMarkdown>
                </div>
                {promptParagraphs.length > 2 && (
                  <div className="mt-4 border-t border-border pt-3">
                    <Button variant="outline" size="sm" onClick={() => setShowFullPrompt(true)}>
                      Show full
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </section>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          <Card className="border-border shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Profile Language</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">English</CardContent>
          </Card>

          <Card className="border-border shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-widest">
                <Bot className="w-4 h-4" />
                Capabilities
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-muted-foreground">Capabilities</h4>
                <div className="flex flex-wrap gap-2">
                  {skills.map((skill) => (
                    <Badge key={skill.id} variant="secondary" className="bg-primary/5 text-primary border-primary/10">
                      {skill.skill_name}
                    </Badge>
                  ))}
                  {skills.length === 0 && (
                    <span className="text-sm text-muted-foreground">No skills attached</span>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-muted-foreground">Tools</h4>
                <div className="flex flex-wrap gap-2">
                  {tools.map((tool) => (
                    <Badge key={tool.id} variant="outline" className="bg-card text-foreground border-border">
                      {tool.tool_name}
                    </Badge>
                  ))}
                  {tools.length === 0 && (
                    <span className="text-sm text-muted-foreground">No tools attached</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <section className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-widest">
              <ActivityIcon className="w-4 h-4" />
              Recent Activity
            </div>
            <div className="relative space-y-4 before:absolute before:bottom-2 before:left-[17px] before:top-2 before:w-px before:bg-border/60">
              {activity.length > 0 ? (
                activity.map((activity) => {
                  const { base, detail, linkedTask } = describeActivity(activity);
                  return (
                  <button
                    key={activity.id}
                    type="button"
                    onClick={() => setSelectedActivity(activity)}
                    className="relative block w-full pl-10 text-left group"
                  >
                    <div className="absolute left-0 top-1 w-9 h-9 flex items-center justify-center">
                      {historyMarker(linkedTask?.status)}
                    </div>
                    <div className="space-y-1.5 rounded-lg border border-transparent p-3 transition-colors hover:border-border hover:bg-secondary/30">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold capitalize text-foreground/90">
                          {formatActivityType(activity.activity_type)}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-muted-foreground font-medium">
                            {new Date(activity.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                          <ArrowUpRight className="h-3 w-3 text-muted-foreground" />
                        </div>
                      </div>
                      <p className="text-xs text-foreground/90 leading-snug">{base}</p>
                      <p className="text-xs text-muted-foreground leading-snug">{activity.message}</p>
                      {detail && (
                        <p className="line-clamp-2 text-[11px] leading-5 text-muted-foreground">{detail}</p>
                      )}
                      {linkedTask && (
                        <div className="flex items-center gap-1.5 pt-1">
                          <Badge variant="outline" className="text-[9px] h-4 px-1.5 bg-background capitalize">
                            {linkedTask.status.replace('_', ' ')}
                          </Badge>
                          <Badge variant="outline" className="text-[9px] h-4 px-1.5 bg-background capitalize">
                            {linkedTask.priority}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </button>
                )})
              ) : (
                <div className="pl-10 text-xs text-muted-foreground italic py-4">
                  No recent activity recorded
                </div>
              )}
            </div>
          </section>
        </div>
      </div>

      <Dialog open={Boolean(selectedActivity)} onOpenChange={(open) => !open && setSelectedActivity(null)}>
        <DialogContent className="max-w-xl">
          {selectedActivity && (() => {
            const { base, detail, linkedTask } = describeActivity(selectedActivity);
            return (
              <>
                <DialogHeader>
                  <DialogTitle>{formatActivityType(selectedActivity.activity_type)}</DialogTitle>
                  <DialogDescription>
                    {new Date(selectedActivity.timestamp).toLocaleString()}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 text-sm text-foreground">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Summary</div>
                    <div className="mt-1 leading-6 text-foreground">{base}</div>
                  </div>
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">What Happened</div>
                    <div className="mt-1 leading-6">{selectedActivity.message}</div>
                  </div>
                  {linkedTask && (
                    <div className="rounded-lg border border-border bg-muted p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-medium text-foreground">{linkedTask.task_title}</div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className={cn("capitalize", taskStatusBadge(linkedTask.status))}>
                            {linkedTask.status.replace('_', ' ')}
                          </Badge>
                          <Badge variant="outline" className="capitalize">
                            {linkedTask.priority}
                          </Badge>
                        </div>
                      </div>
                      {detail && (
                        <div className="mt-2 text-sm leading-6 text-muted-foreground">{detail}</div>
                      )}
                    </div>
                  )}
                  {selectedActivity.metadata && Object.keys(selectedActivity.metadata).length > 0 && (
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Metadata</div>
                      <pre className="mt-2 overflow-x-auto rounded-lg border border-border bg-muted p-3 text-xs leading-5 text-foreground">
                        {JSON.stringify(selectedActivity.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </>
            );
          })()}
        </DialogContent>
      </Dialog>

      <Dialog open={showFullPrompt} onOpenChange={setShowFullPrompt}>
        <DialogContent className="w-[96vw] !max-w-[96vw] sm:!max-w-6xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>System Instructions</DialogTitle>
            <DialogDescription>Complete prompt for {agent.name}</DialogDescription>
          </DialogHeader>
          <div className="rounded-xl border border-border bg-card p-6">
            <div className="max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {normalizedPrompt}
              </ReactMarkdown>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
