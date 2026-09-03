import type { Project, ProjectStatus, RiskTier, AnomalyType } from '@/lib/types'

// Confirmed live shape from GET /api/anomalies/all and GET /api/anomalies/{work_id}
// (ml/schemas.py ANOMALY_SCORES_COLUMNS, verified against real generated output)
export interface RawAnomalyRecord {
  work_id: string
  state: string
  constituency: string
  honble_members_of_parliament: string
  work_category: string
  work_description: string
  work_status: string
  status_category: 'Completed' | 'Ongoing' | 'To Be Implemented'

  anomaly_score: number
  anomaly_label: boolean
  anomaly_severity: 'critical' | 'high' | 'medium' | 'low' | null
  anomaly_category: 'financial' | 'temporal' | 'vendor' | 'compliance' | 'statistical' | null
  triggered_rules: string | null
  explanation: string | null

  sanction_amount: number
  total_spent: number
  amount_disbursed: number

  sanction_delay_days: number | null
  completion_duration_days: number | null
  recommended_date: string | null
  sanction_date: string | null
  completion_date: string | null
}

function mapStatus(status: RawAnomalyRecord['status_category']): ProjectStatus {
  if (status === 'Completed') return 'completed'
  if (status === 'Ongoing') return 'ongoing'
  return 'not_started'
}

function mapRiskTier(score: number, severity: RawAnomalyRecord['anomaly_severity']): RiskTier {
  if (severity === 'critical' || severity === 'high') return 'high'
  if (severity === 'medium') return 'medium'
  if (score >= 0.6) return 'high'
  if (score >= 0.4) return 'medium'
  return 'low'
}

function mapCategoryToAnomalyType(category: RawAnomalyRecord['anomaly_category']): AnomalyType {
  switch (category) {
    case 'financial': return 'cost_overrun'
    case 'temporal': return 'delay'
    case 'vendor': return 'payment_irregularity'
    case 'compliance': return 'payment_irregularity'
    default: return 'cost_overrun'
  }
}

export function adaptAnomalyRecordToProject(record: RawAnomalyRecord): Project {
  const flagged = record.anomaly_label === true
  const riskScore = Math.round((record.anomaly_score ?? 0) * 100)
  const triggeredRules = record.triggered_rules
    ? record.triggered_rules.split(/[;,]/).map(r => r.trim()).filter(Boolean)
    : []

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
    riskTier: mapRiskTier(record.anomaly_score ?? 0, record.anomaly_severity),
    isFlagged: flagged,
    flaggedDate: flagged ? (record.sanction_date ?? null) : null,
    anomalies: flagged
      ? [{
          type: mapCategoryToAnomalyType(record.anomaly_category),
          confidence: record.anomaly_score ?? 0,
          explanation: record.explanation
            || (triggeredRules.length ? `Triggered rules: ${triggeredRules.join(', ')}` : 'Flagged by anomaly detection pipeline.'),
        }]
      : [],
    verificationStatus: flagged ? 'unverified' : 'verified_clean',
  }
}
