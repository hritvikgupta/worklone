import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { CheckCircle2, Circle, Loader2, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const timelineSteps = [
  {
    id: 1,
    title: 'Fetched email thread',
    time: '2 seconds ago',
    status: 'completed',
    icon: CheckCircle2,
    color: 'text-emerald-500',
    detail: 'Retrieved "Urgent: Q3 Roadmap Update" from Product team inbox.'
  },
  {
    id: 2,
    title: 'Analyzing context & data',
    time: '1 second ago',
    status: 'completed',
    icon: CheckCircle2,
    color: 'text-emerald-500',
    detail: 'Extracted key action items, timeline constraints, and stakeholders.'
  },
  {
    id: 3,
    title: 'Writing summary',
    time: 'Just now',
    status: 'active',
    icon: Loader2,
    color: 'text-blue-500',
    detail: 'Drafting concise executive summary for the engineering channel...'
  },
  {
    id: 4,
    title: 'Updating Notion',
    time: 'Pending',
    status: 'pending',
    icon: Circle,
    color: 'text-zinc-300',
    detail: 'Will sync extracted action items to the Q3 Sprint board.'
  }
];

const promptText = "Can you review the urgent Q3 roadmap update from the product team inbox, summarize the key points, and sync the action items to our Notion sprint board?";

export function AgentProgressSection() {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    let i = 0;
    let interval: ReturnType<typeof setInterval>;
    
    const startTyping = () => {
      i = 0;
      setDisplayedText("");
      interval = setInterval(() => {
        setDisplayedText(promptText.slice(0, i));
        i++;
        if (i > promptText.length) {
          clearInterval(interval);
          setTimeout(startTyping, 5000);
        }
      }, 40);
    };
    
    startTyping();
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="bg-white py-32 px-6 sm:px-8 lg:px-10 overflow-hidden border-t border-black/[0.04]">
      <div className="max-w-[1100px] mx-auto">
        <div className="text-center mb-20">
          <h2 className="text-[32px] font-medium tracking-tight text-zinc-950 sm:text-[40px] mb-4">
            Assign work and train employees inside your workspace
          </h2>
          <p className="text-[16px] text-zinc-600 max-w-2xl mx-auto">
            Give employees natural-language tasks, let them learn your tools and operating context, and watch execution happen directly inside the systems your team already uses.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row items-center justify-center gap-8 lg:gap-6">
          
          {/* Left Column: Prompt Box */}
          <div className="w-full lg:w-[35%]">
            <div className="bg-white border border-black/10 rounded-[20px] p-6 shadow-sm relative flex items-center min-h-[100px]">
              <div className="absolute -top-2.5 left-6 bg-white px-2 text-[10px] font-bold uppercase tracking-widest text-zinc-400">
                User Request
              </div>
              <p className="text-[14px] leading-relaxed text-zinc-600 font-normal">
                {displayedText}
              </p>
            </div>
          </div>
          
          <ArrowRight className="w-6 h-6 text-zinc-300 hidden lg:block shrink-0" />

          {/* Center Column: Avatar */}
          <div className="flex items-center justify-center shrink-0">
            <div className="relative">
              <div className="absolute -inset-2 bg-emerald-500/10 rounded-full" />
              <img 
                src="/employees/women_1.png" 
                alt="Katy" 
                className="relative w-24 h-24 rounded-full border-4 border-white shadow-lg object-cover bg-zinc-50 z-10" 
              />
              <div className="absolute bottom-1 right-1 w-6 h-6 bg-emerald-500 border-[2px] border-white rounded-full shadow-sm z-20" />
            </div>
          </div>

          <ArrowRight className="w-6 h-6 text-zinc-300 hidden lg:block shrink-0" />

          {/* Right Column: Timeline (Inline) */}
          <div className="w-full lg:w-[40%] lg:pl-4">
            <div className="mb-8 flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-blue-50 border border-blue-100 flex items-center justify-center">
                <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
              </div>
              <div>
                <h3 className="text-[15px] font-semibold text-zinc-950">Katy <span className="text-zinc-500 font-normal">is executing workflow...</span></h3>
              </div>
            </div>

            <div className="relative">
              {/* Vertical Line */}
              <div className="absolute left-[11px] top-4 bottom-8 w-[2px] bg-zinc-100 rounded-full" />
              
              <div className="space-y-8">
                {timelineSteps.map((step, index) => (
                  <motion.div 
                    key={step.id}
                    initial={{ opacity: 0, x: 20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.15 }}
                    className="relative flex gap-6"
                  >
                    <div className="relative z-10 flex h-6 w-6 items-center justify-center bg-white shrink-0 mt-0.5">
                      {step.status === 'active' ? (
                        <step.icon className={cn("h-5 w-5 animate-spin", step.color)} />
                      ) : (
                        <step.icon className={cn(
                          "h-6 w-6 rounded-full", 
                          step.color, 
                          step.status === 'pending' ? 'fill-white stroke-zinc-200 border-2 border-transparent' : 'fill-emerald-50'
                        )} />
                      )}
                    </div>
                    
                    <div className={cn(
                      "flex flex-col",
                      step.status === 'pending' ? 'opacity-60' : 'opacity-100'
                    )}>
                      <div className="flex items-center justify-between gap-4 mb-1">
                        <h4 className={cn("text-[15px] font-semibold", step.status === 'pending' ? 'text-zinc-500' : 'text-zinc-900')}>
                          {step.title}
                        </h4>
                        <span className="text-[11px] text-zinc-400 font-medium whitespace-nowrap hidden sm:block">
                          {step.time}
                        </span>
                      </div>
                      <p className="text-[13px] text-zinc-500 leading-relaxed pr-4">
                        {step.detail}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
          
        </div>
      </div>
    </section>
  );
}
