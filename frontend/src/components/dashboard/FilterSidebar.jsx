import { useMemo, useState } from 'react'
import { useDashboardStore } from '../../store/dashboardStore'

function SectionLabel({ children }) {
  return <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-500 mb-1.5 mt-3">{children}</p>
}

function Toggle({ label, value, onChange }) {
  return (
    <button
      onClick={() => onChange(!value)}
      className={`flex items-center justify-between w-full px-2.5 py-1.5 rounded text-xs transition-colors ${
        value
          ? 'bg-[#00d4ff]/15 text-[#00d4ff] border border-[#00d4ff]/30'
          : 'bg-white/[0.03] text-gray-400 border border-white/10 hover:border-white/20'
      }`}
    >
      <span>{label}</span>
      <span className={`w-7 h-3.5 rounded-full flex items-center px-0.5 transition-colors ${value ? 'bg-[#00d4ff]' : 'bg-white/20'}`}>
        <span className={`w-2.5 h-2.5 rounded-full bg-white transition-transform ${value ? 'translate-x-3.5' : 'translate-x-0'}`} />
      </span>
    </button>
  )
}

function Select({ value, onChange, options, label }) {
  return (
    <div>
      {label && <p className="text-[10px] text-gray-500 mb-0.5">{label}</p>}
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full bg-[#161b22] border border-white/10 rounded px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-[#00d4ff]/40"
      >
        {options.map(o => (
          <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
        ))}
      </select>
    </div>
  )
}

export default function FilterSidebar() {
  const {
    allCountries, selectedCodes,
    continentFilter, regionFilter, economyTypeFilter,
    yearStart, yearEnd,
    normalize1991,
    showCI, showProjections, showLowess, showRecession,
    colorBy,
    showGrowthPanel, cagrPeriod,
    topK,
    toggleCountry, setFilter, setGeoFilter,
  } = useDashboardStore()

  const [countrySearch, setCountrySearch] = useState('')

  // Derive filter options from data
  const continents = useMemo(() => ['All', ...new Set(allCountries.map(c => c.continent).filter(Boolean))].sort(), [allCountries])
  const regions = useMemo(() => ['All', ...new Set(allCountries.map(c => c.region).filter(Boolean))].sort(), [allCountries])

  // Filtered + searched country list
  const visibleCountries = useMemo(() => {
    return allCountries.filter(c => {
      if (continentFilter !== 'All' && c.continent !== continentFilter) return false
      if (regionFilter !== 'All' && c.region !== regionFilter) return false
      if (economyTypeFilter !== 'All' && c.economy_type !== economyTypeFilter) return false
      if (countrySearch && !c.country_name.toLowerCase().includes(countrySearch.toLowerCase())) return false
      return true
    })
  }, [allCountries, continentFilter, regionFilter, economyTypeFilter, countrySearch])

  const selectAll = () => {
    const codes = visibleCountries.map(c => c.country_code)
    setFilter('selectedCodes', codes)
    useDashboardStore.getState().loadData(codes)
  }
  const clearAll = () => {
    setFilter('selectedCodes', [])
    useDashboardStore.getState().loadData([])
  }

  return (
    <aside className="w-[240px] shrink-0 bg-[#0d1117] border-r border-white/10 overflow-y-auto flex flex-col">
      <div className="px-3 py-3">

        {/* ── Countries ───────────────────────────────────────────────── */}
        <SectionLabel>Countries</SectionLabel>
        <input
          type="text"
          placeholder="Search..."
          value={countrySearch}
          onChange={e => setCountrySearch(e.target.value)}
          className="w-full bg-[#161b22] border border-white/10 rounded px-2 py-1.5 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-[#00d4ff]/40 mb-1.5"
        />
        <div className="flex gap-1 mb-1.5">
          <button onClick={selectAll} className="flex-1 text-[10px] text-[#00d4ff] border border-[#00d4ff]/20 rounded py-1 hover:bg-[#00d4ff]/10">All</button>
          <button onClick={clearAll} className="flex-1 text-[10px] text-gray-500 border border-white/10 rounded py-1 hover:bg-white/5">None</button>
        </div>
        <div className="max-h-44 overflow-y-auto space-y-0.5 pr-0.5">
          {visibleCountries.map(c => {
            const checked = selectedCodes.includes(c.country_code)
            return (
              <label
                key={c.country_code}
                className={`flex items-center gap-2 px-2 py-1 rounded cursor-pointer text-xs transition-colors ${
                  checked ? 'bg-[#00d4ff]/10 text-gray-200' : 'text-gray-400 hover:bg-white/5'
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleCountry(c.country_code)}
                  className="accent-[#00d4ff] w-3 h-3"
                />
                <span className="truncate">{c.country_name}</span>
                <span className="ml-auto text-[9px] text-gray-600 shrink-0">{c.country_code}</span>
              </label>
            )
          })}
        </div>

        {/* ── Geography ──────────────────────────────────────────────── */}
        <SectionLabel>Geography</SectionLabel>
        <div className="space-y-1.5">
          <Select value={continentFilter} onChange={v => setGeoFilter('continentFilter', v)} options={continents} label="Continent" />
          <Select value={regionFilter} onChange={v => setGeoFilter('regionFilter', v)} options={regions} label="Region" />
          <Select
            value={economyTypeFilter}
            onChange={v => setGeoFilter('economyTypeFilter', v)}
            options={['All', 'developed', 'emerging']}
            label="Economy Type"
          />
        </div>

        {/* ── Time & Scale ──────────────────────────────────────────── */}
        <SectionLabel>Time Range</SectionLabel>
        <div className="space-y-1.5">
          <div>
            <div className="flex justify-between text-[10px] text-gray-500 mb-1">
              <span>From</span><span className="text-gray-300 font-mono">{yearStart}</span>
            </div>
            <input
              type="range" min={1991} max={yearEnd - 1} value={yearStart}
              onChange={e => setFilter('yearStart', +e.target.value)}
              className="w-full h-1 accent-[#00d4ff]"
            />
          </div>
          <div>
            <div className="flex justify-between text-[10px] text-gray-500 mb-1">
              <span>To</span><span className="text-gray-300 font-mono">{yearEnd}</span>
            </div>
            <input
              type="range" min={yearStart + 1} max={2029} value={yearEnd}
              onChange={e => setFilter('yearEnd', +e.target.value)}
              className="w-full h-1 accent-[#00d4ff]"
            />
          </div>
        </div>

        {/* ── Top K ────────────────────────────────────────────────── */}
        <SectionLabel>Top K Countries</SectionLabel>
        <div className="space-y-2">
          <Toggle
            label={topK ? `Top ${topK} by GDP at end year` : 'Show All Selected'}
            value={topK !== null}
            onChange={on => setFilter('topK', on ? 5 : null)}
          />
          {topK !== null && (
            <div>
              <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                <span>K = {topK}</span>
                <span className="text-gray-600">2 – 10</span>
              </div>
              <input
                type="range" min={2} max={10} step={1} value={topK}
                onChange={e => setFilter('topK', +e.target.value)}
                className="w-full h-1 accent-[#00d4ff]"
              />
            </div>
          )}
        </div>

        {/* ── Chart Options ─────────────────────────────────────────── */}
        <SectionLabel>Chart Options</SectionLabel>
        <div className="space-y-1.5">
          <Toggle label="90% CI Band" value={showCI} onChange={v => setFilter('showCI', v)} />
          <Toggle label="Show Projections" value={showProjections} onChange={v => setFilter('showProjections', v)} />
          <Toggle label="LOWESS Trend" value={showLowess} onChange={v => setFilter('showLowess', v)} />
          <Toggle label="YoY Growth Colors" value={showRecession} onChange={v => setFilter('showRecession', v)} />
          <Toggle label="Index (first yr = 100)" value={normalize1991} onChange={v => setFilter('normalize1991', v)} />
        </div>

        {/* ── Appearance ────────────────────────────────────────────── */}
        <SectionLabel>Appearance</SectionLabel>
        <div className="space-y-1.5">
          <Select
            value={colorBy}
            onChange={v => setFilter('colorBy', v)}
            label="Color By"
            options={[
              { value: 'country', label: 'Country' },
              { value: 'economy_type', label: 'Economy Type' },
              { value: 'continent', label: 'Continent' },
              { value: 'region', label: 'Region' },
            ]}
          />
        </div>

        {/* ── Growth Analysis ───────────────────────────────────────── */}
        <SectionLabel>Growth Analysis</SectionLabel>
        <div className="space-y-1.5">
          <Toggle label="Show Growth Bar Chart" value={showGrowthPanel} onChange={v => setFilter('showGrowthPanel', v)} />
          {showGrowthPanel && (
            <div>
              <div className="flex items-center gap-1">
                <p className="text-[10px] text-gray-500 mb-1">CAGR Period</p>
                <span
                  title="Computed from historical data only (most recent years) — ML projected years are excluded"
                  className="text-[10px] text-gray-600 cursor-help mb-1 select-none"
                >ⓘ</span>
              </div>
              <div className="flex gap-1">
                {['3yr', '5yr', '10yr'].map(p => (
                  <button
                    key={p}
                    onClick={() => setFilter('cagrPeriod', p)}
                    className={`flex-1 py-1 rounded text-[10px] font-mono transition-colors ${
                      cagrPeriod === p
                        ? 'bg-[#00d4ff]/20 text-[#00d4ff] border border-[#00d4ff]/30'
                        : 'bg-white/[0.03] text-gray-500 border border-white/10 hover:border-white/20'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Selected count ────────────────────────────────────────── */}
        <div className="mt-4 pt-3 border-t border-white/10 text-center">
          <span className="text-[10px] text-gray-600">
            {selectedCodes.length} of {allCountries.length} countries selected
          </span>
        </div>

      </div>
    </aside>
  )
}
