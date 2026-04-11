import React from 'react';
import { Activity, ShieldAlert, DollarSign } from 'lucide-react';
import { Area, AreaChart, ResponsiveContainer, Tooltip } from 'recharts';
import { cn } from '@/lib/utils';

const SPEND_DATA = [
  { time: '00:00', spend: 12 }, { time: '04:00', spend: 25 },
  { time: '08:00', spend: 45 }, { time: '12:00', spend: 80 },
  { time: '16:00', spend: 110 }, { time: '20:00', spend: 145 },
  { time: '24:00', spend: 160 },
];

export function Dashboard() {
  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Top Header */}
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-xl font-semibold text-zinc-900">Global Overview</h1>
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              <span className="text-sm font-medium text-zinc-500">System Healthy</span>
            </div>
            <div className="h-4 w-px bg-zinc-200"></div>
            <div className="text-sm font-medium">
              <span className="text-zinc-500">Total Spend (24h): </span>
              <span className="text-zinc-900">$245.70</span>
              <span className="text-zinc-500"> / $370.00</span>
            </div>
          </div>
        </div>

        {/* Top Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard
            title="Active Agents"
            value="2"
            subtext="Out of 4 total deployed"
            icon={Activity}
            trend="+1 since yesterday"
          />
          <StatCard
            title="Pending Approvals"
            value="3"
            subtext="Requires human intervention"
            icon={ShieldAlert}
            trend="Action needed"
            trendColor="text-amber-600"
          />
          <div className="bg-white border border-zinc-100 rounded-xl p-5 flex flex-col shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-zinc-500">API Spend Velocity</h3>
              <DollarSign className="w-4 h-4 text-zinc-400" />
            </div>
            <div className="flex-1 min-h-[60px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={SPEND_DATA}>
                  <defs>
                    <linearGradient id="colorSpend" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#fff', borderColor: '#e4e4e7', color: '#3f3f46' }}
                    itemStyle={{ color: '#10b981' }}
                  />
                  <Area type="monotone" dataKey="spend" stroke="#10b981" fillOpacity={1} fill="url(#colorSpend)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, subtext, icon: Icon, trend, trendColor = "text-zinc-500" }: any) {
  return (
    <div className="bg-white border border-zinc-100 rounded-xl p-5 flex flex-col justify-between shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-sm font-medium text-zinc-500">{title}</h3>
          <div className="text-2xl font-semibold text-zinc-900 mt-1">{value}</div>
        </div>
        <div className="p-2 bg-zinc-50 rounded-lg">
          <Icon className="w-5 h-5 text-zinc-500" />
        </div>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-zinc-400">{subtext}</span>
        <span className={trendColor}>{trend}</span>
      </div>
    </div>
  );
}
