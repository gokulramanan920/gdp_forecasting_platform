export const COUNTRY_COLORS = [
  '#00d4ff', '#ff6b6b', '#51cf66', '#ffd43b', '#cc5de8',
  '#ff922b', '#74c0fc', '#f783ac', '#a9e34b', '#63e6be',
  '#4dabf7', '#e64980', '#40c057', '#fab005', '#ae3ec9',
  '#fd7e14', '#339af0', '#f06595', '#82c91e', '#20c997',
]

export function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

/** Simple LOWESS smoother — tricube weighted local linear regression */
export function computeLowess(xArr, yArr, frac = 0.4) {
  const n = xArr.length
  if (n < 5) return yArr.slice()
  const h = Math.max(3, Math.floor(frac * n))
  return xArr.map((xi, i) => {
    const dists = xArr.map((xj, j) => ({ d: Math.abs(xj - xi), j }))
    dists.sort((a, b) => a.d - b.d)
    const nbrs = dists.slice(0, h)
    const maxD = nbrs[nbrs.length - 1].d || 1
    let sw = 0, swx = 0, swy = 0, swxx = 0, swxy = 0
    for (const { d, j } of nbrs) {
      const u = d / maxD
      const w = Math.pow(Math.max(0, 1 - Math.pow(u, 3)), 3)
      sw += w
      swx += w * xArr[j]
      swy += w * yArr[j]
      swxx += w * xArr[j] ** 2
      swxy += w * xArr[j] * yArr[j]
    }
    const denom = sw * swxx - swx * swx
    if (Math.abs(denom) < 1e-10) return sw > 0 ? swy / sw : yArr[i]
    const b1 = (sw * swxy - swx * swy) / denom
    const b0 = (swy - b1 * swx) / sw
    return b0 + b1 * xi
  })
}

/** n-year CAGR for a single country from flat historical array */
export function computeCAGR(historical, countryCode, nYears) {
  const pts = historical
    .filter(d => d.country_code === countryCode)
    .sort((a, b) => a.year - b.year)
  if (pts.length < nYears + 1) return null
  const endVal = pts[pts.length - 1].value
  const startVal = pts[pts.length - 1 - nYears].value
  if (!startVal || startVal <= 0) return null
  return (Math.pow(endVal / startVal, 1 / nYears) - 1) * 100
}

/** CAGR between yearStart and yearEnd, using historical + non-baseline predictions. */
export function computeCAGRRange(historical, predictions, countryCode, yearStart, yearEnd) {
  const lookup = {}
  for (const d of historical) {
    if (d.country_code === countryCode) lookup[d.year] = d.value
  }
  for (const d of predictions) {
    if (d.country_code === countryCode && !d.is_baseline) lookup[d.year] = d.value
  }
  const startVal = lookup[yearStart]
  const endVal   = lookup[yearEnd]
  const nYears   = yearEnd - yearStart
  if (!startVal || !endVal || startVal <= 0 || endVal <= 0 || nYears <= 0) return null
  return (Math.pow(endVal / startVal, 1 / nYears) - 1) * 100
}

/** Color a YoY segment: green shades for growth, red shades for decline. */
export function yoySegmentColor(pctChange) {
  if (pctChange > 0) {
    const t = Math.min(pctChange / 0.08, 1) // saturates at 8% growth
    const sat = Math.round(40 + 60 * t)
    const lig = Math.round(60 - 30 * t)
    return `hsl(130,${sat}%,${lig}%)`
  } else {
    const t = Math.min(Math.abs(pctChange) / 0.05, 1) // saturates at 5% decline
    const sat = Math.round(50 + 50 * t)
    const lig = Math.round(65 - 35 * t)
    return `hsl(0,${sat}%,${lig}%)`
  }
}

/**
 * Returns the top K selected codes ranked by GDP per capita at yearEnd.
 * Falls back to the full selectedCodes list when topK is null/disabled or
 * fewer countries are selected than K.
 */
export function computeTopKCodes(selectedCodes, topK, historical, predictions, yearEnd) {
  if (!topK || selectedCodes.length <= topK) return selectedCodes

  const gdpAt = {}
  for (const d of historical) {
    if (d.year === yearEnd && selectedCodes.includes(d.country_code)) gdpAt[d.country_code] = d.value
  }
  for (const d of predictions) {
    if (d.year === yearEnd && !d.is_baseline && selectedCodes.includes(d.country_code)) gdpAt[d.country_code] = d.value
  }

  return [...selectedCodes]
    .sort((a, b) => (gdpAt[b] ?? 0) - (gdpAt[a] ?? 0))
    .slice(0, topK)
}

export const REGION_COLORS = {
  'East Asia and Pacific':       '#00d4ff',
  'Europe and Central Asia':     '#ffd43b',
  'Latin America and Caribbean': '#ff6b6b',
  'Middle East':                 '#ff922b',
  'North America':               '#51cf66',
  'South Asia':                  '#cc5de8',
}

export function getCountryColor(countryCode, allCountries, colorBy, colorIndex) {
  if (colorBy === 'country') {
    return COUNTRY_COLORS[colorIndex % COUNTRY_COLORS.length]
  }
  const meta = allCountries.find(c => c.country_code === countryCode)
  if (!meta) return COUNTRY_COLORS[colorIndex % COUNTRY_COLORS.length]
  if (colorBy === 'economy_type') {
    return meta.economy_type === 'developed' ? '#00d4ff' : '#ff6b6b'
  }
  if (colorBy === 'continent') {
    const MAP = {
      'North America': '#00d4ff', 'Europe': '#51cf66',
      'Asia': '#ffd43b', 'South America': '#ff6b6b',
      'Africa': '#ff922b', 'Oceania': '#cc5de8',
    }
    return MAP[meta.continent] ?? '#aaa'
  }
  if (colorBy === 'region') {
    return REGION_COLORS[meta.region] ?? '#aaa'
  }
  return COUNTRY_COLORS[colorIndex % COUNTRY_COLORS.length]
}
