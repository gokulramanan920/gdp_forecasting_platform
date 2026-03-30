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
    const regions = [...new Set(allCountries.map(c => c.region).filter(Boolean))]
    const idx = regions.indexOf(meta.region)
    return COUNTRY_COLORS[(idx >= 0 ? idx : colorIndex) % COUNTRY_COLORS.length]
  }
  return COUNTRY_COLORS[colorIndex % COUNTRY_COLORS.length]
}
