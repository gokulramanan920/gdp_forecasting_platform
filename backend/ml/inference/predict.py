"""
Gokul Ramanan
03/15/2026

ML Inference — Prediction Pipeline
Runs extrapolation + blending for all countries,
computes confidence intervals, and writes to model_predictions.
"""

import logging

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from db.models.schemas import ModelPrediction
from ml.constants import (
    CI_LOOKBACK_YEARS,
    CI_MIN_SAMPLES,
    FEATURE_COLS_WITH_COUNTRY,
)
from ml.inference.extrapolate import (
    blend_model_with_baseline,
    extrapolate_features_mean_reverting,
)
from ml.training.train import EnsembleCBXGB

logger = logging.getLogger(__name__)


# ── Core prediction loop ──────────────────────────────────────────────────────


def run_predictions(
    df_clean: pd.DataFrame,
    model: EnsembleCBXGB,
    developed_countries: list[str],
    emerging_countries: list[str],
    train_end_year: int,
    forecast_end: int,
) -> pd.DataFrame:
    """
    For each country:
      1. Extrapolate features (mean-reverting)
      2. Get raw model prediction
      3. Blend with cluster baseline
      4. Return combined DataFrame

    train_end_year and forecast_end are resolved dynamically
    by the pipeline — no hardcoded years anywhere.
    """
    future_years = list(range(train_end_year + 1, forecast_end + 1))
    all_preds    = []

    for country in df_clean["country"].unique():
        cohort = "developed" if country in developed_countries else "emerging"

        country_future = extrapolate_features_mean_reverting(
            data                = df_clean,
            country_name        = country,
            feature_cols        = FEATURE_COLS_WITH_COUNTRY,
            future_years        = future_years,
            developed_countries = developed_countries,
            emerging_countries  = emerging_countries,
            train_end_year      = train_end_year,
        )
        if country_future is None:
            continue

        X_future     = country_future[FEATURE_COLS_WITH_COUNTRY]
        raw_preds    = model.predict(X_future)

        baseline_row  = df_clean[df_clean["country"] == country].iloc[-1]
        baseline_gdp  = float(baseline_row["gdp_per_capita"])
        baseline_year = int(baseline_row["date"])
        horizon_years = forecast_end - baseline_year

        blended = np.array([
            blend_model_with_baseline(p, baseline_gdp, cohort, horizon_years)
            for p in raw_preds
        ])

        country_future["predicted_gdp_per_capita"] = blended
        country_future["raw_model_pred"]            = raw_preds
        country_future["baseline_year"]             = baseline_year
        country_future["baseline_gdp"]              = baseline_gdp
        country_future["cohort"]                    = cohort

        all_preds.append(country_future)

    predictions_df = pd.concat(all_preds, ignore_index=True)
    logger.info("Generated %d predictions for %d countries.", len(predictions_df), predictions_df["country"].nunique())
    return predictions_df


# ── Confidence intervals ──────────────────────────────────────────────────────

def compute_confidence_intervals(
    hist_preds: pd.DataFrame,
    predictions_df: pd.DataFrame,
    train_end_year: int,
) -> pd.DataFrame:
    """
    Country-specific 80% CI using the empirical error distribution
    from the last N years of historical predictions.

    hist_preds must have columns: country, year, prediction_error
    """
    ci_rows = []

    ci_window_start = train_end_year - CI_LOOKBACK_YEARS
    for country in predictions_df["country"].unique():
        errors = hist_preds[
            (hist_preds["country"] == country) &
            (hist_preds["year"] >= ci_window_start)
        ]["prediction_error"].values

        if len(errors) < CI_MIN_SAMPLES:
            logger.warning("Not enough error samples for %s — skipping CI.", country)
            continue

        p10 = float(np.percentile(errors, 10))
        p90 = float(np.percentile(errors, 90))

        for _, row in predictions_df[predictions_df["country"] == country].iterrows():
            pred = float(row["predicted_gdp_per_capita"])
            ci_rows.append({
                "country":    country,
                "year":       int(row["date"]),
                "ci_80_lower": pred + p10,
                "ci_80_upper": pred + p90,
            })

    return pd.DataFrame(ci_rows)


# ── Write to DB ───────────────────────────────────────────────────────────────

def persist_predictions(
    df_clean: pd.DataFrame,
    predictions_df: pd.DataFrame,
    ci_df: pd.DataFrame,
    model_version: str,
    session: Session,
) -> int:
    """
    Upsert predictions into model_predictions.
    Also inserts one is_baseline=True row per country (last actual year).
    """
    # Merge CI
    merged = predictions_df.merge(
        ci_df, left_on=["country", "date"], right_on=["country", "year"], how="left"
    ).drop(columns=["year"], errors="ignore")

    rows_written = 0

    # ── Baseline anchor rows (one per country) ─────────────────────────────
    for country in df_clean["country"].unique():
        baseline_row = df_clean[df_clean["country"] == country].iloc[-1]
        baseline_gdp = float(baseline_row["gdp_per_capita"])
        baseline_yr  = int(baseline_row["date"])

        _upsert_prediction(
            session       = session,
            country_code  = country,
            year          = baseline_yr,
            predicted_gdp = baseline_gdp,
            ci_lower      = None,
            ci_upper      = None,
            model_version = model_version,
            is_baseline   = True,
        )
        rows_written += 1

    # ── Forecast rows ──────────────────────────────────────────────────────
    for _, row in merged.iterrows():
        _upsert_prediction(
            session       = session,
            country_code  = str(row["country"]),
            year          = int(row["date"]),
            predicted_gdp = float(row["predicted_gdp_per_capita"]),
            ci_lower      = float(row["ci_80_lower"]) if pd.notna(row.get("ci_80_lower")) else None,
            ci_upper      = float(row["ci_80_upper"]) if pd.notna(row.get("ci_80_upper")) else None,
            model_version = model_version,
            is_baseline   = False,
        )
        rows_written += 1

    session.commit()
    logger.info("Persisted %d prediction rows.", rows_written)
    return rows_written


def _upsert_prediction(
    session: Session,
    country_code: str,
    year: int,
    predicted_gdp: float,
    ci_lower: float | None,
    ci_upper: float | None,
    model_version: str,
    is_baseline: bool,
) -> None:
    existing = session.query(ModelPrediction).filter_by(
        country_code  = country_code,
        year          = year,
        model_version = model_version,
    ).first()

    if existing:
        existing.predicted_gdp_per_capita = predicted_gdp
        existing.ci_80_lower              = ci_lower
        existing.ci_80_upper              = ci_upper
        existing.is_baseline              = is_baseline
    else:
        session.add(ModelPrediction(
            country_code             = country_code,
            year                     = year,
            predicted_gdp_per_capita = predicted_gdp,
            ci_80_lower              = ci_lower,
            ci_80_upper              = ci_upper,
            model_version            = model_version,
            is_baseline              = is_baseline,
        ))