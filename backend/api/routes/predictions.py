# backend/api/routes/predictions.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from db.database import get_db

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("")
def get_predictions(
    countries: Optional[str] = Query(None, description="Comma-separated country codes, e.g. US,CN,IN"),
    db: Session = Depends(get_db),
):
    """
    Return GDP per capita timeseries for requested countries.
    Merges historical indicator_data (gdp_per_capita) with model_predictions.
    Each point includes: country_code, year, value, type (historical|projected|baseline), ci_lower, ci_upper.
    """
    # Resolve country filter
    country_filter = ""
    params: dict = {}
    if countries:
        codes = [c.strip().upper() for c in countries.split(",") if c.strip()]
        if codes:
            country_filter = "AND c.country_code = ANY(:codes)"
            params["codes"] = codes

    # ── Historical GDP per capita ──────────────────────────────────────────────
    historical_sql = text(f"""
        SELECT
            id.country_code,
            id.year,
            CAST(id.value AS FLOAT)      AS value,
            'historical'                  AS type,
            NULL::FLOAT                   AS ci_lower,
            NULL::FLOAT                   AS ci_upper
        FROM indicator_data id
        JOIN indicators i ON i.indicator_id = id.indicator_id
        JOIN countries c  ON c.country_code  = id.country_code
        WHERE i.simplified_name = 'gdp_per_capita'
          AND id.is_extrapolated = FALSE
          {country_filter}
        ORDER BY id.country_code, id.year
    """)

    # ── Model predictions (including baseline anchor row) ─────────────────────
    predictions_sql = text(f"""
        SELECT
            mp.country_code,
            mp.year,
            CAST(mp.predicted_gdp_per_capita AS FLOAT) AS value,
            CASE WHEN mp.is_baseline THEN 'baseline' ELSE 'projected' END AS type,
            CAST(mp.ci_80_lower AS FLOAT) AS ci_lower,
            CAST(mp.ci_80_upper AS FLOAT) AS ci_upper
        FROM model_predictions mp
        JOIN countries c ON c.country_code = mp.country_code
        WHERE 1=1
          {country_filter}
        ORDER BY mp.country_code, mp.year
    """)

    hist_rows = db.execute(historical_sql, params).fetchall()
    pred_rows = db.execute(predictions_sql, params).fetchall()

    def row_to_dict(r):
        return {
            "country_code": r.country_code,
            "year": r.year,
            "value": r.value,
            "type": r.type,
            "ci_lower": r.ci_lower,
            "ci_upper": r.ci_upper,
        }

    return {
        "historical": [row_to_dict(r) for r in hist_rows],
        "predictions": [row_to_dict(r) for r in pred_rows],
    }


@router.get("/countries-meta")
def get_prediction_countries_meta(db: Session = Depends(get_db)):
    """Return distinct countries that have predictions, with metadata."""
    rows = db.execute(
        text("""
            SELECT DISTINCT c.country_code, c.country_name, c.continent, c.region, c.economy_type
            FROM model_predictions mp
            JOIN countries c ON c.country_code = mp.country_code
            ORDER BY c.country_name
        """)
    ).fetchall()
    return [
        {
            "country_code": r.country_code,
            "country_name": r.country_name,
            "continent": r.continent,
            "region": r.region,
            "economy_type": r.economy_type,
        }
        for r in rows
    ]
