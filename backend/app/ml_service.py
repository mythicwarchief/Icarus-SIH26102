from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_ml_pipeline():
    """
    Run the MPLADS anomaly detection pipeline.
    """

    try:
        from ml.anomaly_pipeline import run_pipeline

        run_pipeline()

        return {
            "success": True,
            "message": "ML anomaly detection pipeline completed successfully",
        }

    except Exception as error:
        return {
            "success": False,
            "message": str(error),
        }