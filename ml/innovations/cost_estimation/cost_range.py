"""
Expected Cost Range Estimator.

Calculates an expected cost range (Low-High) for each MPLADS work
by comparing it against historically similar projects.

Grouping Strategy (cascading fallback):
  1. work_category + state + budget_tier  (most specific)
  2. work_category + state               (if tier group too small)
  3. work_category + budget_tier          (if state group too small)
  4. work_category only                   (broadest fallback)

Statistical Method:
  - Expected Range = [P10, P90] of sanction_amount within the comparison group
  - Narrow Range   = [P25, P75] (interquartile range)
  - Baseline       = Median of the comparison group

A work is flagged as a cost anomaly if its sanction_amount falls outside
the P10-P90 range of its comparison group.

Output columns added to the master DataFrame:
  - expected_cost_low       (P10 of comparison group)
  - expected_cost_high      (P90 of comparison group)
  - expected_cost_narrow_low  (P25)
  - expected_cost_narrow_high (P75)
  - expected_cost_median    (Median / baseline)
  - comparison_group        (human-readable description of which group was used)
  - comparison_group_size   (number of projects in the comparison group)
  - cost_deviation_pct      (how far outside the range, as %)
  - cost_in_expected_range  (boolean)
  - cost_range_explanation  (human-readable explanation string)
  - budget_tier             (Small / Medium / Large / Very Large)
"""
import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────
# Budget tier boundaries (INR)
# ──────────────────────────────────────────────────────────
BUDGET_TIERS = [
    (0,          500_000,     "Small"),        # Up to 5 Lakhs
    (500_000,    2_500_000,   "Medium"),       # 5L - 25L
    (2_500_000,  10_000_000,  "Large"),        # 25L - 1 Cr
    (10_000_000, float("inf"), "Very Large"),  # 1 Cr+
]

MIN_GROUP_SIZE = 5  # Minimum works in a group to be statistically meaningful


def estimate_cost_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute expected cost ranges for every work in the master DataFrame.

    Args:
        df: Master work-level DataFrame with at least 'sanction_amount',
            'work_category', and 'state' columns.

    Returns:
        Same DataFrame with cost range columns added.
    """
    print("[CostRange] Computing expected cost ranges...")

    df = df.copy()

    # Step 1: Assign budget tiers
    df["budget_tier"] = df["sanction_amount"].apply(_assign_tier)

    # Step 2: Build comparison group statistics
    # Pre-compute group stats at all granularity levels
    groups = _build_group_stats(df)

    # Step 3: For each work, find the best matching group and assign range
    results = []
    for idx, row in df.iterrows():
        result = _find_best_group(row, groups)
        results.append(result)

    result_df = pd.DataFrame(results, index=df.index)
    for col in result_df.columns:
        df[col] = result_df[col]

    # Step 4: Compute deviation and in-range flag
    df["cost_in_expected_range"] = (
        (df["sanction_amount"] >= df["expected_cost_low"])
        & (df["sanction_amount"] <= df["expected_cost_high"])
    )

    # Deviation percentage (how far outside the range)
    df["cost_deviation_pct"] = df.apply(_compute_deviation_pct, axis=1)

    # Step 5: Generate explanations
    df["cost_range_explanation"] = df.apply(_generate_explanation, axis=1)

    # Summary stats
    in_range = df["cost_in_expected_range"].sum()
    out_of_range = (~df["cost_in_expected_range"]).sum()
    print(f"[CostRange] Done.")
    print(f"  In expected range:     {in_range} ({in_range/len(df)*100:.1f}%)")
    print(f"  Outside expected range: {out_of_range} ({out_of_range/len(df)*100:.1f}%)")
    print(f"  Budget tier distribution:")
    print(f"    {df['budget_tier'].value_counts().to_string()}")

    return df


def _assign_tier(amount) -> str:
    """Assign a budget tier label based on sanction amount."""
    if pd.isna(amount) or amount <= 0:
        return "Unknown"
    for low, high, label in BUDGET_TIERS:
        if low <= amount < high:
            return label
    return "Unknown"


def _build_group_stats(df: pd.DataFrame) -> dict:
    """
    Pre-compute percentile statistics for all possible grouping levels.

    Returns a dict keyed by (level_name, group_key) -> stats_dict.
    """
    groups = {}
    valid = df[df["sanction_amount"].notna() & (df["sanction_amount"] > 0)]

    # Level 1: work_category + state + budget_tier (most specific)
    for keys, grp in valid.groupby(["work_category", "state", "budget_tier"]):
        if len(grp) >= MIN_GROUP_SIZE:
            groups[("cat_state_tier", keys)] = _compute_stats(
                grp["sanction_amount"],
                f"{keys[0]} | {keys[1]} | {keys[2]} budget"
            )

    # Level 2: work_category + state
    for keys, grp in valid.groupby(["work_category", "state"]):
        if len(grp) >= MIN_GROUP_SIZE:
            groups[("cat_state", keys)] = _compute_stats(
                grp["sanction_amount"],
                f"{keys[0]} | {keys[1]}"
            )

    # Level 3: work_category + budget_tier
    for keys, grp in valid.groupby(["work_category", "budget_tier"]):
        if len(grp) >= MIN_GROUP_SIZE:
            groups[("cat_tier", keys)] = _compute_stats(
                grp["sanction_amount"],
                f"{keys[0]} | {keys[1]} budget"
            )

    # Level 4: work_category only (broadest)
    for cat, grp in valid.groupby("work_category"):
        if len(grp) >= MIN_GROUP_SIZE:
            groups[("cat", cat)] = _compute_stats(
                grp["sanction_amount"],
                f"{cat}"
            )

    # Level 5: budget_tier only (ultimate fallback)
    for tier, grp in valid.groupby("budget_tier"):
        if len(grp) >= MIN_GROUP_SIZE:
            groups[("tier", tier)] = _compute_stats(
                grp["sanction_amount"],
                f"All {tier} budget projects"
            )

    print(f"[CostRange] Built {len(groups)} comparison groups across 5 levels")
    return groups


def _compute_stats(amounts: pd.Series, group_label: str) -> dict:
    """Compute percentile statistics for a group of amounts."""
    return {
        "p10": float(amounts.quantile(0.10)),
        "p25": float(amounts.quantile(0.25)),
        "median": float(amounts.median()),
        "p75": float(amounts.quantile(0.75)),
        "p90": float(amounts.quantile(0.90)),
        "mean": float(amounts.mean()),
        "std": float(amounts.std()),
        "count": int(len(amounts)),
        "label": group_label,
    }


def _find_best_group(row, groups: dict) -> dict:
    """
    Find the most specific comparison group for a work record.
    Uses cascading fallback from most specific to broadest.
    """
    cat = row.get("work_category", "")
    state = row.get("state", "")
    tier = row.get("budget_tier", "")

    # Try groups in order of specificity
    lookup_order = [
        ("cat_state_tier", (cat, state, tier)),
        ("cat_state", (cat, state)),
        ("cat_tier", (cat, tier)),
        ("cat", cat),
        ("tier", tier),
    ]

    for level, key in lookup_order:
        stats = groups.get((level, key))
        if stats is not None:
            return {
                "expected_cost_low": stats["p10"],
                "expected_cost_high": stats["p90"],
                "expected_cost_narrow_low": stats["p25"],
                "expected_cost_narrow_high": stats["p75"],
                "expected_cost_median": stats["median"],
                "comparison_group": stats["label"],
                "comparison_group_size": stats["count"],
            }

    # No group found — return NaN
    return {
        "expected_cost_low": np.nan,
        "expected_cost_high": np.nan,
        "expected_cost_narrow_low": np.nan,
        "expected_cost_narrow_high": np.nan,
        "expected_cost_median": np.nan,
        "comparison_group": "Insufficient data",
        "comparison_group_size": 0,
    }


def _compute_deviation_pct(row) -> float:
    """
    Compute how far outside the expected range the actual cost is.
    Returns 0 if within range, positive % if outside.
    """
    amount = row.get("sanction_amount")
    low = row.get("expected_cost_low")
    high = row.get("expected_cost_high")

    if pd.isna(amount) or pd.isna(low) or pd.isna(high):
        return 0.0

    if amount < low:
        return round(((low - amount) / low) * 100, 2) if low > 0 else 0.0
    elif amount > high:
        return round(((amount - high) / high) * 100, 2) if high > 0 else 0.0
    else:
        return 0.0


def _generate_explanation(row) -> str:
    """Generate a human-readable explanation for the cost range assessment."""
    amount = row.get("sanction_amount")
    low = row.get("expected_cost_low")
    high = row.get("expected_cost_high")
    median = row.get("expected_cost_median")
    group = row.get("comparison_group", "")
    group_size = row.get("comparison_group_size", 0)
    in_range = row.get("cost_in_expected_range", True)
    deviation = row.get("cost_deviation_pct", 0)

    if pd.isna(amount) or pd.isna(low) or pd.isna(high):
        return "Insufficient data to compute expected cost range."

    range_str = (
        f"Expected Cost Range: Rs.{low:,.0f} - Rs.{high:,.0f} "
        f"(Median: Rs.{median:,.0f})"
    )

    basis_str = (
        f"Based on {group_size} similar projects in category: {group}."
    )

    if in_range:
        status_str = (
            f"This project's sanction amount of Rs.{amount:,.0f} falls within "
            f"the expected range."
        )
    elif amount < low:
        status_str = (
            f"This project's sanction amount of Rs.{amount:,.0f} is {deviation:.1f}% "
            f"below the expected lower bound of Rs.{low:,.0f}, suggesting possible "
            f"under-budgeting or scope mismatch."
        )
    else:
        status_str = (
            f"This project's sanction amount of Rs.{amount:,.0f} is {deviation:.1f}% "
            f"above the expected upper bound of Rs.{high:,.0f}, suggesting possible "
            f"over-budgeting or cost inflation."
        )

    return f"{range_str} | {basis_str} | {status_str}"
