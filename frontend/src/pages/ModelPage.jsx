const INDICATORS = [
  { name: 'Population Density', category: 'Demographics' },
  { name: 'Trade % of GDP', category: 'Trade' },
  { name: 'Infant Mortality', category: 'Demographics' },
  { name: 'Life Expectancy', category: 'Demographics' },
  { name: 'Age Dependency Ratio', category: 'Demographics' },
  { name: 'Agricultural Land %', category: 'Land Use' },
  { name: 'Oil Rents % GDP', category: 'Energy' },
  { name: 'Fuel Exports %', category: 'Energy' },
  { name: 'Natural Resource Rents %', category: 'Energy' },
  { name: 'Fertility Rate', category: 'Demographics' },
  { name: 'Urban Population %', category: 'Demographics' },
  { name: 'Total Population', category: 'Demographics' },
  { name: 'Patent Applications', category: 'Innovation' },
  { name: 'Unemployment Rate', category: 'Labor' },
  { name: 'Gross Savings %', category: 'Finance' },
  { name: 'Mobile Subscriptions', category: 'Technology' },
  { name: 'Gross Capital Formation %', category: 'Investment' },
  { name: 'Inflation Rate', category: 'Finance' },
  { name: 'FDI Inflows % GDP', category: 'Finance' },
]

export default function ModelPage() {
  return (
    <div className="max-w-[80rem] mx-auto px-8 md:px-16 py-16">
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-bold text-white mb-4">Model & Methodology</h1>
        <p className="text-gray-400 text-lg max-w-3xl mx-auto">
          An ensemble of CatBoost and XGBoost trained on 35 years of World Bank data across
          20 countries, with cluster-aware forecasting and mean-reverting feature extrapolation.
        </p>
      </div>

      {/* Model architecture */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <div className="border border-white/10 rounded-xl p-6 bg-white/[0.02]">
          <h2 className="text-white font-semibold text-lg mb-4">Architecture</h2>
          <div className="space-y-3 text-sm">
            {[
              ['Model type', 'EnsembleCBXGB: CatBoost 50% + XGBoost 50%'],
              ['Training window', '1991 – 2022 (expanding CV folds)'],
              ['Holdout', '2023 – 2025 (3-year out-of-sample)'],
              ['Clustering', 'K-Means (k=2): developed / emerging cohorts'],
              ['Confidence intervals', '90% CI from 10-year empirical error distribution'],
              ['Retraining trigger', 'New World Bank GDP data (annual)'],
            ].map(([label, val]) => (
              <div key={label} className="flex justify-between gap-4 border-b border-white/5 pb-2">
                <span className="text-gray-400">{label}</span>
                <span className="text-gray-200 text-right">{val}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="border border-white/10 rounded-xl p-6 bg-white/[0.02]">
          <h2 className="text-white font-semibold text-lg mb-4">Pipeline</h2>
          <div className="space-y-2">
            {[
              ['1. ETL', 'Fetch 19 indicators × 20 countries from World Bank API'],
              ['2. Impute', 'Linear interpolation + forward/backward fill'],
              ['3. Cluster', 'K-Means on GDP level, 5yr CAGR, volatility'],
              ['4. Train', '4-fold time-series CV + holdout evaluation'],
              ['5. Extrapolate', 'Mean-reverting feature projection (4 years)'],
              ['6. Predict', 'Ensemble inference + cluster baseline blend'],
              ['7. Store', 'Upsert predictions + CIs into PostgreSQL'],
            ].map(([step, desc]) => (
              <div key={step} className="flex gap-3 text-sm">
                <span className="text-[#00d4ff] font-mono whitespace-nowrap shrink-0">{step}</span> 
                <span className="text-gray-400">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Performance metrics */}
      <div className="border border-[#00d4ff]/25 rounded-xl p-6 bg-[#00d4ff]/[0.03] mb-8">
        <h2 className="text-white font-semibold text-lg mb-5">
          Model Performance: Holdout Evaluation (2023–2025)
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-[#00d4ff] font-mono mb-1">0.934</div>
            <div className="text-sm font-medium text-gray-300">R² Score</div>
            <div className="text-xs text-gray-500 mt-0.5">93.4% of variance explained on unseen data</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-[#00d4ff] font-mono mb-1">10.6%</div>
            <div className="text-sm font-medium text-gray-300">MAPE</div>
            <div className="text-xs text-gray-500 mt-0.5">Mean absolute % error across 20 countries</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-[#00d4ff] font-mono mb-1">3 yr</div>
            <div className="text-sm font-medium text-gray-300">Out-of-Sample Holdout</div>
            <div className="text-xs text-gray-500 mt-0.5">Model never saw 2023–2025 during training</div>
          </div>
        </div>
      </div>

      {/* Input features */}
      <div className="border border-white/10 rounded-xl p-6 bg-white/[0.02] mb-8">
        <h2 className="text-white font-semibold text-lg mb-4">
          Input Features — 19 World Bank Indicators
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
          {INDICATORS.map(({ name, category }) => (
            <div key={name} className="flex items-start gap-2 p-2 rounded bg-white/[0.03]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00d4ff] mt-1.5 shrink-0" />
              <div>
                <div className="text-xs text-gray-300">{name}</div>
                <div className="text-[10px] text-gray-500">{category}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Data source note */}
      <div className="border border-[#00d4ff]/20 bg-[#00d4ff]/5 rounded-xl p-6">
        <h3 className="text-[#00d4ff] font-semibold mb-2">Data Source</h3>
        <p className="text-gray-400 text-sm leading-relaxed">
          All training data sourced from the{' '}
          <span className="text-gray-200">World Bank Open Data API</span>.
          GDP per capita values lag approximately 1.5 years behind the current date.
          Projections use mean-reverting extrapolation of indicator trends as model input,
          with cluster-specific dampening factors applied to prevent runaway forecasts.
        </p>
      </div>
    </div>
  )
}
