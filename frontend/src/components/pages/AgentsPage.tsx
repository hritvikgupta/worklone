import React, { useState, useCallback } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgentDetail } from '@/src/components/AgentDetail';
import { AgentList } from '@/src/components/AgentList';
import { EmployeePanel, EmployeeFormData } from '@/src/components/EmployeePanel';
import { ProvisionModal } from '@/src/components/ProvisionModal';
import { MOCK_ACTIVITIES, MOCK_AGENTS, MOCK_ISSUES } from '@/src/constants';
import { Agent } from '@/src/types';
import { listEmployees, createEmployee, EmployeeDetail as EmployeeDetailType } from '@/src/api/employees';

function toAgent(emp: EmployeeDetailType, skills: string[] = []): Agent {
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
  };
}

export function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>(MOCK_AGENTS);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [prefillData, setPrefillData] = useState<EmployeeFormData | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) || null;

  const handleAgentClick = (agent: Agent) => {
    setSelectedAgentId(agent.id);
  };

  const handleOpenModal = () => {
    setModalOpen(true);
  };

  const handleModalGenerated = (form: EmployeeFormData) => {
    setModalOpen(false);
    setPrefillData(form);
    setPanelOpen(true);
  };

  const handleClosePanel = () => {
    setPanelOpen(false);
    setPrefillData(null);
  };

  const handleSave = useCallback(async (form: EmployeeFormData) => {
    setIsSaving(true);
    try {
      const created = await createEmployee(form);
      const newAgent = toAgent(created);
      setAgents((prev) => [newAgent, ...prev]);
      handleClosePanel();
    } catch (err) {
      console.error('Failed to create employee:', err);
    } finally {
      setIsSaving(false);
    }
  }, []);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    try {
      const employees = await listEmployees();
      const mapped = employees.map((e) => toAgent(e));
      if (mapped.length > 0) setAgents(mapped);
    } catch (err) {
      console.error('Failed to load employees:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  if (selectedAgent) {
    return (
      <div className="p-8">
        <AgentDetail
          agent={selectedAgent}
          activities={MOCK_ACTIVITIES}
          issues={MOCK_ISSUES}
          onBack={() => setSelectedAgentId(null)}
        />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-300">
        <div className="flex items-end justify-between border-b border-border/50 pb-3">
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
            <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
            <span className="ml-2 text-sm text-zinc-400">Loading employees...</span>
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
        open={panelOpen}
        onClose={handleClosePanel}
        employee={prefillData}
        onSave={handleSave}
        isSaving={isSaving}
      />
    </div>
  );
}
