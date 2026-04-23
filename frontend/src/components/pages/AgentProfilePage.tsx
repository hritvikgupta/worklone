import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, MessageSquare } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { AgentDetail } from '@/src/components/AgentDetail';
import { EmployeeConfigPanel } from '@/src/components/EmployeeConfigPanel';
import { Agent } from '@/src/types';
import {
  getEmployee,
  updateEmployee,
  EmployeeWithDetails,
  EmployeeDetail as EmployeeDetailType,
} from '@/src/api/employees';
import { EmployeeFormData } from '@/src/components/EmployeePanel';

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
    cover: emp.cover_url || '',
    status: emp.status as Agent['status'],
    description: emp.description,
    systemPrompt: emp.system_prompt,
    skills,
    model: emp.model,
    currentTask,
  };
}

export function AgentProfilePage() {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();

  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeWithDetails | null>(null);
  const [configPanelOpen, setConfigPanelOpen] = useState(false);
  const [configFormData, setConfigFormData] = useState<EmployeeFormData | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [detailLoading, setDetailLoading] = useState(true);

  const selectedAgent = useMemo(() => {
    if (!selectedEmployee) return null;
    return toAgent(
      selectedEmployee.employee,
      selectedEmployee.skills.map((skill) => skill.skill_name),
      deriveCurrentTaskId(selectedEmployee),
    );
  }, [selectedEmployee]);

  const canOpenChat = useMemo(() => {
    if (!selectedEmployee) return false;
    const emp = selectedEmployee.employee;
    return Boolean(
      (emp.name || '').trim() &&
      (emp.role || '').trim() &&
      (emp.description || '').trim() &&
      (emp.system_prompt || '').trim(),
    );
  }, [selectedEmployee]);

  const loadEmployee = useCallback(async () => {
    if (!agentId) return;
    setDetailLoading(true);
    try {
      const employee = await getEmployee(agentId);
      setSelectedEmployee(employee);
    } catch (err) {
      console.error('Failed to load employee details:', err);
      setSelectedEmployee(null);
    } finally {
      setDetailLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    void loadEmployee();
  }, [loadEmployee]);

  const handleCloseConfigPanel = () => {
    setConfigPanelOpen(false);
    setConfigFormData(null);
  };

  const handleBack = () => {
    setConfigPanelOpen(false);
    setConfigFormData(null);
    navigate('/agents');
  };

  const handleConfigure = () => {
    if (!selectedEmployee) return;
    setConfigFormData({
      name: selectedEmployee.employee.name,
      role: selectedEmployee.employee.role,
      avatar_url: selectedEmployee.employee.avatar_url,
      cover_url: selectedEmployee.employee.cover_url || '',
      description: selectedEmployee.employee.description,
      system_prompt: selectedEmployee.employee.system_prompt,
      model: selectedEmployee.employee.model,
      provider: selectedEmployee.employee.provider || '',
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
      const employee = await getEmployee(selectedEmployee.employee.id);
      setSelectedEmployee(employee);
      setConfigFormData({
        name: employee.employee.name,
        role: employee.employee.role,
        avatar_url: employee.employee.avatar_url,
        cover_url: employee.employee.cover_url || '',
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
        provider: employee.employee.provider || '',
      });
    } catch (err) {
      console.error('Failed to update employee:', err);
    } finally {
      setIsSaving(false);
    }
  }, [selectedEmployee]);

  if (detailLoading) {
    return (
      <div className="h-full flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading employee...</span>
      </div>
    );
  }

  if (!selectedAgent || !selectedEmployee) {
    return (
      <div className="h-full flex items-center justify-center py-20 text-sm text-muted-foreground">
        Employee not found.
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8">
        <div className="mb-4 flex justify-end">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => navigate(`/agents/${selectedAgent.id}/workspace`)}
            disabled={!canOpenChat}
            title={!canOpenChat ? 'Add role, description, and system prompt before opening chat.' : 'Open chat workspace'}
          >
            <MessageSquare className="h-4 w-4" />
            Chat
          </Button>
        </div>

        <AgentDetail
          agent={selectedAgent}
          onBack={handleBack}
          onConfigure={handleConfigure}
          onCoverUpdate={async (coverUrl) => {
            await updateEmployee(selectedEmployee.employee.id, { cover_url: coverUrl });
            await loadEmployee();
          }}
          skills={selectedEmployee.skills || []}
          tools={selectedEmployee.tools || []}
          tasks={selectedEmployee.tasks || []}
          activity={selectedEmployee.activity || []}
        />

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
