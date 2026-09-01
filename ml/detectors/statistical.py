"""
Statistical Anomaly Detector.

Uses Modified Z-Score (MAD-based), IQR outlier detection, and Benford's Law
to assign statistical anomaly scores to each work record.
"""
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from .. import config


def detect(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run statistical anomaly detection on the master DataFrame.

    Returns the DataFrame with an added 'statistical_score' column (0–1).
    """
    print("[StatDetector] Running statistical anomaly detection...")
    scores = pd.DataFrame(index=df.index)

    # 1. Modified Z-Score (MAD-based) on key financial columns
    mad_cols = [
        "sanction_amount",
        "total_spent",
        "cost_overrun_ratio",
        "vendor_hhi",
        "sanction_delay_days",
        "completion_duration_days",
    ]
    mad_scores = []
    for col in mad_cols:
        if col in df.columns:
            s = _modified_zscore(df[col])
            mad_scores.append(s)
    if mad_scores:
        # Take the max across all MAD z-scores for each record
        scores["mad_max"] = pd.concat(mad_scores, axis=1).max(axis=1)
    else:
        scores["mad_max"] = 0.0

    # 2. IQR-based outlier detection
    iqr_cols = [
        "sanction_amount",
        "total_spent",
        "cost_overrun_ratio",
        "advance_payment_ratio",
    ]
    iqr_scores = []
    for col in iqr_cols:
        if col in df.columns:
            s = _iqr_score(df[col])
            iqr_scores.append(s)
    if iqr_scores:
        scores["iqr_max"] = pd.concat(iqr_scores, axis=1).max(axis=1)
    else:
        scores["iqr_max"] = 0.0

    # 3. Benford's Law deviation (on total_spent amounts)
    if "total_spent" in df.columns:
        scores["benford_score"] = _benford_score(df["total_spent"])
    else:
        scores["benford_score"] = 0.0

    # Combine: weighted average of the three statistical methods
    combined = (
        0.40 * scores["mad_max"]
        + 0.35 * scores["iqr_max"]
        + 0.25 * scores["benford_score"]
    )
    # Clip to [0, 1]
    df["statistical_score"] = combined.clip(0, 1)

    flagged = (df["statistical_score"] >= config.ANOMALY_FLAG_THRESHOLD).sum()
    print(f"[StatDetector] Done. {flagged} records above threshold.")

    return df


def _modified_zscore(series: pd.Series) -> pd.Series:
    """
    Compute Modified Z-Score using Median Absolute Deviation.
    Returns a normalized score between 0 and 1.
    """
    s = pd.to_numeric(series, errors="coerce")
    median = s.median()
    mad = np.median(np.abs(s - median))
    if mad == 0:
        mad = s.std()
    if mad == 0 or np.isnan(mad):
        return pd.Series(0.0, index=series.index)

    modified_z = 0.6745 * (s - median) / mad
    # Normalize: use sigmoid-like transform to map to [0, 1]
    # Values > 3.5 MAD are strongly anomalous
    score = 1 / (1 + np.exp(-0.5 * (np.abs(modified_z) - 3.5)))
    return score.fillna(0)


def _iqr_score(series: pd.Series) -> pd.Series:
    """
    Compute IQR-based outlier score.
    Returns a normalized score between 0 and 1.
    """
    s = pd.to_numeric(series, errors="coerce")
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return pd.Series(0.0, index=series.index)

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    # Distance beyond IQR bounds, normalized by IQR
    below = ((lower - s) / iqr).clip(lower=0)
    above = ((s - upper) / iqr).clip(lower=0)
    distance = np.maximum(below, above)

    # Sigmoid normalization
    score = 1 / (1 + np.exp(-1.0 * (distance - 1.5)))
    return score.fillna(0)


def _benford_score(series: pd.Series) -> pd.Series:
    """
    Compute per-record Benford's Law conformity score.

    Since Benford's Law is a distributional test, we compute the overall
    chi-squared statistic and then assign higher scores to records whose
    first digit contributes most to the deviation.
    """
    s = pd.to_numeric(series, errors="coerce").abs()
    s = s[s > 0].dropna()

    if len(s) < 10:
        return pd.Series(0.0, index=series.index)

    # Extract first digits
    first_digits = s.apply(lambda x: int(str(abs(x)).lstrip("0.")[0]) if x > 0 else 0)
    first_digits = first_digits[first_digits.between(1, 9)]

    if len(first_digits) < 10:
        return pd.Series(0.0, index=series.index)

    # Observed distribution
    observed_counts = first_digits.value_counts().reindex(range(1, 10), fill_value=0)
    total = observed_counts.sum()
    observed_freq = observed_counts / total

    # Expected distribution (Benford's Law)
    expected_freq = pd.Series(config.BENFORD_EXPECTED)

    # Per-digit deviation
    digit_deviation = {}
    for d in range(1, 10):
        obs = observed_freq.get(d, 0)
        exp = expected_freq[d]
        # Contribution to chi-squared
        if exp > 0:
            digit_deviation[d] = ((obs - exp) ** 2) / exp
        else:
            digit_deviation[d] = 0

    # Overall chi-squared statistic
    chi2 = sum(digit_deviation.values())

    # Assign score based on which first digit the record has
    # Records with over-represented digits get higher scores
    result = pd.Series(0.0, index=series.index)
    for idx in first_digits.index:
        d = first_digits[idx]
        obs = observed_freq.get(d, 0)
        exp = expected_freq.get(d, 0.1)
        # If digit is over-represented, the score is higher
        if obs > exp:
            deviation_ratio = (obs - exp) / exp
            result[idx] = min(deviation_ratio / 2, 1.0)  # normalize roughly

    # Scale by overall chi-squared significance
    # Critical value for 8 df at p=0.05 is ~15.51
    chi2_scale = min(chi2 / 15.51, 1.0)
    result = result * chi2_scale

    # Fill NaN
    return result.reindex(series.index, fill_value=0.0)
