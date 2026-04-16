import React from 'react';
import { Agent } from '@/src/types';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';

interface AgentListProps {
  agents: Agent[];
  onAgentClick: (agent: Agent) => void;
  selectedAgentId?: string;
}

export function AgentList({ agents, onAgentClick, selectedAgentId }: AgentListProps) {
  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'working': return 'bg-blue-400';
      case 'idle': return 'bg-emerald-400';
      case 'blocked': return 'bg-rose-400';
      case 'offline': return 'bg-slate-300';
      default: return 'bg-slate-300';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b pb-2">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Active Employees</h2>
        <span className="text-xs text-muted-foreground">{agents.length} members</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.map((agent, index) => (
          <motion.div
            key={agent.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => onAgentClick(agent)}
            className={cn(
              "flex items-start gap-4 rounded-xl border bg-card p-3 transition-all cursor-pointer group",
              selectedAgentId === agent.id
                ? "border-primary bg-muted shadow-[0_4px_12px_rgba(0,0,0,0.08)]"
                : "border-border shadow-[0_1px_3px_rgba(0,0,0,0.06)] hover:border-foreground/15 hover:bg-muted hover:shadow-[0_4px_12px_rgba(0,0,0,0.08)]"
            )}
          >
            <div className="relative flex-shrink-0">
              <Avatar className="h-10 w-10 rounded-lg border border-border">
                <AvatarImage src={agent.avatar} alt={agent.name} />
                <AvatarFallback className="rounded-lg">{agent.name[0]}</AvatarFallback>
              </Avatar>
              <div className={cn(
                "absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-background",
                getStatusColor(agent.status)
              )} />
            </div>
            <div className="flex-1 min-w-0 space-y-1">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-semibold transition-colors group-hover:text-primary">
                    {agent.name}
                  </h3>
                  {agent.role && (
                    <p className="truncate text-[11px] text-muted-foreground">
                      {agent.role}
                    </p>
                  )}
                </div>
                <Badge variant="secondary" className="shrink-0 text-[10px] font-normal">
                  powered by {agent.model}
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground truncate">
                {agent.status === 'working' ? (
                  <span className="flex items-center gap-1.5">
                    <span className="w-1 h-1 rounded-full bg-blue-400 animate-pulse" />
                    {agent.currentTask}
                  </span>
                ) : agent.status === 'blocked' ? (
                  <span className="text-rose-500 font-medium">Blocked</span>
                ) : (
                  <span>Available</span>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {agent.skills.slice(0, 2).map(skill => (
                  <span key={skill} className="text-[10px] text-muted-foreground/70 bg-muted px-1.5 py-0.5 rounded">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
