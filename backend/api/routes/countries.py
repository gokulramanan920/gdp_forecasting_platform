# backend/api/routes/countries.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from db.database import get_db

router = APIRouter(prefix="/api/countries", tags=["countries"])


@router.get("")
def get_countries(db: Session = Depends(get_db)):
    """Return all countries with metadata."""
    rows = db.execute(
        text("""
            SELECT country_code, country_name, continent, region, economy_type
            FROM countries
            ORDER BY country_name
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
