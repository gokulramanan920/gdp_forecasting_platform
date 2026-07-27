"""
Gokul Ramanan
03/15/2026

Pipeline Entry Point
Orchestrates the full ETL → Train → Predict run.
Designed to be deployment-agnostic — wire to any scheduler:
  - crontab:          0 0 1 * * python pipeline.py
  - Railway/Render:   cron job pointing at this file
  - AWS EventBridge:  Lambda handler calls run_pipeline()
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Ensure backend/ is on the path when called directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from sqlalchemy import text

from db.database import SessionLocal
from db.models.schemas import Country, ModelVersion
from etl.etl import run_etl
from ml.training.clustering import (
    assign_cohorts_kmeans,
    calibrate_cluster_baselines,
    persist_economy_types,
)
from ml.training.train import (
    evaluate_holdout,
    get_train_test_split,
    get_ts_cv_splits,
    load_model,
    persist_model_version,
    run_cv,
    save_model,
    train_final_model,
)
from ml.inference.predict import (
    compute_confidence_intervals,
    persist_predictions,
    run_predictions,
)
from ml.constants import FEATURE_COLS_WITH_COUNTRY, TARGET_COL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True, 
)
logger = logging.getLogger(__name__)


def run_pipeline(version_name: str | None = None) -> None:
    if version_name is None:
        version_name = f"v_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    logger.info("=" * 60)
    logger.info("GDP FORECASTING PIPELINE  version=%s", version_name)
    logger.info("=" * 60)

    session = SessionLocal()

    try:
        # ── 1. ETL ───────────────────────────────────────────────────────
        logger.info("[1/6] Running ETL (ingest + clean + promote)…")
        df_clean = run_etl(session)

        # Resolve dynamic year bounds from the data
        train_end_year    = int(df_clean[df_clean[TARGET_COL].notna()]["date"].max())
        forecast_end_year = train_end_year + 4
        logger.info("Year bounds — train_end=%d  forecast_end=%d", train_end_year, forecast_end_year)

        # ── 2. Cluster ───────────────────────────────────────────────────
        logger.info("[2/6] Clustering countries…")
        developed, emerging, _ = assign_cohorts_kmeans(df_clean, base_year=train_end_year)
        persist_economy_types(developed, emerging, session)

        baselines = calibrate_cluster_baselines(df_clean, developed, emerging)
        logger.info("Calibrated baselines: %s", baselines)

        import ml.constants as C
        C.CLUSTER_BASELINE_ANNUAL_GROWTH.update(baselines)

        # ── 3. Train ─────────────────────────────────────────────────────
        logger.info("[3/6] Training model…")
        X_cv, X_holdout, y_cv, y_holdout, cv_data = get_train_test_split(
            df_clean, FEATURE_COLS_WITH_COUNTRY
        )
        cv_splits = get_ts_cv_splits(cv_data)

        from ml.training.train import EnsembleCBXGB
        base_model      = EnsembleCBXGB()
        cv_metrics      = run_cv(base_model, X_cv, y_cv, cv_splits)
        holdout_metrics = evaluate_holdout(base_model, X_cv, y_cv, X_holdout, y_holdout)

        final_model, hist_preds = train_final_model(df_clean, train_end_year)
        save_model(final_model, version_name)
        persist_model_version(version_name, cv_metrics, holdout_metrics, FEATURE_COLS_WITH_COUNTRY, train_end_year, session)

        # ── 4. Predict ───────────────────────────────────────────────────
        logger.info("[4/6] Generating forecasts…")
        predictions_df = run_predictions(
            df_clean, final_model, developed, emerging,
            train_end_year=train_end_year,
            forecast_end=forecast_end_year,
        )

        # ── 5. Confidence intervals ───────────────────────────────────────
        logger.info("[5/6] Computing confidence intervals…")
        ci_df = compute_confidence_intervals(hist_preds, predictions_df, train_end_year)

        # ── 6. Persist ───────────────────────────────────────────────────
        logger.info("[6/6] Writing predictions to DB…")
        persist_predictions(df_clean, predictions_df, ci_df, version_name, session)

        logger.info("Pipeline complete ✓  version=%s", version_name)

    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        session.rollback()
        raise
    finally:
        session.close()


# ── Inference-only helpers ────────────────────────────────────────────────────

def _load_df_from_db(session) -> pd.DataFrame:
    """Reconstruct df_clean from indicator_data — same wide format as run_etl()."""
    rows = session.execute(text("""
        SELECT id.country_code AS country,
               id.year         AS date,
               i.simplified_name,
               CAST(id.value AS FLOAT) AS value
        FROM indicator_data id
        JOIN indicators i ON i.indicator_id = id.indicator_id
        ORDER BY id.country_code, id.year
    """)).fetchall()

    df = pd.DataFrame(rows, columns=["country", "date", "simplified_name", "value"])
    wide = (
        df.pivot_table(index=["country", "date"], columns="simplified_name", values="value")
        .reset_index()
    )
    wide.columns.name = None
    return wide


def _load_cohorts_from_db(session) -> tuple[list[str], list[str]]:
    """Return (developed, emerging) country code lists from countries.economy_type."""
    countries = session.query(Country).all()
    developed = [c.country_code for c in countries if c.economy_type == "developed"]
    emerging  = [c.country_code for c in countries if c.economy_type == "emerging"]
    return developed, emerging


def _load_active_version_name(session) -> str:
    mv = session.query(ModelVersion).filter_by(is_active=True).first()
    if mv is None:
        raise RuntimeError("No active model version found in model_versions table.")
    return mv.version_name


def _build_hist_preds(df_clean: pd.DataFrame, model, train_end_year: int) -> pd.DataFrame:
    """
    Reconstruct hist_preds without retraining — identical to what train_final_model
    computes, just using the already-fitted model instead of re-fitting.
    """
    full = df_clean[df_clean["date"] <= train_end_year].copy()
    X    = full[FEATURE_COLS_WITH_COUNTRY]

    hist_preds = full[["country", "date", TARGET_COL]].copy()
    hist_preds["ensemble_prediction"] = model.predict(X)
    hist_preds["prediction_error"]    = hist_preds[TARGET_COL] - hist_preds["ensemble_prediction"]
    hist_preds["error_pct"]           = hist_preds["prediction_error"] / hist_preds[TARGET_COL] * 100
    hist_preds = hist_preds.rename(columns={"date": "year", TARGET_COL: "actual_gdp"})
    return hist_preds


# ── Inference-only entry point ────────────────────────────────────────────────

def run_inference_only(version_name: str | None = None) -> None:
    """
    Re-run predictions from an already-trained model — skips ETL and training.
    Use this when you've changed dampening/blending constants and want to
    persist updated forecasts without touching the model weights.
    """
    session = SessionLocal()
    try:
        logger.info("=" * 60)
        logger.info("INFERENCE-ONLY RUN  (no ETL, no retraining)")
        logger.info("=" * 60)

        logger.info("[1/5] Loading indicator data from DB…")
        df_clean = _load_df_from_db(session)

        train_end_year    = int(df_clean[df_clean[TARGET_COL].notna()]["date"].max())
        forecast_end_year = train_end_year + 4
        logger.info("Year bounds — train_end=%d  forecast_end=%d", train_end_year, forecast_end_year)

        logger.info("[2/5] Loading cohorts and model…")
        developed, emerging = _load_cohorts_from_db(session)

        if version_name is None:
            version_name = _load_active_version_name(session)
        model = load_model(version_name)
        logger.info("Loaded model version: %s", version_name)

        logger.info("[3/5] Recalibrating cluster baselines…")
        baselines = calibrate_cluster_baselines(df_clean, developed, emerging)
        import ml.constants as C
        C.CLUSTER_BASELINE_ANNUAL_GROWTH.update(baselines)

        logger.info("[4/5] Generating forecasts with updated constants…")
        predictions_df = run_predictions(
            df_clean, model, developed, emerging,
            train_end_year=train_end_year,
            forecast_end=forecast_end_year,
        )

        logger.info("[5/5] Computing CIs and writing to DB…")
        hist_preds = _build_hist_preds(df_clean, model, train_end_year)
        ci_df      = compute_confidence_intervals(hist_preds, predictions_df, train_end_year)
        persist_predictions(df_clean, predictions_df, ci_df, version_name, session)

        logger.info("Inference-only run complete ✓  version=%s", version_name)

    except Exception as exc:
        logger.exception("Inference-only run failed: %s", exc)
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    if "--inference-only" in sys.argv:
        run_inference_only()
    else:
        run_pipeline()