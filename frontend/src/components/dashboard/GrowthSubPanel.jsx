import { useMemo } from 'react'
import Plot from '../../utils/PlotlyChart'
import { useDashboardStore } from '../../store/dashboardStore'
import { computeCAGR, getCountryColor } from '../../utils/chartUtils'

export default function GrowthSubPanel() {
  const { historical, selectedCodes, allCountries, cagrPeriod, colorBy } = useDashboardStore()

  const { data, layout } = useMemo(() => {
    const n = { '3yr': 3, '5yr': 5, '10yr': 10 }[cagrPeriod]
    const items = selectedCodes
      .map(code => {
        const idx = selectedCodes.indexOf(code)
        const cagr = computeCAGR(historical, code, n)
        if (cagr === null) return null
        const meta = allCountries.find(c => c.country_code === code) ?? {}
        return { code, name: meta.country_name ?? code, cagr, idx }
      })
      .filter(Boolean)
      .sort((a, b) => b.cagr - a.cagr)

    if (!items.length) return { data: [], layout: {} }

    const colors = items.map(({ code, idx }) =>
      getCountryColor(code, allCountries, colorBy, idx)
    )

    const trace = {
      type: 'bar',
      x: items.map(i => i.name),
      y: items.map(i => i.cagr),
      marker: { color: colors },
      hovertemplate: '%{x}<br>CAGR: %{y:.2f}%<extra></extra>',
    }

    const layout = {
      template: 'plotly_dark',
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { family: 'Inter, system-ui, sans-serif', color: '#e6edf3' },
      title: { text: `${cagrPeriod} GDP per Capita CAGR (%)`, font: { size: 14, color: '#e6edf3' }, x: 0.02 },
      xaxis: { gridcolor: 'rgba(255,255,255,0.06)', tickangle: -30 },
      yaxis: { title: 'CAGR (%)', gridcolor: 'rgba(255,255,255,0.06)', tickformat: '.2f' },
      margin: { l: 60, r: 20, t: 50, b: 70 },
      shapes: [{ type: 'line', x0: -0.5, x1: items.length - 0.5, y0: 0, y1: 0, line: { color: 'rgba(255,255,255,0.2)', width: 1 } }],
    }

    return { data: [trace], layout }
  }, [historical, selectedCodes, allCountries, cagrPeriod, colorBy])

  if (!data.length) {
    return (
      <div className="mt-2 p-4 border border-white/10 rounded-lg text-gray-500 text-sm text-center">
        Not enough data to compute {cagrPeriod} CAGR for selected countries.
      </div>
    )
  }

  return (
    <div className="mt-2">
      <Plot
        data={data}
        layout={layout}
        config={{ responsive: true, displaylogo: false, modeBarButtonsToRemove: ['select2d', 'lasso2d', 'zoom2d', 'pan2d'] }}
        style={{ width: '100%', height: '260px' }}
        useResizeHandler
      />
    </div>
  )
}
