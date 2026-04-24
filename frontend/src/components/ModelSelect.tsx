import React, { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { EmployeeModelOption } from '@/src/api/employees';

interface ModelSelectProps {
  value: string;
  onChange: (value: string) => void;
  models: EmployeeModelOption[];
  loading?: boolean;
  error?: string | null;
  provider?: string;
  onProviderChange?: (provider: string) => void;
  availableProviders?: Array<{ id: string; name: string; description: string; available: boolean }>;
}

const PROVIDER_ORDER = ['anthropic', 'openai', 'google', 'qwen', 'moonshotai'];

const PROVIDER_META: Record<string, { name: string; domain: string }> = {
  anthropic: { name: 'Anthropic', domain: 'anthropic.com' },
  openai: { name: 'OpenAI', domain: 'openai.com' },
  google: { name: 'Google', domain: 'google.com' },
  qwen: { name: 'Qwen', domain: 'qwenlm.ai' },
  moonshotai: { name: 'Moonshot', domain: 'moonshot.ai' },
};

function getProviderMeta(prefix: string) {
  return PROVIDER_META[prefix] || { name: prefix, domain: `${prefix}.com` };
}

export function ModelSelect({
  value,
  onChange,
  models,
  loading,
  error,
}: ModelSelectProps) {
  const [open, setOpen] = useState(false);
  const [drillProvider, setDrillProvider] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const map: Record<string, EmployeeModelOption[]> = {};
    for (const m of models) {
      const prefix = m.id.split('/')[0] || 'other';
      if (!PROVIDER_ORDER.includes(prefix)) continue;
      (map[prefix] = map[prefix] || []).push(m);
    }

    for (const key of Object.keys(map)) {
      map[key] = [...map[key]].sort((a, b) => {
        const an = (a.name || a.id).toLowerCase();
        const bn = (b.name || b.id).toLowerCase();
        return an.localeCompare(bn);
      });
    }

    return map;
  }, [models]);

  const providerKeys = useMemo(
    () => PROVIDER_ORDER.filter((provider) => (grouped[provider] || []).length > 0),
    [grouped]
  );

  const selectedLabel = useMemo(() => {
    const hit = models.find((m) => m.id === value);
    return hit?.name || value || '';
  }, [models, value]);

  const drilledModels = useMemo(() => {
    if (!drillProvider) return [];
    return grouped[drillProvider] || [];
  }, [drillProvider, grouped]);

  const valueInKnownList = useMemo(() => models.some((m) => m.id === value), [models, value]);

  return (
    <div className="space-y-1.5">
      <Select
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) setDrillProvider(null);
        }}
        value={value || undefined}
        onValueChange={(next) => {
          onChange(next);
          setOpen(false);
          setDrillProvider(null);
        }}
      >
        <SelectTrigger className="h-[52px] w-full rounded-xl border border-border bg-background px-3 text-left shadow-sm">
          <div className="min-w-0 w-full">
            <SelectValue placeholder="Select a model…">
              {value ? <span className="block truncate text-sm font-medium text-foreground">{selectedLabel}</span> : null}
            </SelectValue>
          </div>
        </SelectTrigger>

        <SelectContent className="max-h-[380px] w-[var(--radix-select-trigger-width)] rounded-xl p-1">
          {loading && models.length === 0 ? (
            <div className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading models...
            </div>
          ) : drillProvider ? (
            <>
              <button
                type="button"
                onClick={() => setDrillProvider(null)}
                className="mb-1 flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm font-medium text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              >
                <ChevronLeft className="h-4 w-4" />
                {getProviderMeta(drillProvider).name}
              </button>

              <SelectGroup>
                {drilledModels.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    <div className="min-w-0 truncate text-sm">{m.name || m.id.split('/')[1] || m.id}</div>
                  </SelectItem>
                ))}

                {!drilledModels.length && (
                  <div className="px-3 py-2 text-sm text-muted-foreground">No models found.</div>
                )}
              </SelectGroup>
            </>
          ) : (
            <div className="space-y-1 py-1">
              {providerKeys.map((provider) => {
                const meta = getProviderMeta(provider);
                return (
                  <button
                    key={provider}
                    type="button"
                    onClick={() => setDrillProvider(provider)}
                    className="flex w-full items-center gap-3 rounded-md px-2.5 py-2 text-left hover:bg-muted/50"
                  >
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(meta.domain)}&sz=64`}
                      alt={`${meta.name} icon`}
                      className="h-6 w-6 rounded-sm bg-muted p-0.5 object-contain"
                    />
                    <span className="flex-1 text-sm font-semibold text-foreground">{meta.name}</span>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </button>
                );
              })}

              {!providerKeys.length && !value && (
                <div className="px-3 py-2 text-sm text-muted-foreground">No models found.</div>
              )}

              {!valueInKnownList && value && (
                <div className="border-t border-border mt-1 pt-1">
                  <SelectItem value={value}>
                    <div className="min-w-0 truncate text-sm">{selectedLabel}</div>
                  </SelectItem>
                </div>
              )}
            </div>
          )}
        </SelectContent>
      </Select>

      {error && <p className="text-xs text-amber-600">Failed to load models. Current model shown only.</p>}
      {loading && models.length > 0 && <p className="text-xs text-muted-foreground">Refreshing model list…</p>}
    </div>
  );
}
