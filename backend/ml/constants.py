"""
Gokul Ramanan
03/15/2026

ML constants for the GDP forecasting pipeline.
All cluster-specific tuning parameters live here.
Update CLUSTER_BASELINE_ANNUAL_GROWTH after each retrain
using the output of calibrate_cluster_baselines().
"""

FEATURE_COLS = [
    "date",
    "population_density",
    "trade_pct_gdp",
    "infant_mortality",
    "life_expectancy",
    "age_dependency_ratio",
    "agricultural_land_pct_total",
    "oil_rents_pct_gdp",
    "fuel_exports_pct",
    "natural_resource_rents_pct",
    "fertility_rate",
    "urban_population_pct",
    "total_population",
    "patent_applications",
    "unemployment_rate",
    "gross_savings_pct",
    "mobile_subscriptions",
    "gross_capital_form_pct",
    "inflation_rate",
    "fdi_inflows_pct",
]

FEATURE_COLS_WITH_COUNTRY = ["country"] + FEATURE_COLS

TARGET_COL = "gdp_per_capita"

TRAIN_START_YEAR = 1991

# ── K-Means clustering ──────────────────────────────────────────────────────────

N_CLUSTERS = 2

# ── CatBoost / XGBoost hyperparameters ───────────────────────────────────────

CB_PARAMS = dict(
    iterations=100,
    depth=5,
    learning_rate=0.1,
    cat_features=["country"],
    subsample=0.8,
    l2_leaf_reg=3,
    random_seed=42,
    verbose=False,
)

XGB_PARAMS = dict(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    tree_method="auto",
    enable_categorical=False,
)

ENSEMBLE_CB_WEIGHT  = 0.5
ENSEMBLE_XGB_WEIGHT = 0.5

# ── Dampening ─────────────────────────────────────────────────────────────────

DAMP_DEVELOPED = 0.96
DAMP_EMERGING  = 0.93

# ── Mean-reversion & blending ─────────────────────────────────────────────────

CLUSTER_BOUNDS = {
    "developed": {"min_3yr": -0.06, "max_3yr": 0.12},
    "emerging":  {"min_3yr": -0.08, "max_3yr": 0.70},
}

# Per-year growth bounds applied sequentially after blending
# Each forecast year is clipped relative to the prior year's prediction,
# not the baseline — prevents runaway spikes in later forecast years.
YOY_GROWTH_BOUNDS = {
    "developed": {"min": -0.05, "max": 0.08},
    "emerging":  {"min": -0.06, "max": 0.12},
}

REVERSION_SPEED = {
    "developed": 0.45,
    "emerging":  0.20,
}

MODEL_SIGNAL_ALPHA = {
    "developed": 0.30,
    "emerging":  0.30,
}

# Updated by calibrate_cluster_baselines() after each retrain
CLUSTER_BASELINE_ANNUAL_GROWTH = {
    "developed": 0.0324,
    "emerging":  0.0701,
}

# ── Feature-specific extrapolation windows & dampening ───────────────────────
# trend_start offsets are relative to TRAIN_END_YEAR (resolved at runtime).
# e.g. offset=-24 means trend_start = TRAIN_END_YEAR - 24
# None dampening → use cluster base dampening

FEATURE_EXTRAPOLATION_CONFIG = {
    "life_expectancy":            {"trend_offset": -24, "dampening": None},
    "infant_mortality":           {"trend_offset": -24, "dampening": None},
    "fertility_rate":             {"trend_offset": -25, "dampening": None},
    "age_dependency_ratio":       {"trend_offset": -25, "dampening": None},
    "urban_population_pct":       {"trend_offset": -25, "dampening": None},
    "inflation_rate":             {"trend_offset":  -5, "dampening": 0.90},
    "unemployment_rate":          {"trend_offset":  -5, "dampening": 0.90},
    "trade_pct_gdp":              {"trend_offset": -14, "dampening": None},
    "fdi_inflows_pct":            {"trend_offset": -14, "dampening": None},
    "natural_resource_rents_pct": {"trend_offset": -14, "dampening": 0.85},
    "oil_rents_pct_gdp":          {"trend_offset": -14, "dampening": 0.85},
    "fuel_exports_pct":           {"trend_offset": -14, "dampening": 0.85},
    "patent_applications":        {"trend_offset": -19, "dampening": None},
    "mobile_subscriptions":       {"trend_offset": -19, "dampening": None},
}

# Default config for any feature not listed above
# trend_offset = TRAIN_END_YEAR - 14
FEATURE_DEFAULT_CONFIG = {"trend_offset": -14, "dampening": None}

# Plateau thresholds — if |slope| < threshold for developed countries, use persistence
PLATEAU_THRESHOLDS = {
    "life_expectancy":     0.15,
    "urban_population_pct": 0.20,
    "fertility_rate":      0.01,
}

# Hard bounds applied after extrapolation
FEATURE_BOUNDS = {
    "life_expectancy":           (50, 90),
    "infant_mortality":          (0.5, None),
    "natural_resource_rents_pct":(0, 50),
    "oil_rents_pct_gdp":         (0, 50),
    "inflation_rate":            (-5, 25),
    "urban_population_pct":      (0, 100),
    "fertility_rate":            (0.8, 7.0),
    "trade_pct_gdp":             (0, 200),
}

# ── Confidence interval ───────────────────────────────────────────────────────
CI_LOOKBACK_YEARS = 10
CI_MIN_SAMPLES    = 5      # minimum error samples required

COUNTRY_BATCH_SIZE   = 2
INDICATOR_BATCH_SIZE = 2

# wbdata returns full country names in the DataFrame — map back to 2-letter
# codes that match the country_code primary key in the countries table
WBDATA_NAME_TO_CODE = {
    "Australia":          "AU",
    "Brazil":             "BR",
    "Canada":             "CA",
    "China":              "CN",
    "France":             "FR",
    "Germany":            "DE",
    "India":              "IN",
    "Indonesia":          "ID",
    "Italy":              "IT",
    "Japan":              "JP",
    "Korea, Rep.":        "KR",
    "Mexico":             "MX",
    "Netherlands":        "NL",
    "Russian Federation": "RU",
    "Saudi Arabia":       "SA",
    "Spain":              "ES",
    "Switzerland":        "CH",
    "Turkiye":            "TR",
    "United Kingdom":     "GB",
    "United States":      "US",
}