/**
 * Presence API — lease-derived employee status.
 *
 * The backend treats the Redis employee lease as the source of truth for
 * "is Alex busy?". These helpers fetch the projected status for one or many
 * employees. For live updates use `useEmployeePresence` which listens on
 * socket.io instead of polling these endpoints.
 */

import { API_BASE } from './_base'

export type EmployeeStatusKind = 'idle' | 'working' | 'blocked' | 'offline'

export interface BusyContext {
  job_id: string
  kind: 'team' | 'sprint' | 'workflow' | 'chat'
  lane: string
  run_id?: string | null
  user_id?: string | null
}

export interface EmployeePresence {
  employee_id: string
  status: EmployeeStatusKind
  busy_in: BusyContext | null
}

export async function getEmployeeStatus(employeeId: string): Promise<EmployeePresence> {
  const res = await fetch(`${API_BASE}/employees/${employeeId}/status`)
  if (!res.ok) throw new Error(`status ${res.status}`)
  return res.json()
}

export async function getEmployeeStatusesBulk(
  employeeIds: string[],
): Promise<Record<string, EmployeePresence>> {
  if (employeeIds.length === 0) return {}
  const res = await fetch(`${API_BASE}/employees/status/bulk`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_ids: employeeIds }),
  })
  if (!res.ok) throw new Error(`bulk status ${res.status}`)
  const data = await res.json()
  return data.statuses || {}
}
