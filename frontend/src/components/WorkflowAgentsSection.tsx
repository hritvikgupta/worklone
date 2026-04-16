import React from 'react';
import { motion } from 'motion/react';
import { Mail, MessageSquare, Github, Calendar, Database, Shield, Zap, ArrowRight, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';

const agents = [
  {
    name: "Gmail Agent",
    icon: Mail,
    color: "text-red-500",
    bg: "bg-red-50",
    description: "Manages email communications, drafts replies, and organizes threads.",
    tasks: ["Draft outreach", "Summarize threads", "Label urgent"]
  },
  {
    name: "Slack Agent",
    icon: MessageSquare,
    color: "text-purple-500",
    bg: "bg-purple-50",
    description: "Monitors channels, handles quick queries, and keeps team updated.",
    tasks: ["Report status", "Answer FAQs", "Broadcast updates"]
  },
  {
    name: "GitHub Agent",
    icon: Github,
    color: "text-zinc-900",
    bg: "bg-zinc-100",
    description: "Reviews PRs, tracks issues, and manages release documentation.",
    tasks: ["Review code", "Triage issues", "Write changelogs"]
  },
  {
    name: "Calendar Agent",
    icon: Calendar,
    color: "text-blue-500",
    bg: "bg-blue-50",
    description: "Coordinates meetings, manages time blocks, and handles scheduling.",
    tasks: ["Book meetings", "Resolve conflicts", "Protect focus time"]
  },
];

export function WorkflowAgentsSection() {
  return (
    <section className="bg-white py-24 px-6 sm:px-8 lg:px-10 overflow-hidden">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-600 ring-1 ring-inset ring-zinc-200 mb-6"
          >
            <Zap className="h-3 w-3 fill-zinc-600" />
            <span>Powerful Automation</span>
          </motion.div>
          <h2 className="text-[36px] font-medium tracking-tight text-zinc-950 sm:text-[48px] leading-[1.1]">
            Create specialized workflow agents
          </h2>
          <p className="mt-6 text-lg text-zinc-600 max-w-2xl mx-auto">
            Assemble your workforce by deploying agents specialized for the tools you already use. Every agent is a building block in your company's automation engine.
          </p>
        </div>

        <div className="relative">
          {/* Connector Lines (Decorative) */}
          <div className="absolute top-1/2 left-0 w-full h-px bg-zinc-100 -translate-y-1/2 hidden lg:block" />
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative z-10">
            {agents.map((agent, index) => (
              <motion.div
                key={agent.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="group relative bg-white rounded-[24px] border border-black/[0.06] p-6 hover:border-black/[0.12] hover:shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all duration-300"
              >
                <div className={cn("h-12 w-12 rounded-2xl flex items-center justify-center mb-6 transition-transform group-hover:scale-110 duration-300", agent.bg)}>
                  <agent.icon className={cn("h-6 w-6", agent.color)} />
                </div>
                
                <h3 className="text-lg font-medium text-zinc-950 mb-2">{agent.name}</h3>
                <p className="text-sm text-zinc-500 leading-relaxed mb-6">
                  {agent.description}
                </p>

                <div className="space-y-2">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400 mb-2">Capabilities</div>
                  {agent.tasks.map((task) => (
                    <div key={task} className="flex items-center gap-2 text-xs text-zinc-600 bg-zinc-50 rounded-lg px-3 py-1.5">
                      <div className="h-1 w-1 rounded-full bg-zinc-300" />
                      {task}
                    </div>
                  ))}
                </div>

                <button className="mt-6 w-full flex items-center justify-center gap-2 rounded-xl border border-black/[0.06] py-2.5 text-xs font-medium text-zinc-600 hover:bg-zinc-50 transition-colors">
                  <Plus className="h-3 w-3" />
                  Add to Workflow
                </button>
              </motion.div>
            ))}
          </div>

          <motion.div 
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
            className="mt-16 flex flex-col items-center justify-center p-12 rounded-[32px] border-2 border-dashed border-zinc-100 bg-zinc-50/30"
          >
            <div className="h-16 w-16 rounded-full bg-white shadow-sm flex items-center justify-center mb-6 border border-zinc-100">
              <Plus className="h-8 w-8 text-zinc-400" />
            </div>
            <h3 className="text-xl font-medium text-zinc-950 mb-2">Custom Workflow Agent</h3>
            <p className="text-zinc-500 text-sm max-w-md text-center mb-8">
              Need something specific? Build a custom agent with its own unique set of skills and tool integrations.
            </p>
            <button className="inline-flex items-center gap-2 rounded-full bg-zinc-950 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-zinc-800">
              Configure Custom Agent
              <ArrowRight className="h-4 w-4" />
            </button>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
