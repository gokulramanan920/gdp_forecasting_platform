"""
backend/api/main.py

FastAPI application — API routes only.
Panel dashboard runs as a separate process on port 5006 (see start.sh).
React embeds Panel via: <iframe src="http://localhost:5006/gdp_dashboard">
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.countries import router as countries_router
from api.routes.predictions import router as predictions_router
from api.routes.indicators import router as indicators_router

app = FastAPI(
    title="GDP Forecasting Platform API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(countries_router)
app.include_router(predictions_router)
app.include_router(indicators_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
