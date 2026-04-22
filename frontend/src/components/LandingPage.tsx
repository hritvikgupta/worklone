import React, { useState, useEffect } from 'react';
import { ArrowRight, Headphones, LineChart, Code, Briefcase, ChevronDown } from 'lucide-react';
import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import { LandingPageDashboard } from './LandingPageDashboard';
import { LandingChatDemoSection } from './LandingChatDemoSection';
import { LandingSprintSection } from './LandingSprintSection';
import { AgentProgressSection } from './AgentProgressSection';
import { CreateWorkflowSection } from './CreateWorkflowSection';
import { AgentNetworkSection } from './AgentNetworkSection';
import { HowItWorksSection } from './HowItWorksSection';
import { researchArticles } from './ResearchArticlePage';

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
  ['Asana', 'Zendesk', 'Confluence', 'Stripe', 'Calendar', 'Airtable', 'Figma'],
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
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-white text-zinc-950">
      {/* Sticky Navbar */}
      <div 
        className="fixed top-0 z-50 flex w-full justify-center transition-all duration-500 bg-white/95 backdrop-blur-md"
      >
        <div 
          className="flex w-full max-w-7xl items-center justify-between px-6 py-3 sm:px-8 lg:px-10"
        >
          <div className="flex items-center gap-3">
            <img
              src="/brand/worklone-mark-black.png"
              alt="Worklone"
              className="h-7 w-auto"
            />
            <div className="text-[18px] font-normal tracking-[-0.02em] text-[#0F172A] font-['Lato']">Worklone</div>
          </div>

          <div className="hidden md:flex flex-1 items-center justify-center gap-8">
            <Link
              to="/what-is-worklone"
              className="text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950"
            >
              What is Worklone
            </Link>
            <div className="relative group">
              <button
                className="flex items-center gap-1 text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950"
              >
                Research
                <ChevronDown className="h-3 w-3" />
              </button>
              <div className="absolute left-1/2 -translate-x-1/2 top-full pt-4 hidden group-hover:block z-50">
                <div className="w-[300px] rounded-xl border border-zinc-200 bg-white p-2 shadow-lg ring-1 ring-black/5">
                  {researchArticles.map((article) => (
                    <Link
                      key={article.slug}
                      to={`/research/${article.slug}`}
                      className="block rounded-lg px-4 py-3 hover:bg-zinc-50 transition-colors"
                    >
                      <div className="text-sm font-medium text-zinc-900">{article.title}</div>
                      <div className="text-xs text-zinc-500 mt-0.5 line-clamp-1">{article.subtitle}</div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
            <Link
              to="/documentation"
              className="text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950"
            >
              Documentation
            </Link>
            <Link
              to="/agentskills"
              className="text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950"
            >
              Agent Skills
            </Link>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="https://github.com/hritvikgupta/worklone"
              target="_blank"
              rel="noreferrer"
              aria-label="Worklone GitHub repository"
              className="inline-flex h-10 w-10 items-center justify-center text-zinc-950 transition-opacity hover:opacity-70"
            >
              <img
                src="https://cdn.simpleicons.org/github/181717"
                alt="GitHub"
                className="h-5 w-5"
              />
            </a>
            <Link
              to="/waitlist"
              className="inline-flex items-center gap-2 rounded-md bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800"
            >
              <span className="hidden sm:inline">Join Waitlist</span>
              <span className="sm:hidden">Waitlist</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>

      <section className="relative overflow-hidden bg-white pt-24 pb-16 sm:pb-20 sm:pt-32">
        <div className="relative z-10 px-6 sm:px-8 lg:px-10 mx-auto max-w-7xl mb-16">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div className="max-w-4xl text-left">
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <h1 className="text-[32px] sm:text-[42px] leading-[1.2] font-normal tracking-tight text-zinc-950 max-w-3xl">
                  Train and build your first AI employee
                </h1>

                <p className="mt-6 text-[16px] sm:text-[18px] leading-[1.6] text-zinc-800 max-w-3xl">
                  Deploy self-adaptive AI employees that learn your workspace and master your workflows. An autonomous team that continuously improves and never makes the same mistake twice. Built for the modern enterprise.
                </p>

                <div className="mt-10 flex flex-wrap items-center justify-start gap-4">
                  <Link
                    to="/waitlist"
                    className="inline-flex items-center justify-center rounded-[4px] bg-[#1a1a1a] px-6 py-3 text-[14px] font-medium text-white transition-colors hover:bg-black"
                  >
                    Join Waitlist
                  </Link>
                  <Link
                    to="/what-is-worklone"
                    className="inline-flex items-center justify-center rounded-[4px] border border-zinc-200 bg-white px-6 py-3 text-[14px] font-medium text-zinc-900 transition-colors hover:bg-zinc-50"
                  >
                    What is Worklone
                  </Link>
                </div>
                
                <div className="mt-8 text-[14px] text-zinc-800">
                  Or, <Link to="/documentation" className="underline underline-offset-4 hover:text-zinc-500 transition-colors">read the documentation</Link>.
                </div>
              </motion.div>
            </div>
            
            <motion.div 
              className="hidden lg:flex justify-center lg:justify-end"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.1 }}
            >
              <img 
                src="/heroright.png" 
                alt="AI Face Visualization" 
                className="w-full max-w-[500px] h-auto object-contain opacity-90"
              />
            </motion.div>
          </div>
        </div>

        <div className="relative z-10 px-6 sm:px-8 lg:px-10 mx-auto max-w-7xl">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Card 1 */}
            <div className="group border border-zinc-200 bg-white p-6 relative transition-all duration-300 hover:-translate-y-1 hover:-translate-x-1 hover:shadow-[4px_4px_0_0_#10b981] hover:border-[#10b981]">
              <div className="mb-6 h-10 w-12 border-2 border-zinc-900 flex items-center justify-center group-hover:border-[#10b981] group-hover:text-[#10b981] transition-colors">
                <Headphones className="h-5 w-5" strokeWidth={1.5} />
              </div>
              <div className="text-[16px] font-semibold text-zinc-950 mb-4 group-hover:bg-[#10b981]/10 w-fit">Customer Support</div>
              <div className="text-[14px] text-zinc-800 mb-1">24/7 automated resolution</div>
              <div className="text-[14px] text-zinc-600">Integrates with Zendesk & Intercom.</div>
            </div>
            
            {/* Card 2 */}
            <div className="group border border-zinc-200 bg-white p-6 relative transition-all duration-300 hover:-translate-y-1 hover:-translate-x-1 hover:shadow-[4px_4px_0_0_#10b981] hover:border-[#10b981]">
              <div className="mb-6 h-10 w-12 border-2 border-zinc-900 flex items-center justify-center group-hover:border-[#10b981] group-hover:text-[#10b981] transition-colors">
                <LineChart className="h-5 w-5" strokeWidth={1.5} />
              </div>
              <div className="text-[16px] font-semibold text-zinc-950 mb-4 group-hover:bg-[#10b981]/10 w-fit">Data Analyst</div>
              <div className="text-[14px] text-zinc-800 mb-1">Real-time insights</div>
              <div className="text-[14px] text-zinc-600">SQL & Python native queries.</div>
            </div>

            {/* Card 3 */}
            <div className="group border border-zinc-200 bg-white p-6 relative transition-all duration-300 hover:-translate-y-1 hover:-translate-x-1 hover:shadow-[4px_4px_0_0_#10b981] hover:border-[#10b981]">
              <div className="mb-6 h-10 w-12 border-2 border-zinc-900 flex items-center justify-center group-hover:border-[#10b981] group-hover:text-[#10b981] transition-colors">
                <Code className="h-5 w-5" strokeWidth={1.5} />
              </div>
              <div className="text-[16px] font-semibold text-zinc-950 mb-4 group-hover:bg-[#10b981]/10 w-fit">Software Engineer</div>
              <div className="text-[14px] text-zinc-800 mb-1">Code & PR reviews</div>
              <div className="text-[14px] text-zinc-600">GitHub & GitLab ready.</div>
            </div>

            {/* Card 4 */}
            <div className="group border border-zinc-200 bg-white p-6 relative transition-all duration-300 hover:-translate-y-1 hover:-translate-x-1 hover:shadow-[4px_4px_0_0_#10b981] hover:border-[#10b981]">
              <div className="mb-6 h-10 w-12 border-2 border-zinc-900 flex items-center justify-center group-hover:border-[#10b981] group-hover:text-[#10b981] transition-colors">
                <Briefcase className="h-5 w-5" strokeWidth={1.5} />
              </div>
              <div className="text-[16px] font-semibold text-zinc-950 mb-4 group-hover:bg-[#10b981]/10 w-fit">Product Manager</div>
              <div className="text-[14px] text-zinc-800 mb-1">Automated roadmaps</div>
              <div className="text-[14px] text-zinc-600">Jira & Linear sync.</div>
            </div>
          </div>
        </div>
      </section>

      <HowItWorksSection />

      <LandingSprintSection />

      <LandingChatDemoSection />

      <section id="workspace-preview" className="bg-white py-16 sm:py-24">
        <div className="mx-auto w-full max-w-7xl px-6 sm:px-8 lg:px-10">
          <div className="grid gap-0 overflow-hidden rounded-[30px] border border-zinc-200 bg-white lg:grid-cols-[0.64fr_1.36fr]">
            <div className="flex items-center border-b border-zinc-200 p-8 sm:p-12 lg:border-b-0 lg:border-r lg:p-16">
              <div>
                <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
                  Employee Training & Deployment
                </div>
                <h2 className="mt-4 text-[24px] font-medium leading-[1.15] tracking-tight text-zinc-900 sm:text-[30px]">
                  Train and deploy your AI employees
                  <span className="block text-zinc-500">with production-ready control</span>
                </h2>
                <p className="mt-4 max-w-md text-[15px] leading-7 text-zinc-600">
                  Define behavior standards, validate outputs, and ship reliable autonomous execution at scale.
                </p>
              </div>
            </div>

            <div className="relative overflow-hidden bg-white p-4 sm:p-8">
              <div className="absolute inset-0 z-0 pointer-events-none">
                <img src="/bgothers.png" alt="" className="h-full w-full object-cover object-center" />
              </div>
              <div className="relative z-10" style={{ zoom: 0.78 }}>
                <LandingPageDashboard />
              </div>
            </div>
          </div>
        </div>
      </section>

      <AgentNetworkSection />

      <AgentProgressSection />

      <CreateWorkflowSection />

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
          <div className="grid gap-10 border-b border-white/10 pb-12 md:grid-cols-2 lg:grid-cols-[minmax(0,1.4fr)_repeat(4,minmax(0,1fr))] lg:gap-12">
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
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Company</div>
              <div className="mt-4 space-y-2.5 text-base text-white/72">
                <Link to="/privacy-policy" className="block transition-colors hover:text-white">
                  Privacy Policy
                </Link>
                <Link to="/contact" className="block transition-colors hover:text-white">
                  Contact
                </Link>
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Research</div>
              <div className="mt-4 space-y-2.5 text-base text-white/72">
                {researchArticles.map((article) => (
                  <Link 
                    key={article.slug} 
                    to={`/research/${article.slug}`} 
                    className="block transition-colors hover:text-white"
                  >
                    {article.title}
                  </Link>
                ))}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Company</div>
              <div className="mt-4 space-y-2.5 text-base text-white/72">
                <Link to="/privacy-policy" className="block transition-colors hover:text-white">
                  Privacy Policy
                </Link>
                <Link to="/contact" className="block transition-colors hover:text-white">
                  Contact
                </Link>
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Connect</div>
              <div className="mt-4 space-y-2.5 text-base text-white/72">
                <a
                  href="https://x.com/worklonemployee"
                  target="_blank"
                  rel="noreferrer"
                  className="block transition-colors hover:text-white"
                >
                  Twitter
                </a>
                <span className="block">LinkedIn</span>
                <span className="block">GitHub</span>
              </div>
            </div>
          </div>

          <div className="mt-8 flex flex-col gap-4 text-xs text-white/58 md:flex-row md:items-center md:justify-between">
            <span>© 2026 Worklone. All rights reserved.</span>
            <div className="flex flex-wrap items-center gap-4 md:justify-end md:gap-6">
              <Link to="/privacy-policy" className="transition-colors hover:text-white">Privacy Policy</Link>
              <Link to="/contact" className="transition-colors hover:text-white">Contact</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
