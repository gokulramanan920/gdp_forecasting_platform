# backend/api/routes/indicators.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from db.database import get_db

router = APIRouter(prefix="/api/indicators", tags=["indicators"])

CURATED = ['total_population', 'life_expectancy', 'unemployment_rate', 'inflation_rate', 'fdi_inflows_pct', 'urban_population_pct']


@router.get("/snapshot")
def get_indicator_snapshot(
    countries: Optional[str] = Query(None, description="Comma-separated country codes"),
    years: Optional[str] = Query(None, description="Comma-separated years"),
    db: Session = Depends(get_db),
):
    """
    Return the 5 curated indicator values for each (country, year) combination.

    Query params produce a cross product (countries × years), so the frontend
    must filter the response down to only the exact (country_code, year) pairs
    it actually selected before rendering.
    """
    if not countries or not years:
        return []

    codes = [c.strip().upper() for c in countries.split(',') if c.strip()]
    year_list = [int(y.strip()) for y in years.split(',') if y.strip().isdigit()]
    if not codes or not year_list:
        return []

    rows = db.execute(
        text("""
            SELECT
                id.country_code,
                id.year,
                i.simplified_name,
                CAST(id.value AS FLOAT) AS value
            FROM indicator_data id
            JOIN indicators i ON i.indicator_id = id.indicator_id
            WHERE i.simplified_name = ANY(:indicators)
              AND id.country_code = ANY(:codes)
              AND id.year = ANY(:years)
              AND id.is_extrapolated = FALSE
            ORDER BY id.country_code, id.year
        """),
        {
            "indicators": CURATED,
            "codes": codes,
            "years": year_list,
        }
    ).fetchall()

    # Pivot: (country_code, year) → {indicator: value}
    pivot: dict[tuple, dict] = {}
    for r in rows:
        key = (r.country_code, r.year)
        if key not in pivot:
            pivot[key] = {"country_code": r.country_code, "year": r.year}
        pivot[key][r.simplified_name] = r.value

    # Fill missing indicators with None
    result = []
    for (code, year), entry in pivot.items():
        for ind in CURATED:
            entry.setdefault(ind, None)
        result.append(entry)

    return result
