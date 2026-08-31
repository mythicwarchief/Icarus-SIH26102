"""
Ensemble Anomaly Combiner.

Combines scores from statistical, rule-based, and Isolation Forest detectors
into a single composite anomaly score with severity classification.
"""
import numpy as np
import pandas as pd
from .. import config


def combine(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combine all detector scores into a final anomaly assessment.

    Expects columns: statistical_score, rule_score, if_score
    Adds columns: anomaly_score, anomaly_label, anomaly_severity, anomaly_category
    """
    print("[Ensemble] Combining detector scores...")

    weights = config.ENSEMBLE_WEIGHTS

    # Get individual scores (default to 0 if missing)
    stat = df.get("statistical_score", pd.Series(0.0, index=df.index)).fillna(0)
    rule = df.get("rule_score", pd.Series(0.0, index=df.index)).fillna(0)
    iso = df.get("if_score", pd.Series(0.0, index=df.index)).fillna(0)

    # Weighted combination
    composite = (
        weights["statistical"] * stat
        + weights["rule_based"] * rule
        + weights["isolation_forest"] * iso
    )

    # Clip to [0, 1]
    df["anomaly_score"] = composite.clip(0, 1)

    # Binary label
    df["anomaly_label"] = df["anomaly_score"] >= config.ANOMALY_FLAG_THRESHOLD

    # Severity classification
    df["anomaly_severity"] = df["anomaly_score"].apply(_classify_severity)

    # Primary anomaly category
    df["anomaly_category"] = df.apply(_determine_category, axis=1)

    # Summary stats
    total_flagged = df["anomaly_label"].sum()
    severity_counts = df[df["anomaly_label"]]["anomaly_severity"].value_counts()
    print(f"[Ensemble] Done. {total_flagged} anomalies flagged out of {len(df)} works.")
    print(f"[Ensemble] Severity distribution:")
    for sev in ["critical", "high", "medium", "low"]:
        count = severity_counts.get(sev, 0)
        if count > 0:
            print(f"  {sev}: {count}")

    return df


def _classify_severity(score: float) -> str:
    """Map anomaly score to severity level."""
    thresholds = config.SEVERITY_THRESHOLDS
    if score >= thresholds["critical"]:
        return "critical"
    elif score >= thresholds["high"]:
        return "high"
    elif score >= thresholds["medium"]:
        return "medium"
    elif score >= thresholds["low"]:
        return "low"
    else:
        return "none"


def _determine_category(row) -> str:
    """
    Determine the primary anomaly category based on which detector
    contributed the most to the anomaly score.
    """
    if not row.get("anomaly_label", False):
        return ""

    # If rules triggered, use rule's primary category
    rule_cat = row.get("rule_primary_category", "")
    if rule_cat:
        return rule_cat

    # Otherwise, determine from which detector scored highest
    stat = row.get("statistical_score", 0) or 0
    iso = row.get("if_score", 0) or 0

    if stat >= iso:
        return "statistical"
    else:
        return "statistical"  # IF doesn't have a clear category, default
