import React, { useState } from 'react';
import { Sparkles, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Button } from '@/components/ui/button';

interface ProvisionModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: { name: string; description: string }) => void;
  initialName?: string;
  initialDescription?: string;
}

export function ProvisionModal({ open, onClose, onSubmit, initialName = '', initialDescription = '' }: ProvisionModalProps) {
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);

  React.useEffect(() => {
    if (open) {
      setName(initialName);
      setDescription(initialDescription);
    }
  }, [open, initialName, initialDescription]);

  const handleGenerate = async () => {
    const trimmedName = name.trim();
    if (!trimmedName) return;
    onSubmit({ name: trimmedName, description: description.trim() });
    setName('');
    setDescription('');
    onClose();
  };

  const handleClose = () => {
    setName('');
    setDescription('');
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
            className="fixed inset-0 z-50 bg-background/40 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-card p-6 shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Provision Employee</h3>
                  <p className="text-[11px] text-muted-foreground">AI will generate the full configuration</p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-muted-foreground transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Form */}
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">
                  Employee Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alex, Jordan, Mira"
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && name.trim()) handleGenerate();
                  }}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">
                  What should this employee do?
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Manage our product backlog, conduct user research, and coordinate with engineering on sprint planning..."
                  rows={4}
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
                />
                <p className="mt-1 text-[11px] text-muted-foreground">
                  The more detail you provide, the better the generated persona will be.
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="mt-6 flex items-center justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleClose}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleGenerate}
                disabled={!name.trim()}
                className="gap-1.5 text-xs bg-primary text-primary-foreground hover:bg-primary/80"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Generate Employee
              </Button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
