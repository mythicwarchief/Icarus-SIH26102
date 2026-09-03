import type { RawAnomalyRecord } from './realAdapter'

export interface RegionalRiskPoint {
  region: string
  risk: number
  projects: number
}

export function computeRegionalRisk(works: RawAnomalyRecord[], topN = 6): RegionalRiskPoint[] {
  const byState = new Map<string, { totalScore: number; count: number }>()

  for (const w of works) {
    if (!w.state) continue
    const entry = byState.get(w.state) ?? { totalScore: 0, count: 0 }
    entry.totalScore += w.anomaly_score ?? 0
    entry.count += 1
    byState.set(w.state, entry)
  }

  return Array.from(byState.entries())
    .map(([region, { totalScore, count }]) => ({
      region,
      risk: Math.round((totalScore / count) * 100),
      projects: count,
    }))
    .filter(r => r.projects >= 10)
    .sort((a, b) => b.risk - a.risk)
    .slice(0, topN)
}

export interface MonthlyTrendPoint {
  month: string
  sanctioned: number
  flagged: number
}

export function computeMonthlyTrend(works: RawAnomalyRecord[], lastN = 6): MonthlyTrendPoint[] {
  const byMonth = new Map<string, { sanctioned: number; flagged: number; sortKey: string }>()

  for (const w of works) {
    if (!w.sanction_date) continue
    const d = new Date(w.sanction_date)
    if (isNaN(d.getTime())) continue

    const sortKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`

    const entry = byMonth.get(sortKey) ?? { sanctioned: 0, flagged: 0, sortKey }
    entry.sanctioned += 1
    if (w.anomaly_label) entry.flagged += 1
    byMonth.set(sortKey, entry)
  }

  return Array.from(byMonth.entries())
    .map(([sortKey, v]) => ({
      month: new Date(sortKey + '-01').toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
      sanctioned: v.sanctioned,
      flagged: v.flagged,
      sortKey,
    }))
    .sort((a, b) => a.sortKey.localeCompare(b.sortKey))
    .slice(-lastN)
    .map(({ month, sanctioned, flagged }) => ({ month, sanctioned, flagged }))
}