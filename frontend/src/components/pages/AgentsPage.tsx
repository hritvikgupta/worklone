import React, { useState, useCallback, useEffect } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgentDetail } from '@/src/components/AgentDetail';
import { AgentList } from '@/src/components/AgentList';
import { EmployeePanel, EmployeeFormData } from '@/src/components/EmployeePanel';
import { EmployeeConfigPanel } from '@/src/components/EmployeeConfigPanel';
import { ProvisionModal } from '@/src/components/ProvisionModal';
import { Agent } from '@/src/types';
import { listEmployees, createEmployee, getEmployee, updateEmployee, EmployeeDetail as EmployeeDetailType, EmployeeWithDetails } from '@/src/api/employees';

function deriveCurrentTaskId(employee?: EmployeeWithDetails | null): string | undefined {
  if (!employee) return undefined;
  return employee.tasks.find((task) => task.status === 'in_progress')?.id
    || employee.tasks.find((task) => task.status === 'blocked')?.id
    || employee.tasks.find((task) => task.status === 'todo')?.id
    || undefined;
}

function toAgent(emp: EmployeeDetailType, skills: string[] = [], currentTask?: string): Agent {
  return {
    id: emp.id,
    name: emp.name,
    role: emp.role,
    avatar: emp.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${emp.name.toLowerCase()}`,
    status: emp.status as Agent['status'],
    description: emp.description,
    systemPrompt: emp.system_prompt,
    skills,
    model: emp.model,
    currentTask,
  };
}

export function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeWithDetails | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [createPanelOpen, setCreatePanelOpen] = useState(false);
  const [createPrefillData, setCreatePrefillData] = useState<EmployeeFormData | null>(null);
  const [configPanelOpen, setConfigPanelOpen] = useState(false);
  const [configFormData, setConfigFormData] = useState<EmployeeFormData | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  const selectedAgent = selectedEmployee
    ? toAgent(
        selectedEmployee.employee,
        selectedEmployee.skills.map((skill) => skill.skill_name),
        deriveCurrentTaskId(selectedEmployee),
      )
    : agents.find((agent) => agent.id === selectedAgentId) || null;

  const handleAgentClick = async (agent: Agent) => {
    setSelectedAgentId(agent.id);
    setDetailLoading(true);
    try {
      const employee = await getEmployee(agent.id);
      setSelectedEmployee(employee);
    } catch (err) {
      console.error('Failed to load employee details:', err);
      setSelectedEmployee(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleOpenModal = () => {
    setModalOpen(true);
  };

  const handleModalGenerated = (form: EmployeeFormData) => {
    setModalOpen(false);
    setCreatePrefillData(form);
    setCreatePanelOpen(true);
  };

  const handleCloseCreatePanel = () => {
    setCreatePanelOpen(false);
    setCreatePrefillData(null);
  };

  const handleCloseConfigPanel = () => {
    setConfigPanelOpen(false);
    setConfigFormData(null);
  };

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    try {
      const employees = await listEmployees();
      const mapped = employees.map((e) => toAgent(e));
      setAgents(mapped);
    } catch (err) {
      console.error('Failed to load employees:', err);
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSave = useCallback(async (form: EmployeeFormData) => {
    setIsSaving(true);
    try {
      const created = await createEmployee(form);
      const newAgent = toAgent(created);
      setAgents((prev) => [newAgent, ...prev]);
      handleCloseCreatePanel();
    } catch (err) {
      console.error('Failed to save employee:', err);
    } finally {
      setIsSaving(false);
    }
  }, []);

  useEffect(() => {
    handleRefresh();
  }, [handleRefresh]);

  useEffect(() => {
    if (!selectedAgentId || !selectedEmployee) return;
    const latestPaused = selectedEmployee.activity.find((entry) => entry.activity_type === 'workflow_paused');
    const latestResumed = selectedEmployee.activity.find((entry) => entry.activity_type === 'workflow_resumed');
    const hasLiveWork = selectedEmployee.tasks.some((task) =>
      task.status === 'in_progress' || task.status === 'blocked'
    );
    const hasPendingPlanWork = selectedEmployee.tasks.some((task) => task.status === 'todo');
    const waitingForApproval = Boolean(
      latestPaused && (!latestResumed || new Date(latestPaused.timestamp).getTime() > new Date(latestResumed.timestamp).getTime())
    );
    const planWasApproved = Boolean(
      latestResumed && (!latestPaused || new Date(latestResumed.timestamp).getTime() >= new Date(latestPaused.timestamp).getTime())
    );
    const shouldRefresh = hasLiveWork || waitingForApproval || (planWasApproved && hasPendingPlanWork);

    if (!shouldRefresh) {
      return;
    }

    let cancelled = false;
    let timeoutId: number | null = null;

    const refreshSelected = async () => {
      if (document.visibilityState !== 'visible') {
        timeoutId = window.setTimeout(refreshSelected, 15000);
        return;
      }
      try {
        const employee = await getEmployee(selectedAgentId);
        if (!cancelled) {
          setSelectedEmployee(employee);
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to refresh selected employee details:', err);
        }
      } finally {
        if (!cancelled) {
          timeoutId = window.setTimeout(refreshSelected, 15000);
        }
      }
    };

    timeoutId = window.setTimeout(refreshSelected, 15000);
    return () => {
      cancelled = true;
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [
    selectedAgentId,
    selectedEmployee?.employee.status,
    selectedEmployee?.tasks.length,
    selectedEmployee?.activity[0]?.timestamp,
  ]);

  const handleBack = () => {
    setConfigPanelOpen(false);
    setConfigFormData(null);
    setSelectedAgentId(null);
    setSelectedEmployee(null);
  };

  const handleConfigure = () => {
    if (!selectedEmployee) return;
    setConfigFormData({
      name: selectedEmployee.employee.name,
      role: selectedEmployee.employee.role,
      avatar_url: selectedEmployee.employee.avatar_url,
      description: selectedEmployee.employee.description,
      system_prompt: selectedEmployee.employee.system_prompt,
      model: selectedEmployee.employee.model,
      temperature: selectedEmployee.employee.temperature,
      max_tokens: selectedEmployee.employee.max_tokens,
      tools: selectedEmployee.tools.filter((tool) => tool.is_enabled).map((tool) => tool.tool_name),
      skills: selectedEmployee.skills.map((skill) => ({
        skill_name: skill.skill_name,
        category: skill.category,
        proficiency_level: skill.proficiency_level,
        description: skill.description,
      })),
      memory: selectedEmployee.employee.memory || [],
    });
    setConfigPanelOpen(true);
  };

  const handleConfigSave = useCallback(async (form: EmployeeFormData) => {
    if (!selectedEmployee) return;
    setIsSaving(true);
    try {
      await updateEmployee(selectedEmployee.employee.id, form);
      await handleRefresh();
      const employee = await getEmployee(selectedEmployee.employee.id);
      setSelectedEmployee(employee);
      setConfigFormData({
        name: employee.employee.name,
        role: employee.employee.role,
        avatar_url: employee.employee.avatar_url,
        description: employee.employee.description,
        system_prompt: employee.employee.system_prompt,
        model: employee.employee.model,
        temperature: employee.employee.temperature,
        max_tokens: employee.employee.max_tokens,
        tools: employee.tools.filter((tool) => tool.is_enabled).map((tool) => tool.tool_name),
        skills: employee.skills.map((skill) => ({
          skill_name: skill.skill_name,
          category: skill.category,
          proficiency_level: skill.proficiency_level,
          description: skill.description,
        })),
        memory: employee.employee.memory || [],
      });
      setConfigPanelOpen(false);
    } catch (err) {
      console.error('Failed to update employee:', err);
    } finally {
      setIsSaving(false);
    }
  }, [handleRefresh, selectedEmployee]);

  if (selectedAgent) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="p-8">
          {detailLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-sm text-muted-foreground">Loading employee...</span>
            </div>
          ) : (
            <AgentDetail
              agent={selectedAgent}
              onBack={handleBack}
              onConfigure={handleConfigure}
              skills={selectedEmployee?.skills || []}
              tools={selectedEmployee?.tools || []}
              tasks={selectedEmployee?.tasks || []}
              activity={selectedEmployee?.activity || []}
            />
          )}

          <EmployeeConfigPanel
            open={configPanelOpen}
            onClose={handleCloseConfigPanel}
            employee={configFormData}
            onSave={handleConfigSave}
            isSaving={isSaving}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8">
        <div className="max-w-6xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-end justify-between border-b border-border pb-3">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Employees</h2>
              <p className="text-muted-foreground mt-1 text-xs">Manage and configure your autonomous teammates.</p>
            </div>
            <Button variant="outline" size="sm" className="gap-2 text-xs font-medium h-8" onClick={handleOpenModal}>
              <Sparkles className="w-3.5 h-3.5" />
              Provision Employee
            </Button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-sm text-muted-foreground">Loading employees...</span>
            </div>
          ) : (
            <AgentList agents={agents} onAgentClick={handleAgentClick} />
          )}
        </div>

        <ProvisionModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          onGenerated={handleModalGenerated}
        />

        <EmployeePanel
          open={createPanelOpen}
          onClose={handleCloseCreatePanel}
          employee={createPrefillData}
          onSave={handleSave}
          isSaving={isSaving}
        />
      </div>
    </div>
  );
}
