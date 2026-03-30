export default function AboutPage() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <h1 className="text-4xl font-bold text-white mb-4">About</h1>
      <p className="text-gray-400 text-lg leading-relaxed mb-8">
        Built by <span className="text-white font-medium">Gokul Ramanan</span> — a full-stack
        platform combining quantitative ML forecasting with qualitative news intelligence
        for global GDP per capita analysis.
      </p>
      <div className="border border-white/10 rounded-xl p-6 bg-white/[0.02] space-y-3 text-sm text-gray-400">
        <div className="flex gap-3">
          <span className="text-gray-500 w-20 shrink-0">Stack</span>
          <span>Python, FastAPI, Panel, PostgreSQL + TimescaleDB, React, Vite</span>
        </div>
        <div className="flex gap-3">
          <span className="text-gray-500 w-20 shrink-0">ML</span>
          <span>CatBoost + XGBoost ensemble, scikit-learn, pandas</span>
        </div>
        <div className="flex gap-3">
          <span className="text-gray-500 w-20 shrink-0">RAG</span>
          <span>GDELT, sentence-transformers, pgvector, Gemini 2.0 Flash</span>
        </div>
        <div className="flex gap-3">
          <span className="text-gray-500 w-20 shrink-0">Data</span>
          <span>World Bank Open Data API (20 indicators, 20 countries, 1991–)</span>
        </div>
      </div>
    </div>
  )
}
