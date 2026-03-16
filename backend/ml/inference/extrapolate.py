"""
ML Inference — Feature Extrapolation
Mean-reverting extrapolation with cluster-specific floors.
"""

import logging

import numpy as np
import pandas as pd
from scipy import stats

from ml.constants import (
    CLUSTER_BASELINE_ANNUAL_GROWTH,
    CLUSTER_BOUNDS,
    DAMP_DEVELOPED,
    DAMP_EMERGING,
    DAMP_OVERRIDES,
    FEATURE_BOUNDS,
    FEATURE_DEFAULT_CONFIG,
    FEATURE_EXTRAPOLATION_CONFIG,
    MODEL_SIGNAL_ALPHA,
    PLATEAU_THRESHOLDS,
    REVERSION_SPEED,
)

logger = logging.getLogger(__name__)


# ── Mean-reverting extrapolation ──────────────────────────────────────────────

def extrapolate_features_mean_reverting(
    data: pd.DataFrame,
    country_name: str,
    feature_cols: list[str],
    future_years: list[int],
    developed_countries: list[str],
    emerging_countries: list[str],
    train_end_year: int,           # resolved dynamically by pipeline
) -> pd.DataFrame | None:
    """
    Project each feature forward using a mean-reverting slope, where the
    recent (5-year) slope is gradually pulled back toward the long-run slope.

    Returns a DataFrame with one row per future year, or None if no data exists.
    """
    country_data = data[data["country"] == country_name].copy()
    if country_data.empty:
        logger.warning("No data found for %s — skipping.", country_name)
        return None

    # Cluster + dampening setup
    if country_name in developed_countries:
        base_dampening = DAMP_OVERRIDES.get(country_name, DAMP_DEVELOPED)
        cohort         = "developed"
        is_developed   = True
    else:
        base_dampening = DAMP_OVERRIDES.get(country_name, DAMP_EMERGING)
        cohort         = "emerging"
        is_developed   = False

    reversion_speed = REVERSION_SPEED[cohort]
    future_data     = []

    for year in future_years:
        year_features = {"country": country_name, "date": year, "cohort": cohort}

        for feature in feature_cols:
            if feature == "date":
                year_features[feature] = year
                continue
            if feature == "country":
                year_features[feature] = country_name
                continue

            cfg              = FEATURE_EXTRAPOLATION_CONFIG.get(feature, FEATURE_DEFAULT_CONFIG)
            trend_start      = train_end_year + cfg["trend_offset"]
            dampening_factor = cfg["dampening"] if cfg["dampening"] is not None else base_dampening

            feature_values = (
                country_data[country_data["date"] >= trend_start][["date", feature]]
                .dropna()
            )

            if len(feature_values) < 3:
                year_features[feature] = feature_values[feature].iloc[-1] if not feature_values.empty else 0
                continue

            try:
                year_features[feature] = _project_feature(
                    feature_values  = feature_values,
                    feature         = feature,
                    year            = year,
                    is_developed    = is_developed,
                    reversion_speed = reversion_speed,
                    dampening_factor = dampening_factor,
                )
            except Exception as exc:
                logger.debug("Extrapolation failed for %s/%s: %s", country_name, feature, exc)
                year_features[feature] = feature_values[feature].iloc[-1]

        future_data.append(year_features)

    return pd.DataFrame(future_data)


def _project_feature(
    feature_values: pd.DataFrame,
    feature: str,
    year: int,
    is_developed: bool,
    reversion_speed: float,
    dampening_factor: float,
) -> float:
    # Recent slope (last 5 years)
    max_year     = feature_values["date"].max()
    recent_window = feature_values[feature_values["date"] >= max_year - 5]
    window        = recent_window if len(recent_window) >= 2 else feature_values
    recent_slope, *_ = stats.linregress(window["date"], window[feature])

    # Long-run slope (full window)
    longrun_slope, *_ = stats.linregress(feature_values["date"], feature_values[feature])

    last_value  = feature_values[feature].iloc[-1]
    last_year   = feature_values["date"].iloc[-1]
    years_ahead = year - last_year

    # Plateau check for developed countries
    if is_developed:
        threshold = PLATEAU_THRESHOLDS.get(feature)
        if threshold and abs(recent_slope) < threshold:
            return float(last_value)

    # Mean-reverting slope projection
    current_slope   = recent_slope
    projected_value = last_value

    for t in range(1, years_ahead + 1):
        current_slope   = current_slope + reversion_speed * (longrun_slope - current_slope)
        dampened_slope  = current_slope * (dampening_factor ** t)
        projected_value = last_value + dampened_slope * t

    return _apply_bounds(feature, float(projected_value))


def _apply_bounds(feature: str, value: float) -> float:
    bounds = FEATURE_BOUNDS.get(feature)
    if bounds is None:
        return value
    lo, hi = bounds
    if lo is not None:
        value = max(value, lo)
    if hi is not None:
        value = min(value, hi)
    return value


# ── Cluster baseline GDP helper ───────────────────────────────────────────────

def compute_cluster_baseline_gdp(cohort: str, horizon_years: int) -> float:
    """
    Compound the long-run mean annual growth rate over the forecast horizon.
    Returns fractional total growth (e.g. 0.078 for 7.8%).
    """
    annual_growth = CLUSTER_BASELINE_ANNUAL_GROWTH[cohort]
    return (1 + annual_growth) ** horizon_years - 1


# ── Model-as-signal blending ──────────────────────────────────────────────────

def blend_model_with_baseline(
    raw_model_pred: float,
    baseline_gdp: float,
    cohort: str,
    horizon_years: int,
) -> float:
    """
    Blends the raw model output (treated as a directional signal) with the
    cluster's long-run baseline growth, then hard-clamps to historical bounds.

    blended_growth = alpha * model_growth + (1 - alpha) * baseline_growth
    final_pred     = baseline_gdp * (1 + blended_growth)
    """
    alpha           = MODEL_SIGNAL_ALPHA[cohort]
    baseline_growth = compute_cluster_baseline_gdp(cohort, horizon_years)
    model_growth    = (raw_model_pred - baseline_gdp) / baseline_gdp

    blended_growth  = alpha * model_growth + (1 - alpha) * baseline_growth

    bounds         = CLUSTER_BOUNDS[cohort]
    blended_growth = float(np.clip(blended_growth, bounds["min_3yr"], bounds["max_3yr"]))

    return baseline_gdp * (1 + blended_growth)