import React from 'react';
import { motion, useScroll, useTransform } from 'motion/react';
import { cn } from '@/lib/utils';

const cards = [
  {
    title: "1. Collaborative Planning",
    description: "Work with AI employees to define roadmaps, PRDs, and execution plans. They understand context and align with your goals.",
    color: "bg-white",
    icon: "📋",
  },
  {
    title: "2. Autonomous Execution",
    description: "Assign tasks and watch as your AI team executes workflows across your tool stack. From code commits to customer support.",
    color: "bg-[#F8F9FA]",
    icon: "⚡",
  },
  {
    title: "3. Tool & File Integration",
    description: "Your AI employees have access to the same tools you do. They can read docs, write code, and interact with APIs seamlessly.",
    color: "bg-[#F1F3F5]",
    icon: "🛠️",
  },
  {
    title: "4. Real-time Oversight",
    description: "Monitor every action in real-time. Full audit trails, session logs, and cost tracking for complete transparency.",
    color: "bg-[#E9ECEF]",
    icon: "👁️",
  },
];

export function StickyCardsSection() {
  return (
    <section className="relative bg-white py-24 px-6 sm:px-8 lg:px-10">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col lg:flex-row gap-16 lg:gap-24">
          <div className="lg:w-1/2 lg:sticky lg:top-32 lg:h-fit">
            <div className="inline-flex items-center rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-600 ring-1 ring-inset ring-zinc-200 mb-6">
              Core Capabilities
            </div>
            <h2 className="text-[32px] font-medium tracking-[-0.02em] leading-[1.2] text-zinc-950 sm:text-[40px]">
              Operating system for autonomous work
            </h2>
            <p className="mt-6 text-[16px] leading-7 text-zinc-600 max-w-xl">
              Worklone provides the infrastructure for AI employees to function as productive team members. From planning to execution, everything happens in one unified environment.
            </p>
            
            <div className="mt-10 flex flex-wrap gap-4">
               <div className="flex items-center gap-2 text-sm font-medium text-zinc-900">
                 <div className="h-1.5 w-1.5 rounded-full bg-zinc-950" />
                 Context Aware
               </div>
               <div className="flex items-center gap-2 text-sm font-medium text-zinc-900">
                 <div className="h-1.5 w-1.5 rounded-full bg-zinc-950" />
                 Tool Integration
               </div>
               <div className="flex items-center gap-2 text-sm font-medium text-zinc-900">
                 <div className="h-1.5 w-1.5 rounded-full bg-zinc-950" />
                 Full Transparency
               </div>
            </div>
          </div>

          <div className="lg:w-1/2 space-y-12 pb-24">
            {cards.map((card, index) => (
              <Card key={index} card={card} index={index} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function Card({ card, index }: { card: typeof cards[0]; index: number }) {
  const ref = React.useRef(null);
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ duration: 0.6, delay: 0.1 }}
      style={{
        top: `${120 + index * 40}px`,
      }}
      className={cn(
        "sticky h-[380px] w-full rounded-[40px] p-10 flex flex-col justify-between border border-black/[0.08] shadow-[0_8px_30px_rgb(0,0,0,0.04)] group",
        card.color
      )}
    >
      <div>
        <div className="h-10 w-10 rounded-xl bg-white shadow-sm border border-black/5 flex items-center justify-center text-xl mb-6">
          {card.icon}
        </div>
        <h3 className="text-lg font-medium tracking-tight text-zinc-950">{card.title}</h3>
        <p className="mt-4 text-zinc-600 leading-relaxed text-[15px]">{card.description}</p>
      </div>
      
      <div className="mt-auto pt-8 border-t border-black/[0.04]">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-zinc-400">0{index + 1}</span>
          <div className="h-8 w-8 rounded-full border border-black/10 flex items-center justify-center group-hover:bg-zinc-950 group-hover:text-white transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
