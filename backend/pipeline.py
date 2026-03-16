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

from db.database import SessionLocal
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


if __name__ == "__main__":
    run_pipeline()