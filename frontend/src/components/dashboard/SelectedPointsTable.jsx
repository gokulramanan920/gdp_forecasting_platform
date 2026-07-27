import { useEffect, useMemo, useState } from 'react'
import { useDashboardStore } from '../../store/dashboardStore'

const CURATED_INDICATORS = ['total_population', 'life_expectancy', 'unemployment_rate', 'inflation_rate', 'fdi_inflows_pct', 'urban_population_pct']
const INDICATOR_LABELS = {
  total_population: 'Population',
  life_expectancy: 'Life Exp.',
  unemployment_rate: 'Unemp. %',
  inflation_rate: 'Inflation %',
  fdi_inflows_pct: 'FDI Inflows %',
  urban_population_pct: 'Urban Pop. %',
}

export default function SelectedPointsTable() {
  const { selectedPoints, setFilter, historical, predictions } = useDashboardStore()
  const [indicatorData, setIndicatorData] = useState({})
  const [loading, setLoading] = useState(false)

  const gdpLookup = useMemo(() => {
    const map = {}
    for (const d of historical) map[`${d.country_code}:${d.year}`] = d.value
    for (const d of predictions) {
      if (!d.is_baseline) map[`${d.country_code}:${d.year}`] = d.value
    }
    return map
  }, [historical, predictions])

  const getCAGR3yr = (pt) => {
    const priorValue = gdpLookup[`${pt.country_code}:${pt.year - 3}`]
    if (!priorValue || priorValue <= 0 || !pt.value || pt.value <= 0) return null
    return (Math.pow(pt.value / priorValue, 1 / 3) - 1) * 100
  }

  useEffect(() => {
    if (!selectedPoints.length) {
      setIndicatorData({})
      return
    }

    // Only fetch for historical points — projected years have no indicator data
    const histPoints = selectedPoints.filter(p => p.type === 'historical')
    if (!histPoints.length) return

    const countries = [...new Set(histPoints.map(p => p.country_code))].join(',')
    const years = [...new Set(histPoints.map(p => p.year))].join(',')

    setLoading(true)
    fetch(`/api/indicators/snapshot?countries=${countries}&years=${years}`)
      .then(r => r.json())
      .then(rows => {
        // The backend returns a cross product (all countries × all years).
        // Filter here to only the exact (country_code, year) pairs in selectedPoints
        // before building the lookup map — this prevents phantom rows from appearing.
        const selectedSet = new Set(histPoints.map(p => `${p.country_code}:${p.year}`))
        const map = {}
        for (const row of rows) {
          const key = `${row.country_code}:${row.year}`
          if (selectedSet.has(key)) map[key] = row
        }
        setIndicatorData(map)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [selectedPoints])

  if (!selectedPoints.length) return null

  const fmt = (val, decimals = 1) =>
    val != null && !isNaN(val) ? Number(val).toFixed(decimals) : '—'

  const fmtPop = (val) => {
    if (val == null || isNaN(val)) return '—'
    const n = Number(val)
    if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B'
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
    return Math.round(n).toLocaleString()
  }

  return (
    <div className="mt-4 border border-white/10 rounded-xl bg-white/[0.02] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div>
          <h3 className="text-sm font-semibold text-white">Selected Points</h3>
          <p className="text-[10px] text-gray-500 mt-0.5">{selectedPoints.length} point{selectedPoints.length !== 1 ? 's' : ''} selected — use lasso or box select on the chart</p>
        </div>
        <button
          onClick={() => setFilter('selectedPoints', [])}
          className="text-xs text-gray-500 hover:text-gray-300 border border-white/10 rounded px-2 py-1 transition-colors"
        >
          Clear
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/10 text-gray-500">
              <th className="text-left px-4 py-2 font-medium">Country</th>
              <th className="text-left px-3 py-2 font-medium">Year</th>
              <th className="text-left px-3 py-2 font-medium">Type</th>
              <th className="text-left px-3 py-2 font-medium">Economy</th>
              <th className="text-right px-3 py-2 font-medium">GDP/Capita</th>
              <th className="text-right px-3 py-2 font-medium whitespace-nowrap">3yr CAGR</th>
              {CURATED_INDICATORS.map(ind => (
                <th key={ind} className="text-right px-3 py-2 font-medium whitespace-nowrap">
                  {INDICATOR_LABELS[ind]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {selectedPoints.map((pt, i) => {
              const key = `${pt.country_code}:${pt.year}`
              const indRow = indicatorData[key]
              const isProjected = pt.type !== 'historical'
              return (
                <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="px-4 py-2 text-gray-200 font-medium">{pt.country_name}</td>
                  <td className="px-3 py-2 text-gray-400 font-mono">{pt.year}</td>
                  <td className="px-3 py-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                      isProjected
                        ? 'bg-[#00d4ff]/10 text-[#00d4ff]'
                        : 'bg-white/5 text-gray-400'
                    }`}>
                      {isProjected ? 'Projected' : 'Historical'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-gray-400 capitalize">{pt.economy_type || '—'}</td>
                  <td className="px-3 py-2 text-right text-gray-200 font-mono">
                    ${Number(pt.value).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </td>
                  <td className="px-3 py-2 text-right font-mono">
                    {(() => {
                      const cagr = getCAGR3yr(pt)
                      if (cagr === null) return <span className="text-gray-600">—</span>
                      const sign = cagr >= 0 ? '+' : ''
                      return (
                        <span className={cagr >= 0 ? 'text-green-400' : 'text-red-400'}>
                          {sign}{cagr.toFixed(1)}%
                        </span>
                      )
                    })()}
                  </td>
                  {CURATED_INDICATORS.map(ind => (
                    <td key={ind} className="px-3 py-2 text-right text-gray-400 font-mono">
                      {isProjected ? (
                        <span className="text-gray-600">—</span>
                      ) : loading ? (
                        <span className="text-gray-600">...</span>
                      ) : ind === 'total_population' ? (
                        fmtPop(indRow?.[ind])
                      ) : (
                        fmt(indRow?.[ind])
                      )}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-2 text-[10px] text-gray-600 border-t border-white/5">
        Indicator detail available for historical years only — projected years (2026–2029) show GDP per capita forecast only.
      </div>
    </div>
  )
}
