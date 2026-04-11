import React, { useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
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
import { ScheduledWorkflowsPage } from './components/pages/ScheduledWorkflowsPage';
import { AgentFilesPage } from './components/pages/AgentFilesPage';
import { AgentsPage } from './components/pages/AgentsPage';
import { SkillLibraryPage } from './components/pages/SkillLibraryPage';

function AuthenticatedShell() {
  const location = useLocation();
  const [isAIOpen, setIsAIOpen] = useState(false);

  const showKatyToggle = location.pathname !== '/chat';

  return (
    <div className="flex h-screen bg-[#f7f7f5] font-sans text-zinc-900 antialiased overflow-hidden">
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
            'flex-1 overflow-y-auto bg-white relative z-20 transition-shadow duration-300 shadow-none',
            isAIOpen && 'shadow-[0_20px_50px_rgba(0,0,0,0.1)] border border-zinc-200/50'
          )}
        >
          {showKatyToggle && (
            <div className="fixed bottom-6 right-6 z-30">
              <Button
                onClick={() => setIsAIOpen((open) => !open)}
                className={cn(
                  'h-11 rounded-full px-5 text-sm font-semibold transition-all shadow-sm border',
                  isAIOpen
                    ? 'bg-white text-zinc-900 border-zinc-200 hover:bg-zinc-50'
                    : 'bg-zinc-900 text-white border-transparent hover:bg-zinc-800'
                )}
              >
                Katy
              </Button>
            </div>
          )}

          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<ChatView />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/current-sprint" element={<CurrentSprintPage />} />
            <Route path="/scheduled-workflows" element={<Navigate to="/workflows" replace />} />
            <Route path="/workflows" element={<ScheduledWorkflowsPage />} />
            <Route path="/agent-files" element={<AgentFilesPage />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/skill-library" element={<SkillLibraryPage />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </motion.main>

        <AnimatePresence>
          {isAIOpen && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 384, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="shrink-0 h-full overflow-hidden z-10"
            >
              <div className="w-96 h-full p-4 pl-0">
                <AIAssistant onClose={() => setIsAIOpen(false)} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function App() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
        <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 bg-zinc-900 rounded-2xl flex items-center justify-center mx-auto mb-4 animate-pulse">
              <div className="w-8 h-8 rounded-full bg-white/90" />
            </div>
            <p className="text-zinc-500">Loading...</p>
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
