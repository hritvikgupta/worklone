import React, { useState } from 'react';
import { motion } from 'motion/react';
import { cn } from '@/lib/utils';
import { CheckCircle2, ArrowLeft } from 'lucide-react';

const workforceProfiles = [
  {
    name: 'Katy',
    role: 'Product Manager',
    image: '/employees/women_1.png',
    bgColor: 'bg-[#F4F7FB]', // soft blue
    summary: 'Katy owns roadmap definition, requirement quality, and execution cadence across the workspace. She translates ambiguous requests into clear plans, creates the right artifacts, and keeps product, engineering, and operations aligned around the next highest-leverage move.',
    stats: {
      runtime: '1,420 hrs',
      tokens: '3.2M',
      workflows: '850',
      successRate: '99.4%'
    },
    skills: ['Roadmapping', 'PRD Generation', 'Stakeholder Comms', 'Backlog Grooming'],
    tasks: ['Created Q3 Roadmap', 'Drafted API PRD', 'Synced Jira Tickets', 'Analyzed user feedback']
  },
  {
    name: 'Sam',
    role: 'Data Analyst',
    image: '/employees/men_1.png',
    bgColor: 'bg-[#F0FDF4]', // soft emerald/green
    summary: 'Sam turns messy operational and product data into decisions that can actually be acted on. He explains movement in the numbers, monitors health across the business, and produces concise analysis that helps the team move faster with less guesswork.',
    stats: {
      runtime: '980 hrs',
      tokens: '5.1M',
      workflows: '1,204',
      successRate: '98.7%'
    },
    skills: ['SQL & NoSQL', 'Data Visualization', 'A/B Test Analysis', 'Metrics Tracking'],
    tasks: ['Built Retention Dashboard', 'Optimized slow queries', 'Analyzed churn data', 'Fixed data pipeline']
  },
  {
    name: 'Mira',
    role: 'Growth Lead',
    image: '/employees/women_2.png',
    bgColor: 'bg-[#FAF5FF]', // soft purple
    summary: 'Mira drives acquisition, positioning, and funnel improvement through disciplined experimentation. She identifies where growth is stalling, tests what changes conversion, and keeps demand generation tied to measurable commercial outcomes.',
    stats: {
      runtime: '1,150 hrs',
      tokens: '2.8M',
      workflows: '620',
      successRate: '99.1%'
    },
    skills: ['Conversion Optimization', 'Campaign Setup', 'SEO Analysis', 'Copywriting'],
    tasks: ['Launched Email Sequence', 'A/B Tested Landing Page', 'Analyzed ad spend', 'Generated social copy']
  }
];

function ProfileCard({ profile }: { profile: typeof workforceProfiles[0] }) {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div className="relative group perspective-[2000px]">
      <motion.div
        initial={false}
        animate={{ rotateY: isFlipped ? 180 : 0 }}
        transition={{ duration: 0.6, type: "spring", stiffness: 260, damping: 20 }}
        className="w-full relative preserve-3d"
        style={{ transformStyle: 'preserve-3d' }}
      >
        {/* Front of Card */}
        <div
          className={cn(
            "w-full rounded-[32px] border border-black/[0.08] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] sm:p-12 backface-hidden",
            profile.bgColor || "bg-white",
            isFlipped ? "pointer-events-none" : "pointer-events-auto"
          )}
          style={{ backfaceVisibility: 'hidden' }}
        >          <div className="grid items-center gap-12 lg:grid-cols-2 min-h-[380px]">
            <div className="order-2 lg:order-1 flex flex-col justify-center h-full">
              <div>
                <h3 className="text-3xl font-medium tracking-tight text-zinc-950">
                  {profile.name}
                </h3>
                <div className="mt-2 text-lg font-medium text-zinc-500">
                  {profile.role}
                </div>
                <p className="mt-6 text-[16px] leading-8 text-zinc-700">
                  {profile.summary}
                </p>
              </div>
              
              <div className="mt-10 flex items-center gap-4">
                <button 
                  onClick={() => setIsFlipped(true)}
                  className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-800"
                >
                  View Capability
                </button>
              </div>
            </div>

            <div className="order-1 lg:order-2 flex justify-center items-center h-full">
              <div className="relative">
                <div className="absolute -inset-4 rounded-full bg-zinc-50/50 blur-2xl" />
                <img
                  src={profile.image}
                  alt={`${profile.name} portrait`}
                  className="relative block max-h-[380px] w-auto bg-transparent object-contain transition-transform duration-500 group-hover:scale-105"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Back of Card */}
        <div 
          className={cn(
            "absolute inset-0 w-full h-full bg-zinc-950 text-white rounded-[32px] border border-zinc-800 p-8 shadow-[0_8px_30px_rgb(0,0,0,0.1)] sm:p-10 backface-hidden flex flex-col overflow-hidden",
            !isFlipped ? "pointer-events-none" : "pointer-events-auto"
          )}
          style={{ 
            backfaceVisibility: 'hidden',
            transform: 'rotateY(180deg)'
          }}
        >
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-4">
                <img src={profile.image} alt={profile.name} className="w-12 h-12 rounded-full object-cover border-2 border-zinc-800 bg-white" />
                <div>
                  <h3 className="text-[17px] font-medium tracking-tight text-white">{profile.name}'s Capabilities</h3>
                  <p className="text-[13px] text-zinc-400 font-normal">{profile.role} · System Details</p>
                </div>
              </div>
              <button 
                onClick={() => setIsFlipped(false)}
                className="h-10 w-10 flex items-center justify-center rounded-full bg-white/5 hover:bg-white/10 transition-colors text-white shrink-0"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 flex-1 text-[13px] font-normal mb-8">
              
              {/* Column 1: Metrics */}
              <div className="space-y-4">
                <h4 className="text-zinc-500 uppercase tracking-widest text-[10px] mb-4 font-medium">System Metrics</h4>
                <div className="flex justify-between items-center border-b border-white/5 pb-2.5">
                  <span className="text-zinc-400">Total Runtime</span>
                  <span className="text-white">{profile.stats.runtime}</span>
                </div>
                <div className="flex justify-between items-center border-b border-white/5 pb-2.5">
                  <span className="text-zinc-400">Tokens Processed</span>
                  <span className="text-white">{profile.stats.tokens}</span>
                </div>
                <div className="flex justify-between items-center border-b border-white/5 pb-2.5">
                  <span className="text-zinc-400">Workflows Executed</span>
                  <span className="text-white">{profile.stats.workflows}</span>
                </div>
                <div className="flex justify-between items-center border-b border-white/5 pb-2.5">
                  <span className="text-zinc-400">Success Rate</span>
                  <span className="text-white">{profile.stats.successRate}</span>
                </div>
              </div>

              {/* Column 2: Skills Attached */}
              <div className="space-y-4 md:border-l md:border-white/5 md:pl-6">
                <h4 className="text-zinc-500 uppercase tracking-widest text-[10px] mb-4 font-medium">Skills Attached</h4>
                <ul className="space-y-3.5">
                  {profile.skills.map(skill => (
                    <li key={skill} className="flex items-center gap-2.5 text-zinc-300">
                      <div className="w-1 h-1 rounded-full bg-zinc-600 shrink-0" />
                      <span>{skill}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Column 3: Tasks Completed */}
              <div className="space-y-4 md:border-l md:border-white/5 md:pl-6">
                <h4 className="text-zinc-500 uppercase tracking-widest text-[10px] mb-4 font-medium">Recent Tasks</h4>
                <ul className="space-y-3">
                  {profile.tasks.map(task => (
                    <li key={task} className="flex gap-2.5 text-zinc-300 items-start">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500/70 shrink-0 mt-0.5" />
                      <span className="leading-snug">{task}</span>
                    </li>
                  ))}
                </ul>
              </div>

            </div>

            <div className="flex items-center justify-between pt-6 border-t border-white/5 mt-auto">
              <span className="text-[12px] text-zinc-500 font-normal">Real-time status: Active</span>
              <button 
                onClick={() => setIsFlipped(false)}
                className="rounded-full border border-white/10 px-5 py-2 text-[12px] font-normal text-white transition-colors hover:bg-white/5"
              >
                Back to Profile
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export function WorkforceStickySection() {
  return (
    <section className="bg-white px-6 py-24 sm:px-8 lg:px-10">
      <div className="mx-auto mb-20 max-w-3xl text-center">
        <h2 className="text-[32px] font-medium tracking-tight text-zinc-950 sm:text-[40px]">
          Meet the employees behind the system
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-[16px] leading-7 text-zinc-600">
          Each employee owns a real lane of execution inside Worklone.
        </p>
      </div>

      <div className="relative mx-auto max-w-5xl space-y-12 pb-24">
        {workforceProfiles.map((profile, index) => (
          <div 
            key={profile.name} 
            className="sticky top-24"
          >
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.5 }}
            >
              <ProfileCard profile={profile} />
            </motion.div>
          </div>
        ))}
      </div>
    </section>
  );
}
