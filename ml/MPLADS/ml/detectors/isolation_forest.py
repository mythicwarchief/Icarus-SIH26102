"""
Isolation Forest Anomaly Detector.

Trains an Isolation Forest on selected numeric features to detect
multivariate outliers that may not be caught by individual rules.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
import joblib
import os
from .. import config


def detect(df: pd.DataFrame, save_model: bool = True) -> pd.DataFrame:
    """
    Train Isolation Forest and score all records.

    Adds columns:
    - if_score (float 0–1, higher = more anomalous)
    - if_label (int, -1 = anomaly, 1 = normal from sklearn)

    Args:
        df: Master DataFrame with engineered features
        save_model: Whether to save the trained model as .joblib

    Returns:
        DataFrame with IF scores added
    """
    print("[IFDetector] Running Isolation Forest anomaly detection...")

    # Select features
    available_features = [f for f in config.IF_FEATURES if f in df.columns]
    if len(available_features) < 3:
        print(f"[IFDetector] WARNING: Only {len(available_features)} features available. "
              f"Need at least 3. Skipping IF detection.")
        df["if_score"] = 0.0
        df["if_label"] = 1
        return df

    print(f"[IFDetector] Using {len(available_features)} features: {available_features}")

    X = df[available_features].copy()

    # Handle inf values
    X = X.replace([np.inf, -np.inf], np.nan)

    # Impute missing values with median
    imputer = SimpleImputer(strategy="median")
    X_imputed = imputer.fit_transform(X)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)

    # Train Isolation Forest
    iso_forest = IsolationForest(
        n_estimators=config.IF_N_ESTIMATORS,
        contamination=config.IF_CONTAMINATION,
        max_samples=config.IF_MAX_SAMPLES,
        random_state=config.IF_RANDOM_STATE,
        n_jobs=-1,
    )
    iso_forest.fit(X_scaled)

    # Get predictions and scores
    labels = iso_forest.predict(X_scaled)  # -1 = anomaly, 1 = normal
    raw_scores = iso_forest.decision_function(X_scaled)  # lower = more anomalous

    # Normalize scores to 0–1 (invert so higher = more anomalous)
    min_score = raw_scores.min()
    max_score = raw_scores.max()
    score_range = max_score - min_score
    if score_range > 0:
        normalized = 1 - (raw_scores - min_score) / score_range
    else:
        normalized = np.zeros_like(raw_scores)

    df["if_score"] = normalized
    df["if_label"] = labels

    anomaly_count = (labels == -1).sum()
    print(f"[IFDetector] Done. {anomaly_count} anomalies detected out of {len(df)} records.")
    print(f"[IFDetector] Score range: [{df['if_score'].min():.4f}, {df['if_score'].max():.4f}]")
    print(f"[IFDetector] Mean score: {df['if_score'].mean():.4f}")

    # Save model artifacts
    if save_model:
        os.makedirs(config.MODEL_DIR, exist_ok=True)
        model_bundle = {
            "model": iso_forest,
            "imputer": imputer,
            "scaler": scaler,
            "features": available_features,
        }
        joblib.dump(model_bundle, config.ISOLATION_FOREST_MODEL)
        print(f"[IFDetector] Model saved to {config.ISOLATION_FOREST_MODEL}")

    return df


def score_new_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score new data using a previously trained model.
    Useful for the FastAPI backend to score on-the-fly.
    """
    if not os.path.exists(config.ISOLATION_FOREST_MODEL):
        raise FileNotFoundError(
            f"No trained model found at {config.ISOLATION_FOREST_MODEL}. "
            f"Run the pipeline first."
        )

    bundle = joblib.load(config.ISOLATION_FOREST_MODEL)
    iso_forest = bundle["model"]
    imputer = bundle["imputer"]
    scaler = bundle["scaler"]
    features = bundle["features"]

    available = [f for f in features if f in df.columns]
    if len(available) < len(features):
        missing = set(features) - set(available)
        print(f"[IFDetector] WARNING: Missing features: {missing}")

    X = df[available].replace([np.inf, -np.inf], np.nan)
    X_imputed = imputer.transform(X)
    X_scaled = scaler.transform(X_imputed)

    labels = iso_forest.predict(X_scaled)
    raw_scores = iso_forest.decision_function(X_scaled)

    min_score = raw_scores.min()
    max_score = raw_scores.max()
    score_range = max_score - min_score
    if score_range > 0:
        normalized = 1 - (raw_scores - min_score) / score_range
    else:
        normalized = np.zeros_like(raw_scores)

    df["if_score"] = normalized
    df["if_label"] = labels

    return df
