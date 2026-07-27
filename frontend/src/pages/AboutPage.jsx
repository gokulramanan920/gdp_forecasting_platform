export default function AboutPage() {
  return (
    <div className="max-w-[48rem] mx-auto px-8 py-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-white mb-4">About</h1>
        <p className="text-gray-400 text-lg leading-relaxed">
          A full-stack platform combining quantitative ML forecasting with economic indicator analysis
          for global GDP per capita trajectories through 2029.
        </p>
      </div>

      {/* Tech Stack */}
      <div className="border border-white/10 rounded-xl p-6 bg-white/[0.02] mb-6">
        <h2 className="text-white font-semibold text-base mb-4">Tech Stack</h2>
        <div className="space-y-3 text-sm text-gray-400">
          <div className="flex gap-4">
            <span className="text-gray-500 w-24 shrink-0">Backend</span>
            <span>Python, FastAPI, PostgreSQL + TimescaleDB</span>
          </div>
          <div className="flex gap-4">
            <span className="text-gray-500 w-24 shrink-0">Frontend</span>
            <span>React, Vite, TailwindCSS, Plotly</span>
          </div>
          <div className="flex gap-4">
            <span className="text-gray-500 w-24 shrink-0">ML</span>
            <span>CatBoost + XGBoost ensemble, scikit-learn, pandas</span>
          </div>
          <div className="flex gap-4">
            <span className="text-gray-500 w-24 shrink-0">Data</span>
            <span>World Bank Open Data API</span>
          </div>
        </div>
      </div>

      {/* Roadmap */}
      <div className="border border-white/10 rounded-xl p-6 bg-white/[0.02] mb-6">
        <h2 className="text-white font-semibold text-base mb-4">Roadmap</h2>
        <div className="space-y-4">
          <div className="flex gap-4 items-start">
            <span className="text-[#00d4ff] text-xs font-mono w-24 shrink-0 mt-0.5">COMPLETE</span>
            <div>
              <div className="text-sm text-gray-300 font-medium">Phase 1 & 2 — Core Platform</div>
              <div className="text-xs text-gray-500 mt-0.5">ETL pipeline, EnsembleCBXGB model, 7-table PostgreSQL schema, interactive dashboard</div>
            </div>
          </div>
          <div className="flex gap-4 items-start">
            <span className="text-yellow-400/70 text-xs font-mono w-24 shrink-0 mt-0.5">PLANNED</span>
            <div>
              <div className="text-sm text-gray-300 font-medium">Phase 3 — News Intelligence</div>
              <div className="text-xs text-gray-500 mt-0.5">GDELT news pipeline, pgvector embeddings, semantic search by country and topic</div>
            </div>
          </div>
          <div className="flex gap-4 items-start">
            <span className="text-yellow-400/70 text-xs font-mono w-24 shrink-0 mt-0.5">PLANNED</span>
            <div>
              <div className="text-sm text-gray-300 font-medium">Phase 4 — Scenario Agent</div>
              <div className="text-xs text-gray-500 mt-0.5">Gemini-powered what-if analysis — modify indicator values, re-run inference, see projected impact</div>
            </div>
          </div>
        </div>
      </div>

      {/* Creator */}
      <div className="border border-white/10 rounded-xl p-6 bg-white/[0.02] mb-6">
        <h2 className="text-white font-semibold text-base mb-4">Creator</h2>
        <div className="space-y-3 text-sm text-gray-400">
          <div className="flex gap-4">
            <span className="text-gray-500 w-24 shrink-0">Name</span>
            <span className="text-gray-200">Gokul Ramanan</span>
          </div>
          <div className="flex gap-4">
            <span className="text-gray-500 w-24 shrink-0">Email</span>
            <a href="mailto:ramanan.g@northeastern.edu" className="text-[#00d4ff] hover:underline">
              ramanan.g@northeastern.edu
            </a>
          </div>
          <div className="flex gap-4">
            <span className="text-gray-500 w-24 shrink-0">LinkedIn</span>
            <a
              href="https://www.linkedin.com/in/gokul-venkat-ramanan/"
              target="_blank"
              rel="noreferrer"
              className="text-[#00d4ff] hover:underline"
            >
              linkedin.com/in/gokul-venkat-ramanan
            </a>
          </div>
          <div className="flex gap-4">
            <span className="text-gray-500 w-24 shrink-0">GitHub</span>
            <a
              href="https://github.com/gokulramanan920"
              target="_blank"
              rel="noreferrer"
              className="text-[#00d4ff] hover:underline"
            >
              github.com/gokulramanan920
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
