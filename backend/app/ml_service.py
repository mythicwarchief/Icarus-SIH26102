"""
ML Service Module.

Provides the bridge between the FastAPI backend and:
- Core MPLADS anomaly detection pipeline
- Cost range estimation
- Delay prediction
- Duplicate project detection
"""

from pathlib import Path
import sys
import json
import re

import pandas as pd


# ==========================================================
# PROJECT PATH SETUP
# ==========================================================

# ml_service.py:
# SIH26102/backend/app/ml_service.py
#
# PROJECT_ROOT:
# SIH26102/

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ==========================================================
# DIRECTORY PATHS
# ==========================================================

ML_DIR = PROJECT_ROOT / "ml"

INNOVATIONS_DIR = ML_DIR / "innovations"

INNOVATIONS_OUTPUT_DIR = (
    INNOVATIONS_DIR / "outputs"
)


# ==========================================================
# CORE DATA PATHS
# ==========================================================

# Cost estimation uses the sanctioned works dataset directly.
SANCTIONED_WORKS_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "works_sanctioned_clean.csv"
)


# ==========================================================
# DELAY PREDICTION OUTPUTS
# ==========================================================

DELAY_PREDICTIONS_CSV = (
    INNOVATIONS_OUTPUT_DIR / "delay_predictions.csv"
)

DELAY_SUMMARY_JSON = (
    INNOVATIONS_OUTPUT_DIR
    / "delay_prediction_summary.json"
)


# ==========================================================
# DUPLICATE DETECTION OUTPUTS
# ==========================================================

DUPLICATE_PAIRS_CSV = (
    INNOVATIONS_OUTPUT_DIR
    / "duplicate_pairs.csv"
)

DUPLICATE_FULL_CSV = (
    INNOVATIONS_OUTPUT_DIR
    / "duplicate_detection_full.csv"
)

DUPLICATE_SUMMARY_JSON = (
    INNOVATIONS_OUTPUT_DIR
    / "duplicate_summary.json"
)


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def dataframe_to_json_records(df: pd.DataFrame):
    """
    Convert a Pandas DataFrame into JSON-safe records.

    Pandas converts NaN values to JSON null.
    """

    return json.loads(
        df.to_json(
            orient="records",
            date_format="iso",
        )
    )


def extract_work_id(value):
    """
    Extract MPLADS work ID from the Work column.

    Expected pattern:
    WS/MP492/2024-2025/134981
    """

    if pd.isna(value):
        return None

    value = str(value)

    match = re.search(
        r"WS/\s*(?:\t\s*)?MP\d+/\d{4}-\d{4}/\d+",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        return re.sub(
            r"\s+",
            "",
            match.group(0),
        )

    return None


def parse_currency(value):
    """
    Convert currency values from the sanctioned CSV into float.

    Handles values such as:
    ₹ 500,000
    500000
    5,00,000
    """

    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value)

    cleaned = re.sub(
        r"[^\d.\-]",
        "",
        value,
    )

    if not cleaned:
        return None

    try:
        return float(cleaned)

    except ValueError:
        return None


# ==========================================================
# CORE ML PIPELINE
# ==========================================================

def run_ml_pipeline():
    """
    Execute the core MPLADS anomaly detection pipeline.
    """

    try:

        from ml.anomaly_pipeline import run_pipeline

        run_pipeline()

        return {
            "success": True,
            "message": (
                "ML anomaly detection pipeline "
                "completed successfully"
            ),
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error),
        }


# ==========================================================
# COST ESTIMATION DATA LOADER
# ==========================================================

def load_cost_estimation_data():
    """
    Load and prepare the sanctioned works dataset for
    the cost range estimation innovation.

    cost_range.py requires:
    - work_id
    - sanction_amount
    - work_category
    - state
    """

    if not SANCTIONED_WORKS_CSV.exists():

        raise FileNotFoundError(
            f"Sanctioned works CSV not found: "
            f"{SANCTIONED_WORKS_CSV}"
        )

    # Load raw sanctioned works data.
    df = pd.read_csv(
        SANCTIONED_WORKS_CSV
    )

    # ------------------------------------------------------
    # Normalize column names
    # ------------------------------------------------------

    column_mapping = {
        "Work category": "work_category",
        "State": "state",
        "Sanction Amount ( ₹ )": "sanction_amount",
    }

    df = df.rename(
        columns=column_mapping
    )

    # ------------------------------------------------------
    # Validate required source columns
    # ------------------------------------------------------

    required_columns = [
        "work_category",
        "state",
        "sanction_amount",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "Missing required columns in "
            f"works_sanctioned.csv: "
            f"{missing_columns}"
        )

    # ------------------------------------------------------
    # Extract work IDs
    # ------------------------------------------------------

    if "work_id" not in df.columns:

        if "Work" not in df.columns:

            raise ValueError(
                "Neither 'work_id' nor 'Work' column "
                "exists in works_sanctioned.csv"
            )

        df["work_id"] = df[
            "Work"
        ].apply(
            extract_work_id
        )

    # ------------------------------------------------------
    # Convert sanction amount to numeric
    # ------------------------------------------------------

    df["sanction_amount"] = df[
        "sanction_amount"
    ].apply(
        parse_currency
    )

    # ------------------------------------------------------
    # Clean text fields
    # ------------------------------------------------------

    df["work_category"] = (
        df["work_category"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    df["state"] = (
        df["state"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    # ------------------------------------------------------
    # Remove invalid records
    # ------------------------------------------------------

    df = df[
        df["sanction_amount"].notna()
        & (df["sanction_amount"] > 0)
    ].copy()

    # Remove Grand Total or summary rows.
    df = df[
        ~df["work_category"]
        .str.contains(
            "grand total",
            case=False,
            na=False,
        )
    ].copy()

    return df


# ==========================================================
# INNOVATION 1
# COST RANGE ESTIMATION
# ==========================================================

def get_cost_estimates():
    """
    Run the cost range estimation innovation.

    Uses the sanctioned works dataset rather than the
    anomaly-detection feature dataset.

    The estimator requires:
    - sanction_amount
    - work_category
    - state
    """

    try:

        from ml.innovations.cost_estimation.cost_range import (
            estimate_cost_ranges
        )

        # Load data specifically prepared for cost estimation.
        df = load_cost_estimation_data()

        # Run the innovation.
        result_df = estimate_cost_ranges(
            df
        )

        # Convert results to JSON-safe records.
        records = dataframe_to_json_records(
            result_df
        )

        return {
            "success": True,
            "count": len(records),
            "cost_estimates": records,
        }

    except Exception as error:

        import traceback

        print(
            "\n========== COST ESTIMATION ERROR =========="
        )

        traceback.print_exc()

        print(
            "===========================================\n"
        )

        return {
            "success": False,
            "message": str(error),
            "cost_estimates": [],
        }


# ==========================================================
# DELAY PREDICTION
# ==========================================================

def get_delay_predictions():
    """
    Return delay prediction results generated by the
    delay prediction innovation pipeline.
    """

    try:

        if not DELAY_PREDICTIONS_CSV.exists():

            return {
                "success": False,
                "message": (
                    "Delay prediction output not found."
                ),
                "predictions": [],
            }

        df = pd.read_csv(
            DELAY_PREDICTIONS_CSV
        )

        records = dataframe_to_json_records(
            df
        )

        return {
            "success": True,
            "count": len(records),
            "predictions": records,
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error),
            "predictions": [],
        }


def get_delay_prediction_summary():
    """
    Return delay prediction summary.
    """

    try:

        if not DELAY_SUMMARY_JSON.exists():

            return {
                "success": False,
                "message": (
                    "Delay prediction summary output "
                    "not found."
                ),
            }

        with open(
            DELAY_SUMMARY_JSON,
            "r",
            encoding="utf-8",
        ) as file:

            summary = json.load(file)

        return {
            "success": True,
            "summary": summary,
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error),
        }


# ==========================================================
# DUPLICATE DETECTION
# ==========================================================

def get_duplicate_projects():
    """
    Return project pairs flagged as potential duplicates.
    """

    try:

        if not DUPLICATE_PAIRS_CSV.exists():

            return {
                "success": False,
                "message": (
                    "Duplicate detection output not found."
                ),
                "duplicates": [],
            }

        df = pd.read_csv(
            DUPLICATE_PAIRS_CSV
        )

        records = dataframe_to_json_records(
            df
        )

        return {
            "success": True,
            "count": len(records),
            "duplicates": records,
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error),
            "duplicates": [],
        }


def get_duplicate_detection_full():
    """
    Return complete duplicate detection results.
    """

    try:

        if not DUPLICATE_FULL_CSV.exists():

            return {
                "success": False,
                "message": (
                    "Full duplicate detection output "
                    "not found."
                ),
                "results": [],
            }

        df = pd.read_csv(
            DUPLICATE_FULL_CSV
        )

        records = dataframe_to_json_records(
            df
        )

        return {
            "success": True,
            "count": len(records),
            "results": records,
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error),
            "results": [],
        }


def get_duplicate_summary():
    """
    Return duplicate detection summary.
    """

    try:

        if not DUPLICATE_SUMMARY_JSON.exists():

            return {
                "success": False,
                "message": (
                    "Duplicate detection summary "
                    "not found."
                ),
            }

        with open(
            DUPLICATE_SUMMARY_JSON,
            "r",
            encoding="utf-8",
        ) as file:

            summary = json.load(file)

        return {
            "success": True,
            "summary": summary,
        }

    except Exception as error:

        return {
            "success": False,
            "message": str(error),
        }