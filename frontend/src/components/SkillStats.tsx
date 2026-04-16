import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Brain, Code, Zap, Target } from 'lucide-react';

export function SkillStats() {
  const stats = [
    { label: 'Autonomous Commits', value: '1,284', icon: Code, color: 'text-blue-400' },
    { label: 'Skills Compounded', value: '42', icon: Brain, color: 'text-purple-400' },
    { label: 'Issue Velocity', value: '+24%', icon: Zap, color: 'text-amber-400' },
    { label: 'Success Rate', value: '98.2%', icon: Target, color: 'text-emerald-400' },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat) => (
        <div key={stat.label} className="space-y-1 p-4 rounded-xl border border-border hover:bg-secondary/30 transition-colors group cursor-default">
          <div className="flex items-center gap-2">
            <stat.icon className={`w-3.5 h-3.5 ${stat.color} opacity-70 group-hover:opacity-100 transition-opacity`} />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              {stat.label}
            </span>
          </div>
          <div className="text-2xl font-bold tracking-tight">{stat.value}</div>
        </div>
      ))}
    </div>
  );
}
