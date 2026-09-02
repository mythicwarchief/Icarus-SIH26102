"""
Duplicate Detection — Stage 1 & Stage 2 Filters.

Stage 1: Exact-duplicate / boilerplate filter (no ML)
  - Groups by exact-match work_description string.
  - Any description repeating 2+ times is flagged as "template phrase"
    and excluded from downstream similarity scoring.

Stage 2: Beneficiary-style text filter (rule-based, no ML)
  - Regex-based detection of beneficiary-list patterns
    (e.g. "PERSON_NAME S/O RELATIVE_NAME ... work type").
  - These are legitimate individual-beneficiary records, heavily
    concentrated in Uttar Pradesh, that would generate massive
    false positives if fed into semantic similarity.

Both stages produce inspectable exclusion labels so that QA (Keerthana)
and validation (Anavadya) can verify what was excluded and why.
"""
import re
import pandas as pd
import numpy as np


# Regex pattern for beneficiary-style descriptions
# Matches: S/O, S\O, W/O, W\O, D/O, D\O (case-insensitive)
BENEFICIARY_PATTERN = re.compile(r'\b[SWD][/\\]O\b', re.IGNORECASE)

# Minimum repeat count to consider a description as boilerplate
BOILERPLATE_MIN_REPEATS = 2


def load_descriptions() -> pd.DataFrame:
    """
    Load work_description text from sanctioned and completed CSVs.
    Returns a combined DataFrame with one row per (work_id, source) pair.
    """
    from ml import config

    # Load sanctioned
    sanc = pd.read_csv(config.SANCTIONED_CSV, dtype=str)
    sanc = sanc[~sanc.iloc[:, 0].astype(str).str.strip().isin(config.GRAND_TOTAL_MARKERS)]

    # Fix work_id extraction (same logic as data_loader)
    from ml.data_loader import _extract_work_id
    missing = sanc["work_id"].isna() | (sanc["work_id"].str.strip() == "")
    if missing.any():
        sanc.loc[missing, "work_id"] = sanc.loc[missing, "work"].apply(_extract_work_id)

    sanc_desc = sanc[["work_id", "work_description", "state", "constituency", "work_category"]].copy()
    sanc_desc["source"] = "sanctioned"

    # Load completed
    comp = pd.read_csv(config.COMPLETED_CSV, dtype=str)
    comp = comp[~comp.iloc[:, 0].astype(str).str.strip().isin(config.GRAND_TOTAL_MARKERS)]

    missing = comp["work_id"].isna() | (comp["work_id"].str.strip() == "")
    if missing.any():
        comp.loc[missing, "work_id"] = comp.loc[missing, "work"].apply(_extract_work_id)

    comp_desc = comp[["work_id", "work_description", "state", "constituency", "work_category"]].copy()
    comp_desc["source"] = "completed"

    # Combine
    combined = pd.concat([sanc_desc, comp_desc], ignore_index=True)

    # Drop rows with missing work_description
    before = len(combined)
    combined = combined[
        combined["work_description"].notna()
        & (combined["work_description"].str.strip() != "")
    ].copy()
    dropped = before - len(combined)

    # Deduplicate: keep one description per work_id (prefer sanctioned, as it has the original)
    combined = combined.sort_values("source", ascending=True)  # 'completed' < 'sanctioned'
    combined = combined.drop_duplicates(subset=["work_id"], keep="last")

    print(f"[Filters] Loaded {len(combined)} works with descriptions ({dropped} dropped for missing text)")
    return combined


def run_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply Stage 1 (boilerplate) and Stage 2 (beneficiary) filters.

    Adds columns:
    - filter_status: 'eligible' / 'excluded_boilerplate' / 'excluded_beneficiary'
    - filter_reason: Human-readable reason for exclusion
    - boilerplate_count: How many times this exact description appears (0 if not boilerplate)

    Returns the same DataFrame with filter columns added.
    """
    df = df.copy()
    n = len(df)

    # Initialize
    df["filter_status"] = "eligible"
    df["filter_reason"] = ""
    df["boilerplate_count"] = 0

    # ── Stage 1: Exact-duplicate / boilerplate filter ──
    print("[Filters] Stage 1: Exact-duplicate / boilerplate detection...")
    desc_counts = df["work_description"].value_counts()
    repeated_descs = set(desc_counts[desc_counts >= BOILERPLATE_MIN_REPEATS].index)

    boilerplate_mask = df["work_description"].isin(repeated_descs)
    df.loc[boilerplate_mask, "filter_status"] = "excluded_boilerplate"
    df.loc[boilerplate_mask, "filter_reason"] = "Template/boilerplate phrase — this exact description appears multiple times across different works, indicating standard scheme language rather than a unique project description."

    # Record how many times each boilerplate description appears
    for desc in repeated_descs:
        mask = df["work_description"] == desc
        df.loc[mask, "boilerplate_count"] = int(desc_counts[desc])

    boilerplate_count = boilerplate_mask.sum()
    unique_boilerplate = len(repeated_descs)
    print(f"  Excluded: {boilerplate_count} rows ({unique_boilerplate} distinct repeated strings)")

    # ── Stage 2: Beneficiary-style text filter ──
    print("[Filters] Stage 2: Beneficiary-style text detection...")
    # Only apply to rows not already excluded
    eligible_mask = df["filter_status"] == "eligible"
    bene_mask = eligible_mask & df["work_description"].str.contains(
        BENEFICIARY_PATTERN, na=False
    )
    df.loc[bene_mask, "filter_status"] = "excluded_beneficiary"
    df.loc[bene_mask, "filter_reason"] = "Beneficiary-record style description (contains S/O, W/O, or D/O patronymic pattern) — these are legitimate individual-beneficiary records that would produce false-positive similarity matches."

    bene_count = bene_mask.sum()
    print(f"  Excluded: {bene_count} rows (beneficiary-style)")
    if bene_count > 0:
        top_states = df[bene_mask]["state"].value_counts().head(3)
        for state, cnt in top_states.items():
            print(f"    {state}: {cnt}")

    # Summary
    eligible_count = (df["filter_status"] == "eligible").sum()
    print(f"[Filters] Summary:")
    print(f"  Total:               {n}")
    print(f"  Excluded boilerplate: {boilerplate_count}")
    print(f"  Excluded beneficiary: {bene_count}")
    print(f"  Eligible for Stage 3: {eligible_count}")

    return df
