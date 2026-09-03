import { apiFetch } from './api'
import type {
  CostEstimate,
  DuplicateFullResponse,
  DuplicateSummary,
  DelayPrediction,
  DelaySummary,
} from '@/types/innovations'

// ============================================================
// COST ESTIMATION
// ============================================================
export async function getCostEstimate(workId: string): Promise<CostEstimate> {
  return apiFetch<CostEstimate>(`/api/cost-estimates/${encodeURIComponent(workId)}`)
}

export async function getCostEstimates(limit = 100, offset = 0) {
  return apiFetch<{ total_estimates: number; limit: number; offset: number; data: CostEstimate[] }>(
    `/api/cost-estimates?limit=${limit}&offset=${offset}`
  )
}

// ============================================================
// DUPLICATE DETECTION
// Note: /api/duplicates/{work_id} has a known backend bug (checks the
// wrong column names) and will 500. We fetch /api/duplicates/full and
// filter client-side by work_id instead, which is unaffected by that bug.
// ============================================================
export async function getDuplicateRecordForWork(workId: string) {
  const response = await apiFetch<DuplicateFullResponse>('/api/duplicates/full')
  return response.results.find(r => r.work_id === workId) ?? null
}

export async function getDuplicateSummary(): Promise<DuplicateSummary> {
  const response = await apiFetch<{ success: boolean; summary: DuplicateSummary; message?: string }>(
    '/api/duplicates/summary'
  )
  return response.summary
}

// ============================================================
// DELAY PREDICTION
// ============================================================
export async function getDelayPrediction(workId: string): Promise<DelayPrediction> {
  return apiFetch<DelayPrediction>(`/api/delay-predictions/${encodeURIComponent(workId)}`)
}

export async function getDelaySummary(): Promise<DelaySummary> {
  const response = await apiFetch<{ success: boolean; summary: DelaySummary; message?: string }>(
    '/api/delay-predictions/summary'
  )
  return response.summary
}