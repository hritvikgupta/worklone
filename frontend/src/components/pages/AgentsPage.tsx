import React, { useState, useCallback, useEffect } from 'react';
import { Sparkles, Loader2, Bell, CheckCircle2, CircleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useLocation, useNavigate } from 'react-router-dom';
import { AgentList } from '@/src/components/AgentList';
import { ProvisionModal } from '@/src/components/ProvisionModal';
import { Agent } from '@/src/types';
import {
  listEmployees,
  createEmployee,
  updateEmployee,
  deleteEmployee,
  getEmployee,
  generateEmployeePrompt,
  EmployeeDetail as EmployeeDetailType,
  GeneratedPromptResult,
} from '@/src/api/employees';
import { EmployeeFormData } from '@/src/components/EmployeePanel';

type ProvisionStatus = 'processing' | 'completed' | 'failed';

interface ProvisionActivity {
  id: string;
  name: string;
  role: string;
  startedAt: number;
  status: ProvisionStatus;
  phase: 'generating' | 'creating';
  employeeId?: string;
  error?: string;
}

function toAgent(emp: EmployeeDetailType): Agent {
  return {
    id: emp.id,
    name: emp.name,
    role: emp.role,
    avatar: emp.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${emp.name.toLowerCase()}`,
    cover: emp.cover_url || '',
    status: emp.status as Agent['status'],
    description: emp.description,
    systemPrompt: emp.system_prompt,
    skills: [],
    tools: emp.tools || [],
    model: emp.model,
  };
}

export function AgentsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [activity, setActivity] = useState<ProvisionActivity[]>([]);
  const [renameTarget, setRenameTarget] = useState<Agent | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<Agent | null>(null);
  const [menuBusyId, setMenuBusyId] = useState<string | null>(null);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    try {
      const employees = await listEmployees();
      setAgents(employees.map((e) => toAgent(e)));
    } catch (err) {
      console.error('Failed to load employees:', err);
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleProvisionEmployee = useCallback(async (payload: { name: string; description: string }) => {
    const activityId = `prov-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const startedAt = Date.now();

    const activityEntry: ProvisionActivity = {
      id: activityId,
      name: payload.name,
      role: '',
      startedAt,
      status: 'processing',
      phase: 'generating',
    };
    setActivity((prev) => [activityEntry, ...prev].slice(0, 12));

    try {
      const result: GeneratedPromptResult = await generateEmployeePrompt(payload.name, payload.description);
      const form: EmployeeFormData = {
        name: payload.name,
        role: result.role,
        avatar_url: '',
        description: payload.description,
        system_prompt: result.system_prompt,
        model: 'openai/gpt-4o',
        provider: '',
        temperature: 0.7,
        max_tokens: 4096,
        tools: result.tools,
        skills: result.skills,
        memory: [],
      };

      setActivity((prev) => prev.map((item) => (
        item.id === activityId
          ? { ...item, role: form.role, phase: 'creating' }
          : item
      )));

      const created = await createEmployee(form);
      setActivity((prev) => prev.map((item) => (
        item.id === activityId
          ? { ...item, status: 'completed', employeeId: created.id }
          : item
      )));
      await handleRefresh();
    } catch (err) {
      const errorText = err instanceof Error ? err.message : 'Provisioning failed';
      setActivity((prev) => prev.map((item) => (
        item.id === activityId
          ? { ...item, status: 'failed', error: errorText }
          : item
      )));
      console.error('Failed to provision employee:', err);
    }
  }, [handleRefresh]);

  useEffect(() => {
    handleRefresh();
  }, [handleRefresh]);

  useEffect(() => {
    const state = location.state as { openProvisionModal?: boolean } | null;
    if (!state?.openProvisionModal) return;

    navigate(location.pathname, { replace: true, state: {} });
    setModalOpen(true);
  }, [location.pathname, location.state, navigate]);

  const processingCount = activity.filter((item) => item.status === 'processing').length;

  const formatAge = (startedAt: number) => {
    const diffMs = Date.now() - startedAt;
    if (diffMs < 60_000) return 'just now';
    const mins = Math.floor(diffMs / 60_000);
    if (mins < 60) return `${mins} min ago`;
    const hours = Math.floor(mins / 60);
    return `${hours} hr ago`;
  };

  const openRename = (agent: Agent) => {
    setRenameTarget(agent);
    setRenameValue(agent.name);
  };

  const confirmRename = async () => {
    if (!renameTarget) return;
    const nextName = renameValue.trim();
    if (!nextName || nextName === renameTarget.name) {
      setRenameTarget(null);
      return;
    }
    setMenuBusyId(renameTarget.id);
    try {
      await updateEmployee(renameTarget.id, { name: nextName });
      await handleRefresh();
      setRenameTarget(null);
    } catch (err) {
      console.error('Failed to rename employee:', err);
    } finally {
      setMenuBusyId(null);
    }
  };

  const duplicateAgent = async (agent: Agent) => {
    setMenuBusyId(agent.id);
    try {
      const full = await getEmployee(agent.id);
      const payload: EmployeeFormData = {
        name: `${full.employee.name} Copy`,
        role: full.employee.role,
        avatar_url: full.employee.avatar_url,
        cover_url: full.employee.cover_url,
        description: full.employee.description,
        system_prompt: full.employee.system_prompt,
        model: full.employee.model,
        provider: full.employee.provider,
        temperature: full.employee.temperature,
        max_tokens: full.employee.max_tokens,
        tools: full.tools.filter((t) => t.is_enabled).map((t) => t.tool_name),
        skills: full.skills.map((s) => ({
          skill_name: s.skill_name,
          category: s.category,
          proficiency_level: s.proficiency_level,
          description: s.description,
        })),
        memory: full.employee.memory || [],
      };
      const created = await createEmployee(payload);
      await handleRefresh();
      navigate(`/agents/${created.id}`);
    } catch (err) {
      console.error('Failed to duplicate employee:', err);
    } finally {
      setMenuBusyId(null);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setMenuBusyId(deleteTarget.id);
    try {
      await deleteEmployee(deleteTarget.id);
      setDeleteTarget(null);
      await handleRefresh();
    } catch (err) {
      console.error('Failed to delete employee:', err);
    } finally {
      setMenuBusyId(null);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8">
        <div className="max-w-6xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-end justify-between border-b border-border pb-3">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Employees</h2>
              <p className="text-muted-foreground mt-1 text-xs">Manage your autonomous teammates.</p>
            </div>
            <div className="flex items-center gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="relative h-8 w-8 p-0">
                    <Bell className="h-4 w-4" />
                    {processingCount > 0 && (
                      <span className="absolute -right-1 -top-1 rounded-full bg-amber-500 px-1 text-[10px] leading-4 text-white">
                        {processingCount}
                      </span>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[360px] p-0">
                  <DropdownMenuLabel className="flex items-center justify-between px-3 py-2">
                    <span>Recent Activity</span>
                    {processingCount > 0 && (
                      <Badge variant="outline" className="text-[10px]">
                        {processingCount} processing
                      </Badge>
                    )}
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <div className="max-h-80 overflow-y-auto p-1">
                    {activity.length === 0 ? (
                      <div className="px-2 py-6 text-center text-xs text-muted-foreground">
                        No recent provisioning activity yet.
                      </div>
                    ) : (
                      activity.map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          className="w-full rounded-sm px-2 py-2 text-left transition-colors hover:bg-accent"
                          onClick={() => {
                            if (item.employeeId) navigate(`/agents/${item.employeeId}`);
                          }}
                        >
                          <div className="flex items-start gap-2">
                            <div className="mt-0.5">
                              {item.status === 'processing' && <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-600" />}
                              {item.status === 'completed' && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />}
                              {item.status === 'failed' && <CircleAlert className="h-3.5 w-3.5 text-rose-600" />}
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-xs font-medium text-foreground">
                                {item.status === 'processing' && `Provisioning ${item.name}`}
                                {item.status === 'completed' && `${item.name} provisioned`}
                                {item.status === 'failed' && `Failed to provision ${item.name}`}
                              </p>
                              <p className="truncate text-[11px] text-muted-foreground">
                                {item.status === 'processing' && (
                                  item.phase === 'generating'
                                    ? 'Generating persona and skill config'
                                    : `${item.role || 'Employee'} being created`
                                )}
                                {item.status === 'completed' && `${item.role || 'Employee'} ready`}
                                {item.status === 'failed' && (item.error || 'Request failed')}
                                {' · '}
                                {formatAge(item.startedAt)}
                              </p>
                            </div>
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                </DropdownMenuContent>
              </DropdownMenu>

              <Button
                variant="outline"
                size="sm"
                className="gap-2 text-xs font-medium h-8"
                onClick={() => setModalOpen(true)}
              >
                <Sparkles className="w-3.5 h-3.5" />
                Provision Employee
              </Button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-sm text-muted-foreground">Loading employees...</span>
            </div>
          ) : (
            <AgentList
              agents={agents}
              onAgentClick={(agent) => navigate(`/agents/${agent.id}`)}
              onChat={(agent) => navigate(`/agents/${agent.id}/workspace`)}
              onRename={openRename}
              onDuplicate={duplicateAgent}
              onDelete={(agent) => setDeleteTarget(agent)}
            />
          )}
        </div>

        <ProvisionModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          onSubmit={(payload) => {
            void handleProvisionEmployee(payload);
          }}
        />

        <Dialog open={!!renameTarget} onOpenChange={(open) => !open && setRenameTarget(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Rename Employee</DialogTitle>
            </DialogHeader>
            <Input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              placeholder="Employee name"
              autoFocus
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => setRenameTarget(null)}>Cancel</Button>
              <Button
                onClick={() => void confirmRename()}
                disabled={!renameValue.trim() || (renameTarget ? menuBusyId === renameTarget.id : false)}
              >
                Save
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Employee</AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently delete {deleteTarget?.name || 'this employee'} and associated tools/skills/tasks.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                className="bg-rose-600 text-white hover:bg-rose-700"
                onClick={() => void confirmDelete()}
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}
