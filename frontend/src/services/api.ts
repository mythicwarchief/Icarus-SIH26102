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

import type { RawAnomalyRecord } from './adapters'

export async function getAnomalyScores(limit = 100, offset = 0) {
  return apiFetch<{ total: number; limit: number; offset: number; data: RawAnomalyRecord[] }>(
    `/api/anomalies?limit=${limit}&offset=${offset}`
  )
}

export async function getAnomalySummary() {
  return apiFetch<{
    total_works_analyzed: number
    total_anomalies: number
    anomaly_rate_percent: number
    severity_distribution: { critical: number; high: number; medium: number; low: number }
    status_distribution: Record<string, number>
  }>('/api/summary')
}

export async function getWorkAnomaly(workId: string) {
  return apiFetch<RawAnomalyRecord>(`/api/anomalies/${encodeURIComponent(workId)}`)
}