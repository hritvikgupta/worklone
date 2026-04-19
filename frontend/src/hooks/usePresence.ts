/**
 * usePresence — live employee busy-status via socket.io.
 *
 * Under the hood this hook:
 *   1. Opens a single shared socket.io connection to the backend.
 *   2. `emit("subscribe", { employee_ids })` so we only receive events
 *      for the employees we care about.
 *   3. Listens for `employee.status_changed` events and updates local state.
 *   4. Seeds state from the REST bulk endpoint on mount so we don't show
 *      stale "idle" for an employee who was already busy when we connected.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { io, Socket } from 'socket.io-client'

import { SOCKET_URL } from '@/src/api/_base'
import {
  EmployeePresence,
  EmployeeStatusKind,
  getEmployeeStatusesBulk,
} from '@/src/api/presence'

type StatusMap = Record<string, EmployeePresence>

// Share one socket across all hook instances so we don't open N connections.
let sharedSocket: Socket | null = null
function getSharedSocket(userId?: string): Socket {
  if (sharedSocket && sharedSocket.connected) return sharedSocket
  sharedSocket = io(SOCKET_URL, {
    path: '/socket.io',
    transports: ['websocket', 'polling'],
    auth: userId ? { user_id: userId } : undefined,
  })
  return sharedSocket
}

export function useEmployeePresence(employeeIds: string[], userId?: string) {
  const [statuses, setStatuses] = useState<StatusMap>({})
  const subscribedRef = useRef<Set<string>>(new Set())

  // Stable key so we don't re-run the effect every render when a fresh
  // array is passed in.
  const idsKey = useMemo(() => [...employeeIds].sort().join(','), [employeeIds])

  useEffect(() => {
    if (!employeeIds.length) {
      setStatuses({})
      return
    }
    let cancelled = false

    // Seed from REST, then periodically refresh as a fallback in case
    // a socket event was missed (reconnects, dropped frames, etc.).
    const refresh = () => {
      getEmployeeStatusesBulk(employeeIds)
        .then((snapshot) => {
          if (cancelled) return
          setStatuses((prev) => ({ ...prev, ...snapshot }))
        })
        .catch((err) => console.warn('presence refresh failed', err))
    }
    refresh()
    const refreshInterval = window.setInterval(refresh, 8000)

    const socket = getSharedSocket(userId)

    const handler = (event: {
      employee_id?: string
      status?: EmployeeStatusKind
      run_id?: string
      kind?: string
      user_id?: string
    }) => {
      if (!event?.employee_id) return
      setStatuses((prev) => ({
        ...prev,
        [event.employee_id as string]: {
          employee_id: event.employee_id as string,
          status: (event.status as EmployeeStatusKind) || 'idle',
          busy_in:
            event.status === 'working'
              ? {
                  job_id: '',
                  kind: (event.kind as any) || 'chat',
                  lane: (event.kind as any) || 'chat',
                  run_id: event.run_id || null,
                  user_id: event.user_id || null,
                }
              : null,
        },
      }))
    }

    socket.on('employee.status_changed', handler)

    // Send subscription once we've connected (or immediately if already).
    const doSubscribe = () => {
      const newIds = employeeIds.filter((id) => !subscribedRef.current.has(id))
      if (newIds.length) {
        socket.emit('subscribe', { employee_ids: newIds })
        newIds.forEach((id) => subscribedRef.current.add(id))
      }
    }
    if (socket.connected) doSubscribe()
    else socket.on('connect', doSubscribe)

    return () => {
      cancelled = true
      window.clearInterval(refreshInterval)
      socket.off('employee.status_changed', handler)
      socket.off('connect', doSubscribe)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, userId])

  const isBusy = (employeeId: string): boolean =>
    statuses[employeeId]?.status === 'working'

  const busyIn = (employeeId: string) => statuses[employeeId]?.busy_in || null

  return { statuses, isBusy, busyIn }
}
