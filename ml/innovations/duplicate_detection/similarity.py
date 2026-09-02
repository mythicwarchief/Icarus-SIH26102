"""
Duplicate Detection — Within-Constituency Similarity Scoring.

Compares embedded work_description vectors within the same constituency
(or state as fallback) to detect potential duplicate/similar projects.

Key design decisions (from feasibility report):
  - Compare WITHIN constituency only — not globally
  - Use cosine similarity (embeddings are already L2-normalized)
  - Threshold is configurable and documented with examples
  - Output is a list of flagged (work_A, work_B, similarity_score) pairs
"""
import os
import json
import numpy as np
import pandas as pd
from collections import defaultdict


# ──────────────────────────────────────────────────────────
# Similarity threshold
# ──────────────────────────────────────────────────────────
# 0.85 = high similarity — descriptions are near-paraphrases
# Justification: After removing boilerplate and beneficiary records,
# remaining descriptions are location-specific. A score of 0.85+
# indicates two different work_ids with nearly identical project
# descriptions in the same constituency, which is a genuine signal.
#
# Threshold tuned against manual inspection of sample pairs:
#   0.90+ : near-exact paraphrases (very few, very high confidence)
#   0.85  : strong similarity, different wording of same project scope
#   0.80  : moderate similarity, could be same project type at different sites
#   <0.75 : generally different projects
SIMILARITY_THRESHOLD = 0.85

# Minimum constituency size to run comparison (skip tiny groups)
MIN_GROUP_SIZE = 2

# Output paths
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
DUPLICATE_PAIRS_CSV = os.path.join(OUTPUT_DIR, "duplicate_pairs.csv")
DUPLICATE_SUMMARY_JSON = os.path.join(OUTPUT_DIR, "duplicate_summary.json")
DUPLICATE_FULL_CSV = os.path.join(OUTPUT_DIR, "duplicate_detection_full.csv")


def find_similar_pairs(
    df: pd.DataFrame,
    embeddings: np.ndarray,
    threshold: float = SIMILARITY_THRESHOLD,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Find similar project pairs within each constituency.

    Args:
        df: Master DataFrame with filter_status, constituency, etc.
        embeddings: Numpy array of shape (n_eligible, dim), aligned with
                    eligible rows of df.
        threshold: Cosine similarity threshold for flagging.

    Returns:
        Tuple of (pairs_df, df_with_flags):
        - pairs_df: DataFrame of flagged pairs with columns
          [work_id_a, work_id_b, similarity, constituency, state,
           description_a, description_b]
        - df_with_flags: Original df with duplicate detection columns added
    """
    eligible_mask = df["filter_status"] == "eligible"
    eligible_df = df[eligible_mask].reset_index(drop=True)
    n = len(eligible_df)

    if n == 0 or embeddings.size == 0:
        print("[Similarity] No eligible records to compare.")
        return pd.DataFrame(), df

    print(f"[Similarity] Comparing {n} eligible works within constituencies...")
    print(f"[Similarity] Threshold: {threshold}")

    # Group eligible indices by constituency
    constituency_groups = defaultdict(list)
    for i, row in eligible_df.iterrows():
        const = str(row.get("constituency", "")).strip()
        if const:
            constituency_groups[const].append(i)

    print(f"[Similarity] {len(constituency_groups)} constituencies with eligible works")

    # Find pairs within each constituency
    all_pairs = []
    constituencies_checked = 0
    comparisons_made = 0

    for constituency, indices in constituency_groups.items():
        if len(indices) < MIN_GROUP_SIZE:
            continue

        constituencies_checked += 1
        group_embeddings = embeddings[indices]
        n_group = len(indices)

        # Cosine similarity matrix (embeddings are L2-normalized, so dot product = cosine)
        sim_matrix = group_embeddings @ group_embeddings.T

        # Find pairs above threshold (upper triangle only to avoid duplicates)
        for i in range(n_group):
            for j in range(i + 1, n_group):
                score = float(sim_matrix[i, j])
                if score >= threshold:
                    idx_a = indices[i]
                    idx_b = indices[j]
                    row_a = eligible_df.iloc[idx_a]
                    row_b = eligible_df.iloc[idx_b]

                    # Skip if same work_id (same project appearing in both sanctioned and completed)
                    if row_a["work_id"] == row_b["work_id"]:
                        continue

                    all_pairs.append({
                        "work_id_a": row_a["work_id"],
                        "work_id_b": row_b["work_id"],
                        "similarity": round(score, 4),
                        "constituency": constituency,
                        "state": row_a.get("state", ""),
                        "description_a": row_a["work_description"],
                        "description_b": row_b["work_description"],
                        "description_a_clean": row_a["description_clean"],
                        "description_b_clean": row_b["description_clean"],
                    })
                comparisons_made += 1

    pairs_df = pd.DataFrame(all_pairs)
    if len(pairs_df) > 0:
        pairs_df = pairs_df.sort_values("similarity", ascending=False).reset_index(drop=True)

    print(f"[Similarity] Done.")
    print(f"  Constituencies checked: {constituencies_checked}")
    print(f"  Pairwise comparisons: {comparisons_made:,}")
    print(f"  Similar pairs found: {len(pairs_df)}")

    # Add duplicate flags back to main df
    df = _add_duplicate_flags(df, pairs_df)

    return pairs_df, df


def _add_duplicate_flags(df: pd.DataFrame, pairs_df: pd.DataFrame) -> pd.DataFrame:
    """Add duplicate detection columns to the main DataFrame."""
    df = df.copy()
    df["duplicate_flag"] = False
    df["duplicate_pair_count"] = 0
    df["duplicate_max_similarity"] = 0.0
    df["duplicate_paired_with"] = ""

    if len(pairs_df) == 0:
        return df

    # Count pairs per work_id
    pair_counts = defaultdict(int)
    max_sims = defaultdict(float)
    paired_ids = defaultdict(list)

    for _, pair in pairs_df.iterrows():
        wid_a = pair["work_id_a"]
        wid_b = pair["work_id_b"]
        sim = pair["similarity"]

        pair_counts[wid_a] += 1
        pair_counts[wid_b] += 1
        max_sims[wid_a] = max(max_sims[wid_a], sim)
        max_sims[wid_b] = max(max_sims[wid_b], sim)
        paired_ids[wid_a].append(wid_b)
        paired_ids[wid_b].append(wid_a)

    for wid in pair_counts:
        mask = df["work_id"] == wid
        if mask.any():
            df.loc[mask, "duplicate_flag"] = True
            df.loc[mask, "duplicate_pair_count"] = pair_counts[wid]
            df.loc[mask, "duplicate_max_similarity"] = max_sims[wid]
            df.loc[mask, "duplicate_paired_with"] = ",".join(paired_ids[wid][:5])  # top 5

    return df


def save_outputs(
    pairs_df: pd.DataFrame,
    full_df: pd.DataFrame,
):
    """Save all duplicate detection outputs."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Duplicate pairs CSV
    if len(pairs_df) > 0:
        pairs_df.to_csv(DUPLICATE_PAIRS_CSV, index=False)
        print(f"  [OK] duplicate_pairs.csv: {len(pairs_df)} pairs")
    else:
        pd.DataFrame(columns=[
            "work_id_a", "work_id_b", "similarity", "constituency",
            "state", "description_a", "description_b"
        ]).to_csv(DUPLICATE_PAIRS_CSV, index=False)
        print(f"  [OK] duplicate_pairs.csv: 0 pairs")

    # 2. Full detection results CSV
    output_cols = [
        "work_id", "state", "constituency", "work_category",
        "work_description", "filter_status", "filter_reason", "boilerplate_count",
        "duplicate_flag", "duplicate_pair_count", "duplicate_max_similarity",
        "duplicate_paired_with",
    ]
    available = [c for c in output_cols if c in full_df.columns]
    full_df[available].to_csv(DUPLICATE_FULL_CSV, index=False)
    print(f"  [OK] duplicate_detection_full.csv: {len(full_df)} records")

    # 3. Summary JSON
    summary = _build_summary(pairs_df, full_df)
    with open(DUPLICATE_SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  [OK] duplicate_summary.json")


def _build_summary(pairs_df: pd.DataFrame, full_df: pd.DataFrame) -> dict:
    """Build summary statistics for the duplicate detection run."""
    total = len(full_df)
    excluded_boilerplate = (full_df["filter_status"] == "excluded_boilerplate").sum()
    excluded_beneficiary = (full_df["filter_status"] == "excluded_beneficiary").sum()
    eligible = (full_df["filter_status"] == "eligible").sum()
    flagged = full_df["duplicate_flag"].sum() if "duplicate_flag" in full_df.columns else 0

    summary = {
        "total_works_with_descriptions": int(total),
        "excluded_boilerplate": int(excluded_boilerplate),
        "excluded_beneficiary": int(excluded_beneficiary),
        "eligible_for_comparison": int(eligible),
        "similar_pairs_found": int(len(pairs_df)),
        "unique_works_flagged": int(flagged),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "comparison_scope": "within-constituency",
    }

    if len(pairs_df) > 0:
        summary["similarity_stats"] = {
            "mean": round(float(pairs_df["similarity"].mean()), 4),
            "median": round(float(pairs_df["similarity"].median()), 4),
            "max": round(float(pairs_df["similarity"].max()), 4),
            "min": round(float(pairs_df["similarity"].min()), 4),
        }
        summary["top_states"] = (
            pairs_df["state"].value_counts().head(5).to_dict()
        )
        # Sample pairs for inspection
        sample = pairs_df.head(5)
        summary["sample_pairs"] = [
            {
                "work_id_a": row["work_id_a"],
                "work_id_b": row["work_id_b"],
                "similarity": row["similarity"],
                "constituency": row["constituency"],
                "desc_a_preview": str(row["description_a"])[:100],
                "desc_b_preview": str(row["description_b"])[:100],
            }
            for _, row in sample.iterrows()
        ]

    return summary
