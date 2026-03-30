import { useEffect } from 'react'
import { useDashboardStore } from '../store/dashboardStore'
import FilterSidebar from '../components/dashboard/FilterSidebar'
import GDPChart from '../components/dashboard/GDPChart'
import GrowthSubPanel from '../components/dashboard/GrowthSubPanel'
import AgentPanel from '../components/dashboard/AgentPanel'

export default function DashboardPage() {
  const { loadCountries, showGrowthPanel, error } = useDashboardStore()

  useEffect(() => {
    loadCountries()
  }, [])

  return (
    <div className="flex h-[calc(100vh-56px)] overflow-hidden">
      <FilterSidebar />

      <main className="flex-1 overflow-y-auto px-5 py-4 min-w-0">
        {error && (
          <div className="mb-3 px-3 py-2 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
            {error} — make sure FastAPI is running on port 8000.
          </div>
        )}

        <GDPChart />

        {showGrowthPanel && <GrowthSubPanel />}
      </main>

      <AgentPanel />
    </div>
  )
}
