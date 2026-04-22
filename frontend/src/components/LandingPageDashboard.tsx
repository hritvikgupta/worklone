import React from 'react';
import type { Agent } from '@/src/types';
import { AgentDetail } from '@/src/components/AgentDetail';
import type { EmployeeActivity, EmployeeSkill, EmployeeTask, EmployeeTool } from '@/src/api/employees';

const PREVIEW_AGENT: Agent = {
  id: 'preview-agent-1',
  name: 'Mira',
  role: 'Growth Lead',
  avatar: '/employees/women_2.png',
  cover: '',
  status: 'working',
  description: 'Owns roadmap definition, requirement quality, and execution cadence.',
  systemPrompt: 'You are Mira, a growth lead. Analyze funnel behavior, propose experiments, and execute growth work with structured reporting.',
  currentTask: 'preview-task-1',
  skills: ['Growth', 'Experimentation', 'Analytics'],
  model: 'claude',
};

const PREVIEW_SKILLS: EmployeeSkill[] = [
  { id: 's1', skill_name: 'Google Analytics', category: 'Analytics', proficiency_level: 9, description: 'Behavior analysis', created_at: '2026-04-21T10:00:00Z' },
  { id: 's2', skill_name: 'Mixpanel', category: 'Analytics', proficiency_level: 8, description: 'Event funnels', created_at: '2026-04-21T10:00:00Z' },
  { id: 's3', skill_name: 'SQL', category: 'Data', proficiency_level: 8, description: 'Querying', created_at: '2026-04-21T10:00:00Z' },
  { id: 's4', skill_name: 'Looker', category: 'BI', proficiency_level: 7, description: 'Dashboards', created_at: '2026-04-21T10:00:00Z' },
  { id: 's5', skill_name: 'Python', category: 'Data', proficiency_level: 7, description: 'Analysis scripts', created_at: '2026-04-21T10:00:00Z' },
];

const PREVIEW_TOOLS: EmployeeTool[] = [
  { id: 't1', tool_name: 'BigQuery', is_enabled: true, config: {}, created_at: '2026-04-21T10:00:00Z' },
  { id: 't2', tool_name: 'dbt', is_enabled: true, config: {}, created_at: '2026-04-21T10:00:00Z' },
  { id: 't3', tool_name: 'Jupyter', is_enabled: true, config: {}, created_at: '2026-04-21T10:00:00Z' },
];

const PREVIEW_TASKS: EmployeeTask[] = [
  {
    id: 'preview-task-1',
    task_title: 'Audit acquisition funnel drop-offs',
    task_description: 'Analyze funnel drop-off rates across paid and organic channels, then produce 3 conversion hypotheses.',
    status: 'in_progress',
    priority: 'high',
    tags: ['growth', 'conversion'],
    created_at: '2026-04-21T10:00:00Z',
    updated_at: '2026-04-21T14:52:00Z',
    completed_at: null,
  },
];

const PREVIEW_ACTIVITY: EmployeeActivity[] = [
  {
    id: 'a1',
    activity_type: 'task_completed',
    message: 'Analyzed funnel drop-off rates across paid and organic channels',
    task_id: 'preview-task-1',
    metadata: {},
    timestamp: '2026-04-21T14:34:00Z',
  },
  {
    id: 'a2',
    activity_type: 'task_completed',
    message: 'Generated 3 conversion hypotheses with supporting data',
    task_id: 'preview-task-1',
    metadata: {},
    timestamp: '2026-04-21T14:41:00Z',
  },
];

export function LandingPageDashboard() {
  return (
    <div className="mx-auto max-w-[90%] overflow-hidden rounded-[28px] border border-zinc-200 bg-white">
      <div className="min-h-[800px]">
        <div className="relative overflow-hidden bg-white">
          <div className="h-full overflow-y-auto p-6">
            <AgentDetail
              agent={PREVIEW_AGENT}
              onBack={() => {}}
              onConfigure={() => {}}
              tools={PREVIEW_TOOLS}
              skills={PREVIEW_SKILLS}
              tasks={PREVIEW_TASKS}
              activity={PREVIEW_ACTIVITY}
              compactPreview
            />
          </div>
        </div>
      </div>
    </div>
  );
}
