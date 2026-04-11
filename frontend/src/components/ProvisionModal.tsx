import React, { useState } from 'react';
import { Sparkles, Loader2, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Button } from '@/components/ui/button';
import { generateEmployeePrompt, GeneratedPromptResult } from '@/src/api/employees';
import type { EmployeeFormData } from '@/src/components/EmployeePanel';

interface ProvisionModalProps {
  open: boolean;
  onClose: () => void;
  onGenerated: (form: EmployeeFormData) => void;
}

export function ProvisionModal({ open, onClose, onGenerated }: ProvisionModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!name.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const result: GeneratedPromptResult = await generateEmployeePrompt(
        name.trim(),
        description.trim(),
      );

      const form: EmployeeFormData = {
        name: name.trim(),
        role: result.role,
        avatar_url: '',
        description: description.trim(),
        system_prompt: result.system_prompt,
        model: 'openai/gpt-4o',
        temperature: 0.7,
        max_tokens: 4096,
        tools: result.tools,
        skills: result.skills,
      };

      onGenerated(form);
      // Reset for next time
      setName('');
      setDescription('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate prompt');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (loading) return;
    setName('');
    setDescription('');
    setError(null);
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-950">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-zinc-900">Provision Employee</h3>
                  <p className="text-[11px] text-zinc-500">AI will generate the full configuration</p>
                </div>
              </div>
              <button
                onClick={handleClose}
                disabled={loading}
                className="rounded-md p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 transition-colors disabled:opacity-50"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Form */}
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-zinc-700">
                  Employee Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alex, Jordan, Mira"
                  disabled={loading}
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950 disabled:opacity-60"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && name.trim()) handleGenerate();
                  }}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-zinc-700">
                  What should this employee do?
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Manage our product backlog, conduct user research, and coordinate with engineering on sprint planning..."
                  rows={4}
                  disabled={loading}
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-950 focus:outline-none focus:ring-1 focus:ring-zinc-950 disabled:opacity-60"
                />
                <p className="mt-1 text-[11px] text-zinc-400">
                  The more detail you provide, the better the generated persona will be.
                </p>
              </div>

              {error && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {error}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="mt-6 flex items-center justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleClose}
                disabled={loading}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleGenerate}
                disabled={loading || !name.trim()}
                className="gap-1.5 text-xs bg-zinc-950 text-white hover:bg-zinc-800"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3.5 w-3.5" />
                    Generate Employee
                  </>
                )}
              </Button>
            </div>

            {/* Loading overlay */}
            {loading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center rounded-xl bg-white/80 backdrop-blur-[2px]">
                <div className="flex flex-col items-center gap-3">
                  <div className="relative">
                    <div className="h-10 w-10 rounded-full border-2 border-zinc-200" />
                    <div className="absolute inset-0 h-10 w-10 animate-spin rounded-full border-2 border-transparent border-t-zinc-950" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-zinc-900">Crafting employee persona...</p>
                    <p className="mt-0.5 text-[11px] text-zinc-500">Kimi K2.5 is generating the system prompt, tools, and skills</p>
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
