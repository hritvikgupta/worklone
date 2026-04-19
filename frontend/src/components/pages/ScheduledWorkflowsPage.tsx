import React, { useEffect, useState, useRef } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { 
  CalendarClock, 
  ChevronRight, 
  Clock3, 
  PlayCircle, 
  Repeat2, 
  RotateCcw, 
  Square, 
  X, 
  Play, 
  Zap, 
  Trash2,
  Plus,
  Loader2
} from 'lucide-react';
import { 
  IconCloud, 
  IconPhotoScan, 
  IconArrowUp,
  IconSparkles,
  IconLayout,
  IconBrain
} from '@tabler/icons-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { ScheduleEditor } from '@/src/components/ScheduleEditor';
import {
  cancelPausedExecution,
  getWorkflow,
  listPausedExecutions,
  PausedExecution,
  resumePausedExecution,
  listWorkflows,
  generateWorkflow,
  executeWorkflow,
  deleteWorkflow,
  updateWorkflow,
  WorkflowDetail,
  WorkflowExecution,
  WorkflowSummary,
} from '@/src/api/workflows';

function formatDateTime(value: string | null | undefined): string {
  if (!value) return 'Not available';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatStatus(status: string): string {
  return status.replace(/_/g, ' ');
}

function formatCron(cron: string | undefined | null): string {
  if (!cron) return 'Scheduled';
  const parts = cron.trim().split(/\s+/);
  if (parts.length < 5) return cron;
  const [min, hour, dom, month, dow] = parts;

  const h = parseInt(hour, 10);
  const m = parseInt(min, 10);
  const isValidTime = !isNaN(h) && !isNaN(m);
  const timeStr = isValidTime
    ? new Date(2000, 0, 1, h, m).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    : `${hour}:${min}`;

  if (dom === '*' && month === '*') {
    if (dow === '*') return `Daily at ${timeStr}`;
    const days: Record<string, string> = { '0':'Sun','1':'Mon','2':'Tue','3':'Wed','4':'Thu','5':'Fri','6':'Sat' };
    const dayName = days[dow] ?? `day ${dow}`;
    return `Every ${dayName} at ${timeStr}`;
  }
  if (dow === '*' && month === '*' && dom !== '*') return `Monthly on day ${dom} at ${timeStr}`;
  return cron;
}

function statusTone(status: string): string {
  if (status === 'active' || status === 'completed') return 'border-emerald-200 text-emerald-700 bg-emerald-50';
  if (status === 'running') return 'border-sky-200 text-sky-700 bg-sky-50';
  if (status === 'failed') return 'border-rose-200 text-rose-700 bg-rose-50';
  if (status === 'paused' || status === 'cancelled') return 'border-border text-muted-foreground bg-muted';
  return 'border-amber-200 text-amber-700 bg-amber-50';
}

export function ScheduledWorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowDetail | null>(null);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [pausedExecutions, setPausedExecutions] = useState<PausedExecution[]>([]);
  const [resumeDrafts, setResumeDrafts] = useState<Record<string, string>>({});
  const [resumeBusy, setResumeBusy] = useState<string | null>(null);
  const [cancelBusy, setCancelBusy] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editDescription, setEditDescription] = useState('');
  const [editSchedule, setEditSchedule] = useState('');
  const [editTasks, setEditTasks] = useState<{ id: string; description: string; status: string; result?: string; error?: string }[]>([]);
  const [editTimezone, setEditTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone);


  const selectedSummary = workflows.find((workflow) => workflow.id === selectedWorkflowId) || null;
  
  // Prompt input states
  const [promptValue, setPromptValue] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const data = await listWorkflows();
        if (!cancelled) setWorkflows(data);
      } catch (err) {
        console.error('Failed to load workflows:', err);
        if (!cancelled) setWorkflows([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);


  const handleGenerate = async () => {
    if (!promptValue.trim()) return;
    setIsGenerating(true);
    try {
      await generateWorkflow(promptValue);
      setPromptValue('');
      const data = await listWorkflows();
      setWorkflows(data);
    } catch (err) {
      console.error('Failed to generate workflow:', err);
      alert('Failed to generate workflow');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExecute = async (workflowId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      // Open the detail panel if not already open
      if (selectedWorkflowId !== workflowId) {
        await openWorkflow(workflowId);
      }

      // Stream execution — refresh detail on events
      await executeWorkflow(workflowId, async (event) => {
        if (
          event.type === 'tool_result' ||
          event.type === 'done' ||
          event.type === 'final' ||
          event.type === 'error' ||
          event.type === 'thinking' ||
          event.type === 'tool_start'
        ) {
          try {
            const detail = await getWorkflow(workflowId);
            setSelectedWorkflow(detail.workflow);
            setExecutions(detail.executions);
          } catch {}
        }
      });

      // Final refresh after stream ends
      const data = await listWorkflows();
      setWorkflows(data);
      try {
        const detail = await getWorkflow(workflowId);
        setSelectedWorkflow(detail.workflow);
        setExecutions(detail.executions);
      } catch {}
    } catch (err) {
      console.error('Failed to execute workflow:', err);
      alert('Failed to execute workflow');
    }
  };

  const handleToggleStatus = async (workflowId: string, currentStatus: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const newStatus = currentStatus === 'active' ? 'cancelled' : 'active';
    try {
      await updateWorkflow(workflowId, { status: newStatus });
      const data = await listWorkflows();
      setWorkflows(data);
      if (selectedWorkflowId === workflowId) {
        await refreshSelectedWorkflow();
      }
    } catch (err) {
      console.error('Failed to toggle workflow status:', err);
    }
  };

  const handleDeleteWorkflow = async (workflowId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const confirmed = window.confirm('Delete this workflow permanently?');
    if (!confirmed) return;

    try {
      await deleteWorkflow(workflowId);
      setWorkflows((prev) => prev.filter((w) => w.id !== workflowId));
      if (selectedWorkflowId === workflowId) {
        closeWorkflow();
      }
    } catch (err) {
      console.error('Failed to delete workflow:', err);
      window.alert('Failed to delete workflow');
    }
  };

  const openWorkflow = async (workflowId: string) => {
    setSelectedWorkflowId(workflowId);
    setDetailLoading(true);
    setIsEditing(false);
    try {
      const data = await getWorkflow(workflowId);
      setSelectedWorkflow(data.workflow);
      setExecutions(data.executions);
      const paused = await listPausedExecutions(workflowId);
      setPausedExecutions(paused);
      setEditDescription(data.workflow.description || '');
      setEditSchedule(data.workflow.triggers?.[0]?.cron_expression || data.workflow.schedule || '');
      setEditTimezone(data.workflow.triggers?.[0]?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone);
      setEditTasks(data.workflow.tasks?.map((t: any) => ({ id: t.id, description: t.description, status: t.status })) || []);
    } catch (err) {
      console.error('Failed to load workflow detail:', err);
      setSelectedWorkflow(null);
      setExecutions([]);
      setPausedExecutions([]);
    } finally {
      setDetailLoading(false);
    }
  };


  const handleSaveEdit = async () => {
    if (!selectedWorkflowId) return;
    try {
      await updateWorkflow(selectedWorkflowId, {
        description: editDescription,
        schedule: editSchedule,
        timezone: editTimezone,
        tasks: editTasks,
      });
      setIsEditing(false);
      await refreshSelectedWorkflow();
      const data = await listWorkflows();
      setWorkflows(data);
    } catch (err) {
      console.error('Failed to save workflow:', err);
      alert('Failed to save workflow changes.');
    }
  };

  const closeWorkflow = () => {
    setSelectedWorkflowId(null);
    setSelectedWorkflow(null);
    setExecutions([]);
    setPausedExecutions([]);
    setResumeDrafts({});
    setDetailLoading(false);
  };

  // Poll for live updates when workflow is open and has running tasks/executions
  useEffect(() => {
    if (!selectedWorkflowId) return;
    const hasRunning =
      selectedWorkflow?.status === 'running' ||
      selectedWorkflow?.tasks?.some((t: any) => t.status === 'running') ||
      executions.some((e) => e.status === 'running');
    if (!hasRunning) return;

    const interval = setInterval(async () => {
      try {
        const data = await getWorkflow(selectedWorkflowId);
        setSelectedWorkflow(data.workflow);
        setExecutions(data.executions);
      } catch {}
    }, 3000);
    return () => clearInterval(interval);
  }, [selectedWorkflowId, selectedWorkflow?.status, executions]);

  const refreshSelectedWorkflow = async () => {
    if (!selectedWorkflowId) return;
    const data = await getWorkflow(selectedWorkflowId);
    setSelectedWorkflow(data.workflow);
    setExecutions(data.executions);
    const paused = await listPausedExecutions(selectedWorkflowId);
    setPausedExecutions(paused);
  };

  const handleResume = async (pauseId: string) => {
    try {
      setResumeBusy(pauseId);
      const raw = (resumeDrafts[pauseId] || '').trim();
      const input = raw ? JSON.parse(raw) : {};
      await resumePausedExecution(pauseId, input);
      await refreshSelectedWorkflow();
      setResumeDrafts((prev) => ({ ...prev, [pauseId]: '' }));
    } catch (err) {
      console.error('Failed to resume paused workflow:', err);
      window.alert(err instanceof Error ? err.message : 'Failed to resume workflow');
    } finally {
      setResumeBusy(null);
    }
  };

  const handleCancelPause = async (pauseId: string) => {
    try {
      setCancelBusy(pauseId);
      await cancelPausedExecution(pauseId);
      await refreshSelectedWorkflow();
    } catch (err) {
      console.error('Failed to cancel paused workflow:', err);
      window.alert(err instanceof Error ? err.message : 'Failed to cancel paused workflow');
    } finally {
      setCancelBusy(null);
    }
  };

  return (
    <div className="p-8 pb-40 h-full overflow-y-auto bg-background relative overflow-x-hidden">
      <div className="max-w-6xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-300">
        
        {/* Header Section (Matching Dashboard/Agents) */}
        <div className="flex items-end justify-between border-b border-border pb-3">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">Workflows</h2>
            <p className="text-muted-foreground mt-1 text-xs">Automated tasks that run on a schedule.</p>
          </div>
        </div>

        {/* Workflow List Section */}
        <div className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-sm text-muted-foreground">Loading workflows...</span>
            </div>
          ) : workflows.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-muted/30 p-12 text-center">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-muted-foreground mb-4">
                <Zap className="h-5 w-5" />
              </div>
              <h3 className="text-foreground text-sm font-semibold">No workflows found</h3>
              <p className="text-muted-foreground text-xs mt-1">Describe an automation in the box below to get started.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {workflows.map((workflow, index) => (
                <motion.div
                  key={workflow.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => openWorkflow(workflow.id)}
                  className={cn(
                    "flex items-center justify-between rounded-lg border bg-card px-5 py-3.5 transition-all cursor-pointer group",
                    selectedWorkflowId === workflow.id
                      ? "border-primary bg-muted/40 shadow-sm"
                      : "border-border hover:border-foreground/10 hover:bg-muted/20"
                  )}
                >
                  <div className="flex items-center gap-4 min-w-0 flex-1">
                    <div className={cn(
                      "h-1.5 w-1.5 rounded-full flex-shrink-0",
                      workflow.status === 'active' ? "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.3)]" : "bg-zinc-300"
                    )} />
                    
                    <div className="min-w-0 flex-1">
                      <h3 className="text-[13.5px] font-medium text-foreground group-hover:text-primary transition-colors truncate">
                        {workflow.name}
                      </h3>
                      <div className="flex items-center gap-2 text-[11px] text-muted-foreground mt-0.5">
                        <span>{formatCron(workflow.schedule)}</span>
                        <span className="h-0.5 w-0.5 rounded-full bg-muted-foreground/20" />
                        <span>{((workflow.task_count || 0) * 20)} credits</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6 ml-4" onClick={(e) => e.stopPropagation()}>
                   <div className="flex items-center gap-2.5">
                     <button
                       onClick={(e) => handleToggleStatus(workflow.id, workflow.status, e)}
                       className={cn(
                         "relative h-4.5 w-8 rounded-full transition-colors focus:outline-none",
                         workflow.status === 'active' ? "bg-zinc-900" : "bg-zinc-200"
                       )}
                     >
                       <div className={cn(
                         "absolute top-0.5 left-0.5 h-3.5 w-3.5 rounded-full bg-white transition-transform shadow-sm",
                         workflow.status === 'active' ? "translate-x-3.5" : "translate-x-0"
                       )} />
                     </button>
                     <Button variant="ghost" size="icon" onClick={(e) => handleExecute(workflow.id, e)} className="h-7 w-7 rounded-full text-muted-foreground hover:text-zinc-900 hover:bg-zinc-100">
                       <Play className="h-3.5 w-3.5 fill-current" />
                     </Button>
                   </div>                    
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => handleDeleteWorkflow(workflow.id, e)}
                      className="h-7 w-7 rounded-full text-muted-foreground hover:text-rose-600 hover:bg-rose-50"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Floating Prompt Input Bar */}
      <div className="fixed bottom-10 left-1/2 -translate-x-1/2 w-full max-w-2xl px-6 z-40">
        <div className="flex flex-col rounded-[24px] border border-border bg-card shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all focus-within:border-foreground/15 focus-within:shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
          {/* Input Area */}
          <div className="p-4 pb-0">
            <Textarea
              ref={textareaRef}
              value={promptValue}
              onChange={(e) => setPromptValue(e.target.value)}
              placeholder="Describe an automation to create..."
              className="min-h-[60px] max-h-[200px] w-full resize-none border-0 bg-transparent p-0 text-[15px] leading-relaxed text-foreground placeholder:text-muted-foreground focus-visible:ring-0 shadow-none"
            />
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-end p-4 pt-2">
            <Button
              size="icon" 
              onClick={handleGenerate}
              className={cn(
                "h-8 w-8 rounded-full transition-all duration-300",
                promptValue.trim() && !isGenerating ? "bg-primary text-primary-foreground scale-100 shadow-md" : "bg-muted text-muted-foreground scale-95 opacity-60"
              )}
              disabled={!promptValue.trim() || isGenerating}
            >
              {isGenerating ? <Loader2 className="h-4.5 w-4.5 animate-spin" /> : <IconArrowUp className="h-4.5 w-4.5" />}
            </Button>
          </div>
        </div>
      </div>

      {/* Sidebar Detail (Maintained existing logic) */}
      <AnimatePresence>
        {selectedWorkflowId && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeWorkflow}
              className="fixed inset-0 z-50 bg-white/40 backdrop-blur-md"
            />
            <motion.aside
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 280 }}
              className="fixed right-0 top-0 z-[60] h-full w-[92%] max-w-2xl overflow-hidden border-l border-border bg-card shadow-2xl"
            >
              <div className="flex h-full flex-col">
                <div className="flex items-start justify-between border-b border-border px-6 py-5">
                  <div className="flex-1">
                    <div className="text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
                      {selectedSummary?.id || selectedWorkflowId}
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <h3 className="text-xl font-semibold text-foreground">
                        {selectedWorkflow?.name || selectedSummary?.name || 'Workflow'}
                      </h3>
                      {selectedWorkflow && (
                        <div className="flex items-center gap-2 mr-2">
                          {isEditing ? (
                            <>
                              <Button variant="outline" size="sm" onClick={() => setIsEditing(false)}>Cancel</Button>
                              <Button size="sm" onClick={handleSaveEdit}>Save Changes</Button>
                            </>
                          ) : (
                            <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>Edit Workflow</Button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" onClick={closeWorkflow} className="rounded-full flex-shrink-0">
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                <div className="flex-1 overflow-y-auto px-6 py-5">
                  {detailLoading || !selectedWorkflow ? (
                    <div className="rounded-2xl border border-border bg-muted p-6 text-sm text-muted-foreground">
                      Loading details...
                    </div>
                  ) : (
                    <div className="space-y-8 pb-12">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="rounded-xl border border-border bg-muted/50 p-4">
                          <div className="flex items-center justify-between">
                            <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Status</div>
                            <button
                              onClick={(e) => handleToggleStatus(selectedWorkflow.id, selectedWorkflow.status, e)}
                              className={cn(
                                "relative h-3.5 w-6 rounded-full transition-colors focus:outline-none",
                                selectedWorkflow.status === 'active' ? "bg-zinc-900" : "bg-zinc-300"
                              )}
                            >
                              <div className={cn(
                                "absolute top-0.5 left-0.5 h-2.5 w-2.5 rounded-full bg-white transition-transform shadow-sm",
                                selectedWorkflow.status === 'active' ? "translate-x-2.5" : "translate-x-0"
                              )} />
                            </button>
                          </div>
                          <div className="mt-1.5 flex items-center gap-2">
                            <div className={cn(
                              "h-1.5 w-1.5 rounded-full",
                              selectedWorkflow.status === 'active' ? "bg-emerald-500" : "bg-zinc-400"
                            )} />
                            <span className="text-xs font-semibold capitalize text-foreground">
                              {formatStatus(selectedWorkflow.status)}
                            </span>
                          </div>
                        </div>
                        <div className="rounded-xl border border-border bg-muted/50 p-4">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Owner</div>
                          <div className="mt-1.5 text-xs font-semibold text-foreground truncate">
                            {/^(user_|wf_|exec_|[A-Za-z0-9_-]{15,})$/.test(selectedWorkflow.owner) ? 'System' : selectedWorkflow.owner}
                          </div>
                          <div className="text-[9px] font-medium text-muted-foreground uppercase tracking-tight mt-0.5">
                            {selectedWorkflow.handoff_actor_type || selectedWorkflow.created_by_actor_type || 'User'}
                          </div>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Description</div>
                        {isEditing ? (
                          <Textarea
                            className="mt-3"
                            value={editDescription}
                            onChange={(e) => setEditDescription(e.target.value)}
                            placeholder="Workflow description..."
                          />
                        ) : (
                          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                            {selectedWorkflow.description || 'No description provided.'}
                          </p>
                        )}
                        <Separator className="my-5 bg-border" />

                        {/* Schedule Section */}
                        <div className="mb-5">
                          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block mb-3">Schedule</span>
                          {isEditing ? (
                            <ScheduleEditor
                              schedule={editSchedule}
                              timezone={editTimezone}
                              nextRunAt={selectedWorkflow.handoff_at}
                              onChange={(newSchedule, newTimezone) => {
                                setEditSchedule(newSchedule);
                                setEditTimezone(newTimezone);
                              }}
                            />
                          ) : (
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-sm">
                                <span className="font-medium text-foreground">{formatCron(selectedWorkflow.schedule)}</span>
                                {selectedWorkflow.triggers?.[0]?.timezone && (
                                  <span className="text-[11px] text-muted-foreground">({selectedWorkflow.triggers[0].timezone})</span>
                                )}
                              </div>
                              {selectedWorkflow.handoff_at && (
                                <div className="rounded-lg bg-muted/50 px-3 py-2 text-[12px] text-muted-foreground">
                                  <span className="font-medium">Next run:</span>{' '}
                                  {formatDateTime(selectedWorkflow.handoff_at)}
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        <Separator className="my-5 bg-border" />
                        <div className="grid grid-cols-2 gap-y-4 gap-x-6 text-[13px]">
                          <div>
                            <span className="text-muted-foreground block mb-1">Created By</span>
                            <span className="font-medium text-foreground">{selectedWorkflow.created_by_actor_name || 'Unknown'}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground block mb-1">Handoff At</span>
                            <span className="font-medium text-foreground">{formatDateTime(selectedWorkflow.handoff_at)}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground block mb-1">Last Updated</span>
                            <span className="font-medium text-foreground">{formatDateTime(selectedWorkflow.updated_at)}</span>
                          </div>
                        </div>
                      </div>

                      {/* Tasks Section - Professional Timeline */}
                      <div className="pt-2">
                        <div className="relative pl-6 ml-2 border-l border-zinc-200 space-y-10">
                          {(!selectedWorkflow.tasks || selectedWorkflow.tasks.length === 0) && !isEditing ? (
                             <div className="text-sm text-muted-foreground ml-2">No tasks defined.</div>
                          ) : (isEditing ? editTasks : selectedWorkflow.tasks).map((task, index) => (
                            <div key={task.id} className="relative">
                              {/* Timeline Dot */}
                              <div className={cn(
                                "absolute -left-[30px] top-1 h-3 w-3 rounded-full border-2 border-background ring-1 ring-zinc-200",
                                task.status === 'completed' || task.status === 'running' ? "bg-zinc-900" : "bg-zinc-200"
                              )} />
                              
                              <div className="space-y-2.5">
                                <div className="flex items-center justify-between">
                                  <div className="text-sm font-medium text-foreground leading-tight flex-1">
                                    {isEditing ? (
                                      <Textarea 
                                        className="w-full text-sm min-h-[60px]"
                                        value={task.description}
                                        onChange={(e) => {
                                          const newTasks = [...editTasks];
                                          newTasks[index] = { ...newTasks[index], description: e.target.value };
                                          setEditTasks(newTasks);
                                        }}
                                      />
                                    ) : (
                                      task.description
                                    )}
                                  </div>
                                  {!isEditing && (
                                    <span className={cn(
                                      "text-[10px] font-bold uppercase tracking-wider ml-4 px-1.5 py-0.5 rounded",
                                      task.status === 'completed' ? "text-zinc-500" : 
                                      task.status === 'running' ? "text-zinc-900 animate-pulse" : 
                                      "text-zinc-300"
                                    )}>
                                      {task.status}
                                    </span>
                                  )}
                                </div>
                                
                                {task.error && !isEditing && (
                                  <div className="pl-4 border-l border-rose-200 py-0.5 text-[12px] text-rose-600 whitespace-pre-wrap">
                                    {task.error}
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                        {isEditing && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="mt-4 w-full border-dashed"
                            onClick={() => setEditTasks([...editTasks, { id: `new_${Date.now()}`, description: "", status: "pending" }])}
                          >
                            <Plus className="w-4 h-4 mr-2" /> Add Task
                          </Button>
                        )}
                      </div>

                      {/* Execution History */}
                      <div>
                        <div className="mb-4 flex items-center justify-between">
                          <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Execution History</h4>
                        </div>
                        <div className="space-y-2">
                          {executions.length === 0 ? (
                            <div className="rounded-xl border border-border bg-muted/30 p-4 text-xs text-muted-foreground text-center font-medium">No history yet.</div>
                          ) : executions.map((execution) => (
                            <div key={execution.id} className="rounded-xl border border-border bg-card p-3 shadow-sm hover:shadow-md transition-shadow">
                              <div className="flex items-center justify-between gap-4">
                                <div className="min-w-0 flex-1">
                                  <div className="text-[12px] font-medium text-foreground flex items-center gap-2">
                                    <span className="capitalize">{execution.trigger_type || 'manual'}</span>
                                    <span className="h-1 w-1 rounded-full bg-muted-foreground/30" />
                                    <span className="text-muted-foreground font-normal">{formatDateTime(execution.started_at)}</span>
                                  </div>
                                  <div className="text-[10px] text-muted-foreground mt-0.5 font-medium">
                                    Duration: {execution.execution_time ? `${execution.execution_time.toFixed(1)}s` : '—'}
                                  </div>
                                </div>
                                <Badge variant="outline" className={cn("rounded-full border-0 px-2 py-0.5 text-[9px] font-bold uppercase", statusTone(execution.status))}>
                                  {formatStatus(execution.status)}
                                </Badge>
                              </div>
                              {execution.error && (
                                <div className="mt-2 rounded-lg bg-rose-50/50 p-2 text-rose-600 text-[10px] font-medium leading-tight border border-rose-100">
                                  {execution.error}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
