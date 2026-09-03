// Matches the ACTUAL backend response shapes, confirmed by reading:
// backend/app/ml_service.py, backend/app/routes.py,
// ml/innovations/cost_estimation/cost_range.py,
// ml/innovations/delay_prediction/predict.py,
// ml/innovations/duplicate_detection/similarity.py

// ============================================================
// INNOVATION 1 — COST ESTIMATION
// GET /api/cost-estimates/{work_id} -> single object (unwrapped)
// GET /api/cost-estimates -> { total_estimates, limit, offset, data: CostEstimate[] }
// ============================================================
export interface CostEstimate {
  work_id: string
  sanction_amount: number
  work_category: string
  state: string
  budget_tier: 'Small' | 'Medium' | 'Large' | 'Very Large' | 'Unknown'
  expected_cost_low: number | null
  expected_cost_high: number | null
  expected_cost_narrow_low: number | null
  expected_cost_narrow_high: number | null
  expected_cost_median: number | null
  comparison_group: string
  comparison_group_size: number
  cost_deviation_pct: number
  cost_in_expected_range: boolean
  cost_range_explanation: string
}

// ============================================================
// INNOVATION 2 — DUPLICATE DETECTION
// GET /api/duplicates/full -> { success, count, results: DuplicateFullRecord[] }
// (Use this instead of /api/duplicates/{work_id} — that endpoint has a
// known backend bug checking for the wrong column names and will 500.)
// ============================================================
export interface DuplicateFullRecord {
  work_id: string
  state: string
  constituency: string
  work_category: string
  work_description: string
  filter_status: 'eligible' | 'excluded_boilerplate' | 'excluded_beneficiary'
  filter_reason: string | null
  boilerplate_count: number | null
  duplicate_flag: boolean | 0 | 1
  duplicate_pair_count: number
  duplicate_max_similarity: number | null
  duplicate_paired_with: string | null // likely a delimited list of work_ids
}

export interface DuplicateFullResponse {
  success: boolean
  count: number
  results: DuplicateFullRecord[]
  message?: string
}

// GET /api/duplicates -> { total_candidates, limit, offset, data: DuplicatePair[] }
export interface DuplicatePair {
  work_id_a: string
  work_id_b: string
  similarity: number
  constituency: string
  state: string
  description_a: string
  description_b: string
}

export interface DuplicateSummary {
  total_works_with_descriptions: number
  excluded_boilerplate: number
  excluded_beneficiary: number
  eligible_for_comparison: number
  similar_pairs_found: number
  unique_works_flagged: number
  similarity_threshold: number
  comparison_scope: string
  similarity_stats?: {
    mean: number
    median: number
    max: number
    min: number
  }
}

// ============================================================
// INNOVATION 3 — DELAY PREDICTION
// GET /api/delay-predictions/{work_id} -> single object (unwrapped)
// GET /api/delay-predictions -> { total_predictions, limit, offset, data: DelayPrediction[] }
// ============================================================
export type DelayRiskLevel = 'Low Delay Risk' | 'Medium Delay Risk' | 'High Delay Risk' | 'Critical Delay Risk'

export interface DelayPrediction {
  work_id: string
  state: string
  constituency: string
  work_category: string
  work_status: string
  status_category: 'Completed' | 'Ongoing' | 'To Be Implemented'
  sanction_amount: number
  budget_tier: string
  sanction_delay_days: number | null
  ida: string
  ida_workload: number
  predicted_duration_days: number
  delay_probability: number // 0-1
  delay_risk_level: DelayRiskLevel
  expected_projected_completion_date: string | null
  completion_duration_days: number | null
  delay_explanation: string
}

export interface DelaySummary {
  total_works_scored: number
  active_works_scored: number
  delay_threshold_days: number
  active_risk_distribution: Record<string, number>
  total_risk_distribution: Record<string, number>
  mean_predicted_duration_active_days: number
  high_delay_risk_active_count: number
  top_high_risk_active_states: Record<string, number>
}