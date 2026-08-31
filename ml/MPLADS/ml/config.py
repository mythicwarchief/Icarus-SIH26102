"""
Configuration for the MPLADS Anomaly Detection Pipeline.
All paths, thresholds, hyperparameters, and feature lists are defined here.
"""
import os

# ──────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = PROJECT_ROOT  # CSVs sit at the project root

# Input CSVs
FEATURES_CSV = os.path.join(DATA_DIR, "mplads_features.csv")
SANCTIONED_CSV = os.path.join(DATA_DIR, "works_sanctioned_clean.csv")
COMPLETED_CSV = os.path.join(DATA_DIR, "works_completed_clean.csv")
EXPENDITURE_CSV = os.path.join(DATA_DIR, "expenditure_clean.csv")

# Output directory
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
MODEL_DIR = os.path.join(OUTPUT_DIR, "model_artifacts")
ANOMALY_SCORES_CSV = os.path.join(OUTPUT_DIR, "anomaly_scores.csv")
ANOMALY_FLAGGED_CSV = os.path.join(OUTPUT_DIR, "anomaly_flagged.csv")
ANOMALY_SUMMARY_JSON = os.path.join(OUTPUT_DIR, "anomaly_summary.json")
ISOLATION_FOREST_MODEL = os.path.join(MODEL_DIR, "isolation_forest.joblib")

# ──────────────────────────────────────────────────────────
# Data Cleaning
# ──────────────────────────────────────────────────────────
GRAND_TOTAL_MARKERS = ["Grand Total", "grand total"]

# Work-ID regex to re-extract from the `work` column
# Pattern: WS/MP<digits>/<year>/<id>
WORK_ID_REGEX = r"(WS/\s*(?:\t\s*)?MP\d+/\d{4}-\d{4}/\d+)"

# ──────────────────────────────────────────────────────────
# Work Status Mapping
# ──────────────────────────────────────────────────────────
# Maps raw work_status values to the three project categories
COMPLETED_STATUSES = {"Work Completed"}
ONGOING_STATUSES = {
    "Physical Inspection",
    "Work partially Completed",
    "Vendor Identification",
    "Work In Progress",
    "Work in Progress",
}
TO_BE_IMPLEMENTED_STATUSES = {"Sanction", "Sanctioned"}

# ──────────────────────────────────────────────────────────
# Feature Engineering
# ──────────────────────────────────────────────────────────
# Financial threshold values (INR) for structuring / smurfing detection
THRESHOLD_VALUES = [20_000, 50_000, 250_000, 500_000, 1_000_000]
THRESHOLD_TOLERANCE = 0.05  # 5% below threshold is "near-threshold"

# ──────────────────────────────────────────────────────────
# Isolation Forest Hyperparameters
# ──────────────────────────────────────────────────────────
IF_FEATURES = [
    "log_total_disbursed",
    "payment_count",
    "vendor_count",
    "largest_payment_ratio",
    "vendor_payment_ratio_clean",
    "sanction_delay_days",
    "completion_duration_days",
    "cost_overrun_ratio",
    "vendor_hhi",
]

IF_CONTAMINATION = "auto"  # let the model decide, or set e.g. 0.05
IF_N_ESTIMATORS = 200
IF_RANDOM_STATE = 42
IF_MAX_SAMPLES = "auto"

# ──────────────────────────────────────────────────────────
# Ensemble Weights
# ──────────────────────────────────────────────────────────
ENSEMBLE_WEIGHTS = {
    "statistical": 0.25,
    "rule_based": 0.40,
    "isolation_forest": 0.35,
}

# ──────────────────────────────────────────────────────────
# Anomaly Severity Thresholds
# ──────────────────────────────────────────────────────────
SEVERITY_THRESHOLDS = {
    "critical": 0.85,
    "high": 0.65,
    "medium": 0.40,
    "low": 0.20,
}

# Score above which a record is flagged as anomalous
ANOMALY_FLAG_THRESHOLD = 0.40

# ──────────────────────────────────────────────────────────
# Rule-based Detector Thresholds
# ──────────────────────────────────────────────────────────
RULE_THRESHOLDS = {
    "cost_overrun_ratio_max": 1.0,
    "sanction_delay_negative": 0,
    "sanction_delay_excessive_days": 365,
    "fast_completion_days": 7,
    "fast_completion_min_amount": 200_000,
    "missing_image_min_amount": 500_000,
    "vendor_hhi_monopolization": 0.80,
    "near_threshold_ratio_suspicious": 0.50,
    "single_vendor_min_amount": 1_000_000,
    "advance_payment_ratio_max": 0.90,
}

# ──────────────────────────────────────────────────────────
# Benford's Law Expected First-Digit Distribution
# ──────────────────────────────────────────────────────────
BENFORD_EXPECTED = {
    1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097,
    5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046,
}
