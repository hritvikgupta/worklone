"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { ChevronRight, ChevronDown, Sparkles, Wrench, AlertCircle } from "lucide-react"

// ── ChainOfThought wrapper ────────────────────────────────────────────────────

interface ChainOfThoughtProps {
  children: React.ReactNode
  className?: string
  defaultOpen?: boolean
}

function ChainOfThought({ children, className }: ChainOfThoughtProps) {
  return (
    <div className={cn("mb-2 flex flex-col gap-1.5", className)}>
      {children}
    </div>
  )
}

// ── ChainOfThoughtStep ────────────────────────────────────────────────────────

interface ChainOfThoughtStepProps {
  status?: "running" | "done" | "error"
  children: React.ReactNode
  className?: string
}

function ChainOfThoughtStep({ status = "done", children, className }: ChainOfThoughtStepProps) {
  const isRunning = status === "running"
  const isError = status === "error"

  // Read props from child ChainOfThoughtTrigger element
  const childEl = React.Children.toArray(children)[0]
  const trigger = React.isValidElement<ChainOfThoughtTriggerProps>(childEl) ? childEl : null
  const type = trigger?.props.type ?? "thinking"
  const label = trigger?.props.children
  const meta = trigger?.props.meta

  const isTool = type === "tool"

  const [open, setOpen] = React.useState(false)

  React.useEffect(() => {
    if (isRunning) setOpen(true)
  }, [isRunning])

  if (!isTool) {
    // ── Thinking step: small-caps collapsible text block ──
    return (
      <div className={cn("", className)}>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[var(--chat-text-tertiary)] hover:text-[var(--chat-text-secondary)] transition-colors"
        >
          <Sparkles className="h-2.5 w-2.5 shrink-0" />
          <span>{isRunning ? "Thinking…" : "Thought"}</span>
          {open ? <ChevronDown className="h-2.5 w-2.5" /> : <ChevronRight className="h-2.5 w-2.5" />}
        </button>
        {open && label && (
          <div className="mt-1 pl-3 border-l-2 border-[var(--chat-border)] text-[11.5px] leading-[1.55] text-[var(--chat-text-tertiary)] whitespace-pre-wrap">
            {label}
          </div>
        )}
      </div>
    )
  }

  // ── Tool step: pill button ────────────────────────────────────────────────
  return (
    <div className={cn("", className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-[5px] text-[12px] font-medium transition-colors cursor-pointer",
          isError
            ? "border-red-300/60 text-red-500 bg-red-500/5"
            : "border-[var(--chat-border-strong)] text-[var(--chat-text-secondary)] bg-[var(--chat-bg-sidebar)] hover:bg-[var(--chat-accent-soft)]"
        )}
      >
        {isError
          ? <AlertCircle className="h-3 w-3 shrink-0 text-red-400" />
          : <Wrench className="h-3 w-3 shrink-0 text-[var(--chat-text-tertiary)]" />
        }
        <span className="max-w-[180px] truncate">{label}</span>
        {meta && (
          <span className="font-normal text-[11px] text-[var(--chat-text-tertiary)] max-w-[100px] truncate">
            · {meta}
          </span>
        )}
        {isRunning && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400 animate-pulse" />}
        {!isRunning && !isError && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />}
        {open ? <ChevronDown className="h-3 w-3 shrink-0 opacity-50" /> : <ChevronRight className="h-3 w-3 shrink-0 opacity-50" />}
      </button>
    </div>
  )
}

// ── ChainOfThoughtTrigger — data carrier only, not rendered directly ───────────

interface ChainOfThoughtTriggerProps {
  children?: React.ReactNode
  type?: "thinking" | "tool"
  meta?: string
  className?: string
}

function ChainOfThoughtTrigger({ children, type = "thinking", meta, className }: ChainOfThoughtTriggerProps) {
  // Rendered by ChainOfThoughtStep — this component is never mounted directly
  return (
    <span className={cn("hidden", className)}>
      {children}
    </span>
  )
}

// ── Legacy compat ─────────────────────────────────────────────────────────────

function ChainOfThoughtContent({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("mt-0.5 text-[10px] text-[var(--chat-text-tertiary)] leading-relaxed", className)}>{children}</div>
}

function ChainOfThoughtItem({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("truncate", className)}>{children}</div>
}

export {
  ChainOfThought,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
  ChainOfThoughtContent,
  ChainOfThoughtItem,
}
