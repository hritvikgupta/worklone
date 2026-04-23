import React, { useMemo } from 'react';
import { Agent } from '@/src/types';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';
import { Copy, MessageSquare, MoreVertical, Pencil, Trash2 } from 'lucide-react';
import { useEmployeePresence } from '@/src/hooks/usePresence';

interface AgentListProps {
  agents: Agent[];
  onAgentClick: (agent: Agent) => void;
  selectedAgentId?: string;
  onRename?: (agent: Agent) => void;
  onDuplicate?: (agent: Agent) => void;
  onDelete?: (agent: Agent) => void;
  onChat?: (agent: Agent) => void;
}

const TOOL_ICON_MAP: Array<{ match: RegExp; icon: string; alt: string }> = [
  { match: /(gmail|googlemail)/i, icon: 'https://cdn.simpleicons.org/gmail/EA4333', alt: 'Gmail' },
  { match: /(slack)/i, icon: '/slackicon.png', alt: 'Slack' },
  { match: /(notion)/i, icon: 'https://cdn.simpleicons.org/notion/000000', alt: 'Notion' },
  { match: /(google.?drive|drive)/i, icon: '/icons/google-drive.svg', alt: 'Google Drive' },
  { match: /(calendar)/i, icon: 'https://cdn.simpleicons.org/googlecalendar/4285F4', alt: 'Calendar' },
  { match: /(github)/i, icon: 'https://cdn.simpleicons.org/github/181717', alt: 'GitHub' },
  { match: /(jira)/i, icon: 'https://cdn.simpleicons.org/jira/0052CC', alt: 'Jira' },
  { match: /(linear)/i, icon: 'https://cdn.simpleicons.org/linear/5E6AD2', alt: 'Linear' },
  { match: /(hubspot)/i, icon: 'https://cdn.simpleicons.org/hubspot/FF7A59', alt: 'HubSpot' },
  { match: /(stripe)/i, icon: 'https://cdn.simpleicons.org/stripe/635BFF', alt: 'Stripe' },
  { match: /(salesforce)/i, icon: 'https://cdn.simpleicons.org/salesforce/00A1E0', alt: 'Salesforce' },
  { match: /(airtable)/i, icon: 'https://cdn.simpleicons.org/airtable/18BFFF', alt: 'Airtable' },
];

function toolIconFor(toolName: string): { icon?: string; label: string } {
  const hit = TOOL_ICON_MAP.find((item) => item.match.test(toolName));
  if (hit) return { icon: hit.icon, label: hit.alt };
  return { label: toolName };
}

export function AgentList({ agents, onAgentClick, selectedAgentId, onRename, onDuplicate, onDelete, onChat }: AgentListProps) {
  const ids = useMemo(() => agents.map((a) => a.id), [agents]);
  const { statuses, busyIn } = useEmployeePresence(ids);

  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'working': return 'bg-amber-400';
      case 'idle': return 'bg-emerald-400';
      case 'blocked': return 'bg-rose-400';
      case 'offline': return 'bg-slate-300';
      default: return 'bg-slate-300';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b pb-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Active Employees</h2>
        <span className="text-xs text-muted-foreground">{agents.length} members</span>
      </div>

      <div className="grid grid-cols-1 gap-7 md:grid-cols-2 xl:grid-cols-3">
        {agents.map((agent, index) => {
          const liveStatus = (statuses[agent.id]?.status as Agent['status']) || agent.status;
          const ctx = busyIn(agent.id);

          return (
            <motion.div
              key={agent.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: index * 0.04 }}
              whileHover={{ y: -2 }}
            >
              <Card
                onClick={() => onAgentClick(agent)}
                className={cn(
                  'group relative cursor-pointer gap-0 overflow-hidden border bg-card py-0 transition-all',
                  selectedAgentId === agent.id
                    ? 'border-primary shadow-[0_10px_28px_rgba(0,0,0,0.12)]'
                    : 'border-border hover:border-foreground/20 hover:shadow-[0_10px_28px_rgba(0,0,0,0.10)]'
                )}
              >
                <div className="h-14 bg-gradient-to-r from-zinc-50 via-zinc-100 to-zinc-50 dark:from-zinc-900 dark:via-zinc-800 dark:to-zinc-900" />

                <CardContent className="relative px-5 pb-5 pt-0">
                  <div className="flex items-start justify-between">
                    <div className="-mt-7">
                      <div className="relative">
                        <Avatar className="h-14 w-14 rounded-2xl border-2 border-background shadow-sm">
                          <AvatarImage src={agent.avatar} alt={agent.name} />
                          <AvatarFallback className="rounded-2xl text-base">{agent.name[0]}</AvatarFallback>
                        </Avatar>
                        <div
                          className={cn(
                            'absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-background',
                            getStatusColor(liveStatus)
                          )}
                        />
                      </div>
                    </div>

                    <div className="mt-2 flex items-center gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 gap-1.5 px-2 text-[11px]"
                        onClick={(e) => {
                          e.stopPropagation();
                          onChat?.(agent);
                        }}
                      >
                        <MessageSquare className="h-3.5 w-3.5" />
                        Chat
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button
                            type="button"
                            aria-label="Employee options"
                            className="rounded-md p-1 text-muted-foreground/80 transition-colors hover:bg-muted hover:text-foreground"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </button>
                        </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenuItem onClick={() => onRename?.(agent)}>
                          <Pencil className="h-4 w-4" />
                          Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onDuplicate?.(agent)}>
                          <Copy className="h-4 w-4" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-rose-600 focus:text-rose-600" onClick={() => onDelete?.(agent)}>
                          <Trash2 className="h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>

                  <div className="mt-3 min-w-0">
                    <h3 className="truncate text-2xl font-semibold tracking-tight text-foreground">
                      {agent.name}
                    </h3>
                    {agent.role && (
                      <p className="mt-2 truncate text-[13px] text-muted-foreground">{agent.role}</p>
                    )}
                  </div>

                  <p className="mt-4 line-clamp-2 min-h-10 text-sm leading-5 text-muted-foreground">
                    {agent.description || 'AI employee ready for autonomous execution and collaboration.'}
                  </p>

                  <div className="mt-4 flex items-center gap-2">
                    {(agent.tools || []).slice(0, 4).map((tool) => {
                      const icon = toolIconFor(tool);
                      return (
                        <div
                          key={tool}
                          title={tool}
                          className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-background"
                        >
                          {icon.icon ? (
                            <>
                              <img
                                src={icon.icon}
                                alt={icon.label}
                                className="h-4 w-4"
                                onError={(e) => {
                                  const img = e.currentTarget;
                                  img.style.display = 'none';
                                  const fallback = img.nextElementSibling as HTMLElement | null;
                                  if (fallback) fallback.style.display = 'inline';
                                }}
                              />
                              <span className="hidden text-[10px] font-semibold text-muted-foreground">
                                {(tool || '?').slice(0, 2).toUpperCase()}
                              </span>
                            </>
                          ) : (
                            <span className="text-[10px] font-semibold text-muted-foreground">
                              {(tool || '?').slice(0, 2).toUpperCase()}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  <div className="mt-5 flex items-center justify-between gap-3 border-t border-border/80 pt-3">
                    <div className="min-w-0 text-xs text-muted-foreground">
                      {liveStatus === 'working' ? (
                        <span className="flex items-center gap-1.5">
                          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
                          {ctx?.kind ? `Busy · ${ctx.kind}` : (agent.currentTask || 'Busy')}
                        </span>
                      ) : liveStatus === 'blocked' ? (
                        <span className="text-rose-500">Blocked</span>
                      ) : (
                        <span>Available</span>
                      )}
                    </div>

                    <Badge variant="secondary" className="shrink-0 text-[10px] font-normal">
                      {agent.model}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
