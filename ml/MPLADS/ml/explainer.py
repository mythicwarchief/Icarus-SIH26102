"""
Explainability Module.

Generates human-readable explanations for every flagged anomaly,
combining rule-based explanations with statistical feature analysis.
"""
import numpy as np
import pandas as pd


def generate_explanations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate a final explanation string for each flagged record.

    Adds columns:
    - explanation (str): Primary human-readable explanation
    - explanation_details (str): JSON-like detailed explanation
    - key_metrics (str): Key metrics that contributed to the flag
    """
    print("[Explainer] Generating explanations for flagged records...")

    explanations = []
    details_list = []
    metrics_list = []

    for _, row in df.iterrows():
        if not row.get("anomaly_label", False):
            explanations.append("")
            details_list.append("")
            metrics_list.append("")
            continue

        expl_parts = []
        metric_parts = []

        # 1. Use rule-based explanations if available
        rule_expl = row.get("rule_explanations", "")
        if rule_expl:
            # Split on separator and take them as individual explanations
            parts = [p.strip() for p in str(rule_expl).split("|") if p.strip()]
            expl_parts.extend(parts)

        # 2. Add statistical context if no rule explanations
        if not expl_parts:
            expl_parts.extend(_statistical_explanation(row))

        # 3. Add IF context if IF flagged but no rules
        if not expl_parts and row.get("if_score", 0) > 0.5:
            expl_parts.append(
                "This work was flagged by the machine learning model as statistically "
                "unusual compared to similar works based on its financial and operational profile."
            )

        # 4. Always add top contributing metrics
        metric_parts = _key_metrics(row)

        # Combine
        explanation = " ".join(expl_parts[:3])  # Top 3 explanation sentences
        metrics_str = "; ".join(metric_parts[:5])  # Top 5 metrics

        explanations.append(explanation)
        details_list.append(str(row.get("triggered_rules", "")))
        metrics_list.append(metrics_str)

    df["explanation"] = explanations
    df["explanation_details"] = details_list
    df["key_metrics"] = metrics_list

    flagged_with_expl = sum(1 for e in explanations if e)
    print(f"[Explainer] Done. {flagged_with_expl} records received explanations.")

    return df


def _statistical_explanation(row) -> list[str]:
    """Generate explanation based on statistical features."""
    parts = []

    # Check which statistical measures are extreme
    stat_score = row.get("statistical_score", 0)
    if stat_score > 0.5:
        # Check specific features
        cost_ratio = row.get("cost_overrun_ratio", None)
        if cost_ratio and not np.isnan(cost_ratio) and cost_ratio > 1.2:
            parts.append(
                f"The expenditure-to-sanction ratio of {cost_ratio:.2f} is "
                f"significantly above the expected value of 1.0."
            )

        delay = row.get("sanction_delay_days", None)
        if delay and not np.isnan(delay):
            if delay > 365:
                parts.append(
                    f"The sanction took {delay:.0f} days after recommendation, "
                    f"which is unusually long."
                )
            elif delay < 0:
                parts.append(
                    f"The sanction appears to predate the recommendation by "
                    f"{abs(delay):.0f} days."
                )

        duration = row.get("completion_duration_days", None)
        amount = row.get("sanction_amount", 0)
        if duration and not np.isnan(duration):
            if duration < 7 and amount > 200_000:
                parts.append(
                    f"The ₹{amount:,.0f} project completed in only {duration:.0f} days."
                )
            elif duration and not np.isnan(duration) and duration > 730:
                parts.append(
                    f"The project took {duration:.0f} days to complete "
                    f"({duration/365:.1f} years)."
                )

        hhi = row.get("vendor_hhi", None)
        if hhi and not np.isnan(hhi) and hhi > 0.8:
            parts.append(
                f"Vendor concentration index (HHI) of {hhi:.2f} suggests "
                f"payments are heavily concentrated."
            )

    if not parts and stat_score > 0.3:
        parts.append(
            "This work shows unusual patterns across multiple financial "
            "and operational metrics compared to similar works."
        )

    return parts


def _key_metrics(row) -> list[str]:
    """Extract the most relevant metrics for display."""
    metrics = []

    sa = row.get("sanction_amount")
    if sa and not np.isnan(sa):
        metrics.append(f"Sanction: ₹{sa:,.0f}")

    ts = row.get("total_spent")
    if ts and not np.isnan(ts):
        metrics.append(f"Disbursed: ₹{ts:,.0f}")

    cr = row.get("cost_overrun_ratio")
    if cr and not np.isnan(cr):
        metrics.append(f"Cost ratio: {cr:.2f}")

    sd = row.get("sanction_delay_days")
    if sd and not np.isnan(sd):
        metrics.append(f"Sanction delay: {sd:.0f}d")

    cd = row.get("completion_duration_days")
    if cd and not np.isnan(cd):
        metrics.append(f"Duration: {cd:.0f}d")

    hhi = row.get("vendor_hhi")
    if hhi and not np.isnan(hhi):
        metrics.append(f"Vendor HHI: {hhi:.2f}")

    pc = row.get("payment_count")
    if pc and not np.isnan(pc):
        metrics.append(f"Payments: {int(pc)}")

    vc = row.get("vendor_count")
    if vc and not np.isnan(vc):
        metrics.append(f"Vendors: {int(vc)}")

    return metrics
