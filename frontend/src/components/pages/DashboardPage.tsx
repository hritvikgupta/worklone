import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Loader2 } from 'lucide-react';
import { EmployeePanel, EmployeeFormData } from '@/src/components/EmployeePanel';
import { ProvisionModal } from '@/src/components/ProvisionModal';
import { AgentList } from '@/src/components/AgentList';
import { ActivityFeed } from '@/src/components/ActivityFeed';
import { SkillStats } from '@/src/components/SkillStats';
import { Button } from '@/components/ui/button';
import { listEmployees, createEmployee, updateEmployee, EmployeeDetail } from '@/src/api/employees';
import { Agent, Activity } from '@/src/types';
import { MOCK_ACTIVITIES, MOCK_ISSUES } from '@/src/constants';

// Map API EmployeeDetail -> Agent type expected by AgentList/AgentDetail
function toAgent(emp: EmployeeDetail, skills?: string[]): Agent {
  return {
    id: emp.id,
    name: emp.name,
    role: emp.role,
    avatar: emp.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${emp.name.toLowerCase()}`,
    status: emp.status as Agent['status'],
    description: emp.description,
    systemPrompt: emp.system_prompt,
    skills: skills || [],
    model: emp.model,
  };
}

export function DashboardPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<EmployeeFormData | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const fetchEmployees = useCallback(async () => {
    setLoading(true);
    try {
      const employees = await listEmployees();
      // Fetch skill names for each employee
      const mapped: Agent[] = employees.map((emp) =>
        toAgent(emp, [])
      );
      setAgents(mapped);
    } catch (err) {
      console.error('Failed to load employees:', err);
      // Fallback to empty — show empty state
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  const handleOpenCreate = () => {
    setModalOpen(true);
  };

  const handleModalGenerated = (form: EmployeeFormData) => {
    setModalOpen(false);
    setEditingEmployee(form);
    setPanelOpen(true);
  };

  const handleOpenEdit = (_agent: Agent) => {
    // TODO: fetch full employee details for editing
    setPanelOpen(true);
  };

  const handleClosePanel = () => {
    setPanelOpen(false);
    setEditingEmployee(null);
  };

  const handleSave = async (form: EmployeeFormData) => {
    setIsSaving(true);
    try {
      if (editingEmployee) {
        // TODO: implement update once we have employee ID
        await createEmployee(form);
      } else {
        await createEmployee(form);
      }
      handleClosePanel();
      await fetchEmployees();
    } catch (err) {
      console.error('Failed to save employee:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAgentClick = (agent: Agent) => {
    setSelectedAgentId(agent.id);
  };

  const selectedAgent = agents.find((a) => a.id === selectedAgentId) || null;

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto space-y-10 animate-in fade-in duration-300">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight">Dashboard</h2>
            <p className="text-muted-foreground text-sm">Monitor your human and AI workforce in real time.</p>
          </div>
          <Button
            onClick={handleOpenCreate}
            className="gap-2 bg-zinc-950 text-white hover:bg-zinc-800"
          >
            <Plus className="h-4 w-4" />
            Create Employee
          </Button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
            <span className="ml-2 text-sm text-zinc-400">Loading employees...</span>
          </div>
        ) : (
          <>
            <SkillStats />
            <AgentList agents={agents} onAgentClick={handleAgentClick} />
            <ActivityFeed activities={MOCK_ACTIVITIES} />
          </>
        )}
      </div>

      <ProvisionModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onGenerated={handleModalGenerated}
      />

      <EmployeePanel
        open={panelOpen}
        onClose={handleClosePanel}
        employee={editingEmployee}
        onSave={handleSave}
        isSaving={isSaving}
      />
    </div>
  );
}
