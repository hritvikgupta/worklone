import React, { useMemo, useState } from 'react';
import { ArrowRight, ChevronDown, BookOpen, Mail, Send, Building2, User, MessageSquare } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { researchArticles } from './ResearchArticlePage';

type SubmitState = 'idle' | 'submitting' | 'success' | 'error';

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
          </div>
        </div>
      </div>
    </footer>
  );
}

function ResearchDropdown() {
  const [isOpen, setIsOpen] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950"
      >
        <BookOpen className="h-4 w-4" />
        Research
        <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-72 rounded-2xl border border-zinc-200 bg-white p-2 shadow-lg">
          <div className="px-3 py-2">
            <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-400">Articles</div>
          </div>
          <div className="space-y-1">
            {researchArticles.map((article) => (
              <Link
                key={article.slug}
                to={`/research/${article.slug}`}
                onClick={() => setIsOpen(false)}
                className="block rounded-xl px-3 py-3 transition-colors hover:bg-zinc-50"
              >
                <div className="text-sm font-medium text-zinc-900">{article.title}</div>
                <div className="mt-1 text-xs text-zinc-500 line-clamp-1">{article.subtitle}</div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function ContactPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [submitState, setSubmitState] = useState<SubmitState>('idle');
  const [submitMessage, setSubmitMessage] = useState('');

  const isSubmitting = submitState === 'submitting';
  const isSuccess = submitState === 'success';

  const buttonLabel = useMemo(() => {
    if (submitState === 'submitting') return 'Sending...';
    if (submitState === 'success') return 'Message Sent';
    return 'Send Message';
  }, [submitState]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitState('submitting');
    setSubmitMessage('');

    try {
      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          company: company.trim(),
          subject: subject.trim(),
          message: message.trim(),
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.reason || data?.error || 'Unable to send your message right now.');
      }

      setSubmitState('success');
      setSubmitMessage(data?.message || 'Thank you. We will get back to you soon.');
      setName('');
      setEmail('');
      setCompany('');
      setSubject('');
      setMessage('');
    } catch (error) {
      setSubmitState('error');
      setSubmitMessage(error instanceof Error ? error.message : 'Unable to send your message right now.');
    }
  };

  return (
    <div className="min-h-screen bg-white text-zinc-950">
      <header className="fixed inset-x-0 top-0 z-40 bg-white/94 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 sm:px-8 lg:px-10">
          <Link to="/" className="flex items-center gap-3">
            <img src="/brand/worklone-mark-black.png" alt="Worklone" className="h-7 w-auto" />
            <div className="text-lg font-semibold tracking-tight">Worklone</div>
          </Link>

          <div className="flex items-center gap-4">
            <Link to="/" className="hidden text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950 sm:block">
              Home
            </Link>
            <ResearchDropdown />
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
            <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-500">Get in Touch</div>
            <h1 className="mt-4 text-balance text-[34px] font-semibold leading-[1.06] tracking-[-0.04em] text-zinc-950 sm:text-[46px]">
              Contact Us
            </h1>
            <p className="mx-auto mt-4 max-w-xl text-[15px] leading-7 text-zinc-600 sm:text-[16px] sm:leading-8">
              Have questions about Worklone, want to discuss a deployment, or need support? We would love to hear from you.
            </p>
          </div>
        </section>

        <section className="px-6 pb-20 sm:px-8 lg:px-10">
          <div className="mx-auto max-w-5xl">
            <div className="grid gap-12 lg:grid-cols-[1fr_1fr] lg:gap-16">
              {/* Left: Contact Info */}
              <div className="space-y-10">
                <div>
                  <h2 className="text-xl font-semibold tracking-tight text-zinc-950">Reach Out Directly</h2>
                  <p className="mt-2 text-sm leading-7 text-zinc-600">
                    Whether you are exploring AI employees for your team or need help with an existing deployment, our team is here to help.
                  </p>
                </div>

                <div className="space-y-6">
                  {/* Email */}
                  <div className="flex items-start gap-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-zinc-200 bg-zinc-50">
                      <Mail className="h-4 w-4 text-zinc-600" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-zinc-900">Email</div>
                      <a
                        href="mailto:hritvik@nanosecondlabs.com"
                        className="mt-0.5 text-sm text-zinc-600 underline decoration-zinc-300 underline-offset-4 hover:text-zinc-900"
                      >
                        hritvik@nanosecondlabs.com
                      </a>
                      <p className="mt-1 text-xs text-zinc-400">We typically respond within 24 hours on business days.</p>
                    </div>
                  </div>

                  {/* Enterprise */}
                  <div className="flex items-start gap-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-zinc-200 bg-zinc-50">
                      <Building2 className="h-4 w-4 text-zinc-600" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-zinc-900">Enterprise Inquiries</div>
                      <p className="mt-0.5 text-sm text-zinc-600">
                        Interested in deploying Worklone across your organization? Email us with your company size and use cases, and we will set up a dedicated conversation.
                      </p>
                    </div>
                  </div>

                  {/* Support */}
                  <div className="flex items-start gap-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-zinc-200 bg-zinc-50">
                      <MessageSquare className="h-4 w-4 text-zinc-600" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-zinc-900">Platform Support</div>
                      <p className="mt-0.5 text-sm text-zinc-600">
                        If you are already using Worklone and need assistance, reach out through the in-app chat or email us directly with your account details.
                      </p>
                    </div>
                  </div>
                </div>

                {/* What to expect */}
                <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-6">
                  <h3 className="text-sm font-semibold text-zinc-900">What to Expect</h3>
                  <ul className="mt-3 space-y-2.5 text-sm text-zinc-600">
                    <li className="flex items-start gap-2">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-zinc-900" />
                      <span>Initial response within 24 hours</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-zinc-900" />
                      <span>Product demos and walkthroughs available on request</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-zinc-900" />
                      <span>Enterprise pricing and deployment timelines discussed individually</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-zinc-900" />
                      <span>Waitlist members receive priority access as we open new cohorts</span>
                    </li>
                  </ul>
                </div>
              </div>

              {/* Right: Contact Form */}
              <div>
                <div className="rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8">
                  <h2 className="text-lg font-semibold tracking-tight text-zinc-950">Send a Message</h2>
                  <p className="mt-1 text-sm text-zinc-500">Fill out the form below and we will get back to you promptly.</p>

                  <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-zinc-900 mb-1.5">Full Name</label>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                        <input
                          type="text"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          className="w-full rounded-lg border border-zinc-200 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900"
                          placeholder="Your name"
                          required
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-zinc-900 mb-1.5">Email</label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                        <input
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="w-full rounded-lg border border-zinc-200 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900"
                          placeholder="you@company.com"
                          required
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-zinc-900 mb-1.5">Company</label>
                      <div className="relative">
                        <Building2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                        <input
                          type="text"
                          value={company}
                          onChange={(e) => setCompany(e.target.value)}
                          className="w-full rounded-lg border border-zinc-200 py-2.5 pl-10 pr-3 text-sm text-zinc-900 outline-none transition focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900"
                          placeholder="Company name"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-zinc-900 mb-1.5">Subject</label>
                      <select
                        value={subject}
                        onChange={(e) => setSubject(e.target.value)}
                        className="w-full rounded-lg border border-zinc-200 py-2.5 px-3 text-sm text-zinc-900 outline-none transition focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 appearance-none bg-white"
                        required
                      >
                        <option value="">Select a topic</option>
                        <option value="general">General Inquiry</option>
                        <option value="enterprise">Enterprise Deployment</option>
                        <option value="pricing">Pricing Question</option>
                        <option value="support">Platform Support</option>
                        <option value="partnership">Partnership</option>
                        <option value="other">Other</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-zinc-900 mb-1.5">Message</label>
                      <textarea
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        rows={4}
                        className="w-full rounded-lg border border-zinc-200 py-2.5 px-3 text-sm text-zinc-900 outline-none transition focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 resize-none"
                        placeholder="Tell us how we can help..."
                        required
                      />
                    </div>

                    {submitMessage && (
                      <div
                        className={cn(
                          'rounded-lg border px-3 py-2.5 text-sm',
                          submitState === 'success'
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                            : 'border-red-200 bg-red-50 text-red-700'
                        )}
                      >
                        {submitMessage}
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={isSubmitting || isSuccess}
                      className={cn(
                        'inline-flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors',
                        'bg-zinc-950 text-white hover:bg-zinc-800',
                        'disabled:cursor-not-allowed disabled:opacity-70'
                      )}
                    >
                      {isSuccess ? null : <Send className="h-4 w-4" />}
                      {buttonLabel}
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
