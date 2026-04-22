import React, { useState } from 'react';
import { IssueBoard } from '@/src/components/IssueBoard';
import { Issue } from '@/src/types';

const initialIssues: Issue[] = [
  {
    id: 'SPR-12',
    title: 'Finalize landing page sprint preview',
    description: 'Port the current sprint experience into the landing page using the same board interaction model.',
    requirements: 'Match the current sprint board styling and preserve drag-and-drop behavior.',
    status: 'todo',
    priority: 'high',
    tags: [],
    createdAt: '2026-04-21T09:00:00Z',
    comments: [],
    runs: [],
  },
  {
    id: 'SPR-16',
    title: 'Train routing prompt for support escalation',
    description: 'Refine escalation rules so support agents can classify urgent tickets correctly.',
    requirements: 'Improve escalation precision and reduce false positives.',
    status: 'in-progress',
    priority: 'medium',
    tags: [],
    createdAt: '2026-04-21T09:20:00Z',
    comments: [],
    runs: [],
  },
  {
    id: 'SPR-18',
    title: 'Sync product notes into roadmap',
    description: 'Aggregate agent findings and push a weekly summary into the roadmap board.',
    requirements: 'Include blockers, decisions, and follow-up owners.',
    status: 'review',
    priority: 'medium',
    tags: [],
    createdAt: '2026-04-21T09:40:00Z',
    comments: [],
    runs: [],
  },
  {
    id: 'SPR-21',
    title: 'Prepare onboarding automation handoff',
    description: 'Package the onboarding workflow so another employee can run it without manual guidance.',
    requirements: 'Define handoff steps and validate the runbook.',
    status: 'backlog',
    priority: 'low',
    tags: [],
    createdAt: '2026-04-21T10:10:00Z',
    comments: [],
    runs: [],
  },
  {
    id: 'SPR-24',
    title: 'QA autonomous task routing',
    description: 'Review assignment logic for current sprint tasks before enabling the next cycle.',
    requirements: 'Confirm no task is assigned to an unavailable employee.',
    status: 'done',
    priority: 'high',
    tags: [],
    createdAt: '2026-04-21T10:35:00Z',
    comments: [],
    runs: [],
  },
];

export function LandingSprintSection() {
  const [issues, setIssues] = useState<Issue[]>(initialIssues);

  const handleAddIssue = (status: string) => {
    const nextId = `SPR-${String(issues.length + 25).padStart(2, '0')}`;
    setIssues((prev) => [
      ...prev,
      {
        id: nextId,
        title: 'New Sprint Task',
        description: 'Add task details for the next sprint cycle.',
        requirements: '',
        status,
        priority: 'medium',
        tags: [],
        createdAt: new Date().toISOString(),
        comments: [],
        runs: [],
      },
    ]);
  };

  const handleUpdateIssueDetails = (
    issueId: string,
    details: { title: string; description: string; requirements: string; priority: 'low' | 'medium' | 'high'; agentId?: string }
  ) => {
    setIssues((prev) =>
      prev.map((issue) =>
        issue.id === issueId
          ? {
              ...issue,
              title: details.title,
              description: details.description,
              requirements: details.requirements,
              priority: details.priority,
              agentId: details.agentId,
            }
          : issue
      )
    );
  };

  return (
    <section className="border-t border-zinc-200/70 bg-white py-16 sm:py-24">
      <div className="mx-auto w-full max-w-7xl px-6 sm:px-8 lg:px-10">
        <div className="grid gap-0 overflow-hidden rounded-[30px] border border-zinc-200 bg-white lg:grid-cols-[0.64fr_1.36fr]">
          <div className="flex items-center border-b border-zinc-300/70 p-8 sm:p-12 lg:border-b-0 lg:border-r lg:p-16">
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
                Sprint Workspace
              </div>
              <h2 className="mt-4 text-[24px] font-medium leading-[1.15] tracking-tight text-zinc-900 sm:text-[30px]">
                Manage agent sprints
                <span className="block text-zinc-500">inside one current sprint workspace</span>
              </h2>
              <p className="mt-4 max-w-md text-[15px] leading-7 text-zinc-600">
                View active sprint execution, move tasks across stages, and coordinate multiple AI employees from the same board.
              </p>
            </div>
          </div>

          <div className="relative overflow-hidden bg-white p-4 sm:p-8">
            <div className="absolute inset-0 z-0 pointer-events-none">
              <img src="/bgothers.png" alt="" className="h-full w-full object-cover object-center" />
            </div>

            <div className="relative z-10 h-[680px] overflow-hidden rounded-[24px] border border-zinc-200 bg-white shadow-[0_12px_28px_rgba(24,24,27,0.06)]">
              <div className="h-full p-8">
                <div className="h-full max-w-[1600px] mx-auto space-y-6 animate-in slide-in-from-bottom-4 duration-300 flex flex-col">
                  <div className="space-y-1">
                    <h2 className="text-2xl font-semibold tracking-tight">Current Sprint</h2>
                    <p className="text-muted-foreground text-sm">
                      Active tasks and agent assignments for the current cycle.
                    </p>
                  </div>
                  <div className="flex-1 min-h-0 pointer-events-none select-none">
                    <IssueBoard
                      issues={issues}
                      setIssues={setIssues}
                      onAddIssue={handleAddIssue}
                      onUpdateIssueDetails={handleUpdateIssueDetails}
                      onRunTask={() => {}}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
