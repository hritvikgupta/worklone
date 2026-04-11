import React, { useState } from 'react';
import { IssueBoard } from '@/src/components/IssueBoard';
import { MOCK_AGENTS, MOCK_ISSUES } from '@/src/constants';
import { Issue } from '@/src/types';

export function CurrentSprintPage() {
  const [issues, setIssues] = useState<Issue[]>(MOCK_ISSUES);

  const handleAddIssue = (status: string) => {
    const newIssue: Issue = {
      id: `issue-${Date.now()}`,
      title: 'New Task',
      description: 'Describe the task here...',
      status,
      priority: 'medium',
      tags: ['new'],
      assigneeId: 'user-1',
      agentId: MOCK_AGENTS[0]?.id,
      createdAt: new Date().toISOString(),
      comments: [],
      fileChanges: [],
    };

    setIssues((prev) => [newIssue, ...prev]);
  };

  return (
    <div className="p-8 h-full">
      <div className="h-full max-w-[1600px] mx-auto space-y-6 animate-in slide-in-from-bottom-4 duration-300 flex flex-col">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">Current Sprint</h2>
          <p className="text-muted-foreground text-sm">Active tasks and agent assignments for the current cycle.</p>
        </div>
        <div className="flex-1 min-h-0">
          <IssueBoard issues={issues} setIssues={setIssues} onAddIssue={handleAddIssue} />
        </div>
      </div>
    </div>
  );
}
