/**
 * BusyDot — tiny presence indicator for an employee.
 *
 * Green  = idle
 * Amber  = working (busy in team/sprint/workflow/chat)
 *
 * Uses the shared socket.io presence hook so the dot updates live whenever a
 * dispatcher admission grants/releases a lease on this employee.
 */

import React from 'react'
import { useEmployeePresence } from '@/src/hooks/usePresence'

interface Props {
  employeeId: string
  withLabel?: boolean
  className?: string
}

export const BusyDot: React.FC<Props> = ({ employeeId, withLabel, className = '' }) => {
  const { statuses, busyIn } = useEmployeePresence([employeeId])
  const status = statuses[employeeId]?.status || 'idle'
  const ctx = busyIn(employeeId)
  const isBusy = status === 'working'

  const color = isBusy ? 'bg-amber-500' : 'bg-emerald-500'
  const label = isBusy
    ? ctx?.kind
      ? `Busy — ${ctx.kind}`
      : 'Busy'
    : 'Available'

  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`} title={label}>
      <span className={`h-2 w-2 rounded-full ${color} ${isBusy ? 'animate-pulse' : ''}`} />
      {withLabel && <span className="text-xs text-muted-foreground">{label}</span>}
    </span>
  )
}

export default BusyDot
