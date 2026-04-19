/**
 * Dispatch API — job admission status.
 *
 * Used to show "waiting for employees to be free" banners while a
 * team/sprint/workflow run is queued on the dispatcher but not yet admitted
 * (i.e. one or more required employees is still busy on another job).
 */

import { API_BASE } from './_base'

export type DispatchJobStatus =
  | 'waiting'
  | 'admitting'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'

export interface DispatchJob {
  id: string
  kind: 'chat' | 'sprint' | 'team' | 'workflow'
  lane: string
  user_id: string
  owner_id: string
  required_employee_ids: string[]
  payload: Record<string, unknown>
  status: DispatchJobStatus
  created_at: number
  admitted_at: number | null
  started_at: number | null
  completed_at: number | null
  error: string | null
  run_id: string | null
  result: Record<string, unknown> | null
}

export async function getDispatchJob(jobId: string): Promise<DispatchJob> {
  const res = await fetch(`${API_BASE}/dispatch/jobs/${jobId}`)
  if (!res.ok) throw new Error(`dispatch job ${res.status}`)
  return res.json()
}
