import React from 'react';
import { Plus, Filter, Search, MoreHorizontal, Github } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

const backlogItems = [
  { id: 'PROD-124', title: 'Implement dark mode toggle', priority: 'low', status: 'todo', team: 'UI/UX', github: '#452' },
  { id: 'PROD-125', title: 'Fix API latency in dashboard', priority: 'high', status: 'in-progress', team: 'Backend', github: '#458' },
  { id: 'PROD-126', title: 'Add export to CSV for analytics', priority: 'medium', status: 'todo', team: 'Data', github: null },
  { id: 'PROD-127', title: 'Update user onboarding flow', priority: 'medium', status: 'todo', team: 'Growth', github: '#460' },
  { id: 'PROD-128', title: 'Integrate Stripe for subscriptions', priority: 'high', status: 'todo', team: 'Payments', github: null },
  { id: 'PROD-129', title: 'Refactor state management', priority: 'low', status: 'backlog', team: 'Frontend', github: '#462' },
];

export function Backlog() {
  return (
    <div className="p-12 max-w-7xl mx-auto space-y-8">
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight text-foreground">Product Backlog</h1>
        <p className="text-muted-foreground">Manage and prioritize your product features and tasks.</p>
      </div>

      <div className="flex gap-4 items-center border-b border-border pb-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input 
            placeholder="Search tasks..." 
            className="pl-8 border-none bg-muted/50 focus-visible:ring-0 h-8 text-sm placeholder:text-muted-foreground" 
          />
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="text-xs text-muted-foreground font-normal h-8">
            <Filter className="w-3.5 h-3.5 mr-2" />
            Filter
          </Button>
          <Button variant="ghost" size="sm" className="text-xs text-muted-foreground font-normal h-8">
            Sort
          </Button>
        </div>
      </div>

      <div className="space-y-0.5">
        <div className="grid grid-cols-12 gap-4 px-2 py-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground border-b border-border">
          <div className="col-span-1">ID</div>
          <div className="col-span-6">Title</div>
          <div className="col-span-2">Priority</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1"></div>
        </div>
        <div className="divide-y divide-zinc-50">
          {backlogItems.map((item) => (
            <div key={item.id} className="grid grid-cols-12 gap-4 px-2 py-3 items-center hover:bg-muted transition-colors cursor-pointer group">
              <div className="col-span-1 text-xs font-mono text-muted-foreground">{item.id}</div>
              <div className="col-span-6 flex items-center gap-3">
                <span className="text-sm font-medium text-foreground">{item.title}</span>
                {item.github && (
                  <span className="flex items-center gap-1 text-[10px] text-muted-foreground font-medium">
                    <Github className="w-3 h-3" />
                    {item.github}
                  </span>
                )}
              </div>
              <div className="col-span-2">
                <span className={cn(
                  "text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider",
                  item.priority === 'high' ? "bg-red-100/50 text-red-700" :
                  item.priority === 'medium' ? "bg-amber-100/50 text-amber-700" :
                  "bg-muted text-muted-foreground"
                )}>
                  {item.priority}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-bold uppercase tracking-wider">
                  {item.status}
                </span>
              </div>
              <div className="col-span-1 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground">
                  <MoreHorizontal className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
          <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-foreground hover:bg-muted h-10 px-2 text-sm font-normal mt-2">
            <Plus className="w-4 h-4 mr-2" />
            New
          </Button>
        </div>
      </div>
    </div>
  );
}
