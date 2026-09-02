from pathlib import Path
import json

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from .data_processor import (
    load_features,
    get_total_works,
    get_columns,
    get_missing_values,
    get_duplicate_count,
    get_work_by_id,
)


# ==========================================================
# ROUTER
# ==========================================================

router = APIRouter()


# ==========================================================
# PROJECT PATHS
# ==========================================================

# routes.py location:
#
# SIH26102/backend/app/routes.py
#
# parents[0] -> app
# parents[1] -> backend
# parents[2] -> SIH26102

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ==========================================================
# ML OUTPUT DIRECTORY
# ==========================================================

ML_OUTPUT_DIR = PROJECT_ROOT / "ml" / "outputs"


# ==========================================================
# ANOMALY DETECTION OUTPUTS
# ==========================================================

ANOMALY_SCORES_FILE = (
    ML_OUTPUT_DIR / "anomaly_scores.csv"
)

ANOMALY_FLAGGED_FILE = (
    ML_OUTPUT_DIR / "anomaly_flagged.csv"
)

ANOMALY_SUMMARY_FILE = (
    ML_OUTPUT_DIR / "anomaly_summary.json"
)


# ==========================================================
# INNOVATION OUTPUTS
# ==========================================================

# Innovation 1: Expected Cost Range
COST_PREDICTIONS_FILE = (
    ML_OUTPUT_DIR / "cost_predictions.csv"
)


# Innovation 2: Duplicate Project Detection
DUPLICATE_CANDIDATES_FILE = (
    ML_OUTPUT_DIR / "duplicate_candidates.csv"
)


# Innovation 3: Delay Prediction
DELAY_PREDICTIONS_FILE = (
    ML_OUTPUT_DIR / "delay_predictions.csv"
)


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def dataframe_to_records(df: pd.DataFrame):
    """
    Convert a Pandas DataFrame into JSON-safe records.

    Handles:
    - NaN values
    - NumPy numeric types
    - Dates
    """

    return json.loads(
        df.to_json(
            orient="records",
            date_format="iso"
        )
    )


def load_csv_file(file_path: Path, name: str):
    """
    Generic CSV loader with consistent error handling.
    """

    if not file_path.exists():

        raise FileNotFoundError(
            f"{name} file not found: {file_path}"
        )

    return pd.read_csv(file_path)


# ==========================================================
# ML OUTPUT LOADERS
# ==========================================================

def load_anomaly_scores():

    return load_csv_file(
        ANOMALY_SCORES_FILE,
        "Anomaly scores"
    )


def load_flagged_anomalies():

    return load_csv_file(
        ANOMALY_FLAGGED_FILE,
        "Flagged anomalies"
    )


def load_cost_predictions():

    return load_csv_file(
        COST_PREDICTIONS_FILE,
        "Cost predictions"
    )


def load_duplicate_candidates():

    return load_csv_file(
        DUPLICATE_CANDIDATES_FILE,
        "Duplicate candidates"
    )


def load_delay_predictions():

    return load_csv_file(
        DELAY_PREDICTIONS_FILE,
        "Delay predictions"
    )


def load_anomaly_summary():

    if not ANOMALY_SUMMARY_FILE.exists():

        raise FileNotFoundError(
            f"Anomaly summary file not found: "
            f"{ANOMALY_SUMMARY_FILE}"
        )

    with open(
        ANOMALY_SUMMARY_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ==========================================================
# HEALTH CHECK
# ==========================================================

@router.get("/health")
def health_check():

    return {
        "status": "ok",
        "message": "MPLADS Anomaly Detection API is running"
    }


# ==========================================================
# DATASET STATISTICS
# ==========================================================

@router.get("/stats")
def get_dataset_stats():

    df = load_features()

    return {
        "total_works": get_total_works(df),
        "columns": get_columns(df),
        "missing_values": get_missing_values(df),
        "duplicate_count": get_duplicate_count(df),
    }


# ==========================================================
# GET ALL WORKS
# ==========================================================

@router.get("/works")
def get_works(

    limit: int = Query(
        default=100,
        ge=1,
        le=1000
    ),

    offset: int = Query(
        default=0,
        ge=0
    ),

):

    df = load_features()

    total = len(df)

    paginated_df = df.iloc[
        offset:offset + limit
    ]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": dataframe_to_records(
            paginated_df
        ),
    }


# ==========================================================
# GET SINGLE WORK
# ==========================================================

# work_id values contain "/" characters.
#
# Example:
#
# WS/MP005/2024-2025/145074
#
# Therefore:
#
# {work_id:path}
#
# is required.

@router.get("/works/{work_id:path}")
def get_work(work_id: str):

    df = load_features()

    work = get_work_by_id(
        df,
        work_id
    )

    if work is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Work with ID "
                f"'{work_id}' was not found"
            )
        )

    return json.loads(
        pd.DataFrame([work]).to_json(
            orient="records",
            date_format="iso"
        )
    )[0]


# ==========================================================
# ANOMALY SUMMARY
# ==========================================================

@router.get("/summary")
def get_summary():

    try:

        return load_anomaly_summary()

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ==========================================================
# GET ALL FLAGGED ANOMALIES
# ==========================================================

@router.get("/anomalies")
def get_anomalies(

    limit: int = Query(
        default=100,
        ge=1,
        le=1000
    ),

    offset: int = Query(
        default=0,
        ge=0
    ),

):

    try:

        anomalies = load_flagged_anomalies()

        total = len(anomalies)

        paginated_anomalies = anomalies.iloc[
            offset:offset + limit
        ]

        return {
            "total_anomalies": total,
            "limit": limit,
            "offset": offset,
            "data": dataframe_to_records(
                paginated_anomalies
            ),
        }

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ==========================================================
# GET ANOMALY COUNT
# ==========================================================

@router.get("/anomalies/count")
def get_anomaly_count():

    try:

        anomalies = load_flagged_anomalies()

        return {
            "total_anomalies": len(anomalies)
        }

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ==========================================================
# GET HIGH-RISK ANOMALIES
# ==========================================================

@router.get("/anomalies/high-risk")
def get_high_risk_anomalies(

    top_n: int = Query(
        default=10,
        ge=1,
        le=100
    ),

):

    try:

        anomalies = load_flagged_anomalies()

        if "anomaly_score" not in anomalies.columns:

            raise HTTPException(
                status_code=500,
                detail=(
                    "anomaly_score column "
                    "not found in anomaly output"
                )
            )

        high_risk = anomalies.sort_values(
            by="anomaly_score",
            ascending=False
        ).head(top_n)

        return {
            "count": len(high_risk),
            "data": dataframe_to_records(
                high_risk
            ),
        }

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ==========================================================
# GET SINGLE ANOMALY
# ==========================================================

@router.get("/anomalies/{work_id:path}")
def get_anomaly_by_work_id(
    work_id: str
):

    try:

        anomalies = load_flagged_anomalies()

        result = anomalies[
            anomalies["work_id"] == work_id
        ]

        if result.empty:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No flagged anomaly found "
                    f"for work ID '{work_id}'"
                )
            )

        return dataframe_to_records(
            result
        )[0]

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ==========================================================
# INNOVATION 1
# EXPECTED COST RANGE
# ==========================================================

@router.get("/cost-estimates")
def get_cost_estimates(

    limit: int = Query(
        default=100,
        ge=1,
        le=1000
    ),

    offset: int = Query(
        default=0,
        ge=0
    ),

):

    try:

        predictions = load_cost_predictions()

        total = len(predictions)

        paginated_predictions = predictions.iloc[
            offset:offset + limit
        ]

        return {
            "total_predictions": total,
            "limit": limit,
            "offset": offset,
            "data": dataframe_to_records(
                paginated_predictions
            ),
        }

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ==========================================================
# GET COST ESTIMATE FOR A SINGLE WORK
# ==========================================================

@router.get("/cost-estimates/{work_id:path}")
def get_cost_estimate_by_work_id(
    work_id: str
):

    try:

        predictions = load_cost_predictions()

        if "work_id" not in predictions.columns:

            raise HTTPException(
                status_code=500,
                detail=(
                    "work_id column not found "
                    "in cost prediction output"
                )
            )

        result = predictions[
            predictions["work_id"] == work_id
        ]

        if result.empty:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No cost estimate found "
                    f"for work ID '{work_id}'"
                )
            )

        return dataframe_to_records(
            result
        )[0]

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ==========================================================
# INNOVATION 2
# DUPLICATE PROJECT DETECTION
# ==========================================================

@router.get("/duplicates")
def get_duplicate_candidates(

    limit: int = Query(
        default=100,
        ge=1,
        le=1000
    ),

    offset: int = Query(
        default=0,
        ge=0
    ),

):

    try:

        duplicates = load_duplicate_candidates()

        total = len(duplicates)

        paginated_duplicates = duplicates.iloc[
            offset:offset + limit
        ]

        return {
            "total_candidates": total,
            "limit": limit,
            "offset": offset,
            "data": dataframe_to_records(
                paginated_duplicates
            ),
        }

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ==========================================================
# GET DUPLICATES FOR A SINGLE WORK
# ==========================================================

@router.get("/duplicates/{work_id:path}")
def get_duplicates_by_work_id(
    work_id: str
):

    try:

        duplicates = load_duplicate_candidates()

        required_columns = {
            "work_id_1",
            "work_id_2"
        }

        if not required_columns.issubset(
            duplicates.columns
        ):

            raise HTTPException(
                status_code=500,
                detail=(
                    "Duplicate detection output "
                    "does not contain the required "
                    "work ID columns"
                )
            )

        result = duplicates[
            (duplicates["work_id_1"] == work_id)
            |
            (duplicates["work_id_2"] == work_id)
        ]

        if result.empty:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No duplicate candidates found "
                    f"for work ID '{work_id}'"
                )
            )

        return {
            "work_id": work_id,
            "count": len(result),
            "data": dataframe_to_records(
                result
            ),
        }

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ==========================================================
# INNOVATION 3
# DELAY PREDICTION
# ==========================================================

@router.get("/delay-predictions")
def get_delay_predictions(

    limit: int = Query(
        default=100,
        ge=1,
        le=1000
    ),

    offset: int = Query(
        default=0,
        ge=0
    ),

):

    try:

        predictions = load_delay_predictions()

        total = len(predictions)

        paginated_predictions = predictions.iloc[
            offset:offset + limit
        ]

        return {
            "total_predictions": total,
            "limit": limit,
            "offset": offset,
            "data": dataframe_to_records(
                paginated_predictions
            ),
        }

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# ==========================================================
# GET DELAY PREDICTION FOR A SINGLE WORK
# ==========================================================

@router.get("/delay-predictions/{work_id:path}")
def get_delay_prediction_by_work_id(
    work_id: str
):

    try:

        predictions = load_delay_predictions()

        if "work_id" not in predictions.columns:

            raise HTTPException(
                status_code=500,
                detail=(
                    "work_id column not found "
                    "in delay prediction output"
                )
            )

        result = predictions[
            predictions["work_id"] == work_id
        ]

        if result.empty:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No delay prediction found "
                    f"for work ID '{work_id}'"
                )
            )

        return dataframe_to_records(
            result
        )[0]

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )