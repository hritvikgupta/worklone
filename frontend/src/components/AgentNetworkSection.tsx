import React from 'react';
import { motion } from 'motion/react';
import { cn } from '@/lib/utils';

const flows = [
  {
    title: "Feature Delivery",
    lines: [
      "M 175 140 L 175 155 Q 175 160 170 160 L 90 160 Q 80 160 80 170 L 80 180",
      "M 150 250 L 220 250",
      "M 80 320 L 80 335 Q 80 340 75 340 L 65 340 Q 60 340 60 345 L 60 360",
      "M 80 320 L 80 335 Q 80 340 85 340 L 205 340 Q 210 340 210 345 L 210 360"
    ],
    nodes: [
      { id: 'top', label: 'Engineer', sub: 'MoltBot', status: 'Running', dot: 'bg-emerald-400', color: 'text-emerald-400', icon: '/employees/men_1.png', left: 105, top: 0 },
      { id: 'midL', label: 'Tech Lead', sub: 'Claude Code', status: 'Running', dot: 'bg-emerald-400', color: 'text-emerald-400', icon: 'https://cdn.simpleicons.org/anthropic/white', iconBg: 'bg-rose-500', left: 10, top: 180 },
      { id: 'midR', label: 'PR Reviewer', sub: 'Devin', status: 'Running', dot: 'bg-emerald-400', color: 'text-emerald-400', icon: 'https://cdn.simpleicons.org/github/white', iconBg: 'bg-blue-500', left: 220, top: 180 },
      { id: 'botL', label: 'FE Dev', sub: 'Claude Code', status: 'Fixing..', dot: 'bg-blue-400', color: 'text-blue-400', icon: 'https://cdn.simpleicons.org/react/white', iconBg: 'bg-sky-500', left: -10, top: 360 },
      { id: 'botR', label: 'BE Dev', sub: 'Manus', status: 'Running', dot: 'bg-emerald-400', color: 'text-emerald-400', icon: 'https://cdn.simpleicons.org/nodedotjs/white', iconBg: 'bg-zinc-800', left: 140, top: 360 }
    ]
  },
  {
    title: "Content Engine",
    lines: [
      "M 60 140 L 60 155 Q 60 160 65 160 L 175 160 Q 180 160 180 165 L 180 180",
      "M 300 140 L 300 155 Q 300 160 295 160 L 185 160 Q 180 160 180 165 L 180 180",
      "M 180 320 L 180 335 Q 180 340 175 340 L 65 340 Q 60 340 60 345 L 60 360",
      "M 180 320 L 180 335 Q 180 340 185 340 L 295 340 Q 300 340 300 345 L 300 360"
    ],
    nodes: [
      { id: 'topL', label: 'Strategist', sub: 'ChatGPT', status: 'Running', dot: 'bg-emerald-400', color: 'text-emerald-400', icon: '/employees/women_1.png', left: -10, top: 0 },
      { id: 'topR', label: 'SEO Expert', sub: 'Surfer', status: 'Running', dot: 'bg-emerald-400', color: 'text-emerald-400', icon: 'https://cdn.simpleicons.org/google/white', iconBg: 'bg-blue-600', left: 230, top: 0 },
      { id: 'mid', label: 'Editor', sub: 'Claude', status: 'Running', dot: 'bg-emerald-400', color: 'text-emerald-400', icon: 'https://cdn.simpleicons.org/anthropic/white', iconBg: 'bg-rose-500', left: 110, top: 180 },
      { id: 'botL', label: 'Copywriter', sub: 'Jasper', status: 'Drafting..', dot: 'bg-blue-400', color: 'text-blue-400', icon: 'https://cdn.simpleicons.org/notion/white', iconBg: 'bg-zinc-800', left: -10, top: 360 },
      { id: 'botR', label: 'Fact Checker', sub: 'Perplexity', status: 'Pending', dot: 'bg-zinc-500', color: 'text-zinc-400', icon: 'https://cdn.simpleicons.org/perplexity/white', iconBg: 'bg-teal-500', left: 230, top: 360 }
    ]
  },
  {
    title: "Growth Campaign",
    lines: [
      "M 150 70 L 170 70 Q 180 70 180 80 L 180 150 Q 180 160 190 160 L 210 160",
      "M 210 160 L 190 160 Q 180 160 180 170 L 180 240 Q 180 250 170 250 L 150 250",
      "M 150 250 L 170 250 Q 180 250 180 260 L 180 330 Q 180 340 190 340 L 210 340",
      "M 210 340 L 190 340 Q 180 340 180 350 L 180 420 Q 180 430 170 430 L 150 430"
    ],
    nodes: [
      { id: '1', label: 'Analyst', sub: 'Looker', status: 'Running', dot: 'bg-emerald-400', color: 'text-emerald-400', icon: '/employees/men_2.png', left: 10, top: 0 },
      { id: '2', label: 'Growth Lead', sub: 'Mira', status: 'Reviewing', dot: 'bg-blue-400', color: 'text-blue-400', icon: 'https://cdn.simpleicons.org/googleanalytics/white', iconBg: 'bg-amber-500', left: 210, top: 90 },
      { id: '3', label: 'Reviewer', sub: 'Katy', status: 'Running', dot: 'bg-emerald-400', color: 'text-emerald-400', icon: '/employees/women_2.png', left: 10, top: 180 },
      { id: '4', label: 'Campaigns', sub: 'HubSpot', status: 'Pending', dot: 'bg-zinc-500', color: 'text-zinc-400', icon: 'https://cdn.simpleicons.org/hubspot/white', iconBg: 'bg-orange-500', left: 210, top: 270 },
      { id: '5', label: 'Ads Opt.', sub: 'Meta', status: 'Pending', dot: 'bg-zinc-500', color: 'text-zinc-400', icon: 'https://cdn.simpleicons.org/meta/white', iconBg: 'bg-blue-700', left: 10, top: 360 }
    ]
  }
];

function TreeFlow({ flow, index }: { flow: typeof flows[0], index: number }) {
  return (
    <div className="flex flex-col items-center">
      <motion.div 
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: index * 0.2 }}
        className="text-white/50 text-[12px] font-semibold uppercase tracking-widest mb-10"
      >
        {flow.title}
      </motion.div>
      
      <div className="relative w-[360px] h-[520px] shrink-0 scale-90 sm:scale-100">
        {/* SVG Connecting Paths */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-0 overflow-visible">
          {flow.lines.map((linePath, i) => (
            <motion.path 
              key={i}
              initial={{ pathLength: 0, opacity: 0 }}
              whileInView={{ pathLength: 1, opacity: 0.5 }}
              viewport={{ once: true }}
              transition={{ duration: 1, delay: index * 0.2 + 0.2 + (i * 0.2) }}
              d={linePath}
              stroke="white" strokeWidth="1.5" strokeDasharray="4 4" fill="none" 
            />
          ))}
        </svg>

        {/* Nodes */}
        {flow.nodes.map((node, i) => (
          <motion.div
            key={node.id}
            initial={{ opacity: 0, scale: 0.9, y: 10 }}
            whileInView={{ opacity: 1, scale: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: index * 0.2 + i * 0.1 }}
            className="absolute w-[140px] h-[140px] bg-white/10 backdrop-blur-xl border border-white/20 rounded-[28px] p-3 flex flex-col items-center justify-center shadow-[0_15px_30px_rgba(0,0,0,0.2)] hover:bg-white/15 transition-colors z-10"
            style={{ left: node.left, top: node.top }}
          >
            <div className={cn("w-10 h-10 rounded-[14px] border border-white/10 shadow-md mb-2 flex items-center justify-center overflow-hidden shrink-0 transition-transform hover:scale-105", node.iconBg || "bg-white/5")}>
              <img src={node.icon} alt={node.label} className={cn("object-cover", node.iconBg ? "w-5 h-5 opacity-90" : "w-full h-full")} />
            </div>
            
            <h3 className="text-white font-medium text-[13px] leading-tight mb-0.5 truncate w-full text-center">{node.label}</h3>
            <div className="text-white/60 text-[11px] mb-auto font-medium truncate w-full text-center">{node.sub}</div>
            
            <div className={cn("flex items-center justify-center gap-1.5 text-[11px] font-medium mt-1.5 w-full", node.color)}>
              <div className={cn("w-1.5 h-1.5 rounded-full shrink-0", node.dot, (node.status.includes('Running') || node.status.includes('ing')) && node.status !== 'Pending' ? "animate-pulse" : "")} />
              <span className="truncate">{node.status}</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

export function AgentNetworkSection() {
  return (
    <section className="relative py-32 px-4 sm:px-8 lg:px-10 overflow-hidden bg-[#111111] border-t border-white/5">
      <div className="relative max-w-[1400px] mx-auto z-10">
        <div className="text-center mb-24">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-[32px] font-normal tracking-tight text-white sm:text-[40px] mb-4"
          >
            Multi-agent collaboration
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-[16px] text-zinc-400 max-w-2xl mx-auto font-light"
          >
            Deploy coordinated teams of specialized agents. They break down tasks, delegate work, and collaborate to deliver complete features autonomously.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-16 lg:gap-4 justify-items-center">
          {flows.map((flow, index) => (
            <TreeFlow key={flow.title} flow={flow} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}
