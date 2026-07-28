# GDP Forecasting Platform

A full-stack platform that forecasts GDP per capita trajectories for 20 countries through 2029 using an ensemble ML model trained on 35 years of World Bank data.

---

## Overview

The platform combines a CatBoost + XGBoost ensemble model with a React/Plotly interactive dashboard, a FastAPI backend, and a PostgreSQL database with TimescaleDB. Users can explore historical GDP per capita, compare ML projections with 90% confidence intervals, and drill into economic indicators for any subset of country-years via a lasso-select datatable.

---

## Features

- **GDP Trajectory Dashboard** — Interactive Plotly charts for 20 countries (1991–2029). Lasso or box-select any set of points to surface a datatable showing GDP per capita, 3-year rolling CAGR, population, unemployment, inflation, FDI, and more. Filter by continent, region, economy type, and year range.
- **Ensemble ML Model (EnsembleCBXGB)** — CatBoost 50% + XGBoost 50%, trained with 4-fold time-series cross-validation on 1991–2022 data. Holdout evaluation on 2023–2025 yields R² 0.934 and 10.6% MAPE.
- **19 World Bank Indicators** — Trade, FDI, inflation, unemployment, demographics, energy, capital formation, and more used as input features to predict GDP per capita (the 20th variable).
- **Cluster-Aware Forecasting** — K-Means (k=2) clusters countries into developed/emerging cohorts; projections blend ensemble output with cluster-level baselines to prevent runaway forecasts.
- **Growth Analysis Panel** — CAGR bar chart (3yr / 5yr / 10yr) for selected countries, rendered as a toggleable sub-panel below the main chart.
- **Automated Pipeline** — GitHub Actions cron job runs on the 1st of every month: fetches fresh World Bank data, retrains the ensemble, and upserts new predictions into the database. Manual dispatch available via the Actions tab.

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | React 18, Vite, TailwindCSS v4, Plotly.js, Zustand |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Database | PostgreSQL + TimescaleDB + pgvector |
| ML | CatBoost, XGBoost, scikit-learn, pandas, numpy |
| CI/CD | GitHub Actions |
| Data Source | World Bank Open Data API |

---

## Project Structure

```
gdp_forecasting_platform/
├── backend/
│   ├── api/          # FastAPI routes (countries, predictions, indicators)
│   ├── db/           # SQLAlchemy models and session management
│   ├── etl/          # World Bank data ingestion pipeline
│   ├── ml/           # EnsembleCBXGB model, training, inference
│   ├── alembic/      # Database migrations (7-table schema)
│   └── pipeline.py   # Bulk ETL + prediction pipeline entry point
├── frontend/
│   ├── src/
│   │   ├── components/dashboard/   # GDPChart, FilterSidebar, GrowthSubPanel, SelectedPointsTable
│   │   ├── pages/                  # Home, Dashboard, Model, About
│   │   ├── store/                  # Zustand dashboard store
│   │   └── utils/                  # Plotly factory, chart utilities
│   └── vite.config.js
├── notebooks/        # Exploratory analysis and model development
├── requirements.txt
└── start.sh          # Starts both FastAPI and Vite dev server
```

---

## ML Pipeline

1. **ETL** — Fetch 19 indicators × 20 countries from World Bank API
2. **Impute** — Linear interpolation + forward/backward fill for missing values
3. **Cluster** — K-Means on GDP level, 5yr CAGR, and volatility to assign country cohort
4. **Train** — 4-fold time-series CV + holdout evaluation (2023–2025)
5. **Extrapolate** — Mean-reverting feature projection 4 years forward
6. **Predict** — Ensemble inference blended with cluster baseline
7. **Store** — Upsert predictions and 90% CIs into PostgreSQL

---

## Database Schema (7 tables)

- `countries` — Country metadata (name, continent, region, economy type)
- `indicators_static` — World Bank indicator definitions
- `historical_gdp` — GDP per capita (1991–2025)
- `indicator_values` — All 19 indicator time series per country
- `ml_predictions` — Projected GDP per capita (2026–2029) with CI bounds
- `model_metadata` — Training run metadata and performance metrics
- `news_events` *(planned)* — GDELT news embeddings for RAG pipeline

---

## Getting Started

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
cd backend && alembic upgrade head

# Run ETL + ML pipeline to populate the database
python backend/pipeline.py

# Start the platform (FastAPI + Vite)
bash start.sh
```

Frontend runs at `http://localhost:5173`, API at `http://localhost:8000`.

---

## Model Performance

| Metric | Value |
|--------|-------|
| R² (holdout 2023–2025) | 0.934 |
| MAPE | 10.6% |

| Out-of-sample period | 3 years |
| Training window | 1991–2022 (expanding CV) |

---

## Deployment

**Live:** [gdp-forecasting-platform.vercel.app](https://gdp-forecasting-platform.vercel.app)

| Service | Provider | Role |
|---------|----------|------|
| Frontend | Vercel | Serves the React app; auto-deploys on push to `main` |
| Backend API | Render | Hosts the FastAPI server (Python 3.11 Web Service) |
| Database | Neon | Serverless PostgreSQL 17 with pgvector extension |

**Routing:** Vercel rewrites `/api/*` requests to the Render backend, so the frontend and API share a single origin and no CORS configuration is needed on the client.

**CI/CD Pipeline (GitHub Actions)**

The pipeline runs the full ETL → cluster → train → predict → persist cycle automatically on the 1st of every month at 06:00 UTC. A manual "Run workflow" button is available in the Actions tab for on-demand runs.

```
ETL (World Bank API fetch + imputation + DB upsert)
  → K-Means cohort clustering
  → EnsembleCBXGB retrain (4-fold CV + holdout eval)
  → Model version persisted to model_versions table
  → Predictions + 90% CIs upserted to model_predictions table
```

The pipeline uses `requirements.txt` (full ML stack) rather than the slim `requirements-api.txt` used by Render.

---

## Roadmap

- **Phase 3** — GDELT news pipeline, pgvector embeddings, semantic search by country and topic
- **Phase 4** — Gemini-powered scenario agent: modify indicators, re-run inference, see projected impact
- **Phase 5** — Google OAuth, user-saved views, human-in-the-loop model tuning advisor
- **Phase 6** — Dockerize, deploy to GCP Cloud Run + Cloud SQL

---

## Creator

**Gokul Ramanan** — Northeastern University

- Email: [ramanan.g@northeastern.edu](mailto:ramanan.g@northeastern.edu)
- LinkedIn: [linkedin.com/in/gokul-venkat-ramanan](https://www.linkedin.com/in/gokul-venkat-ramanan/)
- GitHub: [github.com/gokulramanan920](https://github.com/gokulramanan920)
