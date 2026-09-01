"""
Rule-Based Anomaly Detector.

Implements 10 domain-specific rules derived from MPLADS operational knowledge.
Each rule produces a triggered flag, severity, and human-readable explanation.
"""
import numpy as np
import pandas as pd
from .. import config


# ──────────────────────────────────────────────────────────
# Rule definitions
# ──────────────────────────────────────────────────────────

RULES = {
    "R01": {
        "name": "Cost Overrun",
        "severity": "high",
        "category": "financial",
        "description": "Disbursed amount exceeds sanctioned amount",
    },
    "R02": {
        "name": "Pre-Recommendation Sanction",
        "severity": "critical",
        "category": "temporal",
        "description": "Work sanctioned before it was recommended",
    },
    "R03": {
        "name": "Excessive Sanction Delay",
        "severity": "medium",
        "category": "temporal",
        "description": "Sanction took more than 365 days after recommendation",
    },
    "R04": {
        "name": "Suspiciously Fast Completion",
        "severity": "high",
        "category": "temporal",
        "description": "Large-budget work completed in under 7 days",
    },
    "R05": {
        "name": "Missing Verification Photo",
        "severity": "medium",
        "category": "compliance",
        "description": "Completed high-value work with no verification image",
    },
    "R06": {
        "name": "Vendor Monopolization",
        "severity": "high",
        "category": "vendor",
        "description": "Single vendor dominates payments despite multiple transactions",
    },
    "R07": {
        "name": "Potential Contract Splitting",
        "severity": "high",
        "category": "financial",
        "description": "High proportion of payments just below statutory thresholds",
    },
    "R08": {
        "name": "Pending Payment on Completed Work",
        "severity": "medium",
        "category": "compliance",
        "description": "Work marked completed but payments are still in-progress",
    },
    "R09": {
        "name": "Single-Vendor Large Project",
        "severity": "medium",
        "category": "vendor",
        "description": "All funds for a large project directed to a single vendor",
    },
    "R10": {
        "name": "Excessive Upfront Payment",
        "severity": "high",
        "category": "financial",
        "description": "Over 90% of funds disbursed in the first payment",
    },
}

# Severity weights for scoring
SEVERITY_WEIGHT = {
    "low": 0.25,
    "medium": 0.50,
    "high": 0.75,
    "critical": 1.00,
}


def detect(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run all rule-based checks on the master DataFrame.

    Adds columns:
    - rule_score (float 0–1)
    - triggered_rules (str, comma-separated rule IDs)
    - rule_explanations (list of explanation strings)
    - rule_categories (str, primary category)
    """
    print("[RuleDetector] Running rule-based anomaly detection...")
    thresholds = config.RULE_THRESHOLDS
    n = len(df)

    # Initialize result containers
    all_triggered = [[] for _ in range(n)]
    all_explanations = [[] for _ in range(n)]
    all_severities = [[] for _ in range(n)]
    all_categories = [[] for _ in range(n)]

    # R01: Cost Overrun
    _check_rule(
        df, all_triggered, all_explanations, all_severities, all_categories,
        rule_id="R01",
        mask=(df.get("cost_overrun_ratio", pd.Series(dtype=float)) > thresholds["cost_overrun_ratio_max"]),
        explanation_fn=lambda row: (
            f"Total expenditure (₹{row.get('total_spent', 0):,.0f}) exceeds "
            f"the sanctioned amount (₹{row.get('sanction_amount', 0):,.0f}) "
            f"by {((row.get('cost_overrun_ratio', 0) - 1) * 100):.0f}%, "
            f"indicating a cost overrun."
        ),
    )

    # R02: Pre-Recommendation Sanction
    _check_rule(
        df, all_triggered, all_explanations, all_severities, all_categories,
        rule_id="R02",
        mask=(df.get("sanction_delay_days", pd.Series(dtype=float)) < thresholds["sanction_delay_negative"]),
        explanation_fn=lambda row: (
            f"This work was sanctioned {abs(row.get('sanction_delay_days', 0)):.0f} days "
            f"BEFORE it was recommended, which is a temporal anomaly suggesting "
            f"backdated recommendations or data entry error."
        ),
    )

    # R03: Excessive Sanction Delay
    _check_rule(
        df, all_triggered, all_explanations, all_severities, all_categories,
        rule_id="R03",
        mask=(df.get("sanction_delay_days", pd.Series(dtype=float)) > thresholds["sanction_delay_excessive_days"]),
        explanation_fn=lambda row: (
            f"Sanction was delayed by {row.get('sanction_delay_days', 0):.0f} days "
            f"after recommendation, far exceeding the typical processing time."
        ),
    )

    # R04: Suspiciously Fast Completion
    completion_days = df.get("completion_duration_days", pd.Series(dtype=float))
    sanction_amt = df.get("sanction_amount", pd.Series(dtype=float))
    _check_rule(
        df, all_triggered, all_explanations, all_severities, all_categories,
        rule_id="R04",
        mask=(
            (completion_days < thresholds["fast_completion_days"])
            & (completion_days.notna())
            & (sanction_amt > thresholds["fast_completion_min_amount"])
        ),
        explanation_fn=lambda row: (
            f"This ₹{row.get('sanction_amount', 0):,.0f} work was completed in only "
            f"{row.get('completion_duration_days', 0):.0f} days, which is suspiciously "
            f"fast for a project of this budget."
        ),
    )

    # R05: Missing Verification Photo
    _check_rule(
        df, all_triggered, all_explanations, all_severities, all_categories,
        rule_id="R05",
        mask=df.get("missing_image_flag", pd.Series(False, index=df.index)).astype(bool),
        explanation_fn=lambda row: (
            f"Completed work worth ₹{row.get('amount_disbursed', 0):,.0f} has no "
            f"verification photograph attached, which is a compliance gap."
        ),
    )

    # R06: Vendor Monopolization
    vendor_hhi = df.get("vendor_hhi", pd.Series(dtype=float))
    pay_count = df.get("payment_count", pd.Series(0, index=df.index, dtype=int))
    _check_rule(
        df, all_triggered, all_explanations, all_severities, all_categories,
        rule_id="R06",
        mask=(
            (vendor_hhi > thresholds["vendor_hhi_monopolization"])
            & (pay_count > 3)
        ),
        explanation_fn=lambda row: (
            f"{row.get('max_vendor_share', 0) * 100:.0f}% of all payments "
            f"({row.get('payment_count', 0)} transactions) were directed to a single vendor, "
            f"suggesting vendor monopolization (HHI={row.get('vendor_hhi', 0):.2f})."
        ),
    )

    # R07: Potential Contract Splitting
    _check_rule(
        df, all_triggered, all_explanations, all_severities, all_categories,
        rule_id="R07",
        mask=(df.get("near_threshold_ratio", pd.Series(0.0, index=df.index)) > thresholds["near_threshold_ratio_suspicious"]),
        explanation_fn=lambda row: (
            f"{row.get('near_threshold_count', 0):.0f} out of {row.get('payment_count', 0)} "
            f"payments ({row.get('near_threshold_ratio', 0) * 100:.0f}%) fall just below "
            f"statutory thresholds, suggesting potential contract splitting."
        ),
    )

    # R08: Pending Payment on Completed Work
    _check_rule(
        df, all_triggered, all_explanations, all_severities, all_categories,
        rule_id="R08",
        mask=df.get("payment_still_pending", pd.Series(False, index=df.index)).astype(bool),
        explanation_fn=lambda row: (
            f"This work is marked as completed but still has "
            f"{row.get('exp_payment_in_progress_count', 0):.0f} payment(s) in-progress, "
            f"indicating a financial inconsistency."
        ),
    )

    # R09: Single-Vendor Large Project
    single_vendor = df.get("single_vendor_flag", pd.Series(False, index=df.index))
    total_spent = df.get("total_spent", pd.Series(0.0, index=df.index))
    _check_rule(
        df, all_triggered, all_explanations, all_severities, all_categories,
        rule_id="R09",
        mask=(single_vendor.astype(bool)) & (total_spent > thresholds["single_vendor_min_amount"]),
        explanation_fn=lambda row: (
            f"All ₹{row.get('total_spent', 0):,.0f} of expenditure was directed to a "
            f"single vendor for this large project, raising concentration risk."
        ),
    )

    # R10: Excessive Upfront Payment
    adv_ratio = df.get("advance_payment_ratio", pd.Series(dtype=float))
    _check_rule(
        df, all_triggered, all_explanations, all_severities, all_categories,
        rule_id="R10",
        mask=(
            (adv_ratio > thresholds["advance_payment_ratio_max"])
            & (pay_count > 1)
        ),
        explanation_fn=lambda row: (
            f"{row.get('advance_payment_ratio', 0) * 100:.0f}% of total funds were disbursed "
            f"in the first payment, despite having {row.get('payment_count', 0)} total payments, "
            f"indicating excessive upfront payment."
        ),
    )

    # ── Compute composite rule score ──
    rule_scores = []
    triggered_strs = []
    explanation_strs = []
    primary_categories = []

    for i in range(n):
        if all_triggered[i]:
            # Weighted sum of severity scores for triggered rules
            total_weight = sum(SEVERITY_WEIGHT[s] for s in all_severities[i])
            max_possible = len(all_triggered[i]) * 1.0  # max is critical=1.0 each
            score = min(total_weight / max(max_possible, 1), 1.0)
            # Boost score if multiple rules triggered
            multiplier = 1.0 + 0.1 * (len(all_triggered[i]) - 1)
            score = min(score * multiplier, 1.0)
            rule_scores.append(score)
            triggered_strs.append(",".join(all_triggered[i]))
            explanation_strs.append(" | ".join(all_explanations[i]))
            # Primary category = most common category
            if all_categories[i]:
                primary_categories.append(
                    max(set(all_categories[i]), key=all_categories[i].count)
                )
            else:
                primary_categories.append("unknown")
        else:
            rule_scores.append(0.0)
            triggered_strs.append("")
            explanation_strs.append("")
            primary_categories.append("")

    df["rule_score"] = rule_scores
    df["triggered_rules"] = triggered_strs
    df["rule_explanations"] = explanation_strs
    df["rule_primary_category"] = primary_categories

    flagged = (df["rule_score"] > 0).sum()
    print(f"[RuleDetector] Done. {flagged} records triggered at least one rule.")

    # Per-rule counts
    for rid in RULES:
        count = sum(1 for t in all_triggered if rid in t)
        if count > 0:
            print(f"  {rid} ({RULES[rid]['name']}): {count} triggers")

    return df


def _check_rule(
    df: pd.DataFrame,
    all_triggered: list,
    all_explanations: list,
    all_severities: list,
    all_categories: list,
    rule_id: str,
    mask: pd.Series,
    explanation_fn,
):
    """Helper to apply a rule and collect results."""
    rule_info = RULES[rule_id]
    # Ensure mask is boolean and aligned with df index
    mask = mask.reindex(df.index, fill_value=False).astype(bool)

    for i, (idx, row) in enumerate(df.iterrows()):
        if mask.iloc[i]:
            all_triggered[i].append(rule_id)
            try:
                expl = explanation_fn(row)
            except Exception:
                expl = rule_info["description"]
            all_explanations[i].append(expl)
            all_severities[i].append(rule_info["severity"])
            all_categories[i].append(rule_info["category"])
