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
    <div className="flex h-screen bg-white overflow-hidden">
      {/* Left Panel - Waitlist Form */}
      <div className="flex flex-1 flex-col p-4 lg:p-8 relative overflow-y-auto">
        <div className="w-full max-w-xl mx-auto flex flex-col min-h-full justify-center">
          <div className="flex items-center justify-between mb-6">
            <Link to="/" className="flex items-center gap-2">
              <img
                src="/brand/worklone-mark-black.png"
                alt="Worklone"
                className="h-5 w-auto"
              />
              <span className="text-sm font-semibold tracking-tight text-zinc-950">Worklone</span>
            </Link>

            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-600 transition-colors hover:text-zinc-950"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back
            </Link>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-zinc-400">
              Early Access
            </p>
            <h1 className="mt-2 text-balance text-3xl font-semibold tracking-[-0.04em] text-zinc-950 sm:text-4xl">
              Join the waitlist for AI employees built to do real work.
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-zinc-600">
              Worklone is building specialized, self-adaptive AI employees that operate inside real
              company systems. We are opening access in stages while the backend platform is still
              being finished.
            </p>

            <div className="mt-6 mb-6 max-w-md">
              <h2 className="text-lg font-semibold tracking-tight text-zinc-950 mb-3">
                Request access
              </h2>
              <form onSubmit={handleSubmit} className="space-y-2.5">
                <div>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full rounded-lg border border-zinc-200 py-2 pl-9 pr-3 text-sm text-zinc-900 outline-none transition focus:border-zinc-900"
                      placeholder="Your name"
                    />
                  </div>
                </div>

                <div>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full rounded-lg border border-zinc-200 py-2 pl-9 pr-3 text-sm text-zinc-900 outline-none transition focus:border-zinc-900"
                      placeholder="Work email (you@company.com)"
                      required
                    />
                  </div>
                </div>

                <div>
                  <div className="relative">
                    <Building2 className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
                    <input
                      type="text"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      className="w-full rounded-lg border border-zinc-200 py-2 pl-9 pr-3 text-sm text-zinc-900 outline-none transition focus:border-zinc-900"
                      placeholder="Company name"
                    />
                  </div>
                </div>

                {message && (
                  <div
                    className={cn(
                      'rounded-lg border px-3 py-2 text-xs',
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
                    'inline-flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors mt-2',
                    'bg-zinc-950 text-white hover:bg-zinc-800',
                    'disabled:cursor-not-allowed disabled:opacity-70'
                  )}
                >
                  {isSuccess ? <Check className="h-3.5 w-3.5" /> : <ArrowRight className="h-3.5 w-3.5" />}
                  {buttonLabel}
                </button>
              </form>
              <p className="mt-3 text-[11px] leading-5 text-zinc-400">
                By joining, you agree to receive product updates related to early access.
              </p>
            </div>

            <div className="grid gap-3 border-t border-zinc-200 pt-5 sm:grid-cols-3">
              <div>
                <div className="text-sm font-semibold tracking-tight text-zinc-950">Specialized</div>
                <p className="mt-1 text-xs leading-relaxed text-zinc-500">
                  Employees tuned for product, engineering, analytics, operations.
                </p>
              </div>
              <div>
                <div className="text-sm font-semibold tracking-tight text-zinc-950">Adaptive</div>
                <p className="mt-1 text-xs leading-relaxed text-zinc-500">
                  Agents that reason, act, recover, and improve inside workflows.
                </p>
              </div>
              <div>
                <div className="text-sm font-semibold tracking-tight text-zinc-950">Operational</div>
                <p className="mt-1 text-xs leading-relaxed text-zinc-500">
                  Built to orchestrate work across tools, systems, and teams.
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right Panel - Image */}
      <div className="hidden lg:block relative flex-1 bg-zinc-900">
        <img
          src="/login.jpg"
          alt="Worklone Space"
          className="absolute inset-0 h-full w-full object-cover object-center"
        />
      </div>
    </div>
  );
}
