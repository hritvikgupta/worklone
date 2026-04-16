import * as React from "react"
import {
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  addDays,
  addMonths,
  subMonths,
  format,
  isSameMonth,
  isSameDay,
  isBefore,
} from "date-fns"
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface CalendarProps {
  selected?: Date
  onSelect?: (date: Date | undefined) => void
  disabled?: (date: Date) => boolean
  className?: string
}

function Calendar({ selected, onSelect, disabled, className }: CalendarProps) {
  const [currentMonth, setCurrentMonth] = React.useState(
    selected || new Date()
  )

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const calStart = startOfWeek(monthStart)
  const calEnd = endOfWeek(monthEnd)

  const days: Date[] = []
  let day = calStart
  while (day <= calEnd) {
    days.push(day)
    day = addDays(day, 1)
  }

  const weekdays = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]

  return (
    <div className={cn("p-3 select-none", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <button
          type="button"
          onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
          className="inline-flex items-center justify-center rounded-md h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100 border border-input"
        >
          <ChevronLeftIcon className="h-4 w-4" />
        </button>
        <span className="text-sm font-medium">
          {format(currentMonth, "MMMM yyyy")}
        </span>
        <button
          type="button"
          onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
          className="inline-flex items-center justify-center rounded-md h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100 border border-input"
        >
          <ChevronRightIcon className="h-4 w-4" />
        </button>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 mb-1">
        {weekdays.map((wd) => (
          <div
            key={wd}
            className="text-center text-muted-foreground text-[0.8rem] font-normal h-8 flex items-center justify-center"
          >
            {wd}
          </div>
        ))}
      </div>

      {/* Days grid */}
      <div className="grid grid-cols-7">
        {days.map((d, i) => {
          const isCurrentMonth = isSameMonth(d, currentMonth)
          const isSelected = selected && isSameDay(d, selected)
          const isToday = isSameDay(d, new Date())
          const isDisabled = disabled ? disabled(d) : false

          return (
            <button
              key={i}
              type="button"
              disabled={isDisabled}
              onClick={() => {
                if (!isDisabled && onSelect) {
                  onSelect(isSelected ? undefined : d)
                }
              }}
              className={cn(
                "inline-flex items-center justify-center rounded-md h-8 w-8 p-0 text-sm font-normal",
                !isCurrentMonth && "opacity-30",
                isDisabled && "opacity-50 cursor-not-allowed",
                !isSelected && !isToday && "hover:bg-accent hover:text-accent-foreground",
                isToday && !isSelected && "bg-accent text-accent-foreground",
                isSelected && "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground"
              )}
            >
              {format(d, "d")}
            </button>
          )
        })}
      </div>
    </div>
  )
}

Calendar.displayName = "Calendar"

export { Calendar }
export type { CalendarProps }
