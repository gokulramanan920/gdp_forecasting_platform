import { useMemo } from 'react'
import Plot from '../../utils/PlotlyChart'
import { useDashboardStore } from '../../store/dashboardStore'
import { computeLowess, hexToRgba, getCountryColor } from '../../utils/chartUtils'

export default function GDPChart() {
  const {
    allCountries, selectedCodes,
    historical, predictions,
    yearStart, yearEnd,
    logScale, normalize1991,
    showCI, showProjections, showLowess, showRecession,
    colorBy, plotlyTheme, loading,
  } = useDashboardStore()

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

    selectedCodes.forEach((code, idx) => {
      const meta = allCountries.find(c => c.country_code === code) ?? {}
      const name = meta.country_name ?? code
      const color = getCountryColor(code, allCountries, colorBy, idx)

      const h = hist.filter(d => d.country_code === code).sort((a, b) => a.year - b.year)
      const p = preds.filter(d => d.country_code === code).sort((a, b) => a.year - b.year)
      const baseline = p.filter(d => d.is_baseline)
      const proj = p.filter(d => !d.is_baseline)

      // ── Historical line ──────────────────────────────────────────────────
      if (h.length) {
        traces.push({
          type: 'scatter',
          mode: 'lines',
          name,
          x: h.map(d => d.year),
          y: h.map(d => d.value),
          line: { color, width: 2 },
          legendgroup: code,
          hovertemplate: `<b>${name}</b><br>Year: %{x}<br>${normalize1991 ? 'Index' : 'GDP/capita'}: ${normalize1991 ? '%{y:.1f}' : '$%{y:,.0f}'}<extra></extra>`,
        })

        // ── LOWESS trend ──────────────────────────────────────────────────
        if (showLowess && h.length >= 5) {
          const xs = h.map(d => d.year)
          const ys = computeLowess(xs, h.map(d => d.value))
          traces.push({
            type: 'scatter',
            mode: 'lines',
            name: `${name} trend`,
            x: xs,
            y: ys,
            line: { color, width: 1.5, dash: 'dot' },
            legendgroup: code,
            showlegend: false,
            hoverinfo: 'skip',
          })
        }

        // ── Recession highlights (negative YoY growth years) ─────────────
        if (showRecession && h.length >= 2) {
          h.forEach((pt, i) => {
            if (i === 0) return
            if (pt.value < h[i - 1].value) {
              traces.push({
                type: 'scatter',
                x: [pt.year - 0.5, pt.year + 0.5, pt.year + 0.5, pt.year - 0.5],
                y: [0, 0, 1e9, 1e9],
                fill: 'toself',
                fillcolor: 'rgba(255,80,80,0.07)',
                line: { width: 0 },
                showlegend: false,
                hoverinfo: 'skip',
                legendgroup: code,
              })
            }
          })
        }
      }

      // ── Projections ──────────────────────────────────────────────────────
      if (showProjections && proj.length) {
        // Connect last historical point → baseline → projections via dashed line
        const connectX = []
        const connectY = []
        if (h.length) {
          connectX.push(h[h.length - 1].year)
          connectY.push(h[h.length - 1].value)
        }
        if (baseline.length) {
          connectX.push(baseline[0].year)
          connectY.push(baseline[0].value)
        }
        if (connectX.length === 2) {
          traces.push({
            type: 'scatter',
            mode: 'lines',
            x: connectX,
            y: connectY,
            line: { color, width: 2, dash: 'dash' },
            legendgroup: code,
            showlegend: false,
            hoverinfo: 'skip',
          })
        }

        // CI band
        if (showCI) {
          const ciX = [...proj.map(d => d.year), ...proj.map(d => d.year).reverse()]
          const ciY = [...proj.map(d => d.ci_upper ?? d.value), ...proj.map(d => d.ci_lower ?? d.value).reverse()]
          traces.push({
            type: 'scatter',
            x: ciX,
            y: ciY,
            fill: 'toself',
            fillcolor: hexToRgba(color, 0.12),
            line: { width: 0 },
            showlegend: false,
            hoverinfo: 'skip',
            legendgroup: code,
          })
        }

        // Projection dashed line
        traces.push({
          type: 'scatter',
          mode: 'lines',
          name: `${name} (proj)`,
          x: proj.map(d => d.year),
          y: proj.map(d => d.value),
          line: { color, width: 2, dash: 'dash' },
          legendgroup: code,
          showlegend: false,
          hovertemplate: `<b>${name} (projected)</b><br>Year: %{x}<br>${normalize1991 ? 'Index' : 'GDP/capita'}: ${normalize1991 ? '%{y:.1f}' : '$%{y:,.0f}'}<extra></extra>`,
        })
      }
    })

    // ── Forecast separator line ───────────────────────────────────────────
    const baselineYears = predictions.filter(d => d.is_baseline).map(d => d.year)
    const forecastStart = baselineYears.length ? Math.min(...baselineYears) : null

    const layout = {
      template: plotlyTheme,
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
        type: logScale ? 'log' : 'linear',
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
      hovermode: 'x unified',
      margin: { l: 70, r: 20, t: 60, b: 50 },
      shapes: forecastStart ? [{
        type: 'line',
        x0: forecastStart, x1: forecastStart,
        y0: 0, y1: 1,
        yref: 'paper',
        line: { color: 'rgba(200,200,200,0.3)', width: 1, dash: 'dot' },
      }] : [],
      annotations: forecastStart ? [{
        x: forecastStart,
        y: 1,
        yref: 'paper',
        text: 'Forecast →',
        showarrow: false,
        font: { size: 10, color: 'rgba(200,200,200,0.5)' },
        xanchor: 'left',
        yanchor: 'top',
      }] : [],
    }

    return { traces, layout }
  }, [
    historical, predictions, selectedCodes, allCountries,
    yearStart, yearEnd, logScale, normalize1991,
    showCI, showProjections, showLowess, showRecession,
    colorBy, plotlyTheme,
  ])

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
    <Plot
      data={traces}
      layout={layout}
      config={{
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['select2d', 'lasso2d'],
        toImageButtonOptions: { format: 'png', filename: 'gdp_forecast', scale: 2 },
      }}
      style={{ width: '100%', height: '520px' }}
      useResizeHandler
    />
  )
}
