import React from 'react';
import { Agent, Activity, Issue } from '@/src/types';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';
import { 
  X, 
  Bot, 
  Terminal, 
  History, 
  Code, 
  Sparkles, 
  ChevronLeft,
  Cpu,
  Activity as ActivityIcon,
  Layers,
  Settings,
  ShieldCheck,
  Clock
} from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';

interface AgentDetailProps {
  agent: Agent;
  activities: Activity[];
  issues: Issue[];
  onBack: () => void;
}

export function AgentDetail({ agent, activities, issues, onBack }: AgentDetailProps) {
  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'working': return 'bg-blue-400';
      case 'idle': return 'bg-emerald-400';
      case 'blocked': return 'bg-rose-400';
      case 'offline': return 'bg-slate-300';
      default: return 'bg-slate-300';
    }
  };

  const agentActivities = activities.filter(a => a.agentId === agent.id);
  const currentIssue = agent.currentTask ? issues.find(i => i.id === agent.currentTask) : null;

  return (
    <div className="h-full flex flex-col space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/50 pb-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={onBack} className="h-8 w-8 p-0 -ml-2">
            <ChevronLeft className="w-5 h-5" />
          </Button>
          <div className="relative">
            <Avatar className="h-16 w-16 rounded-2xl border-2 border-border/50 shadow-sm">
              <AvatarImage src={agent.avatar} alt={agent.name} />
              <AvatarFallback className="text-xl">{agent.name[0]}</AvatarFallback>
            </Avatar>
            <div className={cn(
              "absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-4 border-background",
              getStatusColor(agent.status)
            )} />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">{agent.name}</h1>
              <Badge variant="secondary" className="bg-secondary/50 text-muted-foreground font-mono text-[10px]">
                {agent.model}
              </Badge>
            </div>
            {agent.role && (
              <div className="text-sm text-muted-foreground">{agent.role}</div>
            )}
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5 capitalize">
                <span className={cn("w-1.5 h-1.5 rounded-full", getStatusColor(agent.status))} />
                {agent.status}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5" />
                {agent.skills.length} Skills Active
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-9 gap-2 font-medium">
            <Settings className="w-4 h-4" />
            Configure
          </Button>
          <Button size="sm" className="h-9 gap-2 font-bold shadow-sm">
            <Sparkles className="w-4 h-4" />
            Re-Provision
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1 min-h-0">
        {/* Left Column: Overview & Prompt */}
        <div className="lg:col-span-2 space-y-8">
          {/* Current Task Section */}
          <section className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-widest">
              <Terminal className="w-4 h-4" />
              Active Context
            </div>
            {currentIssue ? (
              <Card className="border-border/40 shadow-sm bg-secondary/5">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between mb-1">
                    <Badge variant="outline" className="text-[10px] font-mono border-primary/20 text-primary bg-primary/5">
                      {currentIssue.id}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Started {new Date(currentIssue.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                  <CardTitle className="text-lg">{currentIssue.title}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {currentIssue.description}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {currentIssue.tags.map(tag => (
                      <Badge key={tag} variant="secondary" className="text-[10px] bg-secondary/50">
                        #{tag}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="h-32 flex flex-col items-center justify-center border-2 border-dashed border-border/40 rounded-xl text-muted-foreground bg-secondary/5">
                <p className="text-sm italic">No active task assigned</p>
                <Button variant="link" size="sm" className="text-xs">Assign Task</Button>
              </div>
            )}
          </section>

          {/* Prompt Section */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-widest">
                <Code className="w-4 h-4" />
                System Instructions
              </div>
              <Badge variant="outline" className="text-[9px] border-emerald-500/20 text-emerald-600 bg-emerald-500/5 gap-1">
                <ShieldCheck className="w-3 h-3" />
                Verified Persona
              </Badge>
            </div>
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
              <div className="bg-slate-950 rounded-xl p-6 font-mono text-sm text-slate-300 leading-relaxed border border-slate-800 shadow-xl overflow-hidden">
                <div className="flex items-center gap-2 mb-4 text-slate-500 text-xs border-b border-slate-800 pb-2">
                  <span className="text-emerald-500">system</span>
                  <span>prompt.md</span>
                </div>
                {agent.systemPrompt}
              </div>
            </div>
          </section>
        </div>

        {/* Right Column: Stats & History */}
        <div className="space-y-8">
          {/* Agent Info Card */}
          <Card className="border-border/40 shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-widest mb-2">
                <Bot className="w-4 h-4" />
                Profile
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-muted-foreground">About</h4>
                <p className="text-sm leading-relaxed">
                  {agent.description}
                </p>
              </div>
              
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-muted-foreground">Capabilities</h4>
                <div className="flex flex-wrap gap-2">
                  {agent.skills.map(skill => (
                    <Badge key={skill} variant="secondary" className="bg-primary/5 text-primary border-primary/10">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Activity Timeline */}
          <section className="space-y-4">
            <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-widest">
              <ActivityIcon className="w-4 h-4" />
              Recent Edits & History
            </div>
            <div className="relative space-y-6 before:absolute before:left-[17px] before:top-2 before:bottom-2 before:w-px before:bg-border/60">
              {agentActivities.length > 0 ? (
                agentActivities.map((activity) => (
                  <div key={activity.id} className="relative pl-10 group">
                    <div className="absolute left-0 top-1 w-9 h-9 flex items-center justify-center">
                      <div className="w-2.5 h-2.5 rounded-full bg-background border-2 border-primary z-10 group-hover:scale-125 transition-transform" />
                    </div>
                    <div className="space-y-1.5 p-3 rounded-lg hover:bg-secondary/30 transition-colors border border-transparent hover:border-border/30">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold capitalize text-foreground/90">
                          {activity.type.replace('_', ' ')}
                        </span>
                        <span className="text-[10px] text-muted-foreground font-medium">
                          {new Date(activity.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-snug">{activity.message}</p>
                      {activity.issueId && (
                        <div className="flex items-center gap-1.5 pt-1">
                          <Badge variant="outline" className="text-[9px] h-4 px-1.5 font-mono bg-background">
                            {activity.issueId}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="pl-10 text-xs text-muted-foreground italic py-4">
                  No recent activity recorded
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
