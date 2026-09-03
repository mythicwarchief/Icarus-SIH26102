'use client'

import { AlertTriangle, Calendar, Copy, TrendingDown, TrendingUp } from 'lucide-react'
import { Panel, Reveal, CountUp } from '@/components/Dashboard'
import { useAsyncData } from '@/hooks/useAsyncData'
import { RiskGaugeSkeleton, ErrorPanel, Skeleton } from '@/components/LoadingStates'
import { formatINR } from '@/lib/types'
import { getCostEstimate, getDuplicateRecordForWork, getDelayPrediction } from '@/services/innovationsApi'
import type { DelayRiskLevel } from '@/types/innovations'

// ============================================================
// INNOVATION 1 — COST ESTIMATE PANEL
// ============================================================
export function CostEstimatePanel({ workId }: { workId: string }) {
  const { data, loading, error, retry } = useAsyncData(() => getCostEstimate(workId), [workId])

  if (loading) {
    return (
      <Panel title="Cost estimate" note="AI-powered comparison">
        <div className="space-y-3">
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </Panel>
    )
  }

  if (error || !data) {
    return (
      <Panel title="Cost estimate" note="AI-powered comparison">
        <ErrorPanel message={error ?? 'No cost estimate available for this work.'} onRetry={retry} />
      </Panel>
    )
  }

  const hasRange = data.expected_cost_low != null && data.expected_cost_high != null
  const outOfRange = !data.cost_in_expected_range

  return (
    <Reveal>
      <Panel title="Cost estimate" note="AI-powered comparison">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Sanctioned amount</p>
            <p className="mt-1 text-2xl font-bold tracking-tight">{formatINR(data.sanction_amount)}</p>
          </div>
          <span className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ${
            outOfRange ? 'bg-risk-medium/10 text-risk-medium' : 'bg-risk-low/10 text-risk-low'
          }`}>
            {outOfRange ? <AlertTriangle size={13} /> : <TrendingUp size={13} />}
            {outOfRange ? 'Outside expected range' : 'Within expected range'}
          </span>
        </div>

        {hasRange && (
          <div className="mt-4">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{formatINR(data.expected_cost_low!)}</span>
              <span>Expected range</span>
              <span>{formatINR(data.expected_cost_high!)}</span>
            </div>
            <div className="relative mt-2 h-2 rounded-full bg-muted">
              <div className="absolute inset-y-0 rounded-full bg-primary/25" style={{ left: '10%', right: '10%' }} />
              {(() => {
                const low = data.expected_cost_low!
                const high = data.expected_cost_high!
                const span = high - low || 1
                const pct = Math.min(100, Math.max(0, ((data.sanction_amount - low) / span) * 100))
                return (
                  <div
                    className={`absolute top-1/2 size-3 -translate-y-1/2 rounded-full border-2 border-background ${outOfRange ? 'bg-risk-medium' : 'bg-primary'}`}
                    style={{ left: `calc(${pct}% - 6px)` }}
                  />
                )
              })()}
            </div>
          </div>
        )}

        <div className="mt-4 grid grid-cols-2 gap-4 border-t border-border pt-4 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Budget tier</p>
            <p className="mt-1 font-medium">{data.budget_tier}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Compared against</p>
            <p className="mt-1 font-medium">{data.comparison_group_size} similar projects</p>
          </div>
        </div>

        <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{data.cost_range_explanation}</p>
      </Panel>
    </Reveal>
  )
}

// ============================================================
// INNOVATION 2 — DUPLICATE / SIMILAR PROJECT PANEL
// ============================================================
export function DuplicateIntelligencePanel({ workId }: { workId: string }) {
  const { data, loading, error, retry } = useAsyncData(() => getDuplicateRecordForWork(workId), [workId])

  if (loading) {
    return (
      <Panel title="Similar project check" note="Duplicate detection">
        <div className="space-y-3">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </Panel>
    )
  }

  if (error) {
    return (
      <Panel title="Similar project check" note="Duplicate detection">
        <ErrorPanel message={error} onRetry={retry} />
      </Panel>
    )
  }

  const isFlagged = data && (data.duplicate_flag === true || data.duplicate_flag === 1)

  if (!data || !isFlagged) {
    return (
      <Panel title="Similar project check" note="Duplicate detection">
        <div className="flex items-center gap-3 rounded-xl bg-risk-low/10 p-4">
          <Copy size={18} className="text-risk-low" />
          <p className="text-sm text-muted-foreground">No significant similar projects were identified for this work.</p>
        </div>
      </Panel>
    )
  }

  const similarityPct = data.duplicate_max_similarity != null ? Math.round(data.duplicate_max_similarity * 100) : null
  const label = similarityPct != null
    ? similarityPct >= 85 ? 'High similarity' : similarityPct >= 65 ? 'Moderate similarity' : 'Low similarity'
    : null

  return (
    <Reveal>
      <Panel title="Similar project check" note="Duplicate detection">
        <div className="rounded-xl border border-risk-medium/30 bg-risk-medium/5 p-4">
          <div className="flex items-center justify-between">
            <p className="font-semibold">Potential duplicate or similar project detected</p>
            {similarityPct != null && (
              <span className="rounded-full bg-risk-medium/15 px-3 py-1 text-xs font-bold text-risk-medium">
                <CountUp value={similarityPct} />% {label}
              </span>
            )}
          </div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            {data.duplicate_pair_count} potential match{data.duplicate_pair_count === 1 ? '' : 'es'} found
            {data.duplicate_paired_with ? ` — paired with ${data.duplicate_paired_with}` : ''}. This requires human
            verification before any action is taken; it is not a confirmed duplicate.
          </p>
        </div>
      </Panel>
    </Reveal>
  )
}

// ============================================================
// INNOVATION 3 — DELAY RISK PANEL
// ============================================================
function delayRiskStyles(level: DelayRiskLevel) {
  switch (level) {
    case 'Critical Delay Risk':
    case 'High Delay Risk':
      return { text: 'text-risk-high', bg: 'bg-risk-high/10', ring: 'border-risk-high/30' }
    case 'Medium Delay Risk':
      return { text: 'text-risk-medium', bg: 'bg-risk-medium/10', ring: 'border-risk-medium/30' }
    default:
      return { text: 'text-risk-low', bg: 'bg-risk-low/10', ring: 'border-risk-low/30' }
  }
}

export function DelayRiskPanel({ workId }: { workId: string }) {
  const { data, loading, error, retry } = useAsyncData(() => getDelayPrediction(workId), [workId])

  if (loading) {
    return (
      <Panel title="Delay risk" note="Predictive analysis">
        <RiskGaugeSkeleton />
      </Panel>
    )
  }

  if (error || !data) {
    return (
      <Panel title="Delay risk" note="Predictive analysis">
        <ErrorPanel message={error ?? 'No delay prediction available for this work.'} onRetry={retry} />
      </Panel>
    )
  }

  const styles = delayRiskStyles(data.delay_risk_level)
  const probabilityPct = Math.round(data.delay_probability * 100)

  return (
    <Reveal>
      <Panel title="Delay risk" note="Predictive analysis">
        <div className="flex items-center gap-6">
          <div className={`grid size-32 shrink-0 place-items-center rounded-full border-[12px] ${styles.ring} ${styles.text}`}>
            <span className="text-3xl font-bold"><CountUp value={probabilityPct} />%</span>
          </div>
          <div>
            <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${styles.bg} ${styles.text}`}>
              <TrendingDown size={13} /> {data.delay_risk_level}
            </span>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Predicted duration: ~{Math.round(data.predicted_duration_days)} days
            </p>
            {data.expected_projected_completion_date && (
              <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                <Calendar size={12} /> Projected completion: {data.expected_projected_completion_date}
              </p>
            )}
          </div>
        </div>
        <p className="mt-4 border-t border-border pt-4 text-sm leading-relaxed text-muted-foreground">
          {data.delay_explanation}
        </p>
      </Panel>
    </Reveal>
  )
}