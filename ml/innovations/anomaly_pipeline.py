"""
MPLADS Anomaly Detection Pipeline — Main Orchestrator.

Runs the complete pipeline end-to-end:
1. Load & merge data
2. Engineer features
3. Run statistical detector
4. Run rule-based detector
5. Run Isolation Forest detector
6. Ensemble scoring
7. Generate explanations
8. Save outputs

Usage:
    python -m ml.anomaly_pipeline
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# Add parent directory to path so we can import ml package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml import config
from ml.data_loader import build_master_dataset
from ml.feature_engineering import engineer_features
from ml.cost_estimation.cost_range import estimate_cost_ranges
from ml.detectors import statistical, rule_based, isolation_forest, ensemble
from ml.explainer import generate_explanations
from ml import schemas


def run_pipeline():
    """Execute the full anomaly detection pipeline."""
    start_time = time.time()
    print("=" * 70)
    print("  MPLADS ANOMALY DETECTION PIPELINE")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ── Stage 1: Data Loading & Merging ──
    print("\n[1/9] STAGE 1: Data Loading & Merging")
    print("-" * 50)
    master = build_master_dataset()

    # ── Stage 2: Feature Engineering ──
    print("\n[2/9] STAGE 2: Feature Engineering")
    print("-" * 50)
    master = engineer_features(master)

    # ── Stage 3: Expected Cost Range Estimation ──
    print("\n[3/9] STAGE 3: Expected Cost Range Estimation")
    print("-" * 50)
    master = estimate_cost_ranges(master)

    # ── Stage 4: Statistical Detection ──
    print("\n[4/9] STAGE 4: Statistical Anomaly Detection")
    print("-" * 50)
    master = statistical.detect(master)

    # ── Stage 5: Rule-Based Detection ──
    print("\n[5/9] STAGE 5: Rule-Based Anomaly Detection")
    print("-" * 50)
    master = rule_based.detect(master)

    # ── Stage 6: Isolation Forest Detection ──
    print("\n[6/9] STAGE 6: Isolation Forest Anomaly Detection")
    print("-" * 50)
    master = isolation_forest.detect(master)

    # ── Stage 7: Ensemble Scoring ──
    print("\n[7/9] STAGE 7: Ensemble Scoring")
    print("-" * 50)
    master = ensemble.combine(master)

    # ── Stage 8: Explanation Generation ──
    print("\n[8/9] STAGE 8: Explanation Generation")
    print("-" * 50)
    master = generate_explanations(master)

    # ── Stage 9: Save Outputs ──
    print("\n[9/9] STAGE 9: Saving Outputs")
    print("-" * 50)
    _save_outputs(master)

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"  PIPELINE COMPLETE in {elapsed:.1f} seconds")
    print("=" * 70)

    return master


def _save_outputs(df: pd.DataFrame):
    """Save all output files."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.MODEL_DIR, exist_ok=True)

    # Filter to available columns only
    available_cols = [c for c in schemas.ANOMALY_SCORES_COLUMNS if c in df.columns]

    # ── anomaly_scores.csv (all records) ──
    scores_df = df[available_cols].copy()
    # Convert datetime columns to string for CSV
    for col in ["recommended_date", "sanction_date", "completion_date"]:
        if col in scores_df.columns:
            scores_df[col] = scores_df[col].astype(str).replace("NaT", "")
    scores_df.to_csv(config.ANOMALY_SCORES_CSV, index=False)
    print(f"  [OK] anomaly_scores.csv: {len(scores_df)} records")

    # ── anomaly_flagged.csv (flagged subset) ──
    flagged_df = scores_df[scores_df["anomaly_label"] == True].copy()
    flagged_df = flagged_df.sort_values("anomaly_score", ascending=False)
    flagged_df.to_csv(config.ANOMALY_FLAGGED_CSV, index=False)
    print(f"  [OK] anomaly_flagged.csv: {len(flagged_df)} flagged records")

    # ── anomaly_summary.json ──
    summary = _build_summary(df)
    with open(config.ANOMALY_SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  [OK] anomaly_summary.json")

    print(f"\n  All outputs saved to: {config.OUTPUT_DIR}")


def _build_summary(df: pd.DataFrame) -> dict:
    """Build the dashboard-ready summary JSON."""
    summary = schemas.SUMMARY_TEMPLATE.copy()

    flagged = df[df["anomaly_label"] == True]

    summary["total_works_analyzed"] = int(len(df))
    summary["total_anomalies"] = int(len(flagged))
    summary["anomaly_rate_percent"] = round(
        len(flagged) / len(df) * 100 if len(df) > 0 else 0, 2
    )

    # Severity distribution
    if len(flagged) > 0:
        sev_counts = flagged["anomaly_severity"].value_counts().to_dict()
        summary["severity_distribution"] = {
            "critical": int(sev_counts.get("critical", 0)),
            "high": int(sev_counts.get("high", 0)),
            "medium": int(sev_counts.get("medium", 0)),
            "low": int(sev_counts.get("low", 0)),
        }

    # Category distribution
    if len(flagged) > 0 and "anomaly_category" in flagged.columns:
        cat_counts = flagged["anomaly_category"].value_counts().to_dict()
        summary["category_distribution"] = {
            "financial": int(cat_counts.get("financial", 0)),
            "temporal": int(cat_counts.get("temporal", 0)),
            "vendor": int(cat_counts.get("vendor", 0)),
            "compliance": int(cat_counts.get("compliance", 0)),
            "statistical": int(cat_counts.get("statistical", 0)),
        }

    # Status distributions
    if "status_category" in df.columns:
        status_counts = df["status_category"].value_counts().to_dict()
        summary["status_distribution"] = {
            "Completed": int(status_counts.get("Completed", 0)),
            "Ongoing": int(status_counts.get("Ongoing", 0)),
            "To Be Implemented": int(status_counts.get("To Be Implemented", 0)),
        }
        # Anomalies per status
        if len(flagged) > 0:
            status_anom = flagged["status_category"].value_counts().to_dict()
            summary["status_anomaly_distribution"] = {
                "Completed": int(status_anom.get("Completed", 0)),
                "Ongoing": int(status_anom.get("Ongoing", 0)),
                "To Be Implemented": int(status_anom.get("To Be Implemented", 0)),
            }

    # Top anomaly states
    if len(flagged) > 0 and "state" in flagged.columns:
        state_counts = flagged["state"].value_counts().head(10)
        summary["top_anomaly_states"] = [
            {"state": s, "count": int(c)} for s, c in state_counts.items()
        ]

    # Top triggered rules
    if len(flagged) > 0 and "triggered_rules" in flagged.columns:
        all_rules = []
        for rules_str in flagged["triggered_rules"].dropna():
            if rules_str:
                all_rules.extend(rules_str.split(","))
        if all_rules:
            from collections import Counter
            rule_counts = Counter(all_rules).most_common(10)
            summary["top_triggered_rules"] = [
                {"rule_id": r, "count": int(c)} for r, c in rule_counts
            ]

    # Score statistics
    scores = df["anomaly_score"]
    summary["score_statistics"] = {
        "mean": round(float(scores.mean()), 4),
        "median": round(float(scores.median()), 4),
        "std": round(float(scores.std()), 4),
        "p90": round(float(scores.quantile(0.90)), 4),
        "p95": round(float(scores.quantile(0.95)), 4),
        "p99": round(float(scores.quantile(0.99)), 4),
    }

    # Model metadata
    summary["model_metadata"] = {
        "isolation_forest_contamination": str(config.IF_CONTAMINATION),
        "isolation_forest_n_estimators": config.IF_N_ESTIMATORS,
        "ensemble_weights": config.ENSEMBLE_WEIGHTS,
        "anomaly_flag_threshold": config.ANOMALY_FLAG_THRESHOLD,
    }

    summary["pipeline_run_timestamp"] = datetime.now(timezone.utc).isoformat()

    return summary


if __name__ == "__main__":
    run_pipeline()
