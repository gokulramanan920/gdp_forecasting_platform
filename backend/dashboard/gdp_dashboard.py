"""
backend/dashboard/gdp_dashboard.py

Panel-based GDP per capita dashboard.
Served at /dashboard by FastAPI via panel.serve().
"""

import sys
import os
from pathlib import Path

# Ensure backend/ is on the path when run standalone or via FastAPI mount
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import param
import panel as pn
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from statsmodels.nonparametric.smoothers_lowess import lowess
from sqlalchemy import text

from db.database import SessionLocal

pn.extension("plotly", sizing_mode="stretch_width", template="fast")


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Country metadata (loaded once at startup) ─────────────────────────────────
def _load_country_meta() -> pd.DataFrame:
    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT DISTINCT c.country_code, c.country_name, c.continent,
                       c.region, c.economy_type
                FROM model_predictions mp
                JOIN countries c ON c.country_code = mp.country_code
                ORDER BY c.country_name
            """)
        ).fetchall()
    return pd.DataFrame(
        [{"country_code": r.country_code, "country_name": r.country_name,
          "continent": r.continent, "region": r.region,
          "economy_type": r.economy_type}
         for r in rows]
    )


COUNTRY_META = _load_country_meta()
ALL_CODES = sorted(COUNTRY_META["country_code"].tolist())
CODE_TO_NAME = dict(zip(COUNTRY_META["country_code"], COUNTRY_META["country_name"]))
NAME_TO_CODE = {v: k for k, v in CODE_TO_NAME.items()}
ALL_NAMES = [CODE_TO_NAME[c] for c in ALL_CODES]

CONTINENTS = ["All"] + sorted(COUNTRY_META["continent"].dropna().unique().tolist())
REGIONS = ["All"] + sorted(COUNTRY_META["region"].dropna().unique().tolist())
ECONOMY_TYPES = ["All", "developed", "emerging"]

# Plotly dark color palette — 20 distinct colors
COUNTRY_COLORS = [
    "#00d4ff", "#ff6b6b", "#51cf66", "#ffd43b", "#cc5de8",
    "#ff922b", "#74c0fc", "#f783ac", "#a9e34b", "#63e6be",
    "#4dabf7", "#e64980", "#40c057", "#fab005", "#ae3ec9",
    "#fd7e14", "#339af0", "#f06595", "#82c91e", "#20c997",
]


# ── Data loader ───────────────────────────────────────────────────────────────
def load_gdp_data(country_codes: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (historical_df, predictions_df) for the given country codes."""
    if not country_codes:
        return pd.DataFrame(), pd.DataFrame()

    with SessionLocal() as db:
        hist = db.execute(
            text("""
                SELECT id.country_code, id.year,
                       CAST(id.value AS FLOAT) AS value
                FROM indicator_data id
                JOIN indicators i ON i.indicator_id = id.indicator_id
                WHERE i.simplified_name = 'gdp_per_capita'
                  AND id.is_extrapolated = FALSE
                  AND id.country_code = ANY(:codes)
                ORDER BY id.country_code, id.year
            """),
            {"codes": country_codes},
        ).fetchall()

        preds = db.execute(
            text("""
                SELECT mp.country_code, mp.year,
                       CAST(mp.predicted_gdp_per_capita AS FLOAT) AS value,
                       CAST(mp.ci_80_lower AS FLOAT) AS ci_lower,
                       CAST(mp.ci_80_upper AS FLOAT) AS ci_upper,
                       mp.is_baseline
                FROM model_predictions mp
                WHERE mp.country_code = ANY(:codes)
                ORDER BY mp.country_code, mp.year
            """),
            {"codes": country_codes},
        ).fetchall()

    hist_df = pd.DataFrame(
        [{"country_code": r.country_code, "year": r.year, "value": r.value}
         for r in hist]
    )
    pred_df = pd.DataFrame(
        [{"country_code": r.country_code, "year": r.year, "value": r.value,
          "ci_lower": r.ci_lower, "ci_upper": r.ci_upper,
          "is_baseline": r.is_baseline}
         for r in preds]
    )
    return hist_df, pred_df


# ── Dashboard class ───────────────────────────────────────────────────────────
class GDPDashboard(param.Parameterized):

    # --- Country / Geography filters
    selected_countries = param.List(default=ALL_NAMES[:5], item_type=str)
    continent_filter = param.ObjectSelector(default="All", objects=CONTINENTS)
    region_filter = param.ObjectSelector(default="All", objects=REGIONS)
    economy_type_filter = param.ObjectSelector(default="All", objects=ECONOMY_TYPES)

    # --- Time & Scale
    year_start = param.Integer(default=1991, bounds=(1991, 2028))
    year_end = param.Integer(default=2028, bounds=(1991, 2028))
    log_scale = param.Boolean(default=False)
    normalize_1991 = param.Boolean(default=False)

    # --- Chart visual
    show_ci = param.Boolean(default=True)
    show_projections = param.Boolean(default=True)
    show_lowess = param.Boolean(default=False)
    show_recession = param.Boolean(default=False)
    color_by = param.ObjectSelector(
        default="country",
        objects=["country", "economy_type", "continent", "region"],
    )
    plotly_theme = param.ObjectSelector(
        default="plotly_dark",
        objects=["plotly_dark", "plotly", "ggplot2", "seaborn", "simple_white"],
    )

    # --- Growth sub-panel
    show_growth_panel = param.Boolean(default=False)
    cagr_period = param.ObjectSelector(default="5yr", objects=["3yr", "5yr", "10yr"])

    def __init__(self, **params):
        super().__init__(**params)
        self._color_cache: dict[str, str] = {}

    def _filtered_countries(self) -> list[str]:
        """Returns country codes after applying geography filters."""
        meta = COUNTRY_META.copy()
        if self.continent_filter != "All":
            meta = meta[meta["continent"] == self.continent_filter]
        if self.region_filter != "All":
            meta = meta[meta["region"] == self.region_filter]
        if self.economy_type_filter != "All":
            meta = meta[meta["economy_type"] == self.economy_type_filter]
        available_names = set(meta["country_name"].tolist())
        selected = [n for n in self.selected_countries if n in available_names]
        return [NAME_TO_CODE[n] for n in selected if n in NAME_TO_CODE]

    def _get_color(self, country_code: str, row: pd.Series, idx: int) -> str:
        key = f"{self.color_by}_{country_code}"
        if key in self._color_cache:
            return self._color_cache[key]

        if self.color_by == "country":
            color = COUNTRY_COLORS[idx % len(COUNTRY_COLORS)]
        elif self.color_by == "economy_type":
            color = "#00d4ff" if row.get("economy_type") == "developed" else "#ff6b6b"
        elif self.color_by == "continent":
            cont_colors = {
                "North America": "#00d4ff", "Europe": "#51cf66",
                "Asia": "#ffd43b", "South America": "#ff6b6b",
                "Africa": "#ff922b", "Oceania": "#cc5de8",
            }
            color = cont_colors.get(row.get("continent", ""), "#aaa")
        elif self.color_by == "region":
            region_idx = REGIONS.index(row.get("region", "All")) if row.get("region") in REGIONS else 0
            color = COUNTRY_COLORS[region_idx % len(COUNTRY_COLORS)]
        else:
            color = COUNTRY_COLORS[idx % len(COUNTRY_COLORS)]

        self._color_cache[key] = color
        return color

    def _compute_cagr(self, hist_df: pd.DataFrame, n_years: int) -> dict[str, float]:
        """Compute n-year CAGR for each country."""
        cagrs = {}
        for code, grp in hist_df.groupby("country_code"):
            grp = grp.sort_values("year")
            if len(grp) < n_years + 1:
                continue
            end_val = grp.iloc[-1]["value"]
            start_val = grp.iloc[-1 - n_years]["value"]
            if start_val and start_val > 0:
                cagrs[code] = (end_val / start_val) ** (1 / n_years) - 1
        return cagrs

    @param.depends(
        "selected_countries", "continent_filter", "region_filter", "economy_type_filter",
        "year_start", "year_end", "log_scale", "normalize_1991",
        "show_ci", "show_projections", "show_lowess", "show_recession",
        "color_by", "plotly_theme", "show_growth_panel", "cagr_period",
    )
    def view(self):
        codes = self._filtered_countries()
        if not codes:
            return pn.pane.Markdown("## No countries selected", styles={"color": "#aaa", "padding": "40px"})

        hist_df, pred_df = load_gdp_data(codes)
        if hist_df.empty:
            return pn.pane.Markdown("## No data found", styles={"color": "#aaa", "padding": "40px"})

        # Apply year range
        hist_df = hist_df[(hist_df["year"] >= self.year_start) & (hist_df["year"] <= self.year_end)]
        pred_df = pred_df[(pred_df["year"] >= self.year_start) & (pred_df["year"] <= self.year_end)]

        # Normalization: rebase to first available year for each country
        if self.normalize_1991:
            for code in codes:
                hm = hist_df["country_code"] == code
                base_rows = hist_df.loc[hm].sort_values("year")
                if base_rows.empty:
                    continue
                base_val = base_rows.iloc[0]["value"]
                if base_val and base_val > 0:
                    hist_df.loc[hm, "value"] = hist_df.loc[hm, "value"] / base_val * 100
                    pm = pred_df["country_code"] == code
                    pred_df.loc[pm, "value"] = pred_df.loc[pm, "value"] / base_val * 100
                    pred_df.loc[pm, "ci_lower"] = pred_df.loc[pm, "ci_lower"] / base_val * 100
                    pred_df.loc[pm, "ci_upper"] = pred_df.loc[pm, "ci_upper"] / base_val * 100

        fig = go.Figure()
        meta_map = COUNTRY_META.set_index("country_code").to_dict("index")

        for idx, code in enumerate(codes):
            name = CODE_TO_NAME.get(code, code)
            meta_row = meta_map.get(code, {})
            color = self._get_color(code, meta_row, idx)

            h = hist_df[hist_df["country_code"] == code].sort_values("year")
            p = pred_df[pred_df["country_code"] == code].sort_values("year")

            # Historical line
            if not h.empty:
                fig.add_trace(go.Scatter(
                    x=h["year"].tolist(),
                    y=h["value"].tolist(),
                    mode="lines",
                    name=name,
                    line=dict(color=color, width=2),
                    legendgroup=name,
                    hovertemplate=(
                        f"<b>{name}</b><br>"
                        "Year: %{x}<br>"
                        "GDP/capita: $%{y:,.0f}<extra></extra>"
                    ),
                ))

                # LOWESS trend
                if self.show_lowess and len(h) >= 5:
                    smoothed = lowess(h["value"].values, h["year"].values, frac=0.4)
                    fig.add_trace(go.Scatter(
                        x=smoothed[:, 0].tolist(),
                        y=smoothed[:, 1].tolist(),
                        mode="lines",
                        name=f"{name} (trend)",
                        line=dict(color=color, width=1.5, dash="dot"),
                        legendgroup=name,
                        showlegend=False,
                        hoverinfo="skip",
                    ))

            # Projections
            if self.show_projections and not p.empty:
                proj = p[~p["is_baseline"]].sort_values("year")
                baseline = p[p["is_baseline"]].sort_values("year")

                # Connect historical → projection via baseline point
                connect_x, connect_y = [], []
                if not h.empty and not baseline.empty:
                    connect_x = [h["year"].iloc[-1], baseline["year"].iloc[0]]
                    connect_y = [h["value"].iloc[-1], baseline["value"].iloc[0]]
                    fig.add_trace(go.Scatter(
                        x=connect_x, y=connect_y,
                        mode="lines",
                        line=dict(color=color, width=2, dash="dash"),
                        legendgroup=name, showlegend=False, hoverinfo="skip",
                    ))

                if not proj.empty:
                    # CI band
                    if self.show_ci:
                        ci_x = proj["year"].tolist() + proj["year"].tolist()[::-1]
                        ci_y = proj["ci_upper"].tolist() + proj["ci_lower"].tolist()[::-1]
                        fig.add_trace(go.Scatter(
                            x=ci_x, y=ci_y,
                            fill="toself",
                            fillcolor=_hex_to_rgba(color, 0.12),
                            line=dict(width=0),
                            legendgroup=name, showlegend=False, hoverinfo="skip",
                            name=f"{name} 80% CI",
                        ))

                    fig.add_trace(go.Scatter(
                        x=proj["year"].tolist(),
                        y=proj["value"].tolist(),
                        mode="lines",
                        name=f"{name} (proj)",
                        line=dict(color=color, width=2, dash="dash"),
                        legendgroup=name, showlegend=False,
                        hovertemplate=(
                            f"<b>{name} (projected)</b><br>"
                            "Year: %{x}<br>"
                            "GDP/capita: $%{y:,.0f}<extra></extra>"
                        ),
                    ))

            # Recession highlight (negative YoY growth)
            if self.show_recession and len(h) >= 2:
                h_sorted = h.sort_values("year")
                h_sorted = h_sorted.assign(yoy=h_sorted["value"].pct_change())
                rec_years = h_sorted[h_sorted["yoy"] < 0]["year"].tolist()
                for ry in rec_years:
                    fig.add_vrect(
                        x0=ry - 0.5, x1=ry + 0.5,
                        fillcolor="rgba(255,100,100,0.08)",
                        line_width=0,
                        layer="below",
                    )

        # Vertical line at forecast start
        if not pred_df.empty:
            baseline_years = pred_df[pred_df["is_baseline"]]["year"]
            if not baseline_years.empty:
                forecast_start = int(baseline_years.min())
                fig.add_vline(
                    x=forecast_start,
                    line_dash="dot",
                    line_color="rgba(200,200,200,0.4)",
                    annotation_text="Forecast →",
                    annotation_position="top right",
                    annotation_font_color="rgba(200,200,200,0.6)",
                )

        y_title = "GDP per Capita (Index, first yr = 100)" if self.normalize_1991 else "GDP per Capita (USD)"
        fig.update_layout(
            template=self.plotly_theme,
            title=dict(text="GDP per Capita Trajectories", font=dict(size=18)),
            xaxis=dict(title="Year", showgrid=True, gridcolor="rgba(255,255,255,0.07)"),
            yaxis=dict(
                title=y_title,
                type="log" if self.log_scale else "linear",
                showgrid=True, gridcolor="rgba(255,255,255,0.07)",
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=60, r=20, t=70, b=50),
            hovermode="x unified",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        main_chart = pn.pane.Plotly(fig, height=520, sizing_mode="stretch_width")

        if self.show_growth_panel:
            growth_chart = self._growth_bar(hist_df, codes)
            return pn.Column(main_chart, growth_chart, sizing_mode="stretch_width")

        return main_chart

    def _growth_bar(self, hist_df: pd.DataFrame, codes: list[str]):
        n = {"3yr": 3, "5yr": 5, "10yr": 10}[self.cagr_period]
        cagrs = self._compute_cagr(hist_df, n)
        if not cagrs:
            return pn.pane.Markdown("*Not enough data for CAGR calculation*")

        sorted_items = sorted(cagrs.items(), key=lambda x: x[1], reverse=True)
        names = [CODE_TO_NAME.get(c, c) for c, _ in sorted_items]
        values = [v * 100 for _, v in sorted_items]
        meta_map = COUNTRY_META.set_index("country_code").to_dict("index")

        colors = []
        for idx, (code, _) in enumerate(sorted_items):
            meta_row = meta_map.get(code, {})
            colors.append(self._get_color(code, meta_row, idx))

        fig = go.Figure(go.Bar(
            x=names, y=values,
            marker_color=colors,
            hovertemplate="%{x}<br>CAGR: %{y:.2f}%<extra></extra>",
        ))
        fig.update_layout(
            template=self.plotly_theme,
            title=f"{self.cagr_period} GDP per Capita CAGR (%)",
            yaxis_title="CAGR (%)",
            margin=dict(l=40, r=20, t=50, b=60),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=280,
        )
        return pn.pane.Plotly(fig, height=280, sizing_mode="stretch_width")

    def sidebar(self):
        header = pn.pane.Markdown(
            "## GDP Forecast\n*1991 – 2028*",
            styles={"color": "#00d4ff", "margin-bottom": "8px"},
        )
        country_select = pn.widgets.MultiSelect.from_param(
            self.param.selected_countries,
            name="Countries",
            options=ALL_NAMES,
            size=8,
        )
        continent_sel = pn.widgets.Select.from_param(self.param.continent_filter, name="Continent")
        region_sel = pn.widgets.Select.from_param(self.param.region_filter, name="Region")
        economy_sel = pn.widgets.Select.from_param(self.param.economy_type_filter, name="Economy Type")

        year_range = pn.widgets.RangeSlider(
            name="Year Range",
            start=1991, end=2028,
            value=(self.year_start, self.year_end),
            step=1,
        )

        def _sync_year_range(event):
            self.year_start = event.new[0]
            self.year_end = event.new[1]

        year_range.param.watch(_sync_year_range, "value")

        toggles = pn.Column(
            pn.widgets.Toggle.from_param(self.param.show_ci, name="Show 80% CI", button_type="primary"),
            pn.widgets.Toggle.from_param(self.param.show_projections, name="Show Projections", button_type="primary"),
            pn.widgets.Toggle.from_param(self.param.show_lowess, name="LOWESS Trend", button_type="default"),
            pn.widgets.Toggle.from_param(self.param.show_recession, name="Recession Highlight", button_type="default"),
            pn.widgets.Toggle.from_param(self.param.log_scale, name="Log Scale", button_type="default"),
            pn.widgets.Toggle.from_param(self.param.normalize_1991, name="Index (1991=100)", button_type="default"),
        )

        color_by_sel = pn.widgets.Select.from_param(self.param.color_by, name="Color By")
        theme_sel = pn.widgets.Select.from_param(self.param.plotly_theme, name="Chart Theme")

        growth_toggle = pn.widgets.Toggle.from_param(
            self.param.show_growth_panel, name="Show Growth Bar Chart", button_type="success"
        )
        cagr_sel = pn.widgets.RadioButtonGroup.from_param(
            self.param.cagr_period, name="CAGR Period"
        )

        return pn.Column(
            header,
            pn.layout.Divider(),
            pn.pane.Markdown("**Countries**"),
            country_select,
            pn.layout.Divider(),
            pn.pane.Markdown("**Geography Filters**"),
            continent_sel, region_sel, economy_sel,
            pn.layout.Divider(),
            pn.pane.Markdown("**Time & Scale**"),
            year_range,
            pn.layout.Divider(),
            pn.pane.Markdown("**Chart Options**"),
            toggles,
            color_by_sel, theme_sel,
            pn.layout.Divider(),
            pn.pane.Markdown("**Growth Analysis**"),
            growth_toggle,
            pn.pane.Markdown("CAGR Period:", styles={"font-size": "12px", "color": "#aaa"}),
            cagr_sel,
            width=260,
            styles={"overflow-y": "auto", "padding": "12px"},
        )


def create_dashboard():
    dashboard = GDPDashboard()

    template = pn.template.FastDarkTemplate(
        title="GDP Forecasting Platform",
        sidebar=[dashboard.sidebar()],
        main=[dashboard.view],
        sidebar_width=280,
        header_background="#0d1117",
        accent_base_color="#00d4ff",
    )
    return template


if __name__ == "__main__":
    pn.serve(create_dashboard, port=5006, show=True)
