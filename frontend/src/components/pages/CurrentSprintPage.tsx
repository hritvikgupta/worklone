import React, { useState, useEffect, useRef } from 'react';
import { IssueBoard } from '@/src/components/IssueBoard';
import { Issue } from '@/src/types';
import { getActiveSprint, createTask, updateTaskColumn, updateTaskDetails, updateTaskAssignment, runTask, SprintData, Column } from '@/src/api/sprints';

const mapColumnNameToStatus = (name: string) => {
  const lower = name.toLowerCase();
  if (lower.includes('todo') || lower.includes('to do')) return 'todo';
  if (lower.includes('progress')) return 'in-progress';
  if (lower.includes('review')) return 'review';
  if (lower.includes('done')) return 'done';
  return 'backlog';
};

const mapStatusToColumnId = (status: string, columns: Column[]) => {
  const match = columns.find(c => mapColumnNameToStatus(c.name) === status);
  return match ? match.id : columns[0].id;
};

export function CurrentSprintPage() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [sprintData, setSprintData] = useState<SprintData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchSprint = async () => {
    try {
      const data = await getActiveSprint();
      setSprintData(data);
      // Map Task to Issue format
      const mappedIssues: Issue[] = data.tasks.map((task) => {
        const column = data.columns.find((c) => c.id === task.column_id);
        const status = column ? mapColumnNameToStatus(column.name) : 'backlog';
        return {
          id: task.id,
          title: task.title,
          description: task.description || '',
          requirements: task.requirements || '',
          status,
          priority: task.priority as 'low' | 'medium' | 'high',
          tags: [],
          assigneeId: task.employee_id || 'user-1',
          agentId: task.employee_id || undefined,
          createdAt: task.created_at,
          comments: task.messages.map((m) => ({
            id: m.id,
            authorId: m.sender_id,
            authorName: m.sender_name || 'User',
            content: m.content,
            timestamp: m.created_at,
            type: m.sender_type === 'employee' ? 'agent' : m.message_type === 'system' ? 'system' : 'user',
          })),
          runs: (task.runs || []).map((r) => ({
            id: r.id,
            status: r.status,
            employeeName: r.employee_name,
            summary: r.summary,
            error: r.error,
            createdAt: r.created_at,
            updatedAt: r.updated_at,
            steps: (r.steps || []).map((s) => ({
              id: s.id,
              title: s.title,
              status: s.status,
              updatedAt: s.updated_at,
            })),
          })),
          fileChanges: [],
        };
      });
      setIssues(mappedIssues);

      // Clear active-run flags for any task whose latest run has finished.
      for (const task of data.tasks) {
        const latest = (task.runs || [])[0];
        if (latest && latest.status !== 'running' && activeRunsRef.current.has(task.id)) {
          activeRunsRef.current.delete(task.id);
        }
      }
      if (activeRunsRef.current.size === 0) {
        stopPolling();
      }
    } catch (error) {
      console.error('Failed to fetch sprint:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSprint();
  }, []);

  // Live-poll while any task run is active so the activity log streams updates.
  const activeRunsRef = useRef<Set<string>>(new Set());
  const pollTimerRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  const startPolling = () => {
    if (pollTimerRef.current !== null) return;
    pollTimerRef.current = window.setInterval(() => {
      if (activeRunsRef.current.size === 0) {
        stopPolling();
        return;
      }
      fetchSprint();
    }, 2000);
  };

  useEffect(() => {
    return () => stopPolling();
  }, []);

  const handleAddIssue = async (status: string) => {
    if (!sprintData) return;
    const columnId = mapStatusToColumnId(status, sprintData.columns);
    
    try {
      await createTask(sprintData.sprint.id, {
        title: 'New Task',
        column_id: columnId,
        description: 'Describe the task here...',
        priority: 'medium',
      });
      // Refresh
      fetchSprint();
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const handleUpdateIssues = async (newIssues: Issue[]) => {
    setIssues(newIssues);
    
    if (!sprintData) return;
    const oldIssues = issues;
    for (const newIssue of newIssues) {
      const oldIssue = oldIssues.find(i => i.id === newIssue.id);
      if (oldIssue && oldIssue.status !== newIssue.status) {
        const columnId = mapStatusToColumnId(newIssue.status, sprintData.columns);
        try {
          updateTaskColumn(newIssue.id, columnId);
        } catch (e) { console.error(e); }
      }
    }
  };

  const handleUpdateIssueDetails = async (issueId: string, details: { title: string; description: string; requirements: string; agentId?: string }) => {
    try {
      await updateTaskDetails(issueId, { title: details.title, description: details.description, requirements: details.requirements });
      if (details.agentId !== undefined) {
        await updateTaskAssignment(issueId, details.agentId);
      }
    } catch (e) {
      console.error('Failed to update task details:', e);
    }
  };

  const handleRunTask = async (issueId: string) => {
    if (!sprintData) return;
    try {
      await runTask(sprintData.sprint.id, issueId);
      activeRunsRef.current.add(issueId);
      startPolling();
      // Auto-expire the active run flag after 5 minutes even if the stream never
      // returns a final message — prevents the poll loop from running forever.
      window.setTimeout(() => {
        activeRunsRef.current.delete(issueId);
      }, 5 * 60 * 1000);
      // Fetch immediately so the "started" marker appears without waiting 2s.
      fetchSprint();
    } catch (e) {
      console.error('Failed to run task:', e);
    }
  };

  if (loading) {
    return <div className="p-8 h-full flex items-center justify-center">Loading Sprint...</div>;
  }

  const sprintName = sprintData?.sprint.name?.trim() || '';
  const displaySprintTitle = sprintName && !/^sprint\s*\d+$/i.test(sprintName) ? sprintName : 'Current Sprint';

  return (
    <div className="p-8 h-full">
      <div className="h-full max-w-[1600px] mx-auto space-y-6 animate-in slide-in-from-bottom-4 duration-300 flex flex-col">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">{displaySprintTitle}</h2>
          <p className="text-muted-foreground text-sm">{sprintData?.sprint.goal || 'Active tasks and agent assignments for the current cycle.'}</p>
        </div>
        <div className="flex-1 min-h-0">
          <IssueBoard issues={issues} setIssues={handleUpdateIssues} onAddIssue={handleAddIssue} onUpdateIssueDetails={handleUpdateIssueDetails} onRunTask={handleRunTask} />
        </div>
      </div>
    </div>
  );
}
