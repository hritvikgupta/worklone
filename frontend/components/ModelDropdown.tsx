import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ModelOption {
  value: string;
  label: string;
  provider: string;
}

export const AVAILABLE_MODELS: ModelOption[] = [
  { value: 'z-ai/glm-5.1', label: 'GLM 5.1', provider: 'Z.AI' },
  { value: 'google/gemma-4-26b-a4b-it', label: 'Gemma 4 26B', provider: 'Google' },
  { value: 'xiaomi/mimo-v2-pro', label: 'MiMo V2 Pro', provider: 'Xiaomi' },
  { value: 'minimax/minimax-m2.7', label: 'MiniMax M2.7', provider: 'MiniMax' },
  { value: 'mistralai/mistral-small-2603', label: 'Mistral Small', provider: 'Mistral AI' },
  { value: 'inception/mercury-2', label: 'Mercury 2', provider: 'Inception AI' },
  { value: 'qwen/qwen3-max-thinking', label: 'Qwen3 Max', provider: 'Alibaba' },
];

interface ModelDropdownProps {
  value: string;
  onChange: (model: string) => void;
}

export function ModelDropdown({ value, onChange }: ModelDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedModel = AVAILABLE_MODELS.find(m => m.value === value) || AVAILABLE_MODELS[0];

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
        <span className="max-w-[80px] truncate">{selectedModel.label}</span>
        <ChevronDown className={cn(
          "w-3 h-3 text-zinc-400 transition-transform",
          isOpen && "rotate-180"
        )} />
      </button>

      {isOpen && (
        <div className={cn(
          "absolute bottom-full left-0 mb-2 min-w-[220px]",
          "bg-white border border-zinc-200 rounded-xl shadow-lg overflow-hidden z-50"
        )}>
          <div className="p-1.5 border-b border-zinc-100 bg-zinc-50">
            <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-2">Select Model</p>
          </div>
          <div className="max-h-[280px] overflow-y-auto p-1.5 space-y-0.5">
            {AVAILABLE_MODELS.map((model) => (
              <button
                key={model.value}
                onClick={() => {
                  onChange(model.value);
                  setIsOpen(false);
                }}
                className={cn(
                  "w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg",
                  "text-left transition-all",
                  value === model.value
                    ? "bg-zinc-900 text-white"
                    : "hover:bg-zinc-50 text-zinc-700"
                )}
              >
                <div className="flex flex-col">
                  <span className={cn(
                    "text-xs font-semibold",
                    value === model.value ? "text-white" : "text-zinc-900"
                  )}>
                    {model.label}
                  </span>
                  <span className={cn(
                    "text-[9px]",
                    value === model.value ? "text-zinc-300" : "text-zinc-400"
                  )}>
                    {model.provider}
                  </span>
                </div>
                {value === model.value && (
                  <Check className="w-3.5 h-3.5 flex-shrink-0" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
