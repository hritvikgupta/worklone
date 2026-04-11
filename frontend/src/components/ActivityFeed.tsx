import React from 'react';
import { Activity } from '@/src/types';
import { MOCK_AGENTS } from '@/src/constants';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { motion } from 'motion/react';
import { GitCommit, AlertTriangle, Play, CheckCircle, Lightbulb } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface ActivityFeedProps {
  activities: Activity[];
}

export function ActivityFeed({ activities }: ActivityFeedProps) {
  const getAgent = (id: string) => MOCK_AGENTS.find(a => a.id === id);

  const getIcon = (type: Activity['type']) => {
    switch (type) {
      case 'code_pushed': return <GitCommit className="w-3 h-3 text-blue-400" />;
      case 'blocker_reported': return <AlertTriangle className="w-3 h-3 text-rose-400" />;
      case 'work_started': return <Play className="w-3 h-3 text-emerald-400" />;
      case 'status_updated': return <CheckCircle className="w-3 h-3 text-emerald-400" />;
      case 'skill_learned': return <Lightbulb className="w-3 h-3 text-amber-400" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b pb-2">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Live Activity</h2>
        <span className="text-xs text-muted-foreground">Real-time updates</span>
      </div>
      <ScrollArea className="h-[500px] pr-4">
        <div className="space-y-4">
          {activities.map((activity, index) => {
            const agent = getAgent(activity.agentId);
            return (
              <motion.div
                key={activity.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-start gap-3 group p-2 rounded-lg hover:bg-secondary/30 transition-colors"
              >
                <div className="mt-1">
                  {getIcon(activity.type)}
                </div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">{agent?.name}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground leading-snug">
                    {activity.message}
                  </p>
                  {activity.issueId && (
                    <div className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground/60 hover:text-primary transition-colors cursor-pointer">
                      <span className="opacity-50">↗</span>
                      {activity.issueId}
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
