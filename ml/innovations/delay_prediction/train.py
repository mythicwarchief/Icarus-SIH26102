"""
Delay Prediction — Model Training and Evaluation.

Trains two ML models on historical completed works (4,822 projects):
  1. Regression Model (RandomForestRegressor): Predicts expected completion duration in days.
  2. Classification Model (RandomForestClassifier / GradientBoostingClassifier):
     Predicts probability of severe project delay (> 365 days).

Evaluates models with 5-Fold Cross Validation and saves the artifacts for inference.
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score, f1_score, accuracy_score, classification_report

from ml import config
from ml.innovations.delay_prediction.features import build_feature_dataset, DELAY_THRESHOLD_DAYS


from ml.innovations import config as innovations_config
MODEL_DIR = innovations_config.MODEL_DIR
MODEL_BUNDLE_PATH = os.path.join(MODEL_DIR, "delay_prediction_models.joblib")
METRICS_PATH = os.path.join(MODEL_DIR, "delay_model_metrics.json")


def train_delay_models():
    """Trains regression and classification models, validates them, and saves artifacts."""
    print("=" * 70)
    print("  MPLADS PROJECT DELAY PREDICTION — MODEL TRAINING")
    print("=" * 70)

    os.makedirs(MODEL_DIR, exist_ok=True)
    full_df, train_df, metadata = build_feature_dataset()
    feature_cols = metadata["feature_cols"]

    print(f"\n[Dataset] Total works: {len(full_df)}")
    print(f"[Dataset] Historical completed works for training: {len(train_df)}")
    print(f"[Dataset] Features used ({len(feature_cols)}): {feature_cols}")

    X = train_df[feature_cols].values
    y_reg = train_df["completion_duration_days"].values
    y_clf = train_df["is_delayed_target"].values

    delayed_count = int(y_clf.sum())
    print(f"[Target] Severe delay cases (>365 days): {delayed_count} / {len(train_df)} ({delayed_count / len(train_df) * 100:.2f}%)")

    # ── 1. Train & Validate Duration Regressor ──
    print("\n[Training] Model 1: Completion Duration Regressor (Random Forest)...")
    regressor = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=4,
        random_state=42,
        n_jobs=-1
    )

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_mae = -cross_val_score(regressor, X, y_reg, cv=kf, scoring="neg_mean_absolute_error")
    cv_r2 = cross_val_score(regressor, X, y_reg, cv=kf, scoring="r2")

    print(f"  5-Fold CV MAE: {cv_mae.mean():.2f} ± {cv_mae.std():.2f} days")
    print(f"  5-Fold CV R²:  {cv_r2.mean():.4f} ± {cv_r2.std():.4f}")

    regressor.fit(X, y_reg)

    # ── 2. Train & Validate Delay Classifier ──
    print("\n[Training] Model 2: Delay Probability Classifier (Gradient Boosting)...")
    classifier = GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=5,
        subsample=0.85,
        random_state=42
    )

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_auc = cross_val_score(classifier, X, y_clf, cv=skf, scoring="roc_auc")
    cv_f1 = cross_val_score(classifier, X, y_clf, cv=skf, scoring="f1")

    print(f"  5-Fold CV ROC-AUC: {cv_auc.mean():.4f} ± {cv_auc.std():.4f}")
    print(f"  5-Fold CV F1-Score: {cv_f1.mean():.4f} ± {cv_f1.std():.4f}")

    classifier.fit(X, y_clf)

    # Feature Importance
    importances = regressor.feature_importances_
    feat_imp = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)
    print("\n[Feature Importance - Duration Model Top 6]:")
    for feat, imp in feat_imp[:6]:
        print(f"  - {feat:30s}: {imp * 100:.2f}%")

    # ── 3. Save Model Bundle ──
    bundle = {
        "regressor": regressor,
        "classifier": classifier,
        "feature_cols": feature_cols,
        "delay_threshold_days": DELAY_THRESHOLD_DAYS,
        "training_samples": len(train_df),
        "cv_metrics": {
            "regression_mae_days": round(float(cv_mae.mean()), 2),
            "regression_r2": round(float(cv_r2.mean()), 4),
            "classification_roc_auc": round(float(cv_auc.mean()), 4),
            "classification_f1": round(float(cv_f1.mean()), 4),
        },
    }

    joblib.dump(bundle, MODEL_BUNDLE_PATH)
    print(f"\n[Saved] Models bundle saved to: {MODEL_BUNDLE_PATH}")

    with open(METRICS_PATH, "w") as f:
        json.dump(bundle["cv_metrics"], f, indent=2)
    print(f"[Saved] Metrics summary saved to: {METRICS_PATH}")

    return bundle


if __name__ == "__main__":
    train_delay_models()
