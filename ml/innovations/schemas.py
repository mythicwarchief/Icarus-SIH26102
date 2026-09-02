"""
Output Schemas Module.

Defines the exact output column specifications for CSV and JSON outputs,
ensuring compatibility with the FastAPI backend's anomaly_service.py.
"""

# ──────────────────────────────────────────────────────────
# Columns to include in anomaly_scores.csv (all records)
# ──────────────────────────────────────────────────────────
ANOMALY_SCORES_COLUMNS = [
    # Identifiers
    "work_id",
    "state",
    "constituency",
    "honble_members_of_parliament",
    "work_category",
    "work_description",
    "work_status",
    "status_category",

    # Anomaly assessment
    "anomaly_score",
    "anomaly_label",
    "anomaly_severity",
    "anomaly_category",
    "triggered_rules",
    "explanation",
    "key_metrics",

    # Individual detector scores
    "statistical_score",
    "rule_score",
    "if_score",

    # Key financial metrics
    "sanction_amount",
    "total_spent",
    "cost_overrun_ratio",
    "amount_disbursed",

    # Expected Cost Range
    "expected_cost_low",
    "expected_cost_high",
    "expected_cost_narrow_low",
    "expected_cost_narrow_high",
    "expected_cost_median",
    "comparison_group",
    "comparison_group_size",
    "cost_in_expected_range",
    "cost_deviation_pct",
    "cost_range_explanation",
    "budget_tier",

    # Temporal metrics
    "sanction_delay_days",
    "completion_duration_days",
    "recommended_date",
    "sanction_date",
    "completion_date",

    # Vendor metrics
    "vendor_hhi",
    "vendor_count",
    "payment_count",
    "max_vendor_share",
    "single_vendor_flag",

    # Compliance
    "missing_image_flag",
    "payment_still_pending",

    # Threshold detection
    "near_threshold_count",
    "near_threshold_ratio",
    "advance_payment_ratio",

    # Category-relative
    "amount_vs_category_median",
    "duration_vs_category_median",
]

# ──────────────────────────────────────────────────────────
# Columns for anomaly_flagged.csv (flagged subset only)
# ──────────────────────────────────────────────────────────
ANOMALY_FLAGGED_COLUMNS = ANOMALY_SCORES_COLUMNS  # Same schema, just filtered

# ──────────────────────────────────────────────────────────
# anomaly_summary.json structure template
# ──────────────────────────────────────────────────────────
SUMMARY_TEMPLATE = {
    "total_works_analyzed": 0,
    "total_anomalies": 0,
    "anomaly_rate_percent": 0.0,
    "severity_distribution": {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    },
    "category_distribution": {
        "financial": 0,
        "temporal": 0,
        "vendor": 0,
        "compliance": 0,
        "statistical": 0,
    },
    "status_distribution": {
        "Completed": 0,
        "Ongoing": 0,
        "To Be Implemented": 0,
    },
    "status_anomaly_distribution": {
        "Completed": 0,
        "Ongoing": 0,
        "To Be Implemented": 0,
    },
    "top_anomaly_states": [],
    "top_triggered_rules": [],
    "score_statistics": {
        "mean": 0.0,
        "median": 0.0,
        "std": 0.0,
        "p90": 0.0,
        "p95": 0.0,
        "p99": 0.0,
    },
    "model_metadata": {
        "isolation_forest_contamination": "auto",
        "isolation_forest_n_estimators": 200,
        "ensemble_weights": {
            "statistical": 0.25,
            "rule_based": 0.40,
            "isolation_forest": 0.35,
        },
        "anomaly_flag_threshold": 0.40,
    },
    "pipeline_run_timestamp": "",
}
