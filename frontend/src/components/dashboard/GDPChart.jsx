import { useMemo, useState } from 'react'
import Plot from '../../utils/PlotlyChart'
import { useDashboardStore } from '../../store/dashboardStore'
import { computeLowess, hexToRgba, getCountryColor, yoySegmentColor } from '../../utils/chartUtils'

export default function GDPChart() {
  const {
    allCountries, selectedCodes,
    historical, predictions,
    yearStart, yearEnd,
    normalize1991,
    showCI, showProjections, showLowess, showRecession,
    colorBy, loading,
    selectedPoints, setFilter,
  } = useDashboardStore()

  const clearSelection = () => setFilter('selectedPoints', [])

  const { traces, layout } = useMemo(() => {
    if (!historical.length && !predictions.length) {
      return { traces: [], layout: {} }
    }

    // ── Filter by year range ──────────────────────────────────────────────
    let hist = historical.filter(d => d.year >= yearStart && d.year <= yearEnd)
    let preds = predictions.filter(d => d.year >= yearStart && d.year <= yearEnd)

    // ── Normalization (rebase each country to its first historical year = 100) ──
    const baseValues = {}
    if (normalize1991) {
      for (const code of selectedCodes) {
        const pts = hist.filter(d => d.country_code === code).sort((a, b) => a.year - b.year)
        if (pts.length > 0 && pts[0].value > 0) baseValues[code] = pts[0].value
      }
      hist = hist.map(d => ({
        ...d,
        value: baseValues[d.country_code] ? d.value / baseValues[d.country_code] * 100 : d.value,
      }))
      preds = preds.map(d => {
        const base = baseValues[d.country_code]
        if (!base) return d
        return {
          ...d,
          value: d.value / base * 100,
          ci_lower: d.ci_lower != null ? d.ci_lower / base * 100 : null,
          ci_upper: d.ci_upper != null ? d.ci_upper / base * 100 : null,
        }
      })
    }

    const traces = []
    const yLabel = normalize1991 ? 'Index' : 'GDP/capita'
    const yFmt = normalize1991 ? '%{y:.1f}' : '$%{y:,.0f}'

    selectedCodes.forEach((code, idx) => {
      const meta = allCountries.find(c => c.country_code === code) ?? {}
      const name = meta.country_name ?? code
      const color = getCountryColor(code, allCountries, colorBy, idx)
      const economyType = meta.economy_type ?? ''

      const h = hist.filter(d => d.country_code === code).sort((a, b) => a.year - b.year)
      const p = preds.filter(d => d.country_code === code).sort((a, b) => a.year - b.year)
      const baseline = p.filter(d => d.is_baseline)
      const proj = p.filter(d => !d.is_baseline)

      // ── Historical ───────────────────────────────────────────────────────
      if (h.length) {
        if (showRecession && h.length >= 2) {
          // YoY colored segments — legend anchor (no data, just shows country in legend)
          traces.push({
            type: 'scatter', mode: 'lines',
            name, x: [null], y: [null],
            line: { color, width: 2.5 },
            legendgroup: code, showlegend: true,
          })
          // Draw one trace per year-to-year gap, colored by YoY % change
          for (let i = 1; i < h.length; i++) {
            const pctChange = (h[i].value - h[i - 1].value) / h[i - 1].value
            const segColor = yoySegmentColor(pctChange)
            const sign = pctChange >= 0 ? '+' : ''
            traces.push({
              type: 'scatter',
              mode: 'lines+markers',
              name,
              x: [h[i - 1].year, h[i].year],
              y: [h[i - 1].value, h[i].value],
              line: { color: segColor, width: 2.5 },
              marker: { size: 5, color: segColor, opacity: 0.001 },
              legendgroup: code,
              showlegend: false,
              customdata: [
                { country_code: code, type: 'historical', economy_type: economyType },
                { country_code: code, type: 'historical', economy_type: economyType },
              ],
              hovertemplate: `<b>${name}</b><br>Year: %{x}<br>${yLabel}: ${yFmt}<br>YoY: ${sign}${(pctChange * 100).toFixed(1)}%<extra></extra>`,
            })
          }
        } else {
          // Single-color line — transparent markers enable lasso selection
          traces.push({
            type: 'scatter',
            mode: 'lines+markers',
            name,
            x: h.map(d => d.year),
            y: h.map(d => d.value),
            line: { color, width: 2.5 },
            marker: { size: 6, color, opacity: 0.001, line: { width: 0 } },
            legendgroup: code,
            customdata: h.map(() => ({ country_code: code, type: 'historical', economy_type: economyType })),
            hovertemplate: `<b>${name}</b><br>Year: %{x}<br>${yLabel}: ${yFmt}<extra></extra>`,
          })
        }
      }

      // ── Projections ──────────────────────────────────────────────────────
      if (showProjections && proj.length) {
        // Dashed bridge from last historical → baseline anchor
        if (h.length && baseline.length) {
          const bridgePct = (baseline[0].value - h[h.length - 1].value) / h[h.length - 1].value
          traces.push({
            type: 'scatter', mode: 'lines',
            x: [h[h.length - 1].year, baseline[0].year],
            y: [h[h.length - 1].value, baseline[0].value],
            line: { color: showRecession ? yoySegmentColor(bridgePct) : color, width: 1, dash: 'dot' },
            legendgroup: code, showlegend: false, hoverinfo: 'skip',
          })
        }

        // 80% CI band
        if (showCI) {
          const ciX = [...proj.map(d => d.year), ...proj.map(d => d.year).reverse()]
          const ciY = [...proj.map(d => d.ci_upper ?? d.value), ...proj.map(d => d.ci_lower ?? d.value).reverse()]
          traces.push({
            type: 'scatter', x: ciX, y: ciY,
            fill: 'toself', fillcolor: hexToRgba(color, 0.12),
            line: { width: 0 }, showlegend: false, hoverinfo: 'skip',
            legendgroup: code,
          })
        }

        if (showRecession) {
          // YoY-colored projection segments
          const allProj = [...(baseline.length ? [baseline[0]] : []), ...proj]
          for (let i = 1; i < allProj.length; i++) {
            const pctChange = (allProj[i].value - allProj[i - 1].value) / allProj[i - 1].value
            const segColor = yoySegmentColor(pctChange)
            const sign = pctChange >= 0 ? '+' : ''
            traces.push({
              type: 'scatter',
              mode: 'lines+markers',
              name: `${name} (proj)`,
              x: [allProj[i - 1].year, allProj[i].year],
              y: [allProj[i - 1].value, allProj[i].value],
              line: { color: segColor, width: 1.5, dash: 'dot' },
              marker: { size: 6, color: segColor, opacity: 0.001 },
              opacity: 0.75,
              legendgroup: code,
              showlegend: false,
              customdata: [
                { country_code: code, type: 'projected', economy_type: economyType },
                { country_code: code, type: 'projected', economy_type: economyType },
              ],
              hovertemplate: `<b>${name} (projected)</b><br>Year: %{x}<br>${yLabel}: ${yFmt}<br>YoY: ${sign}${(pctChange * 100).toFixed(1)}%<extra></extra>`,
            })
          }
        } else {
          // Single-color projection line — markers for lasso support
          traces.push({
            type: 'scatter',
            mode: 'lines+markers',
            name: `${name} (proj)`,
            x: proj.map(d => d.year),
            y: proj.map(d => d.value),
            line: { color, width: 1.5, dash: 'dot' },
            marker: { size: 6, color, opacity: 0.001, line: { width: 0 } },
            opacity: 0.75,
            legendgroup: code,
            showlegend: false,
            customdata: proj.map(() => ({ country_code: code, type: 'projected', economy_type: economyType })),
            hovertemplate: `<b>${name} (projected)</b><br>Year: %{x}<br>${yLabel}: ${yFmt}<extra></extra>`,
          })
        }
      }
    })

    // ── Aggregate LOWESS — one trend line across all selected countries ────
    if (showLowess) {
      const yearMap = {}
      for (const d of hist) {
        if (!yearMap[d.year]) yearMap[d.year] = { sum: 0, count: 0 }
        yearMap[d.year].sum += d.value
        yearMap[d.year].count++
      }
      const aggYears = Object.keys(yearMap).map(Number).sort((a, b) => a - b)
      const aggValues = aggYears.map(y => yearMap[y].sum / yearMap[y].count)
      if (aggYears.length >= 5) {
        const smoothed = computeLowess(aggYears, aggValues)
        traces.push({
          type: 'scatter', mode: 'lines',
          name: 'LOWESS trend',
          x: aggYears, y: smoothed,
          line: { color: 'rgba(255,255,255,0.5)', width: 2.5, dash: 'longdash' },
          showlegend: true, hoverinfo: 'skip',
        })
      }
    }

    // ── Forecast separator ────────────────────────────────────────────────
    const baselineYears = predictions.filter(d => d.is_baseline).map(d => d.year)
    const forecastStart = baselineYears.length ? Math.min(...baselineYears) : null

    const layout = {
      template: 'plotly_dark',
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { family: 'Inter, system-ui, sans-serif', color: '#e6edf3' },
      title: {
        text: normalize1991
          ? 'GDP per Capita — Indexed (first yr = 100)'
          : 'GDP per Capita Trajectories (USD)',
        font: { size: 16, color: '#e6edf3' },
        x: 0.02,
      },
      xaxis: {
        title: 'Year',
        gridcolor: 'rgba(255,255,255,0.06)',
        zerolinecolor: 'rgba(255,255,255,0.1)',
        range: [yearStart - 0.5, yearEnd + 0.5],
        tickformat: 'd',
      },
      yaxis: {
        title: normalize1991 ? 'Index (first yr = 100)' : 'GDP per Capita (USD)',
        type: 'linear',
        gridcolor: 'rgba(255,255,255,0.06)',
        zerolinecolor: 'rgba(255,255,255,0.1)',
        tickformat: normalize1991 ? '.0f' : ',.0f',
      },
      legend: {
        orientation: 'h',
        yanchor: 'bottom',
        y: 1.01,
        xanchor: 'right',
        x: 1,
        bgcolor: 'rgba(0,0,0,0)',
        font: { size: 11 },
      },
      hovermode: 'closest',
      hoverlabel: {
        bgcolor: 'white',
        font: { color: '#111', size: 12 },
        bordercolor: '#ddd',
      },
      margin: { l: 70, r: 20, t: 60, b: 50 },
      shapes: forecastStart ? [{
        type: 'line',
        x0: forecastStart, x1: forecastStart,
        y0: 0, y1: 1, yref: 'paper',
        line: { color: 'rgba(200,200,200,0.3)', width: 1, dash: 'dot' },
      }] : [],
      annotations: forecastStart ? [{
        x: forecastStart, y: 1, yref: 'paper',
        text: 'Forecast →', showarrow: false,
        font: { size: 10, color: 'rgba(200,200,200,0.5)' },
        xanchor: 'left', yanchor: 'top',
      }] : [],
    }

    return { traces, layout }
  }, [
    historical, predictions, selectedCodes, allCountries,
    yearStart, yearEnd, normalize1991,
    showCI, showProjections, showLowess, showRecession,
    colorBy,
  ])

  const handleSelected = (eventData) => {
    if (!eventData?.points) return
    const seen = new Set()
    const pts = eventData.points
      .filter(p => p.customdata?.country_code)
      .map(p => ({
        country_code: p.customdata.country_code,
        country_name: allCountries.find(c => c.country_code === p.customdata.country_code)?.country_name ?? p.customdata.country_code,
        year: p.x,
        value: p.y,
        type: p.customdata.type,
        economy_type: p.customdata.economy_type,
      }))
      // Deduplicate by (country_code, year) — colored segments produce two endpoints per gap
      .filter(pt => {
        const key = `${pt.country_code}:${pt.year}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    setFilter('selectedPoints', pts)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[520px] text-gray-500 text-sm">
        Loading data...
      </div>
    )
  }

  if (!selectedCodes.length) {
    return (
      <div className="flex items-center justify-center h-[520px] text-gray-600 text-sm">
        Select countries from the sidebar to begin.
      </div>
    )
  }

  return (
    <div className="relative">
      {selectedPoints.length > 0 && (
        <button
          onClick={clearSelection}
          className="absolute top-2 right-2 z-10 text-[10px] text-gray-500 hover:text-gray-300 border border-white/10 rounded px-2 py-0.5 bg-[#0d1117]/80 transition-colors"
        >
          ✕ Clear selection
        </button>
      )}
      <Plot
        data={traces}
        layout={layout}
        config={{
          responsive: true,
          displaylogo: false,
          // Keep home (resetScale2d), zoom, pan, lasso, select in the toolbar
          modeBarButtonsToRemove: ['hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines'],
          toImageButtonOptions: { format: 'png', filename: 'gdp_forecast', scale: 2 },
        }}
        style={{ width: '100%', height: '520px' }}
        useResizeHandler
        onSelected={handleSelected}
      />
      <div className="flex gap-5 text-[11px] text-gray-500 mt-1 px-2">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-b-2 border-gray-400" />
          Historical data
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-5 border-b-2 border-dotted border-gray-400" />
          ML Projection (2026–2029)
        </span>
      </div>
      {showRecession && (
        <div className="flex items-center gap-3 text-[10px] text-gray-500 mt-1.5 px-2">
          <span className="shrink-0 text-gray-600">YoY growth:</span>
          <div className="flex items-center gap-0.5">
            {[
              { label: '≤−5%', color: 'hsl(0,100%,30%)' },
              { label: '−3%',  color: 'hsl(0,80%,44%)' },
              { label: '−1%',  color: 'hsl(0,60%,58%)' },
              { label: '+1%',  color: 'hsl(130,48%,59%)' },
              { label: '+3%',  color: 'hsl(130,63%,49%)' },
              { label: '≥+8%', color: 'hsl(130,100%,30%)' },
            ].map(({ label, color: swatchColor }) => (
              <div key={label} className="flex flex-col items-center gap-0.5">
                <span className="inline-block w-7 h-1.5 rounded-sm" style={{ backgroundColor: swatchColor }} />
                <span style={{ fontSize: '9px' }}>{label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
