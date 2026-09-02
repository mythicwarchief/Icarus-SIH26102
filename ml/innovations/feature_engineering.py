"""
Feature Engineering Module.

Takes the master work-level DataFrame and computes additional features
for anomaly detection: temporal, financial, vendor behavior, compliance,
threshold avoidance, and category-relative features.
"""
import numpy as np
import pandas as pd


def engineer_features(master: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all engineered features on the master DataFrame.
    Mutates and returns the same DataFrame with new columns added.
    """
    df = master.copy()

    print("[FeatureEng] Computing temporal features...")
    df = _temporal_features(df)

    print("[FeatureEng] Computing financial ratio features...")
    df = _financial_features(df)

    print("[FeatureEng] Computing vendor behavior features...")
    df = _vendor_features(df)

    print("[FeatureEng] Computing compliance features...")
    df = _compliance_features(df)

    print("[FeatureEng] Computing category-relative features...")
    df = _category_relative_features(df)

    print(f"[FeatureEng] Done. Total columns: {len(df.columns)}")
    return df


def _temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute time-based features."""
    # Sanction delay: days between recommendation and sanction
    if "recommended_date" in df.columns and "sanction_date" in df.columns:
        df["sanction_delay_days"] = (
            df["sanction_date"] - df["recommended_date"]
        ).dt.days

        # Flag instant sanctions (same day or next day)
        df["is_instant_sanction"] = df["sanction_delay_days"].between(0, 1)

    # Completion duration: days between sanction and completion
    if "sanction_date" in df.columns and "completion_date" in df.columns:
        df["completion_duration_days"] = (
            df["completion_date"] - df["sanction_date"]
        ).dt.days

    # Expenditure span: days between first and last payment
    if (
        "exp_first_payment_date" in df.columns
        and "exp_last_payment_date" in df.columns
    ):
        df["expenditure_span_days"] = (
            df["exp_last_payment_date"] - df["exp_first_payment_date"]
        ).dt.days

    # Stale work: sanctioned > 365 days ago with no completion
    if "sanction_date" in df.columns:
        today = pd.Timestamp.now()
        days_since_sanction = (today - df["sanction_date"]).dt.days
        df["is_stale_work"] = (
            (days_since_sanction > 365)
            & df["completion_date"].isna()
            & (df["status_category"] != "Completed")
        )
    else:
        df["is_stale_work"] = False

    return df


def _financial_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute financial ratio features."""
    # Use total_disbursed from features file, or exp_total_amount as fallback
    df["total_spent"] = df["total_disbursed"].fillna(df.get("exp_total_amount", 0))

    # Cost overrun ratio
    df["cost_overrun_ratio"] = np.where(
        df["sanction_amount"] > 0,
        df["total_spent"] / df["sanction_amount"],
        np.nan,
    )

    # Underspend flag for completed works
    df["is_underspend"] = (
        (df["status_category"] == "Completed")
        & (df["cost_overrun_ratio"] < 0.3)
        & df["cost_overrun_ratio"].notna()
    )

    # Sanction amount z-score (global)
    sa = df["sanction_amount"]
    sa_mean = sa.mean()
    sa_std = sa.std()
    df["sanction_amount_zscore_global"] = (
        (sa - sa_mean) / sa_std if sa_std > 0 else 0
    )

    # Clean vendor_payment_ratio (replace inf with NaN)
    if "vendor_payment_ratio" in df.columns:
        df["vendor_payment_ratio_clean"] = df["vendor_payment_ratio"].replace(
            [np.inf, -np.inf], np.nan
        )
    else:
        df["vendor_payment_ratio_clean"] = np.nan

    return df


def _vendor_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute vendor behavior features."""
    # Single vendor flag
    df["single_vendor_flag"] = (df.get("vendor_count", 0) == 1) | (
        df.get("exp_vendor_count", 0) == 1
    )

    # Vendor HHI already computed in data_loader; fill NaN with 1.0 (single vendor)
    if "vendor_hhi" not in df.columns:
        df["vendor_hhi"] = 1.0
    df["vendor_hhi"] = df["vendor_hhi"].fillna(1.0)

    # Max vendor share already computed; fill NaN
    if "max_vendor_share" not in df.columns:
        df["max_vendor_share"] = 1.0
    df["max_vendor_share"] = df["max_vendor_share"].fillna(1.0)

    return df


def _compliance_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute compliance and verification features."""
    # Missing image for completed works above threshold
    df["missing_image_flag"] = (
        (df["status_category"] == "Completed")
        & (~df.get("has_image", pd.Series(True, index=df.index)).astype(bool))
        & (df.get("amount_disbursed", 0) > 500_000)
    )

    # Payment still pending for completed works
    df["payment_still_pending"] = (
        (df["status_category"] == "Completed")
        & (df.get("exp_payment_in_progress_count", 0) > 0)
    )

    return df


def _category_relative_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute features relative to the work category."""
    if "work_category" not in df.columns:
        return df

    # Amount vs category median
    cat_medians = (
        df.groupby("work_category")["sanction_amount"]
        .median()
        .rename("cat_median_amount")
    )
    df = df.merge(cat_medians, on="work_category", how="left")
    df["amount_vs_category_median"] = np.where(
        df["cat_median_amount"] > 0,
        df["sanction_amount"] / df["cat_median_amount"],
        np.nan,
    )

    # Duration vs category median (for completed works)
    if "completion_duration_days" in df.columns:
        completed_mask = df["completion_duration_days"].notna()
        cat_dur_medians = (
            df[completed_mask]
            .groupby("work_category")["completion_duration_days"]
            .median()
            .rename("cat_median_duration")
        )
        df = df.merge(cat_dur_medians, on="work_category", how="left")
        df["duration_vs_category_median"] = np.where(
            df["cat_median_duration"] > 0,
            df["completion_duration_days"] / df["cat_median_duration"],
            np.nan,
        )
    else:
        df["cat_median_duration"] = np.nan
        df["duration_vs_category_median"] = np.nan

    return df
