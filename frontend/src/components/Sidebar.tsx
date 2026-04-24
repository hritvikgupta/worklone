import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, UserRound, BookOpen, MessageSquare, Zap, Github, CalendarClock, FolderOpen, LogOut, Sun, Moon, Briefcase, ChevronDown, Coins, DollarSign, Clock, Settings, Home as HomeIcon } from 'lucide-react';
import { SettingsModal } from '@/src/components/SettingsModal';
import { cn } from '@/lib/utils';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { useAuth } from '../contexts/AuthContext';
import { getDashboardStats, DashboardStat } from '@/src/api/dashboard';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';

const navItems = [
  { to: '/home', label: 'Home', icon: HomeIcon },
  { to: '/agents', label: 'Employees', icon: Briefcase },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  // { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  // { to: '/agent', label: 'Agent', icon: UserRound },
  { to: '/current-sprint', label: 'Current Sprint', icon: Zap },
  { to: '/workflows', label: 'Workflows', icon: CalendarClock },
  { to: '/agent-files', label: 'Agent Files', icon: FolderOpen },
  { to: '/teams', label: 'Teams', icon: Users },
  { to: '/skill-library', label: 'Skill Library', icon: BookOpen },
  { to: '/integrations', label: 'Integrations', icon: Github },
];

export function Sidebar() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isDark, setIsDark] = useState(() => {
    const stored = localStorage.getItem('theme');
    return stored ? stored === 'dark' : true;
  });

  const [stats, setStats] = useState<DashboardStat[]>([]);
  useEffect(() => {
    async function loadStats() {
      try {
        const data = await getDashboardStats();
        setStats(data);
      } catch (error) {
        console.error("Failed to load stats", error);
      }
    }
    loadStats();
  }, []);

  const STAT_ICONS: Record<string, any> = {
    "Token Burn": Coins,
    "Expenditure": DollarSign,
    "Total Uptime": Clock
  };

  const [settingsOpen, setSettingsOpen] = useState(false);
  const isCollapsed = location.pathname === '/chat';

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const toggleTheme = () => setIsDark((prev) => !prev);

  return (
    <div className={cn("border-r bg-sidebar flex flex-col h-screen sticky top-0 select-none transition-all duration-300", isCollapsed ? "w-[72px]" : "w-60")}>
      <NavLink to="/home" className={cn("p-4 flex items-center gap-2 hover:bg-sidebar-accent cursor-pointer transition-colors m-2 rounded-md", isCollapsed && "justify-center px-0")}>
        <img
          src={isDark ? "/brand/worklone-mark-white.png" : "/brand/worklone-mark-black.png"}
          alt="Worklone"
          className="h-5 w-auto shrink-0"
        />
        {!isCollapsed && <h1 className="font-semibold text-[15px] tracking-tight text-sidebar-foreground whitespace-nowrap overflow-hidden">Worklone</h1>}
      </NavLink>

      {!isCollapsed && (
        <div className="px-2 pb-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                className="w-full justify-between h-9 px-2 border-sidebar-border/70 bg-sidebar-accent/30 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground font-medium group"
              >
                <div className="flex items-center gap-2">
                  <LayoutDashboard className="w-4 h-4 shrink-0 text-sidebar-foreground/70 group-hover:text-sidebar-foreground transition-colors" />
                  <span>Project Stats</span>
                </div>
                <ChevronDown className="h-4 w-4 opacity-50 shrink-0" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-60" align="start">
              <DropdownMenuLabel className="text-xs text-muted-foreground uppercase tracking-wider">
                Quick Metrics
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              {stats.map(stat => {
                return (
                  <DropdownMenuItem key={stat.title} className="flex flex-col items-start gap-1.5 p-3">
                    <div className="flex flex-col w-full">
                      <span className="text-xs font-semibold text-foreground/90">{stat.title}</span>
                      <span className="text-[10px] text-muted-foreground leading-tight mt-0.5">{stat.description}</span>
                    </div>
                    <div className="flex items-center gap-2 w-full justify-between mt-1">
                      <span className="text-sm font-bold">{stat.value}</span>
                      {stat.trend && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full text-slate-500 bg-slate-500/10">
                          {stat.trend}
                        </span>
                      )}
                    </div>
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>
          <div className="px-2 mt-2">
            <Separator className="opacity-50" />
          </div>
        </div>
      )}

      <nav className="flex-1 px-2 py-2 space-y-0.5 overflow-hidden">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm font-medium transition-colors',
                isCollapsed && "justify-center px-0",
                isActive
                  ? 'bg-sidebar-accent text-sidebar-foreground'
                  : 'text-sidebar-foreground/90 hover:bg-sidebar-accent hover:text-sidebar-foreground'
              )
            }
            title={isCollapsed ? item.label : undefined}
          >
            {({ isActive }) => (
              <>
                <item.icon className={cn('w-4 h-4 shrink-0', isActive ? 'text-sidebar-foreground' : 'text-sidebar-foreground/75')} />
                {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">{item.label}</span>}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-2 mt-auto">
        <Separator className="mb-2 opacity-50" />
        <button
          onClick={() => setSettingsOpen(true)}
          title={isCollapsed ? 'Settings' : undefined}
          className={cn("w-full flex items-center gap-2 px-2 py-2 rounded-md text-sm font-medium text-sidebar-foreground/90 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors", isCollapsed && "justify-center px-0")}
        >
          <Settings className="w-4 h-4 shrink-0 text-sidebar-foreground/75" />
          {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">Settings</span>}
        </button>
        <button
          onClick={toggleTheme}
          title={isCollapsed ? (isDark ? 'Light Mode' : 'Dark Mode') : undefined}
          className={cn("w-full flex items-center gap-2 px-2 py-2 rounded-md text-sm font-medium text-sidebar-foreground/90 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors", isCollapsed && "justify-center px-0")}
        >
          {isDark ? <Sun className="w-4 h-4 shrink-0 text-sidebar-foreground/75" /> : <Moon className="w-4 h-4 shrink-0 text-sidebar-foreground/75" />}
          {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">{isDark ? 'Light Mode' : 'Dark Mode'}</span>}
        </button>
        <button
          onClick={() => {
            logout();
            navigate('/');
          }}
          title={isCollapsed ? 'Logout' : undefined}
          className={cn("w-full flex items-center gap-2 px-2 py-2 rounded-md text-sm font-medium text-sidebar-foreground/90 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors", isCollapsed && "justify-center px-0")}
        >
          <LogOut className="w-4 h-4 shrink-0 text-sidebar-foreground/75" />
          {!isCollapsed && <span className="whitespace-nowrap overflow-hidden">Logout</span>}
        </button>
      </div>
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
