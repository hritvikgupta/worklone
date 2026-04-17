import React, { useState, useEffect } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useAuth } from './contexts/AuthContext';
import { LoginPage } from './components/LoginPage';
import { WaitlistPage } from './components/WaitlistPage';
import { LandingPage } from './components/LandingPage';
import { WhatIsWorklonePage } from './components/WhatIsWorklonePage';
import { IntegrationCallback } from './components/IntegrationCallback';
import { Sidebar } from './components/Sidebar';
import { AIAssistant } from './components/AIAssistant';
import { ChatView } from './components/ChatView';
import { Integrations } from './components/Integrations';
import { DashboardPage } from './components/pages/DashboardPage';
import { CurrentSprintPage } from './components/pages/CurrentSprintPage';
import { TeamsPage } from './components/pages/TeamsPage';
import { ScheduledWorkflowsPage } from './components/pages/ScheduledWorkflowsPage';
import { AgentFilesPage } from './components/pages/AgentFilesPage';
import { AgentsPage } from './components/pages/AgentsPage';
import { SkillLibraryPage } from './components/pages/SkillLibraryPage';

function AuthenticatedShell() {
  const location = useLocation();
  const [isAIOpen, setIsAIOpen] = useState(false);

  const showKatyToggle = location.pathname !== '/chat';

  return (
    <div className="flex h-screen bg-background text-foreground antialiased overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex overflow-hidden relative">
        <motion.main
          layout
          animate={{
            scale: isAIOpen ? 0.96 : 1,
            borderRadius: isAIOpen ? '24px' : '0px',
            margin: isAIOpen ? '16px' : '0px',
            marginRight: isAIOpen ? '8px' : '0px',
          }}
          transition={{
            type: 'spring',
            damping: 30,
            stiffness: 300,
            mass: 0.8,
          }}
          className={cn(
            'flex-1 overflow-hidden bg-card relative z-20 transition-shadow duration-300 shadow-none',
            isAIOpen && 'shadow-lg border border-border'
          )}
        >
          {showKatyToggle && (
            <div className="fixed bottom-6 right-6 z-30">
              <Button
                onClick={() => setIsAIOpen((open) => !open)}
                className={cn(
                  'h-11 rounded-full px-5 text-sm font-semibold transition-all shadow-sm',
                  isAIOpen
                    ? 'bg-card text-foreground border-border hover:bg-muted'
                    : 'bg-primary text-primary-foreground hover:bg-primary/90'
                )}
              >
                Talk
              </Button>
            </div>
          )}

          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<ChatView />} />
            {/* <Route path="/dashboard" element={<DashboardPage />} /> */}
            <Route path="/current-sprint" element={<CurrentSprintPage />} />
            <Route path="/teams" element={<TeamsPage />} />
            <Route path="/scheduled-workflows" element={<Navigate to="/workflows" replace />} />
            <Route path="/workflows" element={<ScheduledWorkflowsPage />} />
            <Route path="/agent-files" element={<AgentFilesPage />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/skill-library" element={<SkillLibraryPage />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </motion.main>

        {showKatyToggle && (
          <motion.div
            animate={{ width: isAIOpen ? 384 : 0, opacity: isAIOpen ? 1 : 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className={cn(
              "shrink-0 h-full overflow-hidden z-10",
              !isAIOpen && "pointer-events-none"
            )}
          >
            <div className="w-96 h-full p-4 pl-0">
              <AIAssistant onClose={() => setIsAIOpen(false)} />
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const { isAuthenticated, isLoading } = useAuth();

  // Centralize dark-mode toggling. Unauthenticated routes (landing, login,
  // waitlist) always render light so theme-variable classes inside embedded
  // dashboard/stepper components don't flip based on stale `.dark` state.
  useEffect(() => {
    const root = document.documentElement;
    if (!isAuthenticated) {
      root.classList.remove('dark');
      return;
    }
    const theme = localStorage.getItem('theme');
    if (theme === 'light') {
      root.classList.remove('dark');
    } else {
      root.classList.add('dark');
    }
  }, [isAuthenticated]);

  if (isLoading) {
    return (
        <div className="min-h-screen bg-background flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center mx-auto mb-4 animate-pulse">
              <div className="w-8 h-8 rounded-full bg-primary-foreground/90" />
            </div>
            <p className="text-muted-foreground">Loading...</p>
          </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/integrations/callback" element={<IntegrationCallback />} />
      {isAuthenticated ? (
        <Route path="/*" element={<AuthenticatedShell />} />
      ) : (
        <>
          <Route path="/" element={<LandingPage />} />
          <Route path="/what-is-worklone" element={<WhatIsWorklonePage />} />
          <Route path="/waitlist" element={<WaitlistPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </>
      )}
    </Routes>
  );
}
