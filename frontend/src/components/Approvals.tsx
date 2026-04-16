import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle2, Check, X, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Approval {
  id: string;
  agentId: string;
  agentName: string;
  action: string;
  context: string;
  risk: 'low' | 'medium' | 'high';
  time: string;
}

const INITIAL_APPROVALS: Approval[] = [
  {
    id: 'ap1', agentId: 'a1', agentName: 'SDR-Alpha',
    action: 'Send cold email to CEO of Acme Corp',
    context: 'Found recent funding news. Drafted highly aggressive pitch.',
    risk: 'high', time: '2 mins ago'
  },
  {
    id: 'ap2', agentId: 'a2', agentName: 'CMO-Nexus',
    action: 'Publish $500/day LinkedIn Ad Campaign',
    context: 'Targeting VP Engineering based on SDR insights.',
    risk: 'medium', time: '15 mins ago'
  },
  {
    id: 'ap3', agentId: 'a4', agentName: 'Data-Miner',
    action: 'Scrape 10,000 profiles from ZoomInfo',
    context: 'Approaching API rate limit. Requires budget override.',
    risk: 'low', time: '1 hour ago'
  }
];

export function Approvals() {
  const [approvals, setApprovals] = useState<Approval[]>(INITIAL_APPROVALS);

  const handleApprove = (id: string) => {
    setApprovals(prev => prev.filter(a => a.id !== id));
  };

  const handleDeny = (id: string) => {
    setApprovals(prev => prev.filter(a => a.id !== id));
  };

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-500" />
            Action Queue
          </h1>
          <span className="text-xs font-medium bg-muted text-foreground px-2 py-1 rounded-full">
            {approvals.length} Pending
          </span>
        </div>

        {/* Approval Cards */}
        <div className="space-y-3">
          <AnimatePresence>
            {approvals.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="bg-muted/50 border border-border border-border rounded-xl p-8 text-center"
              >
                <CheckCircle2 className="w-8 h-8 text-emerald-500/50 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">All caught up! No pending actions.</p>
              </motion.div>
            ) : (
              approvals.map(approval => (
                <motion.div
                  key={approval.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bg-card border border-border rounded-xl p-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)]"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-medium text-foreground bg-muted px-2 py-0.5 rounded">
                        {approval.agentName}
                      </span>
                      <span className="text-xs text-muted-foreground">{approval.time}</span>
                    </div>
                    <RiskBadge risk={approval.risk} />
                  </div>

                  <h4 className="text-sm font-medium text-foreground mb-1">{approval.action}</h4>
                  <p className="text-xs text-muted-foreground mb-4 leading-relaxed">{approval.context}</p>

                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleApprove(approval.id)}
                      className="flex-1 flex items-center justify-center space-x-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 py-1.5 rounded-lg text-xs font-medium transition-colors border border-emerald-200"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Approve</span>
                    </button>
                    <button
                      onClick={() => handleDeny(approval.id)}
                      className="flex-1 flex items-center justify-center space-x-1.5 bg-red-50 text-red-600 hover:bg-red-100 py-1.5 rounded-lg text-xs font-medium transition-colors border border-red-200"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Deny</span>
                    </button>
                  </div>
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function RiskBadge({ risk }: { risk: 'low' | 'medium' | 'high' }) {
  const config = {
    low: 'bg-emerald-50 text-emerald-700',
    medium: 'bg-amber-50 text-amber-700',
    high: 'bg-red-50 text-red-600',
  };
  return (
    <span className={cn("text-[10px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded", config[risk])}>
      {risk} Risk
    </span>
  );
}
