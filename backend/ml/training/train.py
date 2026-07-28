"""
Gokul Ramanan
03/15/2026

ML Training — Model Training
Defines EnsembleCBXGB, runs time-series CV, evaluates on holdout,
trains the final model on full data, and saves the artifact.
"""

import logging
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score
from sqlalchemy import text
from sqlalchemy.orm import Session
from xgboost import XGBRegressor

from db.models.schemas import ModelVersion
from ml.constants import (
    CB_PARAMS,
    ENSEMBLE_CB_WEIGHT,
    ENSEMBLE_XGB_WEIGHT,
    FEATURE_COLS_WITH_COUNTRY,
    TARGET_COL,
    TRAIN_START_YEAR,
    XGB_PARAMS,
)

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ── Ensemble model ────────────────────────────────────────────────────────────

class EnsembleCBXGB(BaseEstimator, RegressorMixin):
    """
    Weighted ensemble: CatBoost (country as categorical) +
                       XGBoost  (country one-hot encoded).
    Both consume the same feature set including 'country'.
    """

    def __init__(
        self,
        cb_weight: float = ENSEMBLE_CB_WEIGHT,
        xgb_weight: float = ENSEMBLE_XGB_WEIGHT,
        cb_params: dict | None = None,
        xgb_params: dict | None = None,
    ):
        self.cb_weight  = cb_weight
        self.xgb_weight = xgb_weight
        self.cb_params  = cb_params  or CB_PARAMS
        self.xgb_params = xgb_params or XGB_PARAMS

        self.cb_model_: CatBoostRegressor | None = None
        self.xgb_model_: XGBRegressor     | None = None
        self.xgb_feature_names_: list[str] = []

    # ── fit ──────────────────────────────────────────────────────────────────

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "EnsembleCBXGB":
        self.cb_model_ = CatBoostRegressor(**self.cb_params)
        self.cb_model_.fit(X, y)

        X_enc = self._encode_for_xgb(X, fit=True)
        self.xgb_model_ = XGBRegressor(**self.xgb_params)
        self.xgb_model_.fit(X_enc, y)

        return self

    # ── predict ──────────────────────────────────────────────────────────────

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.cb_model_ is None or self.xgb_model_ is None:
            raise ValueError("Model must be fitted before calling predict().")

        cb_preds  = self.cb_model_.predict(X)
        xgb_preds = self.xgb_model_.predict(self._encode_for_xgb(X, fit=False))
        return self.cb_weight * cb_preds + self.xgb_weight * xgb_preds

    def score(self, X: pd.DataFrame, y: pd.Series) -> float:
        return float(r2_score(y, self.predict(X)))

    # ── sklearn compatibility ─────────────────────────────────────────────────

    def get_params(self, deep: bool = True) -> dict:
        return {
            "cb_weight":  self.cb_weight,
            "xgb_weight": self.xgb_weight,
            "cb_params":  self.cb_params,
            "xgb_params": self.xgb_params,
        }

    def set_params(self, **params) -> "EnsembleCBXGB":
        for k, v in params.items():
            setattr(self, k, v)
        return self

    # ── internal helpers ──────────────────────────────────────────────────────

    def _encode_for_xgb(self, X: pd.DataFrame, fit: bool) -> pd.DataFrame:
        X_enc = X.copy()
        if "country" in X_enc.columns:
            X_enc = pd.get_dummies(X_enc, columns=["country"], prefix="country", drop_first=True)

        if fit:
            self.xgb_feature_names_ = X_enc.columns.tolist()
        else:
            for col in self.xgb_feature_names_:
                if col not in X_enc.columns:
                    X_enc[col] = 0
            X_enc = X_enc[self.xgb_feature_names_]

        return X_enc


# ── Train/test split ──────────────────────────────────────────────────────────

def get_train_test_split(
    df: pd.DataFrame,
    feature_cols: list[str],
    current_year: int | None = None,
):
    if current_year is None:
        current_year = df[df[TARGET_COL].notna()]["date"].max()

    train_end     = current_year - 3
    holdout_start = current_year - 2

    train_mask = df["date"] <= train_end
    test_mask  = df["date"] >= holdout_start

    X_train = df[train_mask][feature_cols]
    X_test  = df[test_mask][feature_cols]
    y_train = df[train_mask][TARGET_COL]
    y_test  = df[test_mask][TARGET_COL]
    cv_data = df[train_mask].copy()

    logger.info(
        "Split — train: 1991–%d  holdout: %d–%d",
        train_end, holdout_start, current_year,
    )
    return X_train, X_test, y_train, y_test, cv_data


# ── Time-series CV splits ─────────────────────────────────────────────────────

def get_ts_cv_splits(cv_data: pd.DataFrame, n_splits: int = 4) -> list:
    min_yr, max_yr = cv_data["date"].min(), cv_data["date"].max()
    total_years    = max_yr - min_yr + 1
    base_test_size = -(total_years // -(n_splits + 1))
    available      = total_years - base_test_size
    fold_size      = available // n_splits
    remainder      = available % n_splits

    splits, current = [], min_yr + base_test_size

    for i in range(n_splits):
        this_fold = fold_size + (1 if i < remainder else 0)
        t_start   = current
        t_end     = min(t_start + this_fold - 1, max_yr)

        train_mask = cv_data["date"] <= (t_start - 1)
        test_mask  = (cv_data["date"] >= t_start) & (cv_data["date"] <= t_end)
        splits.append((train_mask, test_mask))
        current = t_end + 1

    return splits


# ── Cross-validation ──────────────────────────────────────────────────────────

def run_cv(
    model: EnsembleCBXGB,
    X: pd.DataFrame,
    y: pd.Series,
    cv_splits: list,
) -> dict:
    fold_r2, fold_rmse = [], []

    for fold_num, (train_mask, test_mask) in enumerate(cv_splits, 1):
        m = clone(model)
        m.fit(X[train_mask], y[train_mask])
        preds = m.predict(X[test_mask])

        r2   = r2_score(y[test_mask], preds)
        rmse = np.sqrt(mean_squared_error(y[test_mask], preds))
        fold_r2.append(r2)
        fold_rmse.append(rmse)
        logger.info("CV fold %d — R²=%.4f  RMSE=%.2f", fold_num, r2, rmse)

    return {
        "r2_mean":   float(np.mean(fold_r2)),
        "r2_std":    float(np.std(fold_r2)),
        "rmse_mean": float(np.mean(fold_rmse)),
        "rmse_std":  float(np.std(fold_rmse)),
    }


# ── Holdout evaluation ────────────────────────────────────────────────────────

def evaluate_holdout(
    model: EnsembleCBXGB,
    X_cv: pd.DataFrame,
    y_cv: pd.Series,
    X_holdout: pd.DataFrame,
    y_holdout: pd.Series,
) -> dict:
    m = clone(model)
    m.fit(X_cv, y_cv)
    preds = m.predict(X_holdout)

    metrics = {
        "holdout_r2":   float(r2_score(y_holdout, preds)),
        "holdout_rmse": float(np.sqrt(mean_squared_error(y_holdout, preds))),
        "holdout_mape": float(mean_absolute_percentage_error(y_holdout, preds)),
    }
    logger.info(
        "Holdout — R²=%.4f  RMSE=%.2f  MAPE=%.4f",
        metrics["holdout_r2"], metrics["holdout_rmse"], metrics["holdout_mape"],
    )
    return metrics


# ── Full training run ─────────────────────────────────────────────────────────

def train_final_model(
    df_clean: pd.DataFrame,
    train_end_year: int,
) -> tuple["EnsembleCBXGB", pd.DataFrame]:
    """
    Train the final model on all data up to train_end_year.
    train_end_year is resolved dynamically by the pipeline
    as the last year with a real gdp_per_capita in indicator_data.
    Returns (fitted model, historical predictions DataFrame).
    """
    full = df_clean[df_clean["date"] <= train_end_year].copy()
    X    = full[FEATURE_COLS_WITH_COUNTRY]
    y    = full[TARGET_COL]

    model = EnsembleCBXGB()
    model.fit(X, y)

    hist_preds = full[["country", "date", TARGET_COL]].copy()
    hist_preds["ensemble_prediction"] = model.predict(X)
    hist_preds["prediction_error"]    = hist_preds[TARGET_COL] - hist_preds["ensemble_prediction"]
    hist_preds["error_pct"]           = hist_preds["prediction_error"] / hist_preds[TARGET_COL] * 100
    hist_preds = hist_preds.rename(columns={"date": "year", TARGET_COL: "actual_gdp"})

    logger.info("Final model trained on %d rows.", len(full))
    return model, hist_preds


# ── Artifact persistence ──────────────────────────────────────────────────────

def save_model(model: "EnsembleCBXGB", version_name: str) -> Path:
    path = MODEL_DIR / f"{version_name}.joblib"
    joblib.dump(model, path)
    logger.info("Model saved → %s", path)
    return path


def load_model(version_name: str) -> "EnsembleCBXGB":
    path = MODEL_DIR / f"{version_name}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"No model artifact at {path}")
    return joblib.load(path)


# ── Persist model version to DB ───────────────────────────────────────────────

def persist_model_version(
    version_name: str,
    cv_metrics: dict,
    holdout_metrics: dict,
    feature_list: list[str],
    train_end_year: int,
    session: Session,
) -> ModelVersion:
    # Sync sequence in case rows were inserted via migration with explicit IDs
    session.execute(text(
        "SELECT setval('model_versions_version_id_seq', "
        "(SELECT COALESCE(MAX(version_id), 0) + 1 FROM model_versions), false)"
    ))

    existing = session.query(ModelVersion).filter_by(version_name=version_name).first()
    if existing:
        session.delete(existing)
        session.flush()

    # Deactivate all previously active model versions
    session.query(ModelVersion).filter_by(is_active=True).update({"is_active": False})
    session.flush()

    mv = ModelVersion(
        version_name        = version_name,
        model_type          = "EnsembleCBXGB",
        description         = "CatBoost + XGBoost weighted ensemble with mean-reverting extrapolation",
        hyperparameters     = {"cb_params": CB_PARAMS, "xgb_params": XGB_PARAMS},
        feature_list        = feature_list,
        training_start_year = TRAIN_START_YEAR,
        training_end_year   = train_end_year,
        cv_r2               = cv_metrics["r2_mean"],
        cv_rmse             = cv_metrics["rmse_mean"],
        holdout_r2          = holdout_metrics["holdout_r2"],
        holdout_rmse        = holdout_metrics["holdout_rmse"],
        holdout_mape        = holdout_metrics["holdout_mape"],
        is_active           = True,
    )
    session.add(mv)
    session.commit()
    logger.info("Persisted model version '%s' to DB.", version_name)
    return mv