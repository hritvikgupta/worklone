import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import type { EmployeeModelOption } from '@/src/api/employees';

interface ModelSelectProps {
  value: string;
  onChange: (value: string) => void;
  models: EmployeeModelOption[];
  loading?: boolean;
  error?: string | null;
  provider?: string;
  onProviderChange?: (provider: string) => void;
  availableProviders?: Array<{id: string; name: string; description: string; available: boolean}>;
}

function formatContextLength(value: number): string {
  if (!value) return '';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(value % 1_000_000 === 0 ? 0 : 1)}M`;
  if (value >= 1_000) return `${Math.round(value / 1_000)}K`;
  return `${value}`;
}

export function ModelSelect({ 
  value, 
  onChange, 
  models, 
  loading, 
  error,
  provider = 'openrouter',
  onProviderChange,
  availableProviders = [],
}: ModelSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, []);

  const selectedModel = useMemo(
    () => models.find((model) => model.id === value) || null,
    [models, value],
  );

  const filteredModels = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return models;
    return models.filter((model) => {
      const haystack = `${model.name} ${model.id} ${model.description}`.toLowerCase();
      return haystack.includes(normalized);
    });
  }, [models, query]);

  const providerName = useMemo(() => {
    return availableProviders.find(p => p.id === provider)?.name || provider;
  }, [provider, availableProviders]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          'flex w-full items-center justify-between rounded-xl border border-border bg-card px-3 py-3 text-left shadow-sm transition-colors',
          open ? 'border-primary ring-1 ring-ring' : 'hover:border-border',
        )}
      >
        <div className="min-w-0">
          {value ? (
            <>
              <div className="truncate text-sm font-medium text-foreground">
                {selectedModel?.name || value}
              </div>
              <div className="truncate text-xs text-muted-foreground">
                {selectedModel?.id || value}
              </div>
            </>
          ) : (
            <div className="truncate text-sm text-muted-foreground">Select a model…</div>
          )}
        </div>
        <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', open && 'rotate-180')} />
      </button>

      {error && (
        <p className="mt-2 text-xs text-amber-600">
          Failed to load models. Showing the current model only.
        </p>
      )}

      {open && (
        <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-50 overflow-hidden rounded-2xl border border-border bg-card shadow-[0_18px_50px_rgba(24,24,27,0.14)]">
          <div className="border-b border-border bg-muted/80 p-3">
            {/* Provider selector */}
            {onProviderChange && availableProviders.length > 0 && (
              <div className="mb-3 flex gap-2">
                {availableProviders.filter(p => p.available).map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => onProviderChange(p.id)}
                    className={cn(
                      'flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition-colors',
                      provider === p.id 
                        ? 'border-primary bg-primary/10 text-primary' 
                        : 'border-border bg-card hover:bg-muted',
                    )}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            )}
            
            <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-3">
              <Search className="h-4 w-4 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={`Search ${providerName} models`}
                className="h-10 border-0 bg-transparent px-0 shadow-none focus-visible:border-0 focus-visible:ring-0"
              />
            </div>
            <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
              <span>{loading ? 'Loading models...' : `${filteredModels.length} models`}</span>
              <span>{providerName} catalog</span>
            </div>
          </div>

          <div className="max-h-80 overflow-y-auto p-2">
            {loading && models.length === 0 ? (
              <div className="rounded-xl px-3 py-6 text-center text-sm text-muted-foreground">
                Loading models from {providerName}...
              </div>
            ) : filteredModels.length === 0 ? (
              <div className="rounded-xl px-3 py-6 text-center text-sm text-muted-foreground">
                No models match your search.
              </div>
            ) : (
              filteredModels.map((model) => (
                <button
                  key={model.id}
                  type="button"
                  onClick={() => {
                    onChange(model.id);
                    setOpen(false);
                    setQuery('');
                  }}
                  className={cn(
                    'flex w-full items-start gap-3 rounded-xl px-3 py-3 text-left transition-colors',
                    model.id === value ? 'bg-primary text-primary-foreground' : 'hover:bg-muted',
                  )}
                >
                  <div className="pt-0.5">
                    <div
                      className={cn(
                        'flex h-5 w-5 items-center justify-center rounded-full border',
                        model.id === value ? 'border-white/30 bg-card/10' : 'border-border bg-card',
                      )}
                    >
                      {model.id === value && <Check className="h-3.5 w-3.5" />}
                    </div>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className={cn('truncate text-sm font-semibold', model.id === value ? 'text-white' : 'text-foreground')}>
                      {model.name}
                    </div>
                    <div className={cn('mt-0.5 truncate text-xs', model.id === value ? 'text-muted-foreground' : 'text-muted-foreground')}>
                      {model.id}
                    </div>
                    {model.description && (
                      <p className={cn('mt-2 line-clamp-2 text-xs leading-5', model.id === value ? 'text-muted-foreground' : 'text-muted-foreground')}>
                        {model.description}
                      </p>
                    )}
                  </div>
                  {model.context_length > 0 && (
                    <div
                      className={cn(
                        'shrink-0 rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em]',
                        model.id === value
                          ? 'border-white/20 bg-card/10 text-white'
                          : 'border-border bg-muted text-muted-foreground',
                      )}
                    >
                      {formatContextLength(model.context_length)} ctx
                    </div>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
