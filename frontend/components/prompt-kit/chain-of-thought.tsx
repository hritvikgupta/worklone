"use client"

import * as React from "react"
import { motion, AnimatePresence } from "motion/react"
import { ChevronDown, ChevronRight, Brain } from "lucide-react"

import { cn } from "@/lib/utils"

const ChainOfThoughtContext = React.createContext<{
  expanded: boolean
  setExpanded: React.Dispatch<React.SetStateAction<boolean>>
}>({ expanded: false, setExpanded: () => {} })

export const ChainOfThought = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { defaultExpanded?: boolean }
>(({ className, defaultExpanded = true, ...props }, ref) => {
  const [expanded, setExpanded] = React.useState(defaultExpanded)

  return (
    <ChainOfThoughtContext.Provider value={{ expanded, setExpanded }}>
      <div
        ref={ref}
        className={cn("flex flex-col text-sm rounded-lg border border-border bg-card overflow-hidden", className)}
        {...props}
      />
    </ChainOfThoughtContext.Provider>
  )
})
ChainOfThought.displayName = "ChainOfThought"

export const ChainOfThoughtStep = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("border-b border-border/50 last:border-0", className)}
      {...props}
    />
  )
})
ChainOfThoughtStep.displayName = "ChainOfThoughtStep"

export const ChainOfThoughtTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, children, ...props }, ref) => {
  const { expanded, setExpanded } = React.useContext(ChainOfThoughtContext)

  return (
    <button
      ref={ref}
      onClick={() => setExpanded(!expanded)}
      className={cn(
        "flex w-full items-center justify-between px-3 py-2 text-left text-[13px] font-medium text-muted-foreground hover:bg-muted/50 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
        className
      )}
      {...props}
    >
      <div className="flex items-center gap-2">
        <Brain className="h-3.5 w-3.5" />
        {children}
      </div>
      <ChevronDown
        className={cn("h-4 w-4 shrink-0 transition-transform duration-200", !expanded && "-rotate-90")}
      />
    </button>
  )
})
ChainOfThoughtTrigger.displayName = "ChainOfThoughtTrigger"

export const ChainOfThoughtContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
  const { expanded } = React.useContext(ChainOfThoughtContext)

  return (
    <AnimatePresence initial={false}>
      {expanded && (
        <motion.div
          ref={ref}
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2, ease: "easeInOut" }}
          className="overflow-hidden"
          {...props}
        >
          <div className={cn("px-4 pb-3 pt-1 space-y-2", className)}>
            {children}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
})
ChainOfThoughtContent.displayName = "ChainOfThoughtContent"

export const ChainOfThoughtItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "flex items-start gap-2 text-[12px] leading-5 text-muted-foreground",
        className
      )}
      {...props}
    >
      <ChevronRight className="h-3.5 w-3.5 shrink-0 mt-[3px] opacity-70" />
      <div>{children}</div>
    </div>
  )
})
ChainOfThoughtItem.displayName = "ChainOfThoughtItem"
