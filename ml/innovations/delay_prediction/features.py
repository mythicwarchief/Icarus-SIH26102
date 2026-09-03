"""
Delay Prediction — Feature Engineering and Dataset Builder.

Constructs feature matrices for training and predicting project completion duration
and delay risk in MPLADS works.

Features engineered:
  1. Financial:
     - log_sanction_amount
     - budget_tier (encoded)
     - amount_vs_category_median
  2. Temporal & Approval Dynamics:
     - sanction_delay_days (gap between recommendation and sanction)
     - sanction_delay_vs_state_median (relative bureaucratic lag)
     - sanction_month (seasonality)
     - sanction_quarter
  3. Administrative & Locational:
     - state (target encoded / frequency encoded)
     - constituency (frequency encoded)
     - work_category (one-hot / target encoded)
     - ida_workload (number of active projects handled by this Implementing District Authority)
     - ida_historical_avg_delay (mean sanction lag of the IDA)
  4. Vendor & Risk Profile:
     - vendor_count
     - single_vendor_flag
     - vendor_hhi
     - anomaly_score (overall risk proxy)
"""
import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


from ml import config

# Target delay threshold: A project taking > 365 days (1 year) from sanction to completion is DELAYED
DELAY_THRESHOLD_DAYS = 365


def build_feature_dataset(
    master_df_path: str = config.ANOMALY_SCORES_CSV,
    sanctioned_raw_path: str = config.SANCTIONED_CSV,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Builds the complete enriched dataset with feature columns and targets.
    
    Returns:
        (df_features, df_completed_train, feature_metadata)
    """
    df = pd.read_csv(master_df_path)
    sanc_raw = pd.read_csv(sanctioned_raw_path)

    # budget_tier is not produced by the core anomaly pipeline output;
    # compute it here using the same boundaries as cost_range.py so downstream
    # tier_map logic has a value to work with.
    if "budget_tier" not in df.columns:
        def _assign_budget_tier(amount):
            if pd.isna(amount) or amount <= 0:
                return "Unknown"
            if amount < 500_000:
                return "Small"
            if amount < 2_500_000:
                return "Medium"
            if amount < 10_000_000:
                return "Large"
            return "Very Large"
        df["budget_tier"] = df["sanction_amount"].apply(_assign_budget_tier)

    # 1. Merge IDA (Implementing District Authority) if not in anomaly_scores
    if "ida" not in df.columns:
        # Match by work_id or index
        if "work_id" in sanc_raw.columns and "work_id" in df.columns:
            sanc_ida = sanc_raw[["work_id", "ida"]].drop_duplicates(subset=["work_id"])
            df = df.merge(sanc_ida, on="work_id", how="left")
        else:
            df["ida"] = sanc_raw["ida"].values[:len(df)]
    df["ida"] = df["ida"].fillna("UNKNOWN_IDA")

    # 2. Extract Date features
    df["sanction_date_parsed"] = pd.to_datetime(df["sanction_date"], errors="coerce")
    df["sanction_month"] = df["sanction_date_parsed"].dt.month.fillna(6).astype(int)
    df["sanction_quarter"] = df["sanction_date_parsed"].dt.quarter.fillna(2).astype(int)

    # 3. Financial features
    df["log_sanction_amount"] = np.log1p(df["sanction_amount"].fillna(df["sanction_amount"].median()))
    
    tier_map = {"Small": 1, "Medium": 2, "Large": 3, "Very Large": 4, "Unknown": 2}
    df["budget_tier_code"] = df["budget_tier"].map(tier_map).fillna(2).astype(int)

    # 4. Administrative workload & historical metrics
    ida_counts = df["ida"].value_counts().to_dict()
    df["ida_workload"] = df["ida"].map(ida_counts).fillna(1)

    ida_lag = df.groupby("ida")["sanction_delay_days"].transform("mean")
    df["ida_avg_sanction_lag"] = ida_lag.fillna(df["sanction_delay_days"].median())

    state_lag = df.groupby("state")["sanction_delay_days"].transform("median")
    df["sanction_delay_vs_state_median"] = df["sanction_delay_days"] / (state_lag.replace(0, 1) + 1e-3)

    # 5. Vendor & Risk features
    df["vendor_hhi_clean"] = df["vendor_hhi"].fillna(1.0)
    df["vendor_count_clean"] = df["vendor_count"].fillna(1.0)
    df["single_vendor_int"] = df["single_vendor_flag"].astype(int)
    df["anomaly_score_clean"] = df["anomaly_score"].fillna(df["anomaly_score"].median())

    # 6. Categorical Frequency Encodings
    state_counts = df["state"].value_counts(normalize=True).to_dict()
    df["state_freq"] = df["state"].map(state_counts).fillna(0.01)

    cat_counts = df["work_category"].value_counts(normalize=True).to_dict()
    df["category_freq"] = df["work_category"].map(cat_counts).fillna(0.01)

    const_counts = df["constituency"].value_counts(normalize=True).to_dict()
    df["constituency_freq"] = df["constituency"].map(const_counts).fillna(0.001)

    # Define training targets (Available for Completed projects)
    # Regression target: completion_duration_days
    # Classification target: is_delayed (1 if completion_duration_days > 365, else 0)
    df["is_delayed_target"] = (df["completion_duration_days"] > DELAY_THRESHOLD_DAYS).astype(int)

    feature_cols = [
        "log_sanction_amount",
        "budget_tier_code",
        "sanction_delay_days",
        "sanction_delay_vs_state_median",
        "sanction_month",
        "sanction_quarter",
        "ida_workload",
        "ida_avg_sanction_lag",
        "state_freq",
        "category_freq",
        "constituency_freq",
        "vendor_hhi_clean",
        "vendor_count_clean",
        "single_vendor_int",
        "anomaly_score_clean",
        "amount_vs_category_median",
    ]

    # Fill any remaining NaNs in feature columns
    for c in feature_cols:
        df[c] = df[c].fillna(df[c].median() if df[c].dtype != "object" else 0)

    completed_train = df[
        (df["status_category"] == "Completed")
        & (df["completion_duration_days"].notna())
        & (df["completion_duration_days"] > 0)
    ].copy()

    metadata = {
        "feature_cols": feature_cols,
        "delay_threshold_days": DELAY_THRESHOLD_DAYS,
        "total_works": len(df),
        "completed_train_count": len(completed_train),
    }

    return df, completed_train, metadata
