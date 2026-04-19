import React from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { researchArticles } from './ResearchArticlePage';

function SiteFooter() {
  return (
    <footer className="relative overflow-hidden bg-[#111111] px-6 py-14 text-white sm:px-8 lg:px-10">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.07),transparent_35%),radial-gradient(circle_at_top_right,rgba(255,255,255,0.05),transparent_25%),linear-gradient(180deg,rgba(255,255,255,0.03),rgba(0,0,0,0.08)),linear-gradient(135deg,#171717_0%,#111111_28%,#1a1a1a_50%,#0f0f0f_72%,#171717_100%)]" />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-[linear-gradient(180deg,transparent,rgba(0,0,0,0.22))]" />
      <div className="relative mx-auto max-w-6xl">
        <div className="grid gap-10 border-b border-white/10 pb-12 md:grid-cols-2 lg:grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))] lg:gap-12">
          <div className="max-w-sm">
            <div className="flex items-center gap-3">
              <img src="/brand/worklone-mark-white.png" alt="Worklone" className="h-7 w-auto" />
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
        </div>

        <div className="mt-8 flex flex-col gap-4 text-xs text-white/58 md:flex-row md:items-center md:justify-between">
          <span>© 2026 Worklone. All rights reserved.</span>
          <div className="flex flex-wrap items-center gap-4 md:justify-end md:gap-6">
            <Link to="/privacy-policy" className="transition-colors hover:text-white">Privacy Policy</Link>
            <Link to="/contact" className="transition-colors hover:text-white">Contact</Link>
            <a
              href="https://github.com/hritvikgupta/worklone"
              target="_blank"
              rel="noreferrer"
              className="transition-colors hover:text-white"
            >
              GitHub
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}

export function PrivacyPolicyPage() {
  const lastUpdated = 'April 15, 2026';

  return (
    <div className="min-h-screen bg-white text-zinc-950">
      <header className="fixed inset-x-0 top-0 z-40 bg-white/94 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 sm:px-8 lg:px-10">
          <Link to="/" className="flex items-center gap-3">
            <img src="/brand/worklone-mark-black.png" alt="Worklone" className="h-7 w-auto" />
            <div className="text-lg font-semibold tracking-tight">Worklone</div>
          </Link>

          <div className="flex items-center gap-4">
            <Link
              to="/waitlist"
              className="inline-flex items-center gap-2 rounded-full bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800"
            >
              Join Waitlist
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <main className="pt-24">
        <section className="px-6 pb-8 pt-12 sm:px-8 lg:px-10">
          <div className="mx-auto max-w-2xl text-center">
            <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-500">Legal · Last updated {lastUpdated}</div>
            <h1 className="mt-4 text-balance text-[34px] font-semibold leading-[1.06] tracking-[-0.04em] text-zinc-950 sm:text-[46px]">
              Privacy Policy
            </h1>
            <p className="mx-auto mt-4 max-w-xl text-[15px] leading-7 text-zinc-600 sm:text-[16px] sm:leading-8">
              How Worklone collects, uses, and protects your data when you use our AI employee platform.
            </p>
          </div>
        </section>

        <section className="px-6 pb-20 sm:px-8 lg:px-10">
          <div className="mx-auto max-w-5xl">
            <div className="space-y-16">
              {/* Introduction */}
              <div className="grid gap-8 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Introduction</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <p>
                    Worklone ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform for building and managing AI employees.
                  </p>
                  <p>
                    By accessing or using Worklone, you agree to the collection and use of information in accordance with this policy. If you do not agree with the terms of this policy, please do not access the platform.
                  </p>
                </div>
              </div>

              {/* Information We Collect */}
              <section className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Information We Collect</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <h3 className="text-[17px] font-semibold text-zinc-900">Account Information</h3>
                  <p>When you create an account, we collect your name, email address, and company name. This information is used to identify your account and provide access to the platform.</p>

                  <h3 className="text-[17px] font-semibold text-zinc-900">Usage Data</h3>
                  <p>We collect data about how you interact with the platform, including workflows created, AI employees provisioned, tasks executed, and integrations connected. This data helps us understand platform usage and improve our services.</p>

                  <h3 className="text-[17px] font-semibold text-zinc-900">AI Employee Data</h3>
                  <p>When you configure AI employees, we store their identity, instructions, skills, memory context, and access boundaries. This data is essential for the employees to function within your workspace and is encrypted at rest and in transit.</p>

                  <h3 className="text-[17px] font-semibold text-zinc-900">Integration Data</h3>
                  <p>When you connect third-party tools (Slack, Jira, GitHub, Gmail, etc.), we collect authentication tokens and metadata necessary to operate integrations. We do not store the content of your third-party tool data unless it is directly processed by an AI employee under your instruction.</p>

                  <h3 className="text-[17px] font-semibold text-zinc-900">Automatically Collected Data</h3>
                  <p>We collect browser type, device information, IP address, and access timestamps for security, analytics, and platform performance monitoring.</p>
                </div>
              </section>

              {/* How We Use Your Information */}
              <section className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">How We Use Data</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <p>We use the information we collect to:</p>
                  <ul className="mb-6 space-y-3 pl-0 text-[15px] leading-7 text-zinc-700">
                    {['Provision and manage your AI employees', 'Execute tasks and workflows on your behalf', 'Improve platform performance and AI capabilities', 'Monitor security and prevent unauthorized access', 'Communicate platform updates, maintenance, and policy changes', 'Analyze usage patterns to enhance user experience', 'Comply with legal obligations'].map((item) => (
                      <li key={item} className="flex items-start gap-3">
                        <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-900" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </section>

              {/* Data Storage and Security */}
              <section className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Security</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <p>
                    We implement industry-standard security measures to protect your data, including encryption in transit (TLS) and at rest, access controls, and regular security audits.
                  </p>
                  <p>
                    AI employee memory and context data is isolated per organization and per employee. We do not share your data with other organizations or use your data to train models that benefit other customers.
                  </p>
                  <p>
                    While we strive to protect your personal information, no method of transmission over the Internet or electronic storage is 100% secure. We cannot guarantee absolute security but continuously invest in improving our security posture.
                  </p>
                </div>
              </section>

              {/* Data Sharing */}
              <section className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Data Sharing</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <p>We do not sell your personal information. We may share your data only in the following circumstances:</p>
                  <ul className="mb-6 space-y-3 pl-0 text-[15px] leading-7 text-zinc-700">
                    <li className="flex items-start gap-3">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-900" />
                      <span><strong>With your consent:</strong> When you authorize an AI employee to interact with a third-party integration, data is shared as necessary to complete that action.</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-900" />
                      <span><strong>Service providers:</strong> We engage trusted third-party providers for hosting, infrastructure, and analytics. These providers are contractually bound to use data only for the services they provide.</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-900" />
                      <span><strong>Legal requirements:</strong> We may disclose data if required by law, regulation, or legal process.</span>
                    </li>
                    <li className="flex items-start gap-3">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-900" />
                      <span><strong>Business transfers:</strong> In the event of a merger, acquisition, or asset sale, your data may be transferred as part of that transaction. We will notify you of any change in ownership.</span>
                    </li>
                  </ul>
                </div>
              </section>

              {/* AI-Specific Considerations */}
              <section className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">AI & Data</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <h3 className="text-[17px] font-semibold text-zinc-900">Model Processing</h3>
                  <p>
                    AI employees process data through large language models provided by third-party model providers. Data sent to these models is processed in accordance with their respective privacy policies and is not used to train their base models. We route data through enterprise-grade API endpoints that provide additional data protection guarantees.
                  </p>

                  <h3 className="text-[17px] font-semibold text-zinc-900">Employee Memory</h3>
                  <p>
                    AI employees retain contextual memory of their interactions, decisions, and outcomes within your organization. This memory is scoped to the employee's role and access boundaries. You can review, modify, or clear employee memory at any time through the platform.
                  </p>

                  <h3 className="text-[17px] font-semibold text-zinc-900">Audit Trails</h3>
                  <p>
                    All AI employee actions are logged with timestamps, decisions made, tools used, and outcomes. These audit trails are available to administrators for review and governance purposes.
                  </p>
                </div>
              </section>

              {/* Your Rights */}
              <section className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Your Rights</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <p>You have the right to:</p>
                  <ul className="mb-6 space-y-3 pl-0 text-[15px] leading-7 text-zinc-700">
                    {['Access your personal data and request a copy', 'Correct inaccurate or incomplete data', 'Request deletion of your account and associated data', 'Export your data in a portable format', 'Object to or restrict certain data processing', 'Withdraw consent for data processing at any time'].map((item) => (
                      <li key={item} className="flex items-start gap-3">
                        <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-900" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                  <p>
                    To exercise any of these rights, contact us at <a href="mailto:hritvik@nanosecondlabs.com" className="font-medium text-zinc-900 underline decoration-zinc-300 underline-offset-4 hover:text-zinc-700">hritvik@nanosecondlabs.com</a>. We will respond within 30 days.
                  </p>
                </div>
              </section>

              {/* Data Retention */}
              <section className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Retention</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <p>
                    We retain your data for as long as your account is active or as needed to provide services. If you delete your account, we will delete or anonymize your personal data within 30 days, except where retention is required by law or for legitimate business purposes (such as security logs).
                  </p>
                  <p>
                    AI employee memory and workflow data is deleted when the employee is decommissioned or when your organization is deleted.
                  </p>
                </div>
              </section>

              {/* Children's Privacy */}
              <section className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Children</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <p>
                    Worklone is not intended for use by individuals under the age of 18. We do not knowingly collect personal information from children. If we become aware that we have collected data from a child without parental consent, we will take steps to delete that information.
                  </p>
                </div>
              </section>

              {/* Changes */}
              <section className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Changes</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <p>
                    We may update this Privacy Policy from time to time. We will notify you of material changes by posting a notice on the platform or sending an email to the address associated with your account. Your continued use of Worklone after changes constitutes acceptance of the updated policy.
                  </p>
                </div>
              </section>

              {/* Contact */}
              <section className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Contact</div>
                <div className="space-y-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8">
                  <p>
                    If you have questions about this Privacy Policy or our data practices, please contact us:
                  </p>
                  <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-5">
                    <p className="text-sm text-zinc-700">
                      <strong className="text-zinc-900">Worklone</strong><br />
                      Email: <a href="mailto:hritvik@nanosecondlabs.com" className="font-medium text-zinc-900 underline decoration-zinc-300 underline-offset-4 hover:text-zinc-700">hritvik@nanosecondlabs.com</a>
                    </p>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
