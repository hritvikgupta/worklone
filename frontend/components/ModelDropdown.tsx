import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Sparkles, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getModelsCatalog, getAvailableProviders, ProviderInfo, EmployeeModelOption } from '@/src/api/employees';

interface ModelDropdownProps {
  value: string;
  onChange: (model: string) => void;
}

export function ModelDropdown({ value, onChange }: ModelDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<string>('openrouter');
  const [availableProviders, setAvailableProviders] = useState<ProviderInfo[]>([]);
  const [availableModels, setAvailableModels] = useState<EmployeeModelOption[]>([]);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load providers on mount
  useEffect(() => {
    let cancelled = false;
    
    async function loadProviders() {
      try {
        const providers = await getAvailableProviders();
        if (!cancelled) {
          setAvailableProviders(providers);
          // Auto-select first available provider
          const available = providers.find(p => p.available);
          if (available) {
            setSelectedProvider(available.id);
          }
        }
      } catch (error) {
        console.error('Failed to load providers:', error);
      }
    }
    
    loadProviders();
    return () => { cancelled = true; };
  }, []);

  // Load models when provider changes
  useEffect(() => {
    if (!selectedProvider) return;
    
    let cancelled = false;
    setLoading(true);
    
    getModelsCatalog(selectedProvider)
      .then((models) => {
        if (!cancelled) {
          setAvailableModels(models);
        }
      })
      .catch((error) => {
        console.error('Failed to load models:', error);
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    
    return () => { cancelled = true; };
  }, [selectedProvider]);

  const selectedModel = availableModels.find(m => m.id === value);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const availableProviderIds = availableProviders.filter(p => p.available).map(p => p.id);

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-1.5 px-2 py-1 rounded-lg transition-all text-xs font-medium",
          "bg-zinc-50 border border-zinc-200 text-zinc-600",
          "hover:bg-zinc-100 hover:border-zinc-300",
          isOpen && "bg-zinc-100 border-zinc-300"
        )}
      >
        <Sparkles className="w-3 h-3 text-zinc-500" />
        <span className="max-w-[80px] truncate">
          {selectedModel?.name || value || 'Select Model'}
        </span>
        <ChevronDown className={cn(
          "w-3 h-3 text-zinc-400 transition-transform",
          isOpen && "rotate-180"
        )} />
      </button>

      {isOpen && (
        <div className={cn(
          "absolute bottom-full left-0 mb-2 min-w-[280px]",
          "bg-white border border-zinc-200 rounded-xl shadow-lg overflow-hidden z-50"
        )}>
          <div className="p-1.5 border-b border-zinc-100 bg-zinc-50">
            <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-2 mb-2">Select Provider</p>
            {/* Provider Selection */}
            <div className="flex gap-1.5 px-2">
              {availableProviderIds.map((providerId) => {
                const provider = availableProviders.find(p => p.id === providerId);
                return (
                  <button
                    key={providerId}
                    type="button"
                    onClick={() => {
                      setSelectedProvider(providerId);
                      // Clear current model when switching providers
                      if (selectedModel) {
                        onChange('');
                      }
                    }}
                    className={cn(
                      "flex-1 rounded-lg border px-2 py-1.5 text-xs font-medium transition-colors",
                      selectedProvider === providerId 
                        ? "border-zinc-900 bg-zinc-900 text-white" 
                        : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
                    )}
                  >
                    {provider?.name || providerId}
                  </button>
                );
              })}
            </div>
          </div>
          
          <div className="max-h-[320px] overflow-y-auto p-1.5 space-y-0.5">
            {loading ? (
              <div className="flex items-center justify-center gap-2 py-8 text-zinc-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-xs">Loading models...</span>
              </div>
            ) : availableModels.length === 0 ? (
              <div className="py-8 text-center text-xs text-zinc-400">
                No models available
              </div>
            ) : (
              availableModels.map((model) => (
                <button
                  key={model.id}
                  type="button"
                  onClick={() => {
                    onChange(model.id);
                    setIsOpen(false);
                  }}
                  className={cn(
                    "w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg",
                    "text-left transition-all",
                    model.id === value
                      ? "bg-zinc-900 text-white"
                      : "hover:bg-zinc-50 text-zinc-700"
                  )}
                >
                  <div className="flex flex-col min-w-0">
                    <span className={cn(
                      "text-xs font-semibold truncate",
                      model.id === value ? "text-white" : "text-zinc-900"
                    )}>
                      {model.name}
                    </span>
                    <span className={cn(
                      "text-[9px] truncate",
                      model.id === value ? "text-zinc-300" : "text-zinc-400"
                    )}>
                      {model.id}
                    </span>
                  </div>
                  {model.id === value && (
                    <Check className="w-3.5 h-3.5 flex-shrink-0" />
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
