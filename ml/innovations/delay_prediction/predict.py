"""
Delay Prediction — Inference and Predictions Exporter.

Loads the trained models, runs predictions across all 7,000 works (especially active: Ongoing & To Be Implemented),
and outputs structured risk assessments.

Output columns generated:
  - predicted_duration_days: Model-estimated duration from sanction to completion.
  - delay_probability: Probability (0.0 to 1.0) of project exceeding 365 days.
  - delay_risk_level: "Low", "Medium", "High", "Critical".
  - expected_completion_date: Projected completion timestamp for ongoing/sanctioned works.
  - delay_explanation: Human-readable narrative explaining the primary risk factors.
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import timedelta

from ml import config
from ml.innovations.delay_prediction.features import build_feature_dataset, DELAY_THRESHOLD_DAYS


from ml.innovations import config as innovations_config
OUTPUT_DIR = innovations_config.OUTPUT_DIR
DELAY_PREDICTIONS_CSV = os.path.join(OUTPUT_DIR, "delay_predictions.csv")
DELAY_SUMMARY_JSON = os.path.join(OUTPUT_DIR, "delay_prediction_summary.json")
MODEL_BUNDLE_PATH = os.path.join(innovations_config.MODEL_DIR, "delay_prediction_models.joblib")


def predict_all_works():
    """Generates delay predictions and explainability fields for all 7,000 works."""
    print("=" * 70)
    print("  MPLADS PROJECT DELAY PREDICTION — INFERENCE PIPELINE")
    print("=" * 70)

    if not os.path.exists(MODEL_BUNDLE_PATH):
        from ml.innovations.delay_prediction.train import train_delay_models
        bundle = train_delay_models()
    else:
        bundle = joblib.load(MODEL_BUNDLE_PATH)

    regressor = bundle["regressor"]
    classifier = bundle["classifier"]
    feature_cols = bundle["feature_cols"]

    full_df, _, _ = build_feature_dataset()
    X = full_df[feature_cols].values

    print(f"\n[Inference] Scoring all {len(full_df)} works...")

    # Predict duration & delay probability
    pred_durations = regressor.predict(X)
    pred_probs = classifier.predict_proba(X)[:, 1]

    full_df["predicted_duration_days"] = np.round(pred_durations, 1)
    full_df["delay_probability"] = np.round(pred_probs, 4)

    # Assign Risk Tiers based on probability
    conditions = [
        full_df["delay_probability"] >= 0.70,
        full_df["delay_probability"] >= 0.45,
        full_df["delay_probability"] >= 0.25,
    ]
    choices = ["Critical Delay Risk", "High Delay Risk", "Medium Delay Risk"]
    full_df["delay_risk_level"] = np.select(conditions, choices, default="Low Delay Risk")

    # Compute Expected Projected Completion Date for active works
    full_df["sanction_date_dt"] = pd.to_datetime(full_df["sanction_date"], errors="coerce")
    projected_dates = []
    for idx, row in full_df.iterrows():
        s_date = row["sanction_date_dt"]
        dur = row["predicted_duration_days"]
        if pd.notna(s_date) and pd.notna(dur):
            proj = s_date + timedelta(days=float(dur))
            projected_dates.append(proj.strftime("%Y-%m-%d"))
        else:
            projected_dates.append("")
    full_df["expected_projected_completion_date"] = projected_dates

    # Generate Explainability strings
    full_df["delay_explanation"] = full_df.apply(_generate_delay_explanation, axis=1)

    # Export Columns
    export_cols = [
        "work_id",
        "state",
        "constituency",
        "work_category",
        "work_status",
        "status_category",
        "sanction_amount",
        "budget_tier",
        "sanction_delay_days",
        "ida",
        "ida_workload",
        "predicted_duration_days",
        "delay_probability",
        "delay_risk_level",
        "expected_projected_completion_date",
        "completion_duration_days",
        "delay_explanation",
    ]

    export_df = full_df[export_cols].sort_values("delay_probability", ascending=False)
    export_df.to_csv(DELAY_PREDICTIONS_CSV, index=False)
    print(f"[Saved] Delay predictions exported to: {DELAY_PREDICTIONS_CSV}")

    # Build Summary JSON
    summary = _build_delay_summary(full_df, bundle)
    with open(DELAY_SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[Saved] Summary exported to: {DELAY_SUMMARY_JSON}")

    # Print Quick Stats
    active_works = full_df[full_df["status_category"].isin(["Ongoing", "To Be Implemented"])]
    high_risk_active = active_works[active_works["delay_probability"] >= 0.45]
    print(f"\n[Summary on Active Projects (Ongoing + To Be Implemented)]:")
    print(f"  Total Active Works: {len(active_works)}")
    print(f"  High / Critical Delay Risk: {len(high_risk_active)} ({len(high_risk_active)/len(active_works)*100:.1f}%)")
    print(f"  Mean Predicted Duration: {active_works['predicted_duration_days'].mean():.1f} days")

    return export_df


def _generate_delay_explanation(row) -> str:
    """Generates a plain-English explanation for the project's delay assessment."""
    prob = row.get("delay_probability", 0.0)
    days = row.get("predicted_duration_days", 0.0)
    risk = row.get("delay_risk_level", "Low")
    s_lag = row.get("sanction_delay_days", 0)
    ida = row.get("ida", "District Authority")
    workload = row.get("ida_workload", 1)
    status = row.get("status_category", "Ongoing")

    parts = []
    parts.append(f"Predicted duration is ~{days:.0f} days ({prob*100:.0f}% probability of severe delay).")

    if s_lag > 180:
        parts.append(f"High administrative sanction lag ({s_lag} days) signals bureaucratic friction.")
    if workload > 100:
        parts.append(f"Implementing Authority ({ida[:35]}...) handles a heavy load of {int(workload)} concurrent projects.")
    if row.get("single_vendor_flag", False):
        parts.append("Single vendor reliance increases supply chain delivery risks.")

    if status == "Completed":
        actual = row.get("completion_duration_days", 0)
        parts.append(f"Actual historical completion took {actual:.0f} days.")
    else:
        proj_dt = row.get("expected_projected_completion_date", "")
        if proj_dt:
            parts.append(f"Projected completion target: {proj_dt}.")

    return " ".join(parts)


def _build_delay_summary(df: pd.DataFrame, bundle: dict) -> dict:
    """Creates a dashboard summary JSON for Vaishnav and Navneeth."""
    active = df[df["status_category"].isin(["Ongoing", "To Be Implemented"])]

    return {
        "total_works_scored": len(df),
        "active_works_scored": len(active),
        "delay_threshold_days": DELAY_THRESHOLD_DAYS,
        "active_risk_distribution": active["delay_risk_level"].value_counts().to_dict(),
        "total_risk_distribution": df["delay_risk_level"].value_counts().to_dict(),
        "mean_predicted_duration_active_days": round(float(active["predicted_duration_days"].mean()), 1),
        "high_delay_risk_active_count": int((active["delay_probability"] >= 0.45).sum()),
        "model_performance_cv": bundle.get("cv_metrics", {}),
        "top_high_risk_active_states": active[active["delay_probability"] >= 0.45]["state"].value_counts().head(5).to_dict()
    }


if __name__ == "__main__":
    predict_all_works()
