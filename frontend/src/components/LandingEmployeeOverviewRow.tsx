import React, { useState } from 'react';
import { motion } from 'motion/react';
import { ArrowLeft, BadgeCheck, BriefcaseBusiness, Coins, ListTodo, Sparkles, Target, Wrench } from 'lucide-react';
import { cn } from '@/lib/utils';

const landingEmployeeCards = [
  {
    name: 'Jordan',
    role: 'Executive Personal Assistant',
    avatar: '/employees/men_4.png',
    cover:
      'linear-gradient(135deg, rgba(77,156,230,0.95) 0%, rgba(13,34,113,0.98) 100%)',
    summary:
      'Handles inbox triage, follow-ups, calendar movement, and daily operational coordination with context.',
    skills: ['Inbox Triage', 'Follow-up Coordination', 'Calendar Briefing'],
    tools: ['Gmail', 'Slack', 'Google Calendar'],
    status: 'Idle',
    activeTask: 'Preparing daily executive brief and resolving overnight follow-ups',
    tokens: '184K',
    spend: '$1.82',
    successRate: '98.9%',
    completedTasks: '42',
  },
  {
    name: 'Mira',
    role: 'Growth Lead',
    avatar: '/employees/women_2.png',
    cover:
      'linear-gradient(135deg, rgba(255,214,102,0.95) 0%, rgba(255,122,89,0.98) 100%)',
    summary:
      'Owns experiment design, funnel review, campaign decisions, and commercial reporting across channels.',
    skills: ['Conversion Analysis', 'Experiment Design', 'Growth Reporting'],
    tools: ['HubSpot', 'Stripe', 'Google Analytics'],
    status: 'Working',
    activeTask: 'Drafting experiment spec for paid signup funnel conversion recovery',
    tokens: '263K',
    spend: '$3.47',
    successRate: '97.4%',
    completedTasks: '31',
  },
  {
    name: 'Sam',
    role: 'Data Analyst',
    avatar: '/employees/men_1.png',
    cover:
      'linear-gradient(135deg, rgba(28,201,141,0.92) 0%, rgba(8,84,68,0.98) 100%)',
    summary:
      'Turns operating data into dashboards, investigations, and concise recommendations the team can act on.',
    skills: ['SQL', 'Dashboarding', 'A/B Analysis'],
    tools: ['BigQuery', 'Looker', 'dbt'],
    status: 'Active',
    activeTask: 'Reconciling weekly retention anomalies across workspace cohorts',
    tokens: '312K',
    spend: '$2.96',
    successRate: '99.1%',
    completedTasks: '57',
  },
];

function LandingEmployeeCard({ card }: { card: typeof landingEmployeeCards[number] }) {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div className="relative perspective-[2000px]">
      <motion.div
        initial={false}
        animate={{ rotateY: isFlipped ? 180 : 0 }}
        transition={{ duration: 0.6, type: 'spring', stiffness: 260, damping: 20 }}
        className="relative h-[500px] w-full preserve-3d"
        style={{ transformStyle: 'preserve-3d' }}
      >
        <article
          role="button"
          tabIndex={0}
          onClick={() => setIsFlipped(true)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              setIsFlipped(true);
            }
          }}
          className={cn(
            'absolute inset-0 overflow-hidden rounded-[24px] border border-zinc-200 bg-white shadow-[0_14px_36px_rgba(24,24,27,0.05)] backface-hidden cursor-pointer',
            isFlipped ? 'pointer-events-none' : 'pointer-events-auto'
          )}
          style={{ backfaceVisibility: 'hidden' }}
        >
          <div className="h-28 w-full" style={{ background: card.cover }} />

          <div className="relative flex h-[calc(100%-7rem)] flex-col px-4 pb-4 pt-0">
            <div className="-mt-7 flex items-start justify-between gap-3">
              <div className="rounded-full bg-white p-1 shadow-sm ring-1 ring-black/5">
                <img
                  src={card.avatar}
                  alt={card.name}
                  className="h-14 w-14 rounded-full object-cover"
                />
              </div>
              <div className="mt-9 inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-[10px] font-medium text-emerald-700">
                <BadgeCheck className="h-3 w-3" />
                {card.status}
              </div>
            </div>

            <div className="mt-3">
              <h4 className="text-[18px] font-medium tracking-tight text-zinc-950">{card.name}</h4>
              <div className="mt-1 text-[13px] text-zinc-500">{card.role}</div>
              <p className="mt-3 line-clamp-3 text-[12px] leading-5 text-zinc-700">{card.summary}</p>
            </div>

            <div className="mt-4 grid flex-1 gap-3">
              <div>
                <div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-400">
                  <Sparkles className="h-3 w-3" />
                  Capabilities
                </div>
                <div className="flex flex-wrap gap-2">
                  {card.skills.map((skill) => (
                    <span
                      key={skill}
                      className="rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-[10px] font-medium text-zinc-700"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-zinc-400">
                  <Wrench className="h-3 w-3" />
                  Connected Tools
                </div>
                <div className="flex flex-wrap gap-2">
                  {card.tools.map((tool) => (
                    <span
                      key={tool}
                      className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-[10px] font-medium text-blue-700"
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-auto border-t border-zinc-100 pt-3 text-[11px] text-zinc-500">
                Click anywhere on the card to flip
              </div>
            </div>
          </div>
        </article>

        <article
          role="button"
          tabIndex={0}
          onClick={() => setIsFlipped(false)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              setIsFlipped(false);
            }
          }}
          className={cn(
            'absolute inset-0 overflow-hidden rounded-[24px] border border-zinc-800 bg-zinc-950 text-white shadow-[0_18px_42px_rgba(24,24,27,0.12)] backface-hidden cursor-pointer',
            !isFlipped ? 'pointer-events-none' : 'pointer-events-auto'
          )}
          style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
        >
          <div className="flex h-full flex-col p-4">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <img src={card.avatar} alt={card.name} className="h-10 w-10 rounded-full object-cover ring-2 ring-white/10" />
                <div>
                  <h4 className="text-[16px] font-medium tracking-tight text-white">{card.name}</h4>
                  <div className="text-[12px] text-zinc-400">{card.role} · Live Operations</div>
                </div>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/5 text-white transition-colors hover:bg-white/10">
                <ArrowLeft className="h-4 w-4" />
              </div>
            </div>

            <div className="mb-3 rounded-2xl border border-white/10 bg-white/5 p-3.5">
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Active Task</div>
              <div className="mt-2 line-clamp-3 text-[12px] leading-5 text-zinc-100">{card.activeTask}</div>
            </div>

            <div className="grid flex-1 grid-cols-2 gap-2.5">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3.5">
                <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
                  <Coins className="h-3.5 w-3.5" />
                  Tokens
                </div>
                <div className="mt-2 text-[24px] font-medium tracking-tight text-white">{card.tokens}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3.5">
                <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
                  <Target className="h-3.5 w-3.5" />
                  Success
                </div>
                <div className="mt-2 text-[24px] font-medium tracking-tight text-white">{card.successRate}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3.5">
                <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
                  <BriefcaseBusiness className="h-3.5 w-3.5" />
                  Spend
                </div>
                <div className="mt-2 text-[24px] font-medium tracking-tight text-white">{card.spend}</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3.5">
                <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
                  <ListTodo className="h-3.5 w-3.5" />
                  Completed
                </div>
                <div className="mt-2 text-[24px] font-medium tracking-tight text-white">{card.completedTasks}</div>
              </div>
            </div>

            <div className="mt-4 border-t border-white/10 pt-3 text-[11px] text-zinc-400">
              Click anywhere on the card to return to the profile view.
            </div>
          </div>
        </article>
      </motion.div>
    </div>
  );
}

export function LandingEmployeeOverviewRow() {
  return (
    <section className="bg-white overflow-hidden border-t border-black/[0.04] px-6 pb-8 pt-32 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-[90%]">
        <div className="mx-auto mb-20 max-w-2xl text-center">
          <h3 className="mb-4 text-[32px] font-medium tracking-tight text-zinc-950 sm:text-[40px]">
            Hire the employee on the basis of their abilities
          </h3>
          <p className="mx-auto max-w-2xl text-[16px] text-zinc-600">
            A compact view of identity, capabilities, and connected tools before opening the full employee page.
          </p>
        </div>

        <div className="mx-auto grid max-w-[1180px] gap-5 lg:grid-cols-3">
          {landingEmployeeCards.map((card) => (
            <LandingEmployeeCard key={card.name} card={card} />
          ))}
        </div>
      </div>
    </section>
  );
}
