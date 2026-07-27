"""
Gokul Ramanan
03/15/2026

ML Training — Clustering
K-Means cohort assignment + baseline growth rate calibration.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from db.models.schemas import Country
from ml.constants import N_CLUSTERS, TARGET_COL

logger = logging.getLogger(__name__)


# ── K-Means cohort assignment ─────────────────────────────────────────────────

def assign_cohorts_kmeans(
    df: pd.DataFrame,
    base_year: int | None = None,
    n_clusters: int = N_CLUSTERS,
) -> tuple[list[str], list[str], dict]:
    """
    Cluster countries into developed / emerging using:
      - GDP per capita level   (base year)
      - 5-year CAGR            (growth momentum)
      - GDP volatility         (std of annual growth rates)

    Returns (developed_countries, emerging_countries, cluster_info).
    """
    if base_year is None:
        base_year = df["date"].max()

    logger.info("Clustering %d countries on %d data…", df["country"].nunique(), base_year)

    clustering_features, countries_list = [], []

    for country in df["country"].unique():
        cd = df[df["country"] == country].sort_values("date")

        base_row = cd[cd["date"] == base_year]
        if base_row.empty:
            continue
        gdp_level = base_row[TARGET_COL].values[0]

        recent = cd[cd["date"] >= (base_year - 5)]
        if len(recent) >= 2:
            first, last = recent[TARGET_COL].iloc[0], recent[TARGET_COL].iloc[-1]
            span = recent["date"].iloc[-1] - recent["date"].iloc[0]
            growth_rate = ((last / first) ** (1 / span) - 1) * 100 if span > 0 and first > 0 else 0.0
        else:
            growth_rate = 0.0

        volatility = (cd[TARGET_COL].pct_change() * 100).std()

        clustering_features.append([gdp_level, growth_rate, volatility])
        countries_list.append(country)

    X = np.array(clustering_features)
    X_scaled = StandardScaler().fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    cluster_df = pd.DataFrame({
        "country":     countries_list,
        "gdp_level":   X[:, 0],
        "growth_rate": X[:, 1],
        "volatility":  X[:, 2],
        "cluster":     labels,
    })

    # Identify developed cluster by highest avg GDP
    avg_gdp = cluster_df.groupby("cluster")["gdp_level"].mean()
    developed_id = avg_gdp.idxmax()
    emerging_id  = 1 - developed_id

    developed_countries = cluster_df[cluster_df["cluster"] == developed_id]["country"].tolist()
    emerging_countries  = cluster_df[cluster_df["cluster"] == emerging_id]["country"].tolist()

    # Hard floor: any country below this GDP threshold is always emerging,
    # regardless of where K-Means draws the boundary (prevents China/India
    # from landing in the developed cluster when their feature vector sits near the boundary).
    GDP_EMERGING_CEILING = 20_000
    base_gdp = {
        row["country"]: row[TARGET_COL]
        for _, row in df[df["date"] == base_year][["country", TARGET_COL]].iterrows()
    }
    misclassified = [c for c in developed_countries if base_gdp.get(c, 0) < GDP_EMERGING_CEILING]
    if misclassified:
        logger.warning("K-Means overridden — moving %s to emerging (GDP below $20k)", misclassified)
        developed_countries = [c for c in developed_countries if c not in misclassified]
        emerging_countries  = emerging_countries + misclassified

    _log_cluster_results(cluster_df, developed_id, emerging_id)

    return developed_countries, emerging_countries, {
        "base_year":           base_year,
        "method":              "kmeans",
        "n_clusters":          n_clusters,
        "cluster_df":          cluster_df,
        "developed_cluster_id": developed_id,
        "emerging_cluster_id":  emerging_id,
    }


def _log_cluster_results(cluster_df: pd.DataFrame, developed_id: int, emerging_id: int) -> None:
    for label, cid in [("DEVELOPED", developed_id), ("EMERGING", emerging_id)]:
        subset = cluster_df[cluster_df["cluster"] == cid].sort_values("gdp_level", ascending=False)
        logger.info(
            "%s (%d countries): %s",
            label, len(subset), subset["country"].tolist(),
        )


# ── Baseline growth rate calibration ─────────────────────────────────────────

def calibrate_cluster_baselines(
    training_data: pd.DataFrame,
    developed_countries: list[str],
    emerging_countries: list[str],
    start_year: int = 1991,
    end_year: int | None = None,   # defaults to last real GDP year in the data
) -> dict[str, float]:
    if end_year is None:
        end_year = int(training_data[training_data[TARGET_COL].notna()]["date"].max())
    """
    Computes the winsorized long-run mean annual GDP per capita growth
    for each cluster from actual training data.

    Drop the returned dict directly into CLUSTER_BASELINE_ANNUAL_GROWTH
    in constants.py after each retrain.
    """
    historical = training_data[
        training_data["date"].between(start_year, end_year)
    ].copy()

    historical["annual_growth"] = (
        historical.groupby("country")[TARGET_COL].pct_change()
    )
    historical = historical.dropna(subset=["annual_growth"])

    def winsorized_mean(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> float:
        lo, hi = series.quantile(lower), series.quantile(upper)
        return float(series.clip(lo, hi).mean())

    baselines = {
        "developed": round(winsorized_mean(
            historical[historical["country"].isin(developed_countries)]["annual_growth"]
        ), 4),
        "emerging": round(winsorized_mean(
            historical[historical["country"].isin(emerging_countries)]["annual_growth"]
        ), 4),
    }

    logger.info(
        "Calibrated baselines — developed: %.2f%%  emerging: %.2f%%",
        baselines["developed"] * 100, baselines["emerging"] * 100,
    )
    return baselines


# ── Persist economy_type to DB ────────────────────────────────────────────────

def persist_economy_types(
    developed_countries: list[str],
    emerging_countries: list[str],
    session: Session,
) -> None:
    """
    Write the 'developed' / 'emerging' label back to the countries table.
    """
    for code in developed_countries:
        country = session.query(Country).filter_by(country_code=code).first()
        if country:
            country.economy_type = "developed"

    for code in emerging_countries:
        country = session.query(Country).filter_by(country_code=code).first()
        if country:
            country.economy_type = "emerging"

    session.commit()
    logger.info("Persisted economy_type for %d countries.", len(developed_countries) + len(emerging_countries))