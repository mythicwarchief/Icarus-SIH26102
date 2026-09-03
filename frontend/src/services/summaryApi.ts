import { apiFetch } from './api'
import type { AnomalySummary } from '@/types/summary'

export async function getAnomalySummary(): Promise<AnomalySummary> {
  return apiFetch<AnomalySummary>('/api/summary')
}