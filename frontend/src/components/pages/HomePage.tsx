import React, { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Briefcase, GitBranch, Loader2, Users, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { useAuth } from '@/src/contexts/AuthContext';
import { listEmployees, EmployeeDetail } from '@/src/api/employees';
import { listWorkflows, WorkflowSummary } from '@/src/api/workflows';
import { listTeams } from '@/src/api/teams';

type OperationType = 'agent' | 'team' | 'workflow';
type OperationStatus = 'running' | 'active' | 'pending' | 'idle';

interface OperationRow {
  id: string;
  type: OperationType;
  name: string;
  owner: string;
  status: OperationStatus;
  updatedAt: string;
  detail: string;
}

function statusClass(status: OperationStatus): string {
  switch (status) {
    case 'running':
      return 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20';
    case 'active':
      return 'bg-blue-500/10 text-blue-700 border-blue-500/20';
    case 'pending':
      return 'bg-amber-500/10 text-amber-700 border-amber-500/20';
    default:
      return 'bg-muted text-muted-foreground border-border';
  }
}

function typeIcon(type: OperationType) {
  switch (type) {
    case 'agent':
      return Briefcase;
    case 'team':
      return Users;
    case 'workflow':
      return GitBranch;
  }
}

function parseTime(value?: string): number {
  if (!value) return 0;
  const t = Date.parse(value);
  return Number.isNaN(t) ? 0 : t;
}

function timeAgo(value?: string): string {
  if (!value) return 'just now';
  const ts = parseTime(value);
  if (!ts) return 'just now';
  const diffMs = Date.now() - ts;
  if (diffMs < 60_000) return 'just now';
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

export function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [employees, setEmployees] = useState<EmployeeDetail[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [teamRows, setTeamRows] = useState<OperationRow[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const [employeesData, workflowsData, teamsData] = await Promise.all([
          listEmployees(),
          listWorkflows().catch(() => [] as WorkflowSummary[]),
          listTeams().catch(() => [] as any[]),
        ]);

        const teamsOperations: OperationRow[] = (teamsData || [])
          .flatMap((team: any) => (team.runs || []).map((run: any) => ({
            id: `team-${run.id}`,
            type: 'team' as const,
            name: team.name || 'Team run',
            owner: run.members?.[0]?.employee_name || 'Team',
            status: run.status === 'running' ? 'running' : run.status === 'pending' ? 'pending' : 'active',
            updatedAt: run.updated_at || run.created_at || '',
            detail: run.goal || 'Team execution',
          })))
          .filter((row) => row.status === 'running' || row.status === 'pending' || row.status === 'active');

        if (!cancelled) {
          setEmployees(employeesData);
          setWorkflows(workflowsData);
          setTeamRows(teamsOperations);
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load home data:', error);
          setEmployees([]);
          setWorkflows([]);
          setTeamRows([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const recentEmployees = useMemo(
    () =>
      [...employees]
        .sort((a, b) => parseTime(b.updated_at) - parseTime(a.updated_at))
        .slice(0, 3),
    [employees],
  );

  const operationRows = useMemo(() => {
    const rows: OperationRow[] = [];

    for (const emp of employees) {
      if (emp.status === 'working' || emp.status === 'blocked') {
        rows.push({
          id: `agent-${emp.id}`,
          type: 'agent',
          name: emp.name,
          owner: emp.role || 'Employee',
          status: 'running',
          updatedAt: emp.updated_at,
          detail: emp.status === 'blocked' ? 'Blocked on dependency' : 'Handling active run',
        });
      }
    }

    const latestWorkflow = [...workflows]
      .filter((workflow) => workflow.status === 'running' || workflow.status === 'active')
      .sort((a, b) => parseTime(b.updated_at) - parseTime(a.updated_at))[0];
    if (latestWorkflow) {
      rows.push({
        id: `workflow-${latestWorkflow.id}`,
        type: 'workflow',
        name: latestWorkflow.name,
        owner: latestWorkflow.created_by_actor_name || 'Workflow',
        status: latestWorkflow.status === 'running' ? 'running' : 'active',
        updatedAt: latestWorkflow.updated_at,
        detail: latestWorkflow.status === 'running' ? 'Executing now' : 'Active schedule',
      });
    }

    rows.push(...teamRows);

    return rows
      .sort((a, b) => parseTime(b.updatedAt) - parseTime(a.updatedAt))
      .slice(0, 10);
  }, [employees, teamRows, workflows]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="h-7 w-7 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const firstName = user?.name?.split(' ')[0] || 'there';

  return (
    <div className="h-full overflow-y-auto bg-background">
      <div className="mx-auto max-w-7xl p-8 space-y-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-foreground">
              Welcome back, {firstName}!
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Here is a quick view of your most recent employees and active operations.
            </p>
          </div>
          <Button className="h-10 px-5 font-medium" onClick={() => navigate('/agents')}>
            Create Employee
          </Button>
        </div>

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-medium tracking-tight text-muted-foreground">Recently Edited Employees</h2>
            <Button variant="ghost" className="gap-1 text-muted-foreground" onClick={() => navigate('/agents')}>
              View All <ArrowRight className="h-4 w-4" />
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3 md:grid-cols-2">
            {recentEmployees.length === 0 ? (
              <Card className="col-span-full border-dashed">
                <CardContent className="py-12 text-center text-muted-foreground">
                  No employees yet. Create your first employee to get started.
                </CardContent>
              </Card>
            ) : (
              recentEmployees.map((emp) => (
                <Card
                  key={emp.id}
                  className="group relative cursor-pointer border-border/70 transition-colors hover:border-border hover:bg-muted/20"
                  onClick={() => navigate('/agents')}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-3">
                      <img
                        src={emp.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(emp.name)}`}
                        alt={emp.name}
                        className="h-11 w-11 rounded-full border border-border object-cover"
                      />
                      <div className="min-w-0">
                        <CardTitle className="truncate text-xl font-semibold">{emp.name}</CardTitle>
                        <p className="truncate text-sm text-muted-foreground">{emp.role}</p>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{timeAgo(emp.updated_at)}</span>
                      <Badge
                        variant="outline"
                        className={cn(
                          'capitalize',
                          emp.status === 'working'
                            ? 'border-emerald-500/30 text-emerald-700 bg-emerald-500/5'
                            : 'border-border text-muted-foreground'
                        )}
                      >
                        {emp.status}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </section>

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-2xl font-medium tracking-tight text-muted-foreground">Live Operations</h3>
          </div>

          <Card className="overflow-hidden border-border/70">
            <div className="grid grid-cols-12 gap-3 border-b border-border/70 bg-muted/30 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <div className="col-span-2">Type</div>
              <div className="col-span-3">Name</div>
              <div className="col-span-2">Status</div>
              <div className="col-span-2">Owner</div>
              <div className="col-span-3">Detail</div>
            </div>

            {operationRows.length === 0 ? (
              <div className="px-5 py-10 text-center text-sm text-muted-foreground">
                No active team, workflow, or employee runs right now.
              </div>
            ) : (
              <div>
                {operationRows.map((row, index) => {
                  const Icon = typeIcon(row.type);
                  return (
                    <div key={row.id}>
                      <div className="grid grid-cols-12 gap-3 px-5 py-3.5 text-sm">
                        <div className="col-span-2 flex items-center gap-2">
                          <Icon className="h-4 w-4 text-muted-foreground" />
                          <span className="capitalize">{row.type}</span>
                        </div>
                        <div className="col-span-3 font-medium text-foreground truncate">{row.name}</div>
                        <div className="col-span-2">
                          <Badge variant="outline" className={cn('capitalize', statusClass(row.status))}>
                            {row.status}
                          </Badge>
                        </div>
                        <div className="col-span-2 text-muted-foreground truncate">{row.owner}</div>
                        <div className="col-span-3 text-muted-foreground truncate">{row.detail} · {timeAgo(row.updatedAt)}</div>
                      </div>
                      {index < operationRows.length - 1 && <Separator />}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </section>
      </div>
    </div>
  );
}
