import React from 'react';
import { AlertTriangle, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

const MEMORY_STREAM = [
  { id: 'm1', from: 'SDR-Alpha', to: 'CMO-Nexus', message: 'Leads from the "AI Tools" segment are asking about SOC2 compliance. We need collateral.', time: '10:42 AM' },
  { id: 'm2', from: 'Data-Miner', to: 'SDR-Alpha', message: 'Enriched 450 leads. 20% have recently changed jobs. Prioritize these.', time: '10:15 AM' },
  { id: 'm3', from: 'Support-Bot-1', to: 'Global', message: 'Encountered unhandled exception in Zendesk API integration. Halting operations.', time: '09:30 AM', isError: true },
  { id: 'm4', from: 'CMO-Nexus', to: 'SDR-Alpha', message: 'Published new SOC2 one-pager. Share with enterprise leads.', time: '10:50 AM' },
  { id: 'm5', from: 'Data-Miner', to: 'CMO-Nexus', message: 'Identified 150 high-intent accounts for LinkedIn targeting.', time: '11:15 AM' },
];

export function MemoryGraph() {
  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-muted-foreground" />
            Cross-Agent Memory Stream
          </h1>
        </div>

        {/* Memory Cards */}
        <div className="bg-card border border-border rounded-xl p-1 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <div className="max-h-[600px] overflow-y-auto p-4 space-y-4">
            {MEMORY_STREAM.map(msg => (
              <div key={msg.id} className="flex space-x-3">
                <div className="mt-1">
                  {msg.isError ? (
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                  ) : (
                    <MessageSquare className="w-4 h-4 text-emerald-600" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-baseline space-x-2">
                    <span className="text-sm font-medium text-foreground">{msg.from}</span>
                    <span className="text-xs text-muted-foreground">→</span>
                    <span className="text-sm font-medium text-muted-foreground">{msg.to}</span>
                    <span className="text-xs text-muted-foreground font-mono ml-auto">{msg.time}</span>
                  </div>
                  <p className={cn(
                    "text-sm mt-1 leading-relaxed",
                    msg.isError ? "text-red-600" : "text-muted-foreground"
                  )}>
                    {msg.message}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
