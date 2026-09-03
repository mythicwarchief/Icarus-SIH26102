const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    cache: 'no-store',
  })

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

// Backend endpoints will be wired here once Vaishnav's FastAPI contract is finalized.
// Keep UI components dependent on this service rather than calling fetch directly.
export const API_BASE = API_BASE_URL

import type { RawAnomalyRecord } from './realAdapter'

// Full portfolio (all scored works, not just flagged) - one page
export async function getAllScoredWorks(limit = 100, offset = 0) {
  return apiFetch<{ total_works: number; limit: number; offset: number; data: RawAnomalyRecord[] }>(
    `/api/anomalies/all?limit=${limit}&offset=${offset}`
  )
}

// Fetches every scored work by looping pages (backend caps a single page at 1000).
// Used by Registry, which needs the complete list for client-side search/filter.
export async function getAllScoredWorksComplete(): Promise<RawAnomalyRecord[]> {
  const pageSize = 1000
  const first = await getAllScoredWorks(pageSize, 0)
  const all = [...first.data]
  let fetched = first.data.length
  while (fetched < first.total_works) {
    const next = await getAllScoredWorks(pageSize, fetched)
    all.push(...next.data)
    fetched += next.data.length
    if (next.data.length === 0) break // safety guard against infinite loop
  }
  return all
}

// Single work lookup regardless of flagged status - powers Investigation
export async function getScoredWork(workId: string) {
  return apiFetch<RawAnomalyRecord>(`/api/anomalies/all?work_id=${encodeURIComponent(workId)}`)
}

// Top N highest-risk flagged works - powers the Dashboard priority queue
export async function getHighRiskAnomalies(topN = 6) {
  return apiFetch<{ count: number; data: RawAnomalyRecord[] }>(
    `/api/anomalies/high-risk?top_n=${topN}`
  )
}