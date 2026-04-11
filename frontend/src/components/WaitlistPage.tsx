import React, { useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, Building2, Check, Mail, User } from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { cn } from '@/lib/utils';

type SubmitState = 'idle' | 'submitting' | 'success' | 'error';

export function WaitlistPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [submitState, setSubmitState] = useState<SubmitState>('idle');
  const [message, setMessage] = useState('');

  const isSubmitting = submitState === 'submitting';
  const isSuccess = submitState === 'success';

  const buttonLabel = useMemo(() => {
    if (submitState === 'submitting') return 'Joining...';
    if (submitState === 'success') return 'You are on the list';
    return 'Join Waitlist';
  }, [submitState]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitState('submitting');
    setMessage('');

    try {
      const response = await fetch('/api/waitlist', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          company: company.trim(),
          source: 'landing_page',
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(data?.reason || data?.error || 'Unable to join the waitlist right now.');
      }

      setSubmitState('success');
      setMessage(data?.message || 'Your email has been recorded. We will be in touch.');
    } catch (error) {
      setSubmitState('error');
      setMessage(error instanceof Error ? error.message : 'Unable to join the waitlist right now.');
    }
  };

  return (
    <div className="min-h-screen bg-white text-zinc-950">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-6 sm:px-8 lg:px-10">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <img
              src="/brand/worklone-mark-black.png"
              alt="Worklone"
              className="h-7 w-auto"
            />
            <span className="text-lg font-semibold tracking-tight">Worklone</span>
          </Link>

          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>
        </div>

        <div className="flex flex-1 items-center justify-center py-12 sm:py-16">
          <div className="grid w-full max-w-6xl gap-12 lg:grid-cols-[minmax(0,1.15fr)_minmax(420px,0.85fr)] lg:items-start">
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
              className="max-w-2xl"
            >
              <p className="text-sm font-medium uppercase tracking-[0.28em] text-zinc-400">
                Early Access
              </p>
              <h1 className="mt-6 text-balance text-5xl font-semibold tracking-[-0.05em] text-zinc-950 sm:text-6xl">
                Join the waitlist for AI employees built to do real work.
              </h1>
              <p className="mt-6 max-w-xl text-[17px] leading-8 text-zinc-600">
                Worklone is building specialized, self-adaptive AI employees that operate inside real
                company systems. We are opening access in stages while the backend platform is still
                being finished.
              </p>
              <p className="mt-5 max-w-xl text-[17px] leading-8 text-zinc-600">
                Leave your email and we will notify you when the workspace is ready for broader
                onboarding.
              </p>

              <div className="mt-10 grid gap-6 border-t border-zinc-200 pt-8 sm:grid-cols-3">
                <div>
                  <div className="text-2xl font-semibold tracking-tight text-zinc-950">Specialized</div>
                  <p className="mt-2 text-sm leading-6 text-zinc-500">
                    Employees tuned for product, engineering, analytics, operations, and more.
                  </p>
                </div>
                <div>
                  <div className="text-2xl font-semibold tracking-tight text-zinc-950">Adaptive</div>
                  <p className="mt-2 text-sm leading-6 text-zinc-500">
                    Agents that reason, act, recover, and improve inside live operating workflows.
                  </p>
                </div>
                <div>
                  <div className="text-2xl font-semibold tracking-tight text-zinc-950">Operational</div>
                  <p className="mt-2 text-sm leading-6 text-zinc-500">
                    Built to orchestrate work across tools, systems, and teams instead of just chat.
                  </p>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.05 }}
              className="rounded-[28px] border border-zinc-200 bg-white p-7 shadow-[0_20px_70px_rgba(0,0,0,0.06)] sm:p-8"
            >
              <div className="mb-8">
                <h2 className="text-2xl font-semibold tracking-tight text-zinc-950">
                  Request access
                </h2>
                <p className="mt-2 text-sm leading-6 text-zinc-500">
                  We are inviting teams in batches. Submit your details and we will reach out when
                  access opens.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-zinc-700">Name</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full rounded-xl border border-zinc-200 py-3 pl-10 pr-4 text-sm text-zinc-900 outline-none transition focus:border-zinc-900"
                      placeholder="Your name"
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-zinc-700">Work email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full rounded-xl border border-zinc-200 py-3 pl-10 pr-4 text-sm text-zinc-900 outline-none transition focus:border-zinc-900"
                      placeholder="you@company.com"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-zinc-700">Company</label>
                  <div className="relative">
                    <Building2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                    <input
                      type="text"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      className="w-full rounded-xl border border-zinc-200 py-3 pl-10 pr-4 text-sm text-zinc-900 outline-none transition focus:border-zinc-900"
                      placeholder="Company name"
                    />
                  </div>
                </div>

                {message && (
                  <div
                    className={cn(
                      'rounded-xl border px-4 py-3 text-sm',
                      submitState === 'success'
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                        : 'border-red-200 bg-red-50 text-red-700'
                    )}
                  >
                    {message}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting || isSuccess}
                  className={cn(
                    'inline-flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-medium transition-colors',
                    'bg-zinc-950 text-white hover:bg-zinc-800',
                    'disabled:cursor-not-allowed disabled:opacity-70'
                  )}
                >
                  {isSuccess ? <Check className="h-4 w-4" /> : <ArrowRight className="h-4 w-4" />}
                  {buttonLabel}
                </button>
              </form>

              <p className="mt-5 text-xs leading-5 text-zinc-400">
                By joining, you agree to receive product updates related to early access.
              </p>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}
