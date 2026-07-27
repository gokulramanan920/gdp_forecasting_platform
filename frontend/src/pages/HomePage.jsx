import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

function StatCard({ label, value, sub }) {
  return (
    <div className="border border-white/10 rounded-lg p-5 bg-white/[0.03] text-center">
      <div className="text-2xl font-bold text-[#00d4ff] font-mono">{value}</div>
      <div className="text-sm font-medium text-gray-300 mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  )
}

function FeatureCard({ title, desc }) {
  return (
    <div className="border border-white/10 rounded-xl p-6 bg-white/[0.02] hover:bg-white/[0.04] transition-colors text-center">
      <h3 className="text-white font-semibold mb-2 text-center">{title}</h3>
      <p className="text-gray-400 text-sm leading-relaxed text-center">{desc}</p>
    </div>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState({ countries: 20, indicators: 19 })

  useEffect(() => {
    fetch('/api/countries')
      .then(r => r.json())
      .then(data => setStats(s => ({ ...s, countries: data.length })))
      .catch(() => {})
  }, [])

  return (
    <div className="max-w-[80rem] mx-auto px-8 md:px-16 py-16">
      {/* Hero */}
      <div className="text-center mb-20">
        <div className="inline-flex items-center gap-2 border border-[#00d4ff]/30 bg-[#00d4ff]/5 rounded-full px-4 py-1.5 text-xs text-[#00d4ff] font-mono mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00d4ff] animate-pulse" />
          LIVE FORECASTING PLATFORM
        </div>
        <h1 className="text-5xl font-bold text-white tracking-tight mb-6 leading-tight">
          GDP Per Capita<br />
          <span className="text-[#00d4ff]">Forecasting Intelligence</span>
        </h1>
        <p className="text-gray-400 text-lg max-w-[42rem] mx-auto mb-10 leading-relaxed text-center">
          Ensemble ML model projections across 20 countries and 34 years of World Bank data.
          Explore trajectories and understand the economic forces shaping
          global GDP per capita through 2029.
        </p>
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="bg-[#00d4ff] text-black font-semibold px-8 py-3 rounded-lg hover:bg-[#00d4ff]/90 transition-colors"
          >
            Open Dashboard
          </button>
          <button
            onClick={() => navigate('/model')}
            className="border border-white/20 text-gray-300 font-medium px-8 py-3 rounded-lg hover:bg-white/5 transition-colors"
          >
            How It Works
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-20">
        <StatCard label="Countries Tracked" value={stats.countries} sub="G20 + major economies" />
        <StatCard label="Economic Indicators" value="19" sub="World Bank API" />
        <StatCard label="Years of History" value="34" sub="1991 – 2024" />
        <StatCard label="Projection Horizon" value="4 yrs" sub="2026 – 2029" />
      </div>

      {/* Features */}
      <div className="mb-20">
        <h2 className="text-2xl font-bold text-white mb-8 text-center">Platform Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-[48rem] mx-auto">
          <FeatureCard
            title="GDP Trajectory Dashboard"
            desc="Interactive Plotly charts with historical data and 4-year ML projections (80% CI). Use the lasso tool to select specific points and surface a detailed datatable."
          />
          <FeatureCard
            title="Ensemble ML Model"
            desc="CatBoost + XGBoost ensemble with time-series cross-validation, cluster-aware forecasting, and mean-reverting feature extrapolation. R² 0.934 on holdout."
          />
          <FeatureCard
            title="Continuous Retraining"
            desc="Scheduled pipeline pulls fresh World Bank data, retrains the model, and updates predictions automatically when new GDP data becomes available."
          />
          <FeatureCard
            title="19 World Bank Indicators"
            desc="Trade, FDI, inflation, unemployment, demographics, energy, capital formation — the full economic fingerprint behind each country's trajectory."
          />
        </div>
      </div>

      {/* Model note */}
      <div className="border border-yellow-500/20 bg-yellow-500/5 rounded-xl p-6 text-center max-w-[48rem] mx-auto">
        <p className="text-yellow-300/80 text-sm">
          <span className="font-semibold">Note on data lag:</span>{' '}
          World Bank GDP data lags ~1.5 years. Projections account for this using
          mean-reverting extrapolation of 19 World Bank indicators.
        </p>
      </div>
    </div>
  )
}
