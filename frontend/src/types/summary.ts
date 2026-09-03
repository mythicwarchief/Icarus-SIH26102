// Matches ml/schemas.py -> SUMMARY_TEMPLATE, served by GET /api/summary
export interface AnomalySummary {
  total_works_analyzed: number
  total_anomalies: number
  anomaly_rate_percent: number
  severity_distribution: {
    critical: number
    high: number
    medium: number
    low: number
  }
  category_distribution: {
    financial: number
    temporal: number
    vendor: number
    compliance: number
    statistical: number
  }
  status_distribution: {
    Completed: number
    Ongoing: number
    'To Be Implemented': number
  }
  status_anomaly_distribution: {
    Completed: number
    Ongoing: number
    'To Be Implemented': number
  }
  top_anomaly_states: string[]
  top_triggered_rules: string[]
  score_statistics: {
    mean: number
    median: number
    std: number
    p90: number
    p95: number
    p99: number
  }
  pipeline_run_timestamp: string
}
