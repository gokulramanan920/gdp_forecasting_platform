"""
ETL — Ingest + Clean (consolidated)
1. Fetch raw data from World Bank API
2. Impute missing values
3. Determine is_extrapolated per (country, indicator, year)
4. Promote clean records to indicator_data
"""

import logging

import numpy as np
import pandas as pd
import wbdata as wb
from sqlalchemy.orm import Session
from sqlalchemy import text

from db.models.schemas import IndicatorData, Indicator, Country
from ml.constants import FEATURE_COLS_WITH_COUNTRY, TARGET_COL, TRAIN_START_YEAR, COUNTRY_BATCH_SIZE, INDICATOR_BATCH_SIZE, WBDATA_NAME_TO_CODE

logger = logging.getLogger(__name__)

# ── Helpers: load from DB ─────────────────────────────────────────────────────

def get_countries_from_db(session: Session) -> list[str]:
    """Load country codes from the countries table."""
    return [c.country_code for c in session.query(Country).all()]


def get_indicators_from_db(session: Session) -> dict[str, str]:
    """Load indicator_code → simplified_name mapping from the indicators table."""
    return {
        i.indicator_code: i.simplified_name
        for i in session.query(Indicator).all()
    }


# ── Stage 1: Fetch from World Bank API ───────────────────────────────────────

def fetch_world_bank_data(
    countries: list[str],
    indicators: dict[str, str],
    year_start: int,
    year_end: int,
) -> pd.DataFrame:
    """
    Batch-fetch from World Bank API.
    Returns a wide DataFrame: columns = [country, date, <indicator_names...>]
    """
    country_batches   = [countries[i:i + COUNTRY_BATCH_SIZE]
                         for i in range(0, len(countries), COUNTRY_BATCH_SIZE)]
    indicator_items   = list(indicators.items())
    indicator_batches = [dict(indicator_items[i:i + INDICATOR_BATCH_SIZE])
                         for i in range(0, len(indicator_items), INDICATOR_BATCH_SIZE)]

    all_dfs = []
    for c_batch in country_batches:
        batch_dfs = []
        for i_batch in indicator_batches:
            try:
                df = wb.get_dataframe(i_batch, country=c_batch).reset_index()
                batch_dfs.append(df)
            except Exception as exc:
                logger.warning("Fetch failed — countries=%s indicators=%s: %s",
                               c_batch, list(i_batch.keys()), exc)
                continue

        if not batch_dfs:
            continue

        merged = batch_dfs[0]
        for df in batch_dfs[1:]:
            merged = merged.merge(df, on=["country", "date"], how="outer")
        all_dfs.append(merged)

    if not all_dfs:
        raise RuntimeError("No data returned from World Bank API.")

    data = pd.concat(all_dfs, ignore_index=True)
    data["date"] = data["date"].astype(int)
    data = (data[(data["date"] >= year_start) & (data["date"] <= year_end)]
            .sort_values(["country", "date"])
            .reset_index(drop=True))

    # Map full country names → 2-letter codes to match countries.country_code
    unmapped = set(data["country"].unique()) - set(WBDATA_NAME_TO_CODE.keys())
    if unmapped:
        logger.warning("Unmapped country names from wbdata: %s", unmapped)
    data["country"] = data["country"].map(WBDATA_NAME_TO_CODE).fillna(data["country"])

    logger.info("Fetched %d rows for %d countries.", len(data), data["country"].nunique())
    return data


# ── Stage 2: Smart imputation ─────────────────────────────────────────────────

def clean_and_impute(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """
    1. Trim each country to its last valid GDP year
    2. Linear interpolation within each country
    3. Forward / backward fill for edge cases
    4. Drop unfillable rows
    5. Remove inf values
    """
    # Step 1 — trim
    valid_rows = []
    for country in df["country"].unique():
        cd = df[df["country"] == country].copy().sort_values("date")
        last_gdp_yr = cd[cd[TARGET_COL].notna()]["date"].max()
        if pd.notna(last_gdp_yr):
            valid_rows.append(cd[cd["date"] <= last_gdp_yr])

    df_trimmed = pd.concat(valid_rows, ignore_index=True).sort_values(["country", "date"])

    numeric_cols = [c for c in feature_cols if c not in ("date", "country")]

    # Step 2 — interpolate
    for col in numeric_cols:
        df_trimmed[col] = df_trimmed.groupby("country")[col].transform(
            lambda x: x.interpolate(method="linear", limit_direction="both")
        )

    # Step 3 — fill edges
    for col in numeric_cols:
        df_trimmed[col] = df_trimmed.groupby("country")[col].ffill()
        df_trimmed[col] = df_trimmed.groupby("country")[col].bfill()

    # Step 4 — drop still-missing
    df_clean = df_trimmed.dropna(subset=numeric_cols + [TARGET_COL])

    # Step 5 — remove inf
    for col in df_clean.select_dtypes(include=[np.number]).columns:
        if np.isinf(df_clean[col]).any():
            df_clean = df_clean[~np.isinf(df_clean[col])]

    logger.info("Imputation: %d → %d rows (%.1f%% retained).",
                len(df), len(df_clean), len(df_clean) / len(df) * 100)
    return df_clean.reset_index(drop=True)


# ── Stage 3: is_extrapolated check ───────────────────────────────────────────

def _build_raw_present_set(raw_df: pd.DataFrame) -> set[tuple[str, str, int]]:
    """
    Returns a set of (country_code, indicator_name, year) tuples
    where the World Bank API returned a non-null value.
    Used to flag imputed rows as is_extrapolated=True.
    """
    indicator_cols = [c for c in raw_df.columns if c not in ("country", "date", "country-year")]
    raw_present    = set()

    for _, row in raw_df.iterrows():
        country_code = row["country"]
        year         = int(row["date"])
        for col in indicator_cols:
            if pd.notna(row.get(col)):
                raw_present.add((country_code, col, year))

    return raw_present


def is_value_extrapolated(
    country_code: str,
    indicator_name: str,
    year: int,
    raw_present: set[tuple[str, str, int]],
) -> bool:
    """
    Returns True if this (country, indicator, year) combination was NOT
    present in the raw API response, meaning it was imputed during cleaning.
    """
    return (country_code, indicator_name, year) not in raw_present


# ── Stage 4: Promote to indicator_data ───────────────────────────────────────

def _get_indicator_id_map(session: Session) -> dict[str, int]:
    """Returns simplified_name → indicator_id from the indicators table."""
    return {
        i.simplified_name: i.indicator_id
        for i in session.query(Indicator).all()
    }


def promote_to_indicator_data(
    df_clean: pd.DataFrame,
    raw_df: pd.DataFrame,
    session: Session,
) -> int:
    """
    Upsert cleaned rows into indicator_data.
    Sets is_extrapolated=True for any value that was imputed (not from raw API).
    """
    session.close()  # release connection held idle during World Bank fetch; pool_pre_ping gets a fresh one
    raw_present    = _build_raw_present_set(raw_df)
    indicator_map  = _get_indicator_id_map(session)
    numeric_cols   = [c for c in df_clean.columns if c not in ("country", "date", "country-year")]
    rows_written   = 0

    for _, row in df_clean.iterrows():
        country_code = str(row["country"])
        year         = int(row["date"])

        for col in numeric_cols:
            indicator_id = indicator_map.get(col)
            if indicator_id is None:
                continue

            val = row.get(col)
            if pd.isna(val):
                continue

            extrapolated = is_value_extrapolated(country_code, col, year, raw_present)

            existing = session.query(IndicatorData).filter_by(
                country_code=country_code,
                indicator_id=indicator_id,
                year=year,
            ).first()

            if existing:
                existing.value           = float(val)
                existing.is_extrapolated = extrapolated
            else:
                session.add(IndicatorData(
                    country_code    = country_code,
                    indicator_id    = indicator_id,
                    year            = year,
                    value           = float(val),
                    is_extrapolated = extrapolated,
                    data_source     = "World Bank API",
                ))
            rows_written += 1

    session.commit()
    logger.info("Promoted %d rows to indicator_data.", rows_written)
    return rows_written


# ── Public entry point ────────────────────────────────────────────────────────

def run_etl(session: Session) -> pd.DataFrame:
    """
    Full ETL run:
      1. Load countries + indicators from DB
      2. Fetch from World Bank API
      3. Clean and impute
      4. Promote to indicator_data
      5. Return clean DataFrame for the training pipeline
    """
    countries  = get_countries_from_db(session)
    indicators = get_indicators_from_db(session)

    logger.info("Running ETL for %d countries, %d indicators.", len(countries), len(indicators))

    raw_df   = fetch_world_bank_data(countries, indicators, TRAIN_START_YEAR,
                                     _get_current_year())
    df_clean = clean_and_impute(raw_df, FEATURE_COLS_WITH_COUNTRY)
    promote_to_indicator_data(df_clean, raw_df, session)

    return df_clean


def _get_current_year() -> int:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).year