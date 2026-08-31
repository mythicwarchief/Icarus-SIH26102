"""
Data Loading and Merging Module.

Loads all clean CSV files, drops footer rows, fixes work_id extraction issues,
parses dates, and produces a single master work-level DataFrame.
"""
import re
import pandas as pd
import numpy as np
from . import config


def _drop_footer(df: pd.DataFrame) -> pd.DataFrame:
    """Remove 'Grand Total' footer rows."""
    mask = df.iloc[:, 0].astype(str).str.strip().isin(config.GRAND_TOTAL_MARKERS)
    return df[~mask].copy()


def _extract_work_id(work_str: str) -> str | None:
    """
    Re-extract work_id from the 'work' column using regex.
    Handles tab characters and whitespace that broke original extraction.
    """
    if pd.isna(work_str):
        return None
    # Normalize tabs and extra spaces
    cleaned = re.sub(r"[\t]+\s*", "", str(work_str))
    match = re.search(r"(WS/MP\d+/\d{4}-\d{4}/\d+)", cleaned)
    return match.group(1) if match else None


def _parse_date_flexible(series: pd.Series) -> pd.Series:
    """Parse dates, trying multiple formats."""
    # Try ISO format first (YYYY-MM-DD), then DD-Mon-YYYY
    result = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
    mask_nat = result.isna() & series.notna()
    if mask_nat.any():
        fallback = pd.to_datetime(series[mask_nat], format="%d-%b-%Y", errors="coerce")
        result[mask_nat] = fallback
    return result


def load_sanctioned() -> pd.DataFrame:
    """Load and clean works_sanctioned_clean.csv."""
    df = pd.read_csv(config.SANCTIONED_CSV, dtype=str)
    df = _drop_footer(df)

    # Fix missing work_ids by re-extracting from 'work' column
    missing_mask = df["work_id"].isna() | (df["work_id"].str.strip() == "")
    if missing_mask.any():
        df.loc[missing_mask, "work_id"] = df.loc[missing_mask, "work"].apply(
            _extract_work_id
        )

    # Parse dates
    df["recommended_date"] = _parse_date_flexible(df["recommended_date"])
    df["sanction_date"] = _parse_date_flexible(df["sanction_date"])

    # Parse amounts
    df["sanction_amount"] = (
        df["sanction_amount"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # Use 'amount' where sanction_amount is NaN
    df["sanction_amount"] = df["sanction_amount"].fillna(df["amount"])

    return df


def load_completed() -> pd.DataFrame:
    """Load and clean works_completed_clean.csv."""
    df = pd.read_csv(config.COMPLETED_CSV, dtype=str)
    df = _drop_footer(df)

    # Fix missing work_ids
    missing_mask = df["work_id"].isna() | (df["work_id"].str.strip() == "")
    if missing_mask.any():
        df.loc[missing_mask, "work_id"] = df.loc[missing_mask, "work"].apply(
            _extract_work_id
        )

    df["completion_date"] = _parse_date_flexible(df["completion_date"])
    df["amount_disbursed"] = pd.to_numeric(
        df["amount_disbursed"].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["amount_disbursed"] = df["amount_disbursed"].fillna(df["amount"])

    # Image presence flag
    df["has_image"] = df["image"].notna() & (df["image"].str.strip() != "")

    return df


def load_features() -> pd.DataFrame:
    """Load and clean mplads_features.csv."""
    df = pd.read_csv(config.FEATURES_CSV)

    # Drop the corrupted row with empty work_id
    df = df.dropna(subset=["work_id"])
    df = df[df["work_id"].str.strip() != ""].copy()

    # Replace inf values with NaN
    df = df.replace([np.inf, -np.inf], np.nan)

    return df


def load_expenditure() -> pd.DataFrame:
    """Load and clean expenditure_clean.csv."""
    df = pd.read_csv(config.EXPENDITURE_CSV, dtype=str)
    df = _drop_footer(df)

    df["expenditure_date"] = _parse_date_flexible(df["expenditure_date"])
    df["amount"] = pd.to_numeric(
        df["amount"].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )
    df["fund_disbursed_amount"] = pd.to_numeric(
        df["fund_disbursed_amount"].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )

    return df


def _aggregate_expenditure(expenditure_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate expenditure transactions to work_id level.
    Produces vendor behavior and temporal features per work.
    """
    exp = expenditure_df.dropna(subset=["work_id"]).copy()

    agg = exp.groupby("work_id").agg(
        exp_total_amount=("amount", "sum"),
        exp_payment_count=("amount", "count"),
        exp_vendor_count=("vendor_name", "nunique"),
        exp_max_payment=("amount", "max"),
        exp_min_payment=("amount", "min"),
        exp_mean_payment=("amount", "mean"),
        exp_std_payment=("amount", "std"),
        exp_first_payment_date=("expenditure_date", "min"),
        exp_last_payment_date=("expenditure_date", "max"),
        exp_payment_in_progress_count=(
            "payment_status",
            lambda x: (x == "Payment In-Progress").sum(),
        ),
        exp_payment_success_count=(
            "payment_status",
            lambda x: (x == "Payment Success").sum(),
        ),
    )
    agg = agg.reset_index()

    # Vendor HHI per work
    vendor_shares = (
        exp.groupby(["work_id", "vendor_name"])["amount"]
        .sum()
        .reset_index()
    )
    vendor_totals = vendor_shares.groupby("work_id")["amount"].sum().reset_index()
    vendor_totals.columns = ["work_id", "vendor_total"]
    vendor_shares = vendor_shares.merge(vendor_totals, on="work_id")
    vendor_shares["share"] = vendor_shares["amount"] / vendor_shares["vendor_total"]
    vendor_shares["share_sq"] = vendor_shares["share"] ** 2
    hhi = vendor_shares.groupby("work_id")["share_sq"].sum().reset_index()
    hhi.columns = ["work_id", "vendor_hhi"]

    # Max vendor share
    max_share = vendor_shares.groupby("work_id")["share"].max().reset_index()
    max_share.columns = ["work_id", "max_vendor_share"]

    # Near-threshold payment counts
    threshold_counts = []
    for wid, grp in exp.groupby("work_id"):
        amounts = grp["amount"].dropna()
        near_count = 0
        for thresh in config.THRESHOLD_VALUES:
            lower = thresh * (1 - config.THRESHOLD_TOLERANCE)
            near_count += ((amounts >= lower) & (amounts < thresh)).sum()
        total_payments = len(amounts)
        threshold_counts.append(
            {
                "work_id": wid,
                "near_threshold_count": near_count,
                "near_threshold_ratio": near_count / total_payments
                if total_payments > 0
                else 0,
            }
        )
    threshold_df = pd.DataFrame(threshold_counts)

    # First payment ratio (advance payment)
    first_payments = []
    for wid, grp in exp.groupby("work_id"):
        grp_sorted = grp.sort_values("expenditure_date")
        total = grp_sorted["amount"].sum()
        first_amt = grp_sorted["amount"].iloc[0] if len(grp_sorted) > 0 else 0
        first_payments.append(
            {
                "work_id": wid,
                "advance_payment_ratio": first_amt / total if total > 0 else 0,
            }
        )
    first_df = pd.DataFrame(first_payments)

    # Merge all aggregations
    result = agg.merge(hhi, on="work_id", how="left")
    result = result.merge(max_share, on="work_id", how="left")
    result = result.merge(threshold_df, on="work_id", how="left")
    result = result.merge(first_df, on="work_id", how="left")

    return result


def build_master_dataset() -> pd.DataFrame:
    """
    Build the master work-level DataFrame by merging all data sources.

    Returns a DataFrame with one row per work_id containing:
    - Lifecycle data from sanctioned
    - Completion data from completed
    - Pre-computed features from mplads_features
    - Aggregated expenditure features
    """
    print("[DataLoader] Loading sanctioned works...")
    sanctioned = load_sanctioned()
    print(f"  → {len(sanctioned)} rows, {sanctioned['work_id'].notna().sum()} with work_id")

    print("[DataLoader] Loading completed works...")
    completed = load_completed()
    print(f"  → {len(completed)} rows, {completed['work_id'].notna().sum()} with work_id")

    print("[DataLoader] Loading features...")
    features = load_features()
    print(f"  → {len(features)} rows")

    print("[DataLoader] Loading expenditure...")
    expenditure = load_expenditure()
    print(f"  → {len(expenditure)} rows")

    print("[DataLoader] Aggregating expenditure by work_id...")
    exp_agg = _aggregate_expenditure(expenditure)
    print(f"  → {len(exp_agg)} unique works with expenditure")

    # --- Build master from sanctioned as base ---
    master = sanctioned[sanctioned["work_id"].notna()].copy()
    master = master.drop_duplicates(subset=["work_id"], keep="first")
    print(f"[DataLoader] Base master: {len(master)} sanctioned works with work_id")

    # Deduplicate completed
    completed_dedup = completed[completed["work_id"].notna()].drop_duplicates(
        subset=["work_id"], keep="first"
    )

    # Create a set of completed work_ids for fast lookup
    completed_ids = set(completed_dedup["work_id"].unique())

    # Merge completion info
    comp_cols = [
        "work_id",
        "completion_date",
        "amount_disbursed",
        "has_image",
    ]
    master = master.merge(
        completed_dedup[comp_cols],
        on="work_id",
        how="left",
        suffixes=("", "_completed"),
    )

    # Merge pre-computed features
    feat_cols = [
        "work_id",
        "total_disbursed",
        "payment_count",
        "vendor_count",
        "max_single_payment",
        "min_single_payment",
        "avg_payment",
        "vendor_payment_ratio",
        "largest_payment_ratio",
        "vendor_count_zscore",
        "vendor_count_outlier",
        "max_single_payment_zscore",
        "max_single_payment_outlier",
        "total_disbursed_zscore",
        "total_disbursed_outlier",
        "log_total_disbursed",
        "log_max_payment",
        "log_avg_payment",
    ]
    available_cols = [c for c in feat_cols if c in features.columns]
    master = master.merge(
        features[available_cols].drop_duplicates(subset=["work_id"]),
        on="work_id",
        how="left",
    )

    # Merge expenditure aggregations
    master = master.merge(exp_agg, on="work_id", how="left")

    # --- Derive work status category ---
    def _assign_status(row):
        wid = row["work_id"]
        raw_status = str(row.get("work_status", "")).strip()

        if wid in completed_ids:
            return "Completed"
        elif raw_status in config.ONGOING_STATUSES:
            return "Ongoing"
        elif raw_status in config.TO_BE_IMPLEMENTED_STATUSES:
            # Check if there's any expenditure → then it's ongoing
            if pd.notna(row.get("exp_total_amount")) and row["exp_total_amount"] > 0:
                return "Ongoing"
            return "To Be Implemented"
        elif raw_status in config.COMPLETED_STATUSES:
            return "Completed"
        else:
            # Default: if has expenditure → Ongoing, else → To Be Implemented
            if pd.notna(row.get("exp_total_amount")) and row["exp_total_amount"] > 0:
                return "Ongoing"
            return "To Be Implemented"

    master["status_category"] = master.apply(_assign_status, axis=1)

    print(f"[DataLoader] Master dataset built: {len(master)} works")
    print(f"  Status distribution:\n{master['status_category'].value_counts().to_string()}")

    return master
