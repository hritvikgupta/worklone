import React from 'react';
import { BookOpen, CalendarClock, FolderOpen, Github, LayoutDashboard, MessageSquare, Users, Zap, Clock, Coins, MessageCircle, CheckCircle2, ArrowRight, Wrench, Brain } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgentList } from '@/src/components/AgentList';
import { cn } from '@/lib/utils';

const previewNavItems = [
  { label: 'Chat', icon: MessageSquare },
  { label: 'Dashboard', icon: LayoutDashboard },
  { label: 'Current Sprint', icon: Zap },
  { label: 'Workflows', icon: CalendarClock },
  { label: 'Agent Files', icon: FolderOpen },
  { label: 'Employees', icon: Users, active: true },
  { label: 'Skill Library', icon: BookOpen },
  { label: 'Integrations', icon: Github },
];

const MOCK_AGENTS = [
  {
    id: 'agent-1',
    name: 'Mira',
    role: 'Growth Lead',
    avatar: '/workforce/employee-1.png',
    status: 'working' as const,
    description: 'Owns roadmap definition, requirement quality, and execution cadence.',
    currentTask: 'issue-101',
    skills: ['Growth', 'Experimentation', 'Analytics'],
    model: 'claude',
  },
  {
    id: 'agent-2',
    name: 'Sam',
    role: 'Data Analyst',
    avatar: '/workforce/employee-4.png',
    status: 'idle' as const,
    description: 'Turns messy operational and product data into decisions.',
    skills: ['SQL', 'Analytics', 'Dashboards'],
    model: 'minimax',
  },
  {
    id: 'agent-3',
    name: 'Leo',
    role: 'Backend Engineer',
    avatar: '/workforce/employee-3.png',
    status: 'working' as const,
    description: 'Builds the backend systems that keep the operating environment reliable.',
    currentTask: 'issue-102',
    skills: ['Python', 'APIs', 'Postgres'],
    model: 'openai',
  },
  {
    id: 'agent-4',
    name: 'Katy',
    role: 'Product Manager',
    avatar: '/workforce/employee-5.png',
    status: 'idle' as const,
    description: 'Translates ambiguous requests into clear plans.',
    skills: ['Roadmapping', 'PRDs', 'Prioritization'],
    model: 'gpt',
  },
];

const taskTimeline = [
  {
    time: '2:34 PM',
    type: 'completed',
    message: 'Analyzed funnel drop-off rates across paid and organic channels',
    icon: CheckCircle2,
  },
  {
    time: '2:41 PM',
    type: 'completed',
    message: 'Generated 3 conversion hypotheses with supporting data',
    icon: CheckCircle2,
  },
  {
    time: '2:52 PM',
    type: 'active',
    message: 'Drafting experiment brief for top-performing hypothesis',
    icon: MessageCircle,
  },
];

const skillsUsed = ['Google Analytics', 'Mixpanel', 'SQL', 'Looker', 'Python'];
const toolsUsed = ['BigQuery', 'dbt', 'Jupyter'];

export function LandingPageDashboard() {
  return (
    <div className="mx-auto max-w-[90%] overflow-hidden rounded-[28px] border border-black/8 bg-[#f7f7f5]">
      <div className="grid min-h-[800px] lg:grid-cols-[240px_1fr]">
        <aside className="border-r border-black/6 bg-sidebar">
          <div className="m-2 flex items-center gap-2 rounded-md p-4">
            <img
              src="/brand/worklone-mark-black.png"
              alt="Worklone"
              className="h-5 w-auto"
            />
            <h1 className="text-[15px] font-semibold tracking-tight text-sidebar-foreground">Worklone</h1>
          </div>

          <nav className="space-y-0.5 px-2 py-4">
            {previewNavItems.map((item) => (
              <div
                key={item.label}
                className={cn(
                  'flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium',
                  item.active
                    ? 'bg-sidebar-accent text-sidebar-foreground'
                    : 'text-sidebar-foreground/70'
                )}
              >
                <item.icon
                  className={cn(
                    'h-4 w-4',
                    item.active ? 'text-sidebar-foreground' : 'text-sidebar-foreground/50'
                  )}
                />
                {item.label}
              </div>
            ))}
          </nav>
        </aside>

        <div className="relative overflow-hidden bg-white">
          <div className="h-full overflow-y-auto p-8">
            <div className="mx-auto max-w-6xl space-y-8">
              <div className="flex items-end justify-between border-b border-border/50 pb-3">
                <div>
                  <h2 className="text-2xl font-semibold tracking-tight">Employees</h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Manage and configure your autonomous teammates.
                  </p>
                </div>
                <Button variant="outline" size="sm" className="h-8 gap-2 text-xs font-medium">
                  Provision Employee
                </Button>
              </div>

              <AgentList agents={MOCK_AGENTS} onAgentClick={() => {}} selectedAgentId="agent-1" />
            </div>
          </div>

          <div className="absolute inset-y-4 right-4 z-10 w-80">
            <div className="flex h-full rounded-xl bg-white/95 shadow-lg ring-1 ring-black/10">
              <div className="flex h-full flex-col">
                <div className="border-b border-black/6 p-4">
                  <div className="flex items-center gap-3">
                    <img
                      src="/workforce/employee-1.png"
                      alt="Mira"
                      className="h-9 w-9 rounded-lg object-cover"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-semibold">Mira</div>
                      <div className="text-[11px] text-muted-foreground">Growth Lead · Working</div>
                    </div>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                  <div className="mb-4 rounded-lg bg-zinc-50 p-3">
                    <div className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Current Task</div>
                    <div className="mt-1 text-xs font-medium text-zinc-900">Audit acquisition funnel drop-offs</div>
                  </div>

                  <div className="mb-4">
                    <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-zinc-500">Activity</div>
                    <div className="space-y-0">
                      {taskTimeline.map((item, index) => (
                        <div key={index} className="relative flex gap-3">
                          <div className="flex flex-col items-center">
                            <div className={cn(
                              "relative flex h-6 w-6 items-center justify-center rounded-full",
                              item.type === 'active' ? 'bg-blue-100' : 'bg-green-100'
                            )}>
                              <item.icon className={cn(
                                "h-3.5 w-3.5",
                                item.type === 'active' ? 'text-blue-600' : 'text-green-600'
                              )} />
                              {item.type === 'active' && (
                                <span className="absolute inset-0 animate-ping rounded-full bg-blue-400/30" />
                              )}
                            </div>
                            {index < taskTimeline.length - 1 && (
                              <div className="w-px bg-zinc-200" style={{ minHeight: '24px' }} />
                            )}
                          </div>
                          <div className="flex-1 pb-4">
                            <div className="text-[10px] text-zinc-400">{item.time}</div>
                            <div className="mt-0.5 text-xs text-zinc-700">{item.message}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mb-4">
                    <div className="mb-2 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                      <Brain className="h-3 w-3" />
                      Skills used
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {skillsUsed.map((skill) => (
                        <span key={skill} className="rounded-md bg-violet-50 px-2 py-1 text-[10px] font-medium text-violet-700">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="mb-4">
                    <div className="mb-2 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                      <Wrench className="h-3 w-3" />
                      Tools used
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {toolsUsed.map((tool) => (
                        <span key={tool} className="rounded-md bg-blue-50 px-2 py-1 text-[10px] font-medium text-blue-700">
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="border-t border-black/6 p-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-1.5 text-zinc-500">
                        <Clock className="h-3.5 w-3.5" />
                        Session time
                      </span>
                      <span className="font-medium text-zinc-900">18m 42s</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-1.5 text-zinc-500">
                        <Coins className="h-3.5 w-3.5" />
                        Tokens used
                      </span>
                      <span className="font-medium text-zinc-900">24,812</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-1.5 text-zinc-500">
                        <ArrowRight className="h-3.5 w-3.5" />
                        Cost
                      </span>
                      <span className="font-medium text-zinc-900">$0.04</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
