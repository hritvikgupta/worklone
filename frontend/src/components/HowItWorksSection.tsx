"use client"

import React, { useRef, useState, useEffect } from 'react';
import {
  Stepper,
  StepperDescription,
  StepperIndicator,
  StepperItem,
  StepperNav,
  StepperSeparator,
  StepperTitle,
  StepperTrigger,
} from "@/components/reui/stepper"
import { CheckIcon, Mail, Code, Search, Database, Slack, Github, Calendar, Terminal, Bot, FileText, Settings, Layers } from 'lucide-react'
import { motion, AnimatePresence, useScroll, useTransform } from "motion/react"
import AI_Prompt from "./prompt-kit/AI_Prompt"
import { cn } from '@/lib/utils';

const steps = [
  { 
    title: "Create employee", 
    description: "Choose from predefined roles or customize your own AI employee with specific personalities and goals.",
  },
  { 
    title: "Equip with tools and skills", 
    description: "Connect Gmail, Slack, GitHub, and 100+ other tools to give them the capabilities they need.",
  },
  { 
    title: "Assign task", 
    description: "Give them a goal and watch them plan and execute autonomously using their assigned tools.",
  },
  { 
    title: "Create workflows", 
    description: "Set up recurring schedules or trigger-based automation for complex multi-step processes.",
  },
  { 
    title: "Monitor and chat", 
    description: "Stay in the loop, provide feedback, and collaborate with your AI coworkers in real-time.",
  },
]

// Typewriter hook for Step 1
const useTypewriter = (text: string, active: boolean) => {
  const [displayText, setDisplayText] = useState("");
  useEffect(() => {
    if (!active) {
      setDisplayText("");
      return;
    }
    let i = 0;
    const interval = setInterval(() => {
      setDisplayText(text.slice(0, i));
      i++;
      if (i > text.length) clearInterval(interval);
    }, 40);
    return () => clearInterval(interval);
  }, [text, active]);
  return displayText;
};

const SkillCard = ({ name, delay }: { name: string, delay: number }) => {
  const iconMap: Record<string, string> = {
    'Gmail': 'https://cdn.simpleicons.org/gmail/EA4333',
    'Slack': '/slackicon.png',
    'GitHub': 'https://cdn.simpleicons.org/github/181717',
    'Postgres': 'https://cdn.simpleicons.org/postgresql/4169E1',
    'Notion': 'https://cdn.simpleicons.org/notion/000000',
    'Linear': 'https://cdn.simpleicons.org/linear/5E6AD2',
    'Calendar': 'https://cdn.simpleicons.org/googlecalendar/4285F4',
    'Jira': 'https://cdn.simpleicons.org/jira/0052CC',
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, duration: 0.4 }}
      className="flex items-center gap-3 rounded-xl border border-black/5 bg-white p-3 shadow-sm hover:border-black/10 transition-colors"
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-50 overflow-hidden border border-black/5">
        <img 
          src={iconMap[name] || `https://cdn.simpleicons.org/${name.toLowerCase()}/black`} 
          alt={name} 
          className="h-5 w-5 object-contain" 
        />
      </div>
      <span className="text-[13px] font-medium text-zinc-700">{name}</span>
    </motion.div>
  );
};

const TaskCard = ({ icon: Icon, label, status, delay }: { icon: any, label: string, status: string, delay: number }) => (
  <motion.div
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay, duration: 0.5 }}
    className="w-full flex items-center justify-between gap-4 rounded-xl border border-black/5 bg-white p-4 shadow-sm"
  >
    <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-100 text-zinc-600">
            <Icon size={18} />
        </div>
        <div className="text-left">
            <div className="text-sm font-medium text-zinc-950">{label}</div>
            <div className="text-[11px] text-zinc-500 font-mono italic">{status}</div>
        </div>
    </div>
    <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
  </motion.div>
);

// Styled node exactly like AgentNetworkSection but adapted for light mode
const GraphNode = ({ label, sub, icon, iconBg, left, top, delay, status, color, dot }: any) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.9, y: 10 }}
    animate={{ opacity: 1, scale: 1, y: 0 }}
    transition={{ duration: 0.4, delay }}
    className="absolute w-[130px] h-[130px] bg-white/80 backdrop-blur-xl border border-black/10 rounded-[28px] p-3 flex flex-col items-center justify-center shadow-[0_10px_25px_rgba(0,0,0,0.05)] z-10"
    style={{ left, top }}
  >
    <div className={cn("w-9 h-9 rounded-[14px] border border-black/5 shadow-sm mb-2 flex items-center justify-center overflow-hidden shrink-0", iconBg || "bg-zinc-50")}>
      {typeof icon === 'string' ? <img src={icon} className="w-full h-full object-cover" /> : React.createElement(icon, { size: 18, className: "text-zinc-600" })}
    </div>
    <h3 className="text-zinc-950 font-medium text-[12px] leading-tight mb-0.5 truncate w-full text-center">{label}</h3>
    <div className="text-zinc-500 text-[10px] mb-auto font-medium truncate w-full text-center">{sub}</div>
    <div className={cn("flex items-center justify-center gap-1.5 text-[10px] font-medium mt-1.5 w-full", color || "text-emerald-600")}>
      <div className={cn("w-1.5 h-1.5 rounded-full shrink-0", dot || "bg-emerald-500 animate-pulse")} />
      <span className="truncate">{status || "Running"}</span>
    </div>
  </motion.div>
);

export function HowItWorksSection() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  const stepProgress = useTransform(scrollYProgress, [0, 1], [1, steps.length]);
  const [activeStep, setActiveStep] = useState(1);

  useEffect(() => {
    return stepProgress.on("change", (latest) => {
      setActiveStep(Math.round(latest));
    });
  }, [stepProgress]);

  const promptText = useTypewriter("I want an AI employee who can manage our product roadmap and sync with Jira every morning...", activeStep === 1);

  const renderRightSide = () => {
    switch (activeStep) {
      case 1:
        return (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-lg">
            <AI_Prompt 
              headerText="New Hire: Product Manager" 
              headerAction="Configuring..."
              placeholder="Describing role..."
              value={promptText}
              className="bg-transparent"
            />
          </motion.div>
        );
      case 2:
        return (
          <div className="grid grid-cols-2 gap-4 w-full max-w-md mx-auto">
            <SkillCard name="Gmail" delay={0.1} />
            <SkillCard name="Slack" delay={0.2} />
            <SkillCard name="GitHub" delay={0.3} />
            <SkillCard name="Postgres" delay={0.4} />
            <SkillCard name="Notion" delay={0.5} />
            <SkillCard name="Linear" delay={0.6} />
            <SkillCard name="Calendar" delay={0.7} />
            <SkillCard name="Jira" delay={0.8} />
          </div>
        );
      case 3:
        return (
          <div className="w-full max-w-md mx-auto space-y-4">
            <TaskCard icon={Search} label="Analyze Backlog" status="> scanning jira-project-v2..." delay={0.1} />
            <TaskCard icon={FileText} label="Draft PR Document" status="> generating notion specs..." delay={0.3} />
            <TaskCard icon={Code} label="Run Test Suite" status="> executing py-test-sandbox..." delay={0.5} />
            <TaskCard icon={Layers} label="Update Roadmap" status="> syncing cloud-dependencies..." delay={0.7} />
          </div>
        );
      case 4:
        return (
          <div className="relative w-[360px] h-[480px] scale-90 sm:scale-100 mx-auto">
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-0 overflow-visible">
                <motion.path 
                    d="M 180 140 L 180 155 Q 180 160 170 160 L 90 160 Q 80 160 80 170 L 80 180"
                    stroke="#18181b" strokeWidth="1.5" strokeDasharray="4 4" fill="none"
                    initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 0.15 }}
                    transition={{ duration: 1 }}
                />
                <motion.path 
                    d="M 180 140 L 180 155 Q 180 160 190 160 L 270 160 Q 280 160 280 170 L 280 180"
                    stroke="#18181b" strokeWidth="1.5" strokeDasharray="4 4" fill="none"
                    initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 0.15 }}
                    transition={{ duration: 1, delay: 0.2 }}
                />
                <motion.path 
                    d="M 80 320 L 80 335 Q 80 340 75 340 L 65 340 Q 60 340 60 345 L 60 360"
                    stroke="#18181b" strokeWidth="1.5" strokeDasharray="4 4" fill="none"
                    initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 0.15 }}
                    transition={{ duration: 1, delay: 0.4 }}
                />
                <motion.path 
                    d="M 80 320 L 80 335 Q 80 340 85 340 L 205 340 Q 210 340 210 345 L 210 360"
                    stroke="#18181b" strokeWidth="1.5" strokeDasharray="4 4" fill="none"
                    initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 0.15 }}
                    transition={{ duration: 1, delay: 0.6 }}
                />
            </svg>
            
            <GraphNode label="Lead Bot" sub="Supervisor" icon={Bot} left={115} top={0} delay={0.1} />
            <GraphNode label="Tech Lead" sub="Claude" icon="/employees/men_1.png" left={10} top={180} delay={0.3} />
            <GraphNode label="Researcher" sub="Perplexity" icon={Search} left={220} top={180} delay={0.5} />
            <GraphNode label="Engineer" sub="Manus" icon={Code} left={-10} top={360} delay={0.7} status="Coding.." dot="bg-blue-400" color="text-blue-600" />
            <GraphNode label="Action" sub="Slack" icon={Slack} left={140} top={360} delay={0.9} />
          </div>
        );
      case 5:
        return (
          <div className="w-full max-w-md mx-auto rounded-[32px] border border-black/5 bg-white p-6 shadow-xl space-y-6 overflow-hidden">
             <div className="flex items-center gap-3 pb-4 border-b border-black/5">
                <div className="h-10 w-10 rounded-full bg-zinc-100 overflow-hidden border border-black/5">
                    <img src="/employees/women_2.png" className="w-full h-full object-cover" alt="Katy" />
                </div>
                <div>
                    <div className="text-sm font-semibold text-zinc-950">Katy</div>
                    <div className="text-[10px] text-emerald-600 font-medium flex items-center gap-1">
                        <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                        Online
                    </div>
                </div>
             </div>
             <div className="space-y-4">
                <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="bg-zinc-100 p-4 rounded-2xl rounded-tl-none text-[13px] leading-relaxed text-zinc-800 max-w-[85%] shadow-sm">
                    I've updated the 3 Jira tickets and summarized the progress in Slack. Should I draft the weekly report next?
                </motion.div>
                <motion.div initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 0.5 }} className="bg-zinc-950 text-white p-4 rounded-2xl rounded-tr-none text-[13px] leading-relaxed ml-auto max-w-[85%] shadow-md">
                    Great work, Katy. Yes, please proceed with the report and tag the tech lead for review.
                </motion.div>
             </div>
          </div>
        );
      default:
        return null;
    }
  }

  return (
    <div className="mb-32 sm:mb-48">
        <div className="mb-16 pt-16 text-center mx-auto max-w-2xl px-6">
            <h2 className="text-[32px] sm:text-[40px] font-medium tracking-tight text-zinc-950 leading-tight">
                How it works
            </h2>
            <p className="mt-6 text-[16px] sm:text-[18px] leading-7 text-zinc-600">
                From hiring to execution, get your AI workforce up and running in minutes.
            </p>
        </div>

        <div ref={containerRef} className="relative h-[500vh]">
            <section className="sticky top-0 h-screen flex items-center bg-white px-6 sm:px-8 lg:px-10 border-y border-black/5 overflow-hidden">

            <div className="mx-auto max-w-6xl w-full">
                <div className="grid lg:grid-cols-[0.8fr_1.4fr] gap-12 lg:gap-24 items-center">
            <div className="w-full">
                <Stepper value={activeStep} orientation="vertical">
                <StepperNav className="w-full">
                    {steps.map((step, index) => (
                    <StepperItem
                        key={index}
                        step={index + 1}
                        className="relative flex flex-col items-start w-full group/step"
                        completed={activeStep > index + 1}
                    >
                        <StepperTrigger className="w-full items-start gap-4 pb-8 last:pb-0 group-data-[state=inactive]/step:opacity-30 transition-all duration-700 ease-in-out">
                        <StepperIndicator className="mt-0.5 size-8 shrink-0 border-none data-[state=active]:bg-zinc-950 data-[state=active]:text-white data-[state=completed]:bg-zinc-950 data-[state=completed]:text-white bg-zinc-100 text-zinc-500 font-medium text-sm transition-all duration-500">
                            {activeStep > index + 1 ? <CheckIcon className="size-4" /> : index + 1}
                        </StepperIndicator>
                        <div className="text-left flex-1 pt-1">
                            <StepperTitle className="text-[16px] font-medium text-zinc-950 mb-1.5">
                            {step.title}
                            </StepperTitle>
                            <StepperDescription className="text-[14px] leading-relaxed text-zinc-600">
                            {step.description}
                            </StepperDescription>
                        </div>
                        </StepperTrigger>
                        
                        {index < steps.length - 1 && (
                        <StepperSeparator className="absolute left-[15px] top-10 h-[calc(100%-2.5rem)] w-[1.5px] bg-zinc-100 group-data-[state=completed]/step:bg-zinc-950 transition-colors duration-1000" />
                        )}
                    </StepperItem>
                    ))}
                </StepperNav>
                </Stepper>
            </div>

            <div className="relative h-[580px] w-full rounded-[48px] border border-black/5 bg-zinc-50/50 p-8 flex items-center justify-center overflow-hidden">
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:24px_24px]" />
                
                <AnimatePresence mode="wait">
                    <motion.div
                    key={activeStep}
                    initial={{ opacity: 0, scale: 0.95, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 1.05, y: -20 }}
                    transition={{ duration: 0.5, ease: "circOut" }}
                    className="relative z-10 w-full flex items-center justify-center"
                    >
                    {renderRightSide()}
                    </motion.div>
                </AnimatePresence>
            </div>
            </div>
        </div>
        </section>
        </div>
    </div>
  );
}
