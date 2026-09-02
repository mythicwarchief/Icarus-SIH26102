"""
ML Service Module.

Provides the bridge between the FastAPI backend and the
MPLADS anomaly detection ML pipeline.
"""

from pathlib import Path
import sys


# ==========================================================
# PROJECT PATH SETUP
# ==========================================================

# ml_service.py location:
# SIH26102/backend/app/ml_service.py
#
# parents[2]:
# SIH26102/

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Ensure the project root is available for Python imports.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ==========================================================
# ML PIPELINE EXECUTION
# ==========================================================

def run_ml_pipeline():
    """
    Execute the MPLADS anomaly detection pipeline.

    The pipeline generates:
    - anomaly_scores.csv
    - anomaly_flagged.csv
    - anomaly_summary.json
    - model_artifacts/isolation_forest.joblib
    """

    try:
        # Import here so the backend can still start even if
        # there is a temporary ML dependency problem.
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