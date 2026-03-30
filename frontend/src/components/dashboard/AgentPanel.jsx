import { useDashboardStore } from '../../store/dashboardStore'

export default function AgentPanel() {
  const { agentOpen, setFilter } = useDashboardStore()

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => setFilter('agentOpen', !agentOpen)}
        className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-semibold shadow-lg transition-all duration-200 ${
          agentOpen
            ? 'bg-[#00d4ff] text-black'
            : 'bg-[#1a1f2e] border border-[#00d4ff]/40 text-[#00d4ff] hover:bg-[#00d4ff]/10'
        }`}
      >
        <span className="text-base">🤖</span>
        {agentOpen ? 'Close Agent' : 'Scenario Analysis'}
      </button>

      {/* Slide-in panel */}
      <div
        className={`fixed top-14 right-0 h-[calc(100vh-56px)] w-96 bg-[#0d1117] border-l border-white/10 z-40 flex flex-col transition-transform duration-300 ease-in-out ${
          agentOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div>
            <h3 className="text-white font-semibold text-sm">Scenario Analysis</h3>
            <p className="text-gray-500 text-xs mt-0.5">Powered by Gemini 2.0 Flash</p>
          </div>
          <button
            onClick={() => setFilter('agentOpen', false)}
            className="text-gray-500 hover:text-gray-300 text-lg leading-none"
          >
            ×
          </button>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center gap-4">
          <div className="w-12 h-12 rounded-full bg-[#00d4ff]/10 border border-[#00d4ff]/20 flex items-center justify-center text-2xl">
            🤖
          </div>
          <div>
            <p className="text-gray-300 font-medium text-sm">Coming in Phase 4</p>
            <p className="text-gray-500 text-xs mt-2 leading-relaxed">
              Ask the agent to run what-if scenarios: "What happens to Brazil's GDP
              if inflation rises 5% in 2026?" The agent will modify indicator values
              and re-run model inference to show the projected impact.
            </p>
          </div>
          <div className="w-full border border-white/5 rounded-lg p-3 bg-white/[0.02] text-left">
            <p className="text-gray-600 text-xs font-mono">
              Example prompts coming soon:<br />
              • "Show emerging Asia economies"<br />
              • "If China trade_pct_gdp drops 10%..."<br />
              • "Compare G7 growth rates"
            </p>
          </div>
        </div>

        <div className="px-5 pb-5">
          <input
            disabled
            placeholder="Ask about a scenario... (Phase 4)"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-gray-500 placeholder-gray-600 cursor-not-allowed"
          />
        </div>
      </div>

      {/* Backdrop */}
      {agentOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/20 backdrop-blur-[1px]"
          onClick={() => setFilter('agentOpen', false)}
        />
      )}
    </>
  )
}
