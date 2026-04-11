import React from 'react';
import { ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import { LandingPageDashboard } from './LandingPageDashboard';

const workforceProfiles = [
  {
    name: 'Katy',
    role: 'Product Manager',
    image: '/workforce/employee-5.png',
    summary: 'Katy owns roadmap definition, requirement quality, and execution cadence across the workspace. She translates ambiguous requests into clear plans, creates the right artifacts, and keeps product, engineering, and operations aligned around the next highest-leverage move.',
  },
  {
    name: 'Sam',
    role: 'Data Analyst',
    image: '/workforce/employee-4.png',
    summary: 'Sam turns messy operational and product data into decisions that can actually be acted on. He explains movement in the numbers, monitors health across the business, and produces concise analysis that helps the team move faster with less guesswork.',
  },
  {
    name: 'Mira',
    role: 'Growth Lead',
    image: '/workforce/employee-1.png',
    summary: 'Mira drives acquisition, positioning, and funnel improvement through disciplined experimentation. She identifies where growth is stalling, tests what changes conversion, and keeps demand generation tied to measurable commercial outcomes.',
  },
  {
    name: 'Leo',
    role: 'Backend Engineer',
    image: '/workforce/employee-3.png',
    summary: 'Leo builds the backend systems that keep the operating environment reliable under real use. He owns API quality, integration resilience, and the operational details that make sessions, workflows, and infrastructure behave predictably at scale.',
  },
];

// Integration icon component - uses simple SVG icons from public CDN
const IntegrationIcon: React.FC<{ name: string }> = ({ name }) => {
  const iconMap: Record<string, string> = {
    'Gmail': 'https://cdn.simpleicons.org/gmail/EA4333',
    'Jira': 'https://cdn.simpleicons.org/jira/0052CC',
    'Notion': 'https://cdn.simpleicons.org/notion/000000',
    'GitHub': 'https://cdn.simpleicons.org/github/181717',
    'Slack': '/slackicon.png',
    'Linear': 'https://cdn.simpleicons.org/linear/5E6AD2',
    'HubSpot': 'https://cdn.simpleicons.org/hubspot/FF7A59',
    'Google Drive': 'https://cdn.simpleicons.org/googledrive/4285F4',
    'Asana': 'https://cdn.simpleicons.org/asana/F06A6A',
    'Salesforce': 'https://cdn.simpleicons.org/salesforce/00A1E0',
    'Zendesk': 'https://cdn.simpleicons.org/zendesk/03363D',
    'Confluence': 'https://cdn.simpleicons.org/confluence/172B4D',
    'Stripe': 'https://cdn.simpleicons.org/stripe/635BFF',
    'Calendar': 'https://cdn.simpleicons.org/googlecalendar/4285F4',
    'Airtable': 'https://cdn.simpleicons.org/airtable/18BFFF',
    'Figma': 'https://cdn.simpleicons.org/figma/F24E1E',
    'Snowflake': 'https://cdn.simpleicons.org/snowflake/29B5E8',
    'Postgres': 'https://cdn.simpleicons.org/postgresql/4169E1',
    'BigQuery': 'https://cdn.simpleicons.org/googlebigquery/669DF6',
    'ClickUp': 'https://cdn.simpleicons.org/clickup/7B68EE',
    'Intercom': 'https://cdn.simpleicons.org/intercom/6AF13A',
    'Dropbox': 'https://cdn.simpleicons.org/dropbox/0061FF',
    'Trello': 'https://cdn.simpleicons.org/trello/0052CC',
    'Zapier': 'https://cdn.simpleicons.org/zapier/FF4A00',
  };

  const iconUrl = iconMap[name] || null;

  if (!iconUrl) {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full border border-black/10 bg-zinc-100 text-xs font-semibold text-zinc-500">
        {name.slice(0, 2).toUpperCase()}
      </span>
    );
  }

  return (
    <img
      src={iconUrl}
      alt={`${name} icon`}
      className="h-7 w-7 rounded-full object-contain"
      style={{ filter: 'contrast(1.05)' }}
    />
  );
};

const integrationRows = [
  ['Gmail', 'Jira', 'Notion', 'GitHub', 'Slack', 'Linear', 'HubSpot', 'Google Drive'],
  ['Asana', 'Salesforce', 'Zendesk', 'Confluence', 'Stripe', 'Calendar', 'Airtable', 'Figma'],
  ['Snowflake', 'Postgres', 'BigQuery', 'ClickUp', 'Intercom', 'Dropbox', 'Trello', 'Zapier'],
];

const pricingPlans = [
  {
    name: 'Starter',
    price: '$2',
    detail: 'per employee hour',
    description: 'For small teams proving out one or two AI employees.',
    features: ['Core workspace', 'Chat, files, and workflows', 'Standard integrations', 'Claude Haiku, GPT-4o mini, Gemini Flash'],
  },
  {
    name: 'Team',
    price: '$5',
    detail: 'per employee hour',
    description: 'For operating multiple employees across product, ops, and GTM.',
    features: ['Everything in Starter', 'Advanced integrations', 'Priority execution and audit trails', 'Access to WhatsApp, Telegram, or email messaging to employee', 'Claude Sonnet, GPT-4.1, Gemini Pro, Minimax'],
    featured: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    detail: 'volume-based hourly pricing',
    description: 'For companies standardizing AI employees across the organization.',
    features: ['Custom deployment', 'Security review and SSO', 'Dedicated support and onboarding', 'Claude, OpenAI, Gemini, Minimax, Grok, custom routing'],
  },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-zinc-950">
      <section className="relative overflow-hidden bg-white">
        <div className="relative px-6 pt-5 sm:px-8 lg:px-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img
                src="/brand/worklone-mark-black.png"
                alt="Worklone"
                className="h-7 w-auto"
              />
              <div className="text-lg font-semibold tracking-tight">Worklone</div>
            </div>

            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-full bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800"
            >
              Join Waitlist
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-6 bg-white">
            <img
              src="/landing-hero.png"
              alt="Worklone hero artwork"
              className="block h-[300px] w-full bg-white object-cover object-center sm:h-[380px] lg:h-[440px]"
            />
          </div>

          <div className="relative z-10 mx-auto -mt-12 max-w-4xl px-4 pb-20 text-center sm:-mt-18">
            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55 }}
              className="mx-auto mt-6 max-w-3xl text-balance text-[48px] font-semibold tracking-[-0.05em] text-zinc-950 sm:text-[68px] sm:leading-[0.95]"
            >
              Build your team of AI employees
            </motion.h1>

            <p className="mx-auto mt-5 max-w-2xl text-[16px] leading-7 text-zinc-600 sm:text-[18px]">
              Hire specialized AI employees for real work across your business. One operating system for AI coworkers that actually do the work.
            </p>

            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Link
                to="/login"
                className="inline-flex items-center gap-2 rounded-full bg-zinc-950 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-zinc-800"
              >
                Join Waitlist
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/what-is-worklone"
                className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-white/90 px-6 py-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-white"
              >
                What is Worklone
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section id="workspace-preview" className="bg-white px-6 py-10 sm:px-8 lg:px-10">
        <div className="space-y-6">
          <LandingPageDashboard />
        </div>
      </section>

      <section className="bg-white px-6 py-8 sm:px-8 lg:px-10">
        <div className="mx-auto mb-14 max-w-3xl text-center">
          <h2
            className="text-4xl font-semibold tracking-tight text-zinc-950"
          >
            Meet the employees behind the system
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-zinc-600">
            Scroll through the team. Each employee owns a real lane of execution inside Worklone.
          </p>
        </div>

        <div className="space-y-24">
          {workforceProfiles.map((profile, index) => (
            <motion.div
              key={profile.name}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.45 }}
              className="grid items-center gap-6 lg:grid-cols-[minmax(0,560px)_360px] lg:justify-center"
            >
              <div className="max-w-[560px]">
                <h3 className="mt-3 text-3xl font-semibold tracking-tight text-zinc-950">
                  {profile.name}
                </h3>
                <div className="mt-2 text-xl font-medium text-zinc-500">
                  {profile.role}
                </div>
                <p className="mt-6 text-[17px] leading-8 text-zinc-700">{profile.summary}</p>
              </div>

              <div className="flex justify-center lg:justify-start">
                <img
                  src={profile.image}
                  alt={`${profile.name} portrait`}
                  className="block max-h-[520px] w-auto max-w-[360px] bg-white object-contain object-center"
                />
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="overflow-hidden bg-white px-6 py-16 sm:px-8 lg:px-10">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="text-4xl font-semibold tracking-tight text-zinc-950">100+ integrations to power your employees</h2>
          <p className="mt-4 text-lg leading-8 text-zinc-600">
            Connect the tools your team already uses so every employee can operate inside the same system of record.
          </p>
        </div>

        <div className="mt-12 space-y-4">
          {integrationRows.map((row, rowIndex) => {
            const items = [...row, ...row];
            const direction = rowIndex % 2 === 0 ? ['0%', '-50%'] : ['-50%', '0%'];

            return (
              <div key={rowIndex} className="overflow-hidden">
                <motion.div
                  animate={{ x: direction }}
                  transition={{ duration: 22 + rowIndex * 3, repeat: Infinity, ease: 'linear' }}
                  className="flex w-max gap-3"
                >
                  {items.map((item, index) => (
                    <div
                      key={`${item}-${index}`}
                      className="flex items-center gap-3 rounded-full border border-black/10 bg-white px-5 py-3 text-sm font-medium text-zinc-700"
                    >
                      <IntegrationIcon name={item} />
                      {item}
                    </div>
                  ))}
                </motion.div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="bg-white px-6 py-16 sm:px-8 lg:px-10">
        <div className="mx-auto max-w-5xl">
          <div className="mx-auto max-w-3xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight text-zinc-950">Pricing</h2>
            <p className="mt-4 text-base leading-7 text-zinc-600">
              Start with one employee, then expand the system as more teams and workflows move into Worklone.
            </p>
          </div>

          <div className="mt-10 grid gap-4 lg:grid-cols-3">
            {pricingPlans.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-3xl border px-8 py-8 ${
                  plan.featured ? 'border-zinc-950' : 'border-black/10'
                }`}
              >
                <div className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">{plan.name}</div>
                <div className="mt-3 text-[28px] font-semibold tracking-tight text-zinc-950">{plan.price}</div>
                <div className="mt-1 text-xs text-zinc-500">{plan.detail}</div>
                <p className="mt-5 text-sm leading-6 text-zinc-600">{plan.description}</p>
                <div className="mt-6 space-y-2.5 text-sm text-zinc-700">
                  {plan.features.map((feature) => (
                    <div key={feature} className="flex items-start gap-2">
                      <svg className="mt-0.5 h-4 w-4 shrink-0 text-zinc-950" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      {feature}
                    </div>
                  ))}
                </div>
                <div
                  className={`mt-6 inline-flex w-full items-center justify-center rounded-full px-4 py-2.5 text-sm font-medium transition-colors ${
                    plan.featured
                      ? 'bg-zinc-950 text-white'
                      : 'border border-black/10 bg-white text-zinc-900'
                  }`}
                >
                  Coming soon
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="relative overflow-hidden bg-[#111111] px-6 py-14 text-white sm:px-8 lg:px-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.07),transparent_35%),radial-gradient(circle_at_top_right,rgba(255,255,255,0.05),transparent_25%),linear-gradient(180deg,rgba(255,255,255,0.03),rgba(0,0,0,0.08)),linear-gradient(135deg,#171717_0%,#111111_28%,#1a1a1a_50%,#0f0f0f_72%,#171717_100%)]" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-[linear-gradient(180deg,transparent,rgba(0,0,0,0.22))]" />
        <div className="relative mx-auto max-w-6xl">
          <div className="grid gap-10 border-b border-white/10 pb-12 md:grid-cols-2 lg:grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))] lg:gap-12">
            <div className="max-w-sm">
              <div className="flex items-center gap-3">
                <img
                  src="/brand/worklone-mark-white.png"
                  alt="Worklone"
                  className="h-7 w-auto"
                />
                <div className="text-lg font-semibold tracking-tight text-white">Worklone</div>
              </div>
              <p className="mt-4 text-sm leading-6 text-white/64">
                The operating system for AI employees across planning, execution, files, workflows, and integrations.
              </p>
            </div>

            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Product</div>
              <div className="mt-4 space-y-2.5 text-base text-white/72">
                <Link to="/what-is-worklone" className="block transition-colors hover:text-white">
                  What is Worklone
                </Link>
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Company</div>
              <div className="mt-4 space-y-2.5 text-base text-white/72">
                <span className="block">Privacy Policy</span>
                <span className="block">Terms</span>
                <span className="block">Contact</span>
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Connect</div>
              <div className="mt-4 space-y-2.5 text-base text-white/72">
                <span className="block">Twitter</span>
                <span className="block">LinkedIn</span>
                <span className="block">GitHub</span>
              </div>
            </div>
          </div>

          <div className="mt-8 flex flex-col gap-4 text-xs text-white/58 md:flex-row md:items-center md:justify-between">
            <span>© 2026 Worklone. All rights reserved.</span>
            <div className="flex flex-wrap items-center gap-4 md:justify-end md:gap-6">
              <span>Privacy Policy</span>
              <span>Terms</span>
              <span>Contact</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
