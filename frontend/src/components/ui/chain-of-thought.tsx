"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { ChevronDown, Brain, Wrench, CheckCircle2, AlertCircle, Loader2 } from "lucide-react"

interface ChainOfThoughtProps {
  children: React.ReactNode
  className?: string
  defaultOpen?: boolean
}

function ChainOfThought({ children, className, defaultOpen = false }: ChainOfThoughtProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen)

  const hasRunning = React.Children.toArray(children).some((child) => {
    if (React.isValidElement<{ status?: string }>(child) && child.props.status === "running") return true
    return false
  })

  React.useEffect(() => {
    if (hasRunning) setIsOpen(true)
  }, [hasRunning])

  const count = React.Children.count(children)

  return (
    <div className={cn("mb-2", className)}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 text-[11px] font-medium text-[var(--chat-text-tertiary)] hover:text-[var(--chat-text-secondary)] transition-colors"
      >
        <ChevronDown
          className={cn(
            "h-3 w-3 transition-transform duration-200",
            !isOpen && "-rotate-90"
          )}
        />
        <span>
          {hasRunning ? "Thinking…" : `${count} step${count !== 1 ? "s" : ""}`}
        </span>
        {hasRunning && (
          <Loader2 className="h-3 w-3 animate-spin" />
        )}
      </button>
      {isOpen && (
        <div className="mt-1.5 ml-1.5 border-l border-[var(--chat-border)] pl-3 space-y-1.5">
          {children}
        </div>
      )}
    </div>
  )
}

interface ChainOfThoughtStepProps {
  status?: "running" | "done" | "error"
  children: React.ReactNode
  className?: string
}

function ChainOfThoughtStep({ status = "done", children, className }: ChainOfThoughtStepProps) {
  return (
    <div className={cn("flex items-start gap-2", className)}>
      <div className="mt-0.5 shrink-0">
        {status === "running" ? (
          <Loader2 className="h-3 w-3 animate-spin text-amber-400" />
        ) : status === "error" ? (
          <AlertCircle className="h-3 w-3 text-red-400" />
        ) : (
          <CheckCircle2 className="h-3 w-3 text-emerald-400" />
        )}
      </div>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}

interface ChainOfThoughtTriggerProps {
  children: React.ReactNode
  type?: "thinking" | "tool"
  meta?: string
  className?: string
}

function ChainOfThoughtTrigger({ children, type = "thinking", meta, className }: ChainOfThoughtTriggerProps) {
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      {type === "tool" ? (
        <Wrench className="h-2.5 w-2.5 text-[var(--chat-text-tertiary)]" />
      ) : (
        <Brain className="h-2.5 w-2.5 text-[var(--chat-text-tertiary)]" />
      )}
      <span className="text-[11px] font-medium text-[var(--chat-text-secondary)] truncate">
        {children}
      </span>
      {meta && (
        <span className="text-[10px] text-[var(--chat-text-tertiary)] truncate">
          · {meta}
        </span>
      )}
    </div>
  )
}

interface ChainOfThoughtContentProps {
  children: React.ReactNode
  className?: string
}

function ChainOfThoughtContent({ children, className }: ChainOfThoughtContentProps) {
  return (
    <div className={cn("mt-0.5 text-[10px] text-[var(--chat-text-tertiary)] leading-relaxed", className)}>
      {children}
    </div>
  )
}

interface ChainOfThoughtItemProps {
  children: React.ReactNode
  className?: string
}

function ChainOfThoughtItem({ children, className }: ChainOfThoughtItemProps) {
  return (
    <div className={cn("truncate", className)}>
      {children}
    </div>
  )
}

export {
  ChainOfThought,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
  ChainOfThoughtContent,
  ChainOfThoughtItem,
}
