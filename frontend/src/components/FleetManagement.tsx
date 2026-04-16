import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Zap, Network, Headset, Database, Activity, Clock, XCircle, Settings, Sliders, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';

type AgentStatus = 'running' | 'idle' | 'failed';

interface Agent {
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
  icon: React.ElementType;
  spend: number;
  budget: number;
  traits: {
    aggression: number;
    autonomy: number;
    creativity: number;
  };
}

const INITIAL_AGENTS: Agent[] = [
  {
    id: 'a1', name: 'SDR-Alpha', role: 'Sales Development', status: 'running', icon: Zap,
    spend: 48.50, budget: 50.00,
    traits: { aggression: 85, autonomy: 90, creativity: 40 }
  },
  {
    id: 'a2', name: 'CMO-Nexus', role: 'Marketing Strategy', status: 'idle', icon: Network,
    spend: 12.20, budget: 100.00,
    traits: { aggression: 30, autonomy: 60, creativity: 95 }
  },
  {
    id: 'a3', name: 'Support-Bot-1', role: 'Customer Success', status: 'failed', icon: Headset,
    spend: 5.00, budget: 20.00,
    traits: { aggression: 10, autonomy: 40, creativity: 20 }
  },
  {
    id: 'a4', name: 'Data-Miner', role: 'Research & Enrichment', status: 'running', icon: Database,
    spend: 180.00, budget: 200.00,
    traits: { aggression: 50, autonomy: 100, creativity: 10 }
  }
];

export function FleetManagement() {
  const [agents, setAgents] = useState<Agent[]>(INITIAL_AGENTS);
  const [tuningAgent, setTuningAgent] = useState<string | null>(null);

  const handleTraitChange = (agentId: string, trait: keyof Agent['traits'], value: number) => {
    setAgents(prev => prev.map(a =>
      a.id === agentId ? { ...a, traits: { ...a.traits, [trait]: value } } : a
    ));
  };

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-foreground">Agent Fleet</h1>
          <button className="text-sm font-medium text-emerald-600 hover:text-emerald-500 transition-colors flex items-center gap-1">
            <Plus className="w-4 h-4" /> Deploy New Agent
          </button>
        </div>

        {/* Agent Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map(agent => (
            <div key={agent.id} className="bg-card border border-border rounded-xl p-5 relative overflow-hidden group shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
              {/* Status Indicator Line */}
              <div className={cn(
                "absolute top-0 left-0 w-1 h-full",
                agent.status === 'running' ? "bg-emerald-500" :
                agent.status === 'failed' ? "bg-red-500" : "bg-muted"
              )} />

              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-muted rounded-lg">
                    <agent.icon className="w-5 h-5 text-foreground" />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground">{agent.name}</h3>
                    <p className="text-xs text-muted-foreground">{agent.role}</p>
                  </div>
                </div>
                <StatusBadge status={agent.status} />
              </div>

              <div className="space-y-4">
                {/* Budget Bar */}
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-muted-foreground">Daily Budget</span>
                    <span className={cn(
                      "font-medium",
                      (agent.spend / agent.budget) > 0.9 ? "text-red-600" : "text-foreground"
                    )}>${agent.spend.toFixed(2)} / ${agent.budget.toFixed(2)}</span>
                  </div>
                  <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-500",
                        (agent.spend / agent.budget) > 0.9 ? "bg-red-500" : "bg-emerald-500"
                      )}
                      style={{ width: `${Math.min((agent.spend / agent.budget) * 100, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="pt-2 border-t border-border flex justify-between items-center">
                  <div className="flex space-x-2">
                    <button className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
                      {agent.status === 'running' ? <Clock className="w-4 h-4" /> : <Activity className="w-4 h-4" />}
                    </button>
                    <button className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
                      <Settings className="w-4 h-4" />
                    </button>
                  </div>
                  <button
                    onClick={() => setTuningAgent(tuningAgent === agent.id ? null : agent.id)}
                    className={cn(
                      "flex items-center space-x-1.5 text-xs font-medium px-2.5 py-1.5 rounded-md transition-colors",
                      tuningAgent === agent.id
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : "bg-muted text-muted-foreground hover:bg-muted border border-border"
                    )}
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    <span>Tune Behavior</span>
                  </button>
                </div>
              </div>

              {/* Tuning Panel (Expandable) */}
              <AnimatePresence>
                {tuningAgent === agent.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="pt-4 mt-4 border-t border-border space-y-4">
                      <TraitSlider
                        label="Aggression"
                        value={agent.traits.aggression}
                        onChange={(v) => handleTraitChange(agent.id, 'aggression', v)}
                        description="Higher values lead to more assertive outreach and risk-taking."
                      />
                      <TraitSlider
                        label="Autonomy"
                        value={agent.traits.autonomy}
                        onChange={(v) => handleTraitChange(agent.id, 'autonomy', v)}
                        description="How often the agent asks for human approval."
                      />
                      <TraitSlider
                        label="Creativity"
                        value={agent.traits.creativity}
                        onChange={(v) => handleTraitChange(agent.id, 'creativity', v)}
                        description="Temperature setting for generated content."
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: AgentStatus }) {
  const config = {
    running: { icon: Activity, text: 'Running', classes: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    idle: { icon: Clock, text: 'Idle', classes: 'bg-muted text-muted-foreground border-border' },
    failed: { icon: XCircle, text: 'Failed', classes: 'bg-red-50 text-red-600 border-red-200' },
  };
  const { icon: Icon, text, classes } = config[status];

  return (
    <div className={cn("flex items-center space-x-1.5 px-2 py-1 rounded-md border text-xs font-medium", classes)}>
      <Icon className="w-3.5 h-3.5" />
      <span>{text}</span>
    </div>
  );
}

function TraitSlider({ label, value, onChange, description }: { label: string, value: number, onChange: (v: number) => void, description: string }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <label className="text-xs font-medium text-foreground">{label}</label>
        <span className="text-xs font-mono text-muted-foreground">{value}%</span>
      </div>
      <input
        type="range"
        min="0" max="100"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-emerald-500"
      />
      <p className="text-[10px] text-muted-foreground mt-1.5">{description}</p>
    </div>
  );
}
