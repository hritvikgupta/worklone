import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, BookOpen, MessageSquare, Zap, Github, CalendarClock, FolderOpen, LogOut } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '../contexts/AuthContext';

const navItems = [
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/current-sprint', label: 'Current Sprint', icon: Zap },
  { to: '/workflows', label: 'Workflows', icon: CalendarClock },
  { to: '/agent-files', label: 'Agent Files', icon: FolderOpen },
  { to: '/agents', label: 'Employees', icon: Users },
  { to: '/skill-library', label: 'Skill Library', icon: BookOpen },
  { to: '/integrations', label: 'Integrations', icon: Github },
];

export function Sidebar() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="w-60 border-r bg-sidebar flex flex-col h-screen sticky top-0 select-none">
      <NavLink to="/dashboard" className="p-4 flex items-center gap-2 hover:bg-sidebar-accent cursor-pointer transition-colors m-2 rounded-md">
        <img
          src="/brand/worklone-mark-black.png"
          alt="Worklone"
          className="h-5 w-auto"
        />
        <h1 className="font-semibold text-[15px] tracking-tight text-sidebar-foreground">Worklone</h1>
      </NavLink>

      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-foreground'
                  : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground'
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon className={cn('w-4 h-4', isActive ? 'text-sidebar-foreground' : 'text-sidebar-foreground/50')} />
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-2 mt-auto">
        <Separator className="mb-2 opacity-50" />
        <button
          onClick={() => {
            logout();
            navigate('/');
          }}
          className="w-full flex items-center gap-2 px-2 py-2 rounded-md text-sm font-medium text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors"
        >
          <LogOut className="w-4 h-4 text-sidebar-foreground/50" />
          Logout
        </button>
      </div>
    </div>
  );
}
