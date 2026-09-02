import type { Project, ProjectStatus, RiskTier } from '@/lib/types'

// Matches ml/schemas.py -> ANOMALY_SCORES_COLUMNS
export interface RawAnomalyRecord {
  work_id: string
  state: string
  constituency: string
  honble_members_of_parliament: string
  work_category: string
  work_description: string
  work_status: string
  status_category: 'Completed' | 'Ongoing' | 'To Be Implemented'

  anomaly_score: number // 0-1 scale, per anomaly_flag_threshold: 0.40 in schema
  anomaly_label: boolean | 0 | 1
  anomaly_severity: 'critical' | 'high' | 'medium' | 'low' | null
  anomaly_category: 'financial' | 'temporal' | 'vendor' | 'compliance' | 'statistical' | null
  triggered_rules: string[] | string | null
  explanation: string | null
  key_metrics: Record<string, unknown> | null

  statistical_score: number
  rule_score: number
  if_score: number

  sanction_amount: number
  total_spent: number
  cost_overrun_ratio: number
  amount_disbursed: number

  sanction_delay_days: number | null
  completion_duration_days: number | null
  recommended_date: string | null
  sanction_date: string | null
  completion_date: string | null

  vendor_hhi: number | null
  vendor_count: number
  payment_count: number
  max_vendor_share: number | null
  single_vendor_flag: boolean | 0 | 1

  missing_image_flag: boolean | 0 | 1
  payment_still_pending: boolean | 0 | 1

  near_threshold_count: number | null
  near_threshold_ratio: number | null
  advance_payment_ratio: number | null

  amount_vs_category_median: number | null
  duration_vs_category_median: number | null
}

function mapStatus(status: RawAnomalyRecord['status_category']): ProjectStatus {
  if (status === 'Completed') return 'completed'
  if (status === 'Ongoing') return 'ongoing'
  return 'not_started' // "To Be Implemented"
}

function mapRiskTier(severity: RawAnomalyRecord['anomaly_severity']): RiskTier {
  if (severity === 'critical' || severity === 'high') return 'high'
  if (severity === 'medium') return 'medium'
  return 'low'
}

function isFlagged(record: RawAnomalyRecord): boolean {
  return record.anomaly_label === true || record.anomaly_label === 1
}

function parseTriggeredRules(rules: RawAnomalyRecord['triggered_rules']): string[] {
  if (!rules) return []
  if (Array.isArray(rules)) return rules
  // some pipelines serialize this as a comma or semicolon separated string
  return rules.split(/[;,]/).map(r => r.trim()).filter(Boolean)
}

export function adaptAnomalyRecordToProject(record: RawAnomalyRecord): Project {
  const flagged = isFlagged(record)
  const riskScore = Math.round((record.anomaly_score ?? 0) * 100)
  const triggeredRules = parseTriggeredRules(record.triggered_rules)

  return {
    id: record.work_id,
    name: record.work_description || `Work ${record.work_id}`,
    location: record.constituency,
    region: record.state,
    status: mapStatus(record.status_category),
    sanctionedAmount: record.sanction_amount ?? 0,
    releasedAmount: record.amount_disbursed ?? record.sanction_amount ?? 0,
    utilizedAmount: record.total_spent ?? 0,
    plannedDuration: record.completion_duration_days ?? 0,
    actualDuration: record.completion_duration_days ?? null,
    sanctionedDate: record.sanction_date ?? '',
    workStartDate: record.recommended_date ?? null,
    completedDate: record.completion_date ?? null,
    riskScore,
    riskTier: mapRiskTier(record.anomaly_severity),
    isFlagged: flagged,
    flaggedDate: flagged ? (record.sanction_date ?? null) : null,
    anomalies: flagged
      ? [{
          // anomaly_category doesn't map 1:1 to your existing AnomalyType union yet —
          // using a safe fallback until you confirm categories with Kawshik
          type: mapCategoryToAnomalyType(record.anomaly_category),
          confidence: record.anomaly_score ?? 0,
          explanation: record.explanation
            || (triggeredRules.length ? `Triggered rules: ${triggeredRules.join(', ')}` : 'Flagged by anomaly detection pipeline.'),
        }]
      : [],
    verificationStatus: flagged ? 'unverified' : 'verified_clean',
  }
}

// Your AnomalyType union is: 'cost_overrun' | 'delay' | 'duplicate' | 'payment_irregularity' | 'geospatial_mismatch'
// Kawshik's anomaly_category is: 'financial' | 'temporal' | 'vendor' | 'compliance' | 'statistical'
// These don't line up 1:1 — confirm with Kawshik, this is a reasonable first-pass mapping:
function mapCategoryToAnomalyType(category: RawAnomalyRecord['anomaly_category']) {
  switch (category) {
    case 'financial': return 'cost_overrun' as const
    case 'temporal': return 'delay' as const
    case 'vendor': return 'payment_irregularity' as const
    case 'compliance': return 'payment_irregularity' as const
    default: return 'cost_overrun' as const
  }
}