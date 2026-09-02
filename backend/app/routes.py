"""
API Routes Module.

Provides API endpoints for:
- Dataset statistics
- Works data
- Core anomaly detection
- Cost estimation innovation
- Duplicate project detection innovation
- Delay prediction innovation
"""

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

from .ml_service import (
    run_ml_pipeline,
    get_cost_estimates as get_cost_estimates_service,
    get_delay_predictions as get_delay_predictions_service,
    get_delay_prediction_summary,
    get_duplicate_projects,
    get_duplicate_detection_full,
    get_duplicate_summary,
)


# ==========================================================
# ROUTER
# ==========================================================

router = APIRouter()


# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ML_OUTPUT_DIR = PROJECT_ROOT / "ml" / "outputs"


# ==========================================================
# CORE ANOMALY OUTPUT FILES
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
# HELPER FUNCTIONS
# ==========================================================

def dataframe_to_records(df: pd.DataFrame):
    """
    Convert a DataFrame into JSON-safe Python records.
    """

    return json.loads(
        df.to_json(
            orient="records",
            date_format="iso",
        )
    )


def load_csv_file(
    file_path: Path,
    name: str,
):
    """
    Generic CSV loader.
    """

    if not file_path.exists():

        raise FileNotFoundError(
            f"{name} file not found: {file_path}"
        )

    return pd.read_csv(file_path)


# ==========================================================
# CORE ML OUTPUT LOADERS
# ==========================================================

def load_anomaly_scores():

    return load_csv_file(
        ANOMALY_SCORES_FILE,
        "Anomaly scores",
    )


def load_flagged_anomalies():

    return load_csv_file(
        ANOMALY_FLAGGED_FILE,
        "Flagged anomalies",
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
        encoding="utf-8",
    ) as file:

        return json.load(file)


# ==========================================================
# HEALTH CHECK
# ==========================================================

@router.get("/health")
def health_check():

    return {
        "status": "ok",
        "message": (
            "MPLADS Anomaly Detection API is running"
        ),
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
        le=1000,
    ),

    offset: int = Query(
        default=0,
        ge=0,
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

@router.get("/works/{work_id:path}")
def get_work(
    work_id: str,
):

    df = load_features()

    work = get_work_by_id(
        df,
        work_id,
    )

    if work is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Work with ID "
                f"'{work_id}' was not found"
            ),
        )

    return dataframe_to_records(
        pd.DataFrame([work])
    )[0]


# ==========================================================
# RUN CORE ML PIPELINE
# ==========================================================

@router.post("/ml/run")
def run_pipeline():

    result = run_ml_pipeline()

    if not result["success"]:

        raise HTTPException(
            status_code=500,
            detail=result["message"],
        )

    return result


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
            detail=str(error),
        )


# ==========================================================
# GET ALL FLAGGED ANOMALIES
# ==========================================================

@router.get("/anomalies")
def get_anomalies(

    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),

    offset: int = Query(
        default=0,
        ge=0,
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
            detail=str(error),
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
            detail=str(error),
        )


# ==========================================================
# GET HIGH-RISK ANOMALIES
# ==========================================================

@router.get("/anomalies/high-risk")
def get_high_risk_anomalies(

    top_n: int = Query(
        default=10,
        ge=1,
        le=100,
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
                ),
            )

        high_risk = anomalies.sort_values(
            by="anomaly_score",
            ascending=False,
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
            detail=str(error),
        )


# ==========================================================
# GET SINGLE ANOMALY
# ==========================================================

@router.get("/anomalies/{work_id:path}")
def get_anomaly_by_work_id(
    work_id: str,
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
                ),
            )

        return dataframe_to_records(
            result
        )[0]

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


# ==========================================================
# INNOVATION 1
# COST RANGE ESTIMATION
# ==========================================================

@router.get("/cost-estimates")
def get_cost_estimates(

    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),

    offset: int = Query(
        default=0,
        ge=0,
    ),
):

    result = get_cost_estimates_service()

    if not result["success"]:

        raise HTTPException(
            status_code=500,
            detail=result["message"],
        )

    estimates = result["cost_estimates"]

    total = len(estimates)

    paginated_estimates = estimates[
        offset:offset + limit
    ]

    return {
        "total_estimates": total,
        "limit": limit,
        "offset": offset,
        "data": paginated_estimates,
    }


# ==========================================================
# GET COST ESTIMATE FOR SINGLE WORK
# ==========================================================

@router.get("/cost-estimates/{work_id:path}")
def get_cost_estimate_by_work_id(
    work_id: str,
):

    result = get_cost_estimates_service()

    if not result["success"]:

        raise HTTPException(
            status_code=500,
            detail=result["message"],
        )

    estimates = pd.DataFrame(
        result["cost_estimates"]
    )

    if "work_id" not in estimates.columns:

        raise HTTPException(
            status_code=500,
            detail=(
                "work_id column not found "
                "in cost estimation output"
            ),
        )

    estimate = estimates[
        estimates["work_id"] == work_id
    ]

    if estimate.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No cost estimate found "
                f"for work ID '{work_id}'"
            ),
        )

    return dataframe_to_records(
        estimate
    )[0]


# ==========================================================
# INNOVATION 2
# DUPLICATE DETECTION
# ==========================================================

@router.get("/duplicates")
def get_duplicates(

    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),

    offset: int = Query(
        default=0,
        ge=0,
    ),
):

    result = get_duplicate_projects()

    if not result["success"]:

        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )

    duplicates = result["duplicates"]

    total = len(duplicates)

    paginated_duplicates = duplicates[
        offset:offset + limit
    ]

    return {
        "total_candidates": total,
        "limit": limit,
        "offset": offset,
        "data": paginated_duplicates,
    }


# ==========================================================
# FULL DUPLICATE RESULTS
# ==========================================================

@router.get("/duplicates/full")
def get_full_duplicate_results():

    result = get_duplicate_detection_full()

    if not result["success"]:

        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )

    return result


# ==========================================================
# DUPLICATE SUMMARY
# ==========================================================

@router.get("/duplicates/summary")
def get_duplicates_summary():

    result = get_duplicate_summary()

    if not result["success"]:

        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )

    return result


# ==========================================================
# GET DUPLICATES FOR SINGLE WORK
# IMPORTANT: MUST COME AFTER STATIC ROUTES
# ==========================================================

@router.get("/duplicates/{work_id:path}")
def get_duplicates_by_work_id(
    work_id: str,
):

    result = get_duplicate_projects()

    if not result["success"]:

        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )

    duplicates = pd.DataFrame(
        result["duplicates"]
    )

    required_columns = {
        "work_id_1",
        "work_id_2",
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
            ),
        )

    matching_duplicates = duplicates[
        (duplicates["work_id_1"] == work_id)
        |
        (duplicates["work_id_2"] == work_id)
    ]

    if matching_duplicates.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No duplicate candidates found "
                f"for work ID '{work_id}'"
            ),
        )

    return {
        "work_id": work_id,
        "count": len(matching_duplicates),
        "data": dataframe_to_records(
            matching_duplicates
        ),
    }


# ==========================================================
# INNOVATION 3
# DELAY PREDICTION
# ==========================================================

@router.get("/delay-predictions")
def get_delay_predictions(

    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),

    offset: int = Query(
        default=0,
        ge=0,
    ),
):

    result = get_delay_predictions_service()

    if not result["success"]:

        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )

    predictions = result["predictions"]

    total = len(predictions)

    paginated_predictions = predictions[
        offset:offset + limit
    ]

    return {
        "total_predictions": total,
        "limit": limit,
        "offset": offset,
        "data": paginated_predictions,
    }


# ==========================================================
# DELAY PREDICTION SUMMARY
# ==========================================================

@router.get("/delay-predictions/summary")
def get_delay_summary():

    result = get_delay_prediction_summary()

    if not result["success"]:

        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )

    return result


# ==========================================================
# GET DELAY PREDICTION FOR SINGLE WORK
# IMPORTANT: MUST COME LAST
# ==========================================================

@router.get("/delay-predictions/{work_id:path}")
def get_delay_prediction_by_work_id(
    work_id: str,
):

    result = get_delay_predictions_service()

    if not result["success"]:

        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )

    predictions = pd.DataFrame(
        result["predictions"]
    )

    if "work_id" not in predictions.columns:

        raise HTTPException(
            status_code=500,
            detail=(
                "work_id column not found "
                "in delay prediction output"
            ),
        )

    prediction = predictions[
        predictions["work_id"] == work_id
    ]

    if prediction.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No delay prediction found "
                f"for work ID '{work_id}'"
            ),
        )

    return dataframe_to_records(
        prediction
    )[0]