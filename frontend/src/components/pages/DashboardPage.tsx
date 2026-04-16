import React, { useEffect, useState } from 'react';
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
  TrendingUp,
  Plus,
  Loader2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import useEmblaCarousel from 'embla-carousel-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { listEmployees, EmployeeDetail } from '@/src/api/employees';
import { getDashboardStats, getDashboardActivity, DashboardStat, DashboardActivity } from '@/src/api/dashboard';

const STAT_ICONS: Record<string, any> = {
  "Token Burn": Coins,
  "Expenditure": DollarSign,
  "Total Uptime": Clock
};

const ACTIVITY_ICONS: Record<string, any> = {
  "sprint": Zap,
  "team": Users,
  "workflow": GitBranch,
  "task": MessageSquare
};

export function DashboardPage() {
  const navigate = useNavigate();
  const [emblaRef] = useEmblaCarousel({ align: 'start', containScroll: 'trimSnaps', dragFree: true, slidesToScroll: 1 });
  
  const [employees, setEmployees] = useState<EmployeeDetail[]>([]);
  const [stats, setStats] = useState<DashboardStat[]>([]);
  const [activities, setActivities] = useState<DashboardActivity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [empData, statsData, actData] = await Promise.all([
          listEmployees(),
          getDashboardStats(),
          getDashboardActivity()
        ]);
        setEmployees(empData);
        setStats(statsData);
        setActivities(actData);
      } catch (error) {
        console.error("Failed to load dashboard data", error);
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-background">
      <div className="max-w-6xl mx-auto p-6 space-y-6 animate-in fade-in duration-500">
        
        {/* Compact Header */}
        <div className="flex items-center justify-between pb-2 border-b border-border/10">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Global Overview</h1>
            <p className="text-sm text-muted-foreground">System healthy • 84% Efficiency</p>
          </div>
          <Button size="sm" className="h-9 gap-2 font-semibold shadow-sm">
            <Plus className="h-4 w-4" />
            Provision Agent
          </Button>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
          {stats.map((stat) => {
            const Icon = STAT_ICONS[stat.title] || Activity;
            return (
              <Card key={stat.title} className="shadow-none border-border/60">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-4 px-4">
                  <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{stat.title}</CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground/40" />
                </CardHeader>
                <CardContent className="px-4 pb-4">
                  <div className="flex items-baseline gap-2">
                    <div className="text-2xl font-bold tracking-tight">{stat.value}</div>
                    <Badge variant="outline" className="text-[10px] h-4 px-1.5 border-emerald-500/20 text-emerald-600 bg-emerald-500/5">
                      {stat.trend}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5">{stat.description}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Workforce Section */}
        <div className="space-y-3 pt-2 w-full overflow-hidden">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
              <Users className="h-4 w-4 text-primary" />
              Active Workforce
            </h2>
            <button 
              onClick={() => navigate('/agents')}
              className="text-xs font-bold text-primary hover:underline flex items-center gap-1"
            >
              View All <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          
          <div className="relative w-full">
            <div className="flex gap-4 overflow-x-auto pb-4 pt-1 px-1 scrollbar-hide snap-x snap-mandatory touch-pan-x">
              {employees.length === 0 ? (
                <div className="text-sm text-muted-foreground italic px-2 py-4">No employees provisioned yet.</div>
              ) : employees.map((employee) => (
                <div key={employee.id} className="snap-start shrink-0">
                  <Card className="w-[180px] aspect-square relative group overflow-hidden border-border/60 hover:border-primary/50 transition-all shadow-sm">
                    <CardContent className="p-0 h-full">
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent z-10" />
                      <img 
                        src={employee.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${employee.name}`} 
                        alt={employee.name} 
                        className="h-full w-full object-cover pointer-events-none" 
                      />
                      <div className="absolute bottom-0 left-0 right-0 p-3 z-20 text-white">
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <span className={cn("h-1.5 w-1.5 rounded-full", employee.status === 'working' ? "bg-emerald-400" : employee.status === 'idle' ? "bg-amber-400" : "bg-slate-400")} />
                          <p className="text-sm font-bold truncate">{employee.name}</p>
                        </div>
                        <p className="text-[10px] text-white/70 truncate font-medium mb-2">{employee.role}</p>
                        <div className="flex items-center justify-between border-t border-white/20 pt-2">
                          <p className="text-xs font-bold text-emerald-400">${55}/hr</p>
                          <Badge className="text-[9px] h-4 bg-white/10 border-none text-white font-bold uppercase">{employee.status}</Badge>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ))}
            </div>
            {employees.length > 0 && (
              <div className="absolute top-0 right-0 bottom-4 w-12 bg-gradient-to-l from-background via-background/20 to-transparent pointer-events-none z-30" />
            )}
          </div>
        </div>

        {/* Live Activity Section */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              Live activity
            </h2>
          </div>
          <Card className="shadow-none border-border/60 overflow-hidden bg-card/20">
            <div className="divide-y divide-border/40">
              {activities.length === 0 ? (
                <div className="p-6 text-center text-sm text-muted-foreground italic">No recent activity detected.</div>
              ) : activities.map((activity) => {
                const Icon = ACTIVITY_ICONS[activity.sourceType] || Activity;
                return (
                  <div key={activity.id} className="p-4 hover:bg-muted/30 transition-all flex items-center gap-4">
                    <div className={cn(
                      "p-2 rounded-lg", 
                      activity.color === 'blue' ? "bg-blue-500/10 text-blue-600" : 
                      activity.color === 'purple' ? "bg-purple-500/10 text-purple-600" : 
                      activity.color === 'amber' ? "bg-amber-500/10 text-amber-600" : 
                      "bg-slate-500/10 text-slate-600"
                    )}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 flex items-center justify-between">
                      <div>
                        <Badge variant="outline" className="text-[10px] font-bold uppercase tracking-tight h-4 mb-1 border-muted-foreground/20 text-muted-foreground">{activity.source}</Badge>
                        <div className="text-sm font-medium text-foreground/90 line-clamp-2 prose prose-sm dark:prose-invert">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{activity.message}</ReactMarkdown>
                        </div>
                      </div>
                      <span className="text-[11px] text-muted-foreground font-bold">{activity.time}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

      </div>
    </div>
  );
}
