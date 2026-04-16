import React from 'react';
import { 
  Activity, 
  Coins, 
  DollarSign, 
  Clock, 
  Users, 
  Zap, 
  GitBranch, 
  MessageSquare,
  ArrowRight,
  TrendingUp
} from 'lucide-react';
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle, 
  CardDescription 
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import useEmblaCarousel from 'embla-carousel-react';

// --- Dummy Data ---
const STATS = [
  {
    title: "Total Token Burn",
    value: "1,245,892",
    description: "Aggregate consumption across models",
    icon: Coins,
    trend: "+12.5%",
    trendText: "vs last 24h"
  },
  {
    title: "Total Money Used",
    value: "$142.50",
    description: "Total API expenditure (USD)",
    icon: DollarSign,
    trend: "$0.12/min",
    trendText: "current velocity"
  },
  {
    title: "Hours Running",
    value: "164.5h",
    description: "Total active employee uptime",
    icon: Clock,
    trend: "4",
    trendText: "active sessions"
  }
];

const EMPLOYEES = [
  {
    id: "1",
    name: "Mira",
    role: "Growth Lead",
    avatar: "/workforce/employee-1.png",
    hourlyRate: 45,
    status: "working",
    activeTask: "Funnel Analysis"
  },
  {
    id: "2",
    name: "Leo",
    role: "Backend Engineer",
    avatar: "/workforce/employee-3.png",
    hourlyRate: 60,
    status: "working",
    activeTask: "API Integration"
  },
  {
    id: "3",
    name: "Sam",
    role: "Data Analyst",
    avatar: "/workforce/employee-4.png",
    hourlyRate: 50,
    status: "idle",
    activeTask: "None"
  },
  {
    id: "4",
    name: "Katy",
    role: "Product Manager",
    avatar: "/workforce/employee-5.png",
    hourlyRate: 55,
    status: "working",
    activeTask: "Roadmap Planning"
  },
  {
    id: "5",
    name: "Alex",
    role: "UI Designer",
    avatar: "/workforce/employee-2.png",
    hourlyRate: 48,
    status: "offline",
    activeTask: "None"
  },
  {
    id: "6",
    name: "Zoe",
    role: "DevOps",
    avatar: "/workforce/employee-1.png",
    hourlyRate: 65,
    status: "working",
    activeTask: "K8s Optimization"
  }
];

const ACTIVITIES = [
  {
    id: "a1",
    source: "Sprint",
    sourceType: "sprint",
    message: "Sprint 'Q1 Growth' — Leo pushed 3 commits to 'auth-module'",
    time: "2m ago",
    icon: Zap
  },
  {
    id: "a2",
    source: "Team",
    sourceType: "team",
    message: "Mira & Sam started a collaboration on 'User Retention'",
    time: "5m ago",
    icon: Users
  },
  {
    id: "a3",
    source: "Workflow",
    sourceType: "workflow",
    message: "Workflow 'Auto-PR Review' completed successfully",
    time: "12m ago",
    icon: GitBranch
  },
  {
    id: "a4",
    source: "Employee",
    sourceType: "task",
    message: "Katy created a new task: 'Draft Q2 Strategy'",
    time: "15m ago",
    icon: MessageSquare
  },
  {
    id: "a5",
    source: "Sprint",
    sourceType: "sprint",
    message: "Daily Standup scheduled for tomorrow 10:00 AM",
    time: "45m ago",
    icon: Zap
  },
  {
    id: "a6",
    source: "Workflow",
    sourceType: "workflow",
    message: "Deployment to Staging triggered by Alex",
    time: "1h ago",
    icon: GitBranch
  }
];

export function Dashboard() {
  const [emblaRef] = useEmblaCarousel({ 
    align: 'start',
    containScroll: 'trimSnaps',
    dragFree: true
  });

  return (
    <div className="flex-1 overflow-y-auto bg-background p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-10">
        {/* Header Section */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Global Overview</h1>
            <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 hover:bg-emerald-500/10">
              System Active
            </Badge>
          </div>
          <p className="text-muted-foreground">Monitor token burn, workforce expenditure, and live operational activity.</p>
        </div>

        {/* Top Stats Cards */}
        <div className="grid gap-6 md:grid-cols-3">
          {STATS.map((stat) => (
            <Card key={stat.title} className="shadow-sm border-border/60">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">{stat.title}</CardTitle>
                <div className="p-2 bg-muted rounded-lg">
                  <stat.icon className="h-4 w-4 text-primary" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold tracking-tight">{stat.value}</div>
                <div className="flex items-center gap-2 mt-2">
                  <span className="flex items-center text-xs font-medium text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    {stat.trend}
                  </span>
                  <span className="text-xs text-muted-foreground">{stat.trendText}</span>
                </div>
                <p className="text-[11px] text-muted-foreground/70 mt-4 border-t pt-3">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Dashboard Content */}
        <div className="grid gap-8 lg:grid-cols-12">
          
          {/* Active Employees Section (Carousel) */}
          <div className="lg:col-span-8 space-y-6">
            <div className="flex items-center justify-between px-1">
              <div className="space-y-1">
                <h2 className="text-xl font-bold tracking-tight">Active Employees</h2>
                <p className="text-sm text-muted-foreground">Hired agents currently in session.</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="font-mono text-[10px]">{EMPLOYEES.length} TOTAL</Badge>
                <button className="text-xs font-semibold text-primary hover:underline flex items-center gap-1">
                  Manage <ArrowRight className="h-3 w-3" />
                </button>
              </div>
            </div>
            
            <div className="relative group">
              <div className="overflow-hidden rounded-xl" ref={emblaRef}>
                <div className="flex gap-4">
                  {EMPLOYEES.map((employee) => (
                    <Card key={employee.id} className="flex-[0_0_220px] aspect-square relative group overflow-hidden border-border/50 hover:border-primary/50 transition-all duration-300 shadow-sm">
                      <CardContent className="p-0 h-full">
                        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent z-10" />
                        <img 
                          src={employee.avatar} 
                          alt={employee.name} 
                          className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-110"
                        />
                        <div className="absolute bottom-0 left-0 right-0 p-4 z-20 text-white">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={cn(
                              "h-2 w-2 rounded-full",
                              employee.status === 'working' ? "bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" : 
                              employee.status === 'idle' ? "bg-amber-400" : "bg-slate-400"
                            )} />
                            <p className="text-sm font-bold truncate">{employee.name}</p>
                          </div>
                          <p className="text-[10px] text-white/70 truncate uppercase tracking-widest font-bold mb-3">
                            {employee.role}
                          </p>
                          <div className="flex items-center justify-between border-t border-white/10 pt-3">
                            <div className="space-y-0.5">
                              <p className="text-[9px] text-white/50 uppercase font-bold tracking-tighter">Rate</p>
                              <p className="text-xs font-black text-emerald-400">${employee.hourlyRate}/hr</p>
                            </div>
                            <Badge className="text-[9px] h-5 bg-white/10 hover:bg-white/20 border-none text-white font-bold uppercase">
                              {employee.status}
                            </Badge>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </div>

            {/* Quick Insights / Action Card */}
            <Card className="bg-primary/5 border-primary/10 overflow-hidden relative">
              <div className="absolute top-0 right-0 p-8 opacity-10">
                <Activity className="h-24 w-24 text-primary" />
              </div>
              <CardContent className="p-6 flex flex-col md:flex-row items-center justify-between gap-6 relative z-10">
                <div className="space-y-1 text-center md:text-left">
                  <h3 className="text-lg font-bold text-primary">Workforce Health</h3>
                  <p className="text-sm text-muted-foreground max-w-md">
                    Agents are currently operating at <span className="text-foreground font-bold italic text-emerald-600">84% efficiency</span>. 
                    Tokens are being burned primarily by the <span className="font-bold">Growth Team</span>.
                  </p>
                </div>
                <div className="flex gap-3">
                  <Badge variant="secondary" className="h-10 px-4 gap-2 text-xs font-bold border-primary/20 bg-white">
                    <TrendingUp className="h-4 w-4 text-emerald-500" />
                    +4.2% EOD
                  </Badge>
                  <button className="h-10 px-6 bg-primary text-primary-foreground rounded-lg text-xs font-bold shadow-lg shadow-primary/20 hover:opacity-90 transition-all flex items-center gap-2">
                    Optimize Costs <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Live Activity Feed Column */}
          <div className="lg:col-span-4 flex flex-col h-full">
            <Card className="flex flex-col h-full border-border/60 shadow-sm overflow-hidden">
              <CardHeader className="pb-4 border-b border-border/40 bg-muted/30">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg font-bold tracking-tight">Live activity</CardTitle>
                    <CardDescription className="text-xs">Real-time pulse from the edge.</CardDescription>
                  </div>
                  <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-emerald-500/10 text-[10px] font-black text-emerald-600 border border-emerald-500/20">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    LIVE
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0 flex-1 flex flex-col">
                <ScrollArea className="flex-1 h-[520px]">
                  <div className="divide-y divide-border/30">
                    {ACTIVITIES.map((activity) => (
                      <div key={activity.id} className="p-4 hover:bg-muted/30 transition-all cursor-default flex gap-4 group">
                        <div className={cn(
                          "mt-0.5 p-2 rounded-xl h-fit shadow-sm transition-transform group-hover:scale-110",
                          activity.sourceType === 'sprint' ? "bg-blue-100 text-blue-600" :
                          activity.sourceType === 'team' ? "bg-purple-100 text-purple-600" :
                          activity.sourceType === 'workflow' ? "bg-amber-100 text-amber-600" :
                          "bg-slate-100 text-slate-600"
                        )}>
                          <activity.icon className="h-4 w-4" />
                        </div>
                        <div className="flex-1 space-y-1.5">
                          <div className="flex items-center justify-between gap-2">
                            <Badge variant="secondary" className="text-[9px] font-black uppercase tracking-widest py-0 px-1.5 h-4 bg-muted border-none">
                              {activity.source}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground font-bold font-mono">{activity.time}</span>
                          </div>
                          <div className="text-sm leading-snug font-medium text-foreground/90 line-clamp-2 prose prose-sm dark:prose-invert max-w-none">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{activity.message}</ReactMarkdown>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
                <div className="p-4 bg-muted/10 border-t border-border/40">
                  <button className="w-full text-[10px] font-black py-3 rounded-lg hover:bg-muted transition-all text-muted-foreground uppercase tracking-[0.2em] border border-border/50">
                    Full Audit Log
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>

        </div>
      </div>
    </div>
  );
}
