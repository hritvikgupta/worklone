import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { CalendarClock, ChevronRight, Clock3, PlayCircle, Repeat2, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  getWorkflow,
  listWorkflows,
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

function statusTone(status: string): string {
  if (status === 'active' || status === 'completed') return 'border-emerald-200 text-emerald-700 bg-emerald-50';
  if (status === 'running') return 'border-sky-200 text-sky-700 bg-sky-50';
  if (status === 'failed') return 'border-rose-200 text-rose-700 bg-rose-50';
  if (status === 'paused' || status === 'cancelled') return 'border-zinc-300 text-zinc-600 bg-zinc-50';
  return 'border-amber-200 text-amber-700 bg-amber-50';
}

export function ScheduledWorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowDetail | null>(null);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);

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

  const selectedSummary = workflows.find((workflow) => workflow.id === selectedWorkflowId) || null;

  const activeSchedules = workflows.filter((workflow) => workflow.status === 'active').length;
  const nextRunValue = workflows
    .map((workflow) => workflow.handoff_at)
    .filter(Boolean)
    .sort()[0] || null;

  const completedRuns = executions.filter((execution) => execution.status === 'completed').length;
  const failedRuns = executions.filter((execution) => execution.status === 'failed').length;
  const successRate = completedRuns + failedRuns > 0
    ? `${((completedRuns / (completedRuns + failedRuns)) * 100).toFixed(1)}%`
    : 'N/A';

  const openWorkflow = async (workflowId: string) => {
    setSelectedWorkflowId(workflowId);
    setDetailLoading(true);
    try {
      const data = await getWorkflow(workflowId);
      setSelectedWorkflow(data.workflow);
      setExecutions(data.executions);
    } catch (err) {
      console.error('Failed to load workflow detail:', err);
      setSelectedWorkflow(null);
      setExecutions([]);
    } finally {
      setDetailLoading(false);
    }
  };

  const closeWorkflow = () => {
    setSelectedWorkflowId(null);
    setSelectedWorkflow(null);
    setExecutions([]);
    setDetailLoading(false);
  };

  return (
    <div className="relative p-8">
      <div className="w-full space-y-6 animate-in slide-in-from-bottom-4 duration-300">
        <div className="flex items-end justify-between border-b border-border/50 pb-4">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Workflows</h2>
            <p className="text-muted-foreground mt-1 text-[14px] leading-6">
              Live workflow records from the shared workflow engine. Owner means who handed the workflow over for execution.
            </p>
          </div>
          <Button className="h-9 px-4 text-[13px] bg-zinc-900 text-white hover:bg-zinc-800" disabled>
            <CalendarClock className="w-4 h-4 mr-2" />
            New Workflow
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="rounded-lg border border-zinc-200 bg-white p-5">
            <div className="flex items-center gap-2 text-zinc-500 text-[14px] font-medium">
              <Repeat2 className="w-4 h-4" />
              Active Schedules
            </div>
            <div className="mt-2 text-2xl font-semibold text-zinc-900">{activeSchedules}</div>
          </div>
          <div className="rounded-lg border border-zinc-200 bg-white p-5">
            <div className="flex items-center gap-2 text-zinc-500 text-[14px] font-medium">
              <Clock3 className="w-4 h-4" />
              Latest Handoff
            </div>
            <div className="mt-2 text-lg font-semibold text-zinc-900">{formatDateTime(nextRunValue)}</div>
          </div>
          <div className="rounded-lg border border-zinc-200 bg-white p-5">
            <div className="flex items-center gap-2 text-zinc-500 text-[14px] font-medium">
              <PlayCircle className="w-4 h-4" />
              Success Rate
            </div>
            <div className="mt-2 text-2xl font-semibold text-zinc-900">{successRate}</div>
          </div>
        </div>

        <div className="space-y-3">
          {loading ? (
            <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
              Loading workflows...
            </div>
          ) : workflows.length === 0 ? (
            <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
              No workflows found.
            </div>
          ) : (
            workflows.map((workflow) => (
              <button
                key={workflow.id}
                type="button"
                onClick={() => openWorkflow(workflow.id)}
                className="w-full rounded-lg border border-zinc-200 bg-white p-5 text-left transition-colors hover:border-zinc-300 hover:bg-zinc-50"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="text-[12px] font-semibold tracking-wide uppercase text-zinc-400">{workflow.id}</div>
                    <h3 className="text-[18px] font-semibold text-zinc-900">{workflow.name}</h3>
                    <p className="text-[14px] text-zinc-500 leading-6 max-w-3xl">{workflow.description || 'No description provided.'}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${statusTone(workflow.status)}`}>
                      {formatStatus(workflow.status)}
                    </span>
                    <ChevronRight className="h-4 w-4 text-zinc-400" />
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-5 text-[14px] text-zinc-500">
                  <div>
                    <span className="font-medium text-zinc-700">Schedule:</span> {workflow.schedule}
                  </div>
                  <div>
                    <span className="font-medium text-zinc-700">Owner:</span> {workflow.owner}
                  </div>
                  <div>
                    <span className="font-medium text-zinc-700">Blocks:</span> {workflow.block_count}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      <AnimatePresence>
        {selectedWorkflowId && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeWorkflow}
              className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[1px]"
            />
            <motion.aside
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 280 }}
              className="fixed right-0 top-0 z-50 h-full w-[92%] max-w-2xl overflow-hidden border-l border-zinc-200 bg-white shadow-2xl"
            >
              <div className="flex h-full flex-col">
                <div className="flex items-start justify-between border-b border-zinc-200 px-6 py-5">
                  <div>
                    <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-zinc-400">
                      {selectedSummary?.id || selectedWorkflowId}
                    </div>
                    <h3 className="mt-1 text-xl font-semibold text-zinc-950">
                      {selectedWorkflow?.name || selectedSummary?.name || 'Workflow'}
                    </h3>
                    <p className="mt-1 text-sm text-zinc-500">
                      Owner is the actor who handed this workflow over for execution.
                    </p>
                  </div>
                  <Button variant="ghost" size="icon" onClick={closeWorkflow}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                <div className="flex-1 overflow-y-auto px-6 py-5">
                  {detailLoading || !selectedWorkflow ? (
                    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-500">
                      Loading workflow details...
                    </div>
                  ) : (
                    <div className="space-y-6">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-400">Status</div>
                          <div className="mt-2">
                            <Badge variant="outline" className={statusTone(selectedWorkflow.status)}>
                              {formatStatus(selectedWorkflow.status)}
                            </Badge>
                          </div>
                        </div>
                        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-400">Owner</div>
                          <div className="mt-2 text-sm font-medium text-zinc-900">{selectedWorkflow.owner}</div>
                          <div className="mt-1 text-xs text-zinc-500">
                            {selectedWorkflow.handoff_actor_type || selectedWorkflow.created_by_actor_type || 'unknown'}
                            {selectedWorkflow.owner_id ? ` • ${selectedWorkflow.owner_id}` : ''}
                          </div>
                        </div>
                      </div>

                      <div className="rounded-lg border border-zinc-200 bg-white p-4">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-400">Description</div>
                        <p className="mt-2 text-sm leading-6 text-zinc-600">
                          {selectedWorkflow.description || 'No description provided.'}
                        </p>
                        <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-zinc-600">
                          <div>
                            <span className="font-medium text-zinc-800">Schedule:</span> {selectedWorkflow.schedule}
                          </div>
                          <div>
                            <span className="font-medium text-zinc-800">Handoff At:</span> {formatDateTime(selectedWorkflow.handoff_at)}
                          </div>
                          <div>
                            <span className="font-medium text-zinc-800">Created By:</span> {selectedWorkflow.created_by_actor_name || 'Unknown'}
                          </div>
                          <div>
                            <span className="font-medium text-zinc-800">Updated:</span> {formatDateTime(selectedWorkflow.updated_at)}
                          </div>
                        </div>
                      </div>

                      <div>
                        <div className="mb-3 flex items-center justify-between">
                          <h4 className="text-sm font-semibold uppercase tracking-[0.16em] text-zinc-400">Triggers</h4>
                          <span className="text-xs text-zinc-500">{selectedWorkflow.triggers.length}</span>
                        </div>
                        <div className="space-y-3">
                          {selectedWorkflow.triggers.length === 0 ? (
                            <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-500">No triggers configured.</div>
                          ) : selectedWorkflow.triggers.map((trigger) => (
                            <div key={trigger.id} className="rounded-lg border border-zinc-200 bg-white p-4">
                              <div className="flex items-center justify-between gap-3">
                                <div>
                                  <div className="text-sm font-medium text-zinc-900">{trigger.name || trigger.trigger_type}</div>
                                  <div className="mt-1 text-xs text-zinc-500">
                                    {trigger.trigger_type} • {trigger.cron_expression || trigger.schedule_preset || trigger.webhook_path || 'No extra config'}
                                  </div>
                                </div>
                                <Badge variant="outline" className={trigger.enabled ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-zinc-200 bg-zinc-50 text-zinc-500'}>
                                  {trigger.enabled ? 'Enabled' : 'Disabled'}
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div>
                        <div className="mb-3 flex items-center justify-between">
                          <h4 className="text-sm font-semibold uppercase tracking-[0.16em] text-zinc-400">Blocks</h4>
                          <span className="text-xs text-zinc-500">{selectedWorkflow.blocks.length}</span>
                        </div>
                        <div className="space-y-3">
                          {selectedWorkflow.blocks.length === 0 ? (
                            <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-500">No blocks configured.</div>
                          ) : selectedWorkflow.blocks.map((block) => (
                            <div key={block.id} className="rounded-lg border border-zinc-200 bg-white p-4">
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <div className="text-sm font-medium text-zinc-900">{block.name}</div>
                                  <div className="mt-1 text-xs text-zinc-500">
                                    {block.block_type}
                                    {block.tool_name ? ` • ${block.tool_name}` : ''}
                                    {block.url ? ` • ${block.method} ${block.url}` : ''}
                                  </div>
                                  {block.description ? (
                                    <p className="mt-2 text-sm leading-6 text-zinc-600">{block.description}</p>
                                  ) : null}
                                </div>
                                <Badge variant="outline" className={statusTone(block.status)}>
                                  {formatStatus(block.status)}
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div>
                        <div className="mb-3 flex items-center justify-between">
                          <h4 className="text-sm font-semibold uppercase tracking-[0.16em] text-zinc-400">Execution History</h4>
                          <span className="text-xs text-zinc-500">{executions.length}</span>
                        </div>
                        <div className="space-y-3">
                          {executions.length === 0 ? (
                            <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-500">No executions recorded yet.</div>
                          ) : executions.map((execution) => (
                            <div key={execution.id} className="rounded-lg border border-zinc-200 bg-white p-4">
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <div className="text-sm font-medium text-zinc-900">{execution.id}</div>
                                  <div className="mt-1 text-xs text-zinc-500">
                                    {execution.trigger_type || 'manual'} • started {formatDateTime(execution.started_at)}
                                  </div>
                                </div>
                                <Badge variant="outline" className={statusTone(execution.status)}>
                                  {formatStatus(execution.status)}
                                </Badge>
                              </div>
                              <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-zinc-600">
                                <div>
                                  <span className="font-medium text-zinc-800">Completed:</span> {formatDateTime(execution.completed_at)}
                                </div>
                                <div>
                                  <span className="font-medium text-zinc-800">Duration:</span> {execution.execution_time ? `${execution.execution_time.toFixed(2)}s` : 'N/A'}
                                </div>
                              </div>
                              {execution.error ? (
                                <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                                  {execution.error}
                                </div>
                              ) : null}
                              <Separator className="my-3" />
                              <div>
                                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-400">Block Results</div>
                                <pre className="mt-2 overflow-x-auto rounded-lg bg-zinc-950 p-3 text-xs leading-5 text-zinc-100">
                                  {JSON.stringify(execution.block_results, null, 2)}
                                </pre>
                              </div>
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
