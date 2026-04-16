import React from 'react';
import { motion } from 'motion/react';

const agents = [
  {
    name: "Support Agent",
    icons: [
      "https://cdn.simpleicons.org/notion/white",
      "https://cdn.simpleicons.org/github/white",
      "/slackicon.png"
    ],
    status: "Updated runbook"
  },
  {
    name: "Email Agent",
    icons: [
      "https://cdn.simpleicons.org/gmail/EA4333",
      "https://cdn.simpleicons.org/googlecalendar/4285F4"
    ],
    status: "Drafted reply to Sarah"
  },
  {
    name: "Slack Agent",
    icons: [
      "/slackicon.png",
      "https://cdn.simpleicons.org/googledocs/4285F4"
    ],
    status: "Synced channel topic"
  },
  {
    name: "SQL Agent",
    icons: [
      "https://cdn.simpleicons.org/supabase/3ECF8E",
      "https://cdn.simpleicons.org/googlesheets/34A853"
    ],
    status: "Optimized slow query"
  },
  {
    name: "Code Review Agent",
    icons: [
      "https://cdn.simpleicons.org/github/white",
      "https://cdn.simpleicons.org/linear/5E6AD2"
    ],
    status: "Approved PR #131"
  },
  {
    name: "Research Agent",
    icons: [
      "https://cdn.simpleicons.org/firebase/FFCA28",
      "https://cdn.simpleicons.org/notion/white"
    ],
    status: "Summarized findings"
  }
];

export function CreateWorkflowSection() {
  return (
    <section className="bg-[#111111] py-24 px-6 sm:px-8 lg:px-10 border-t border-white/5">
      <div className="max-w-[1200px] mx-auto">
        <div className="flex flex-col lg:flex-row gap-16 lg:gap-12 justify-between items-center lg:items-start">
          
          {/* Left Column */}
          <div className="w-full lg:w-[40%] flex flex-col justify-center">
            <div className="mb-6">
              <h2 className="text-[36px] font-medium text-white tracking-tight leading-tight">
                Generate workflows
              </h2>
            </div>
            
            <p className="text-[17px] text-zinc-300 leading-relaxed mb-6 max-w-md">
              Your agents have the intelligence. Now let them execute automatically across your entire tool stack.
            </p>
            
            <p className="text-[15px] text-zinc-400 leading-relaxed mb-10 max-w-md">
              Describe what you want to automate in plain English. Worklone will instantly generate a specialized, multi-step workflow combining the right agents, tools, and logic to handle the repetitive work autonomously.
            </p>
            
            <div>
              <button className="bg-white text-black text-[12px] font-bold tracking-widest px-6 py-3 uppercase hover:bg-zinc-200 transition-colors">
                LEARN MORE
              </button>
            </div>
          </div>
          
          {/* Right Column: Grid */}
          <div className="w-full lg:w-[60%] grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent, index) => (
              <motion.div 
                key={agent.name}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="bg-[#18181B] border border-white/5 rounded-md p-5 flex flex-col h-[180px] hover:border-white/10 transition-colors"
              >
                <div className="flex items-center justify-between mb-5">
                  <span className="text-[13px] font-mono text-zinc-100">{agent.name}</span>
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                </div>
                
                <div className="flex items-center gap-2 mb-auto">
                  {agent.icons.map((icon, i) => (
                    <div key={i} className="w-7 h-7 flex items-center justify-center">
                      <img src={icon} alt="icon" className="w-full h-full object-contain" />
                    </div>
                  ))}
                </div>
                
                <div className="text-[11px] font-mono text-zinc-500 mt-4">
                  {agent.status}
                </div>
              </motion.div>
            ))}
          </div>
          
        </div>
      </div>
    </section>
  );
}
