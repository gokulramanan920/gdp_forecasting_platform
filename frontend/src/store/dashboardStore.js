import { create } from 'zustand'

export const useDashboardStore = create((set, get) => ({
  // ── Country & Geography ──────────────────────────────────────────────────
  allCountries: [],          // [{country_code, country_name, continent, region, economy_type}]
  selectedCodes: [],         // currently selected country codes
  continentFilter: 'All',
  regionFilter: 'All',
  economyTypeFilter: 'All',

  // ── Time & Scale ─────────────────────────────────────────────────────────
  yearStart: 1991,
  yearEnd: 2029,
  normalize1991: false,

  // ── Chart Visual ─────────────────────────────────────────────────────────
  showCI: true,
  showProjections: true,
  showLowess: false,
  showRecession: false,
  colorBy: 'country',

  // ── Growth sub-panel ─────────────────────────────────────────────────────
  showGrowthPanel: false,
  cagrPeriod: '5yr',

  // ── Top K filter ─────────────────────────────────────────────────────────
  topK: null,   // null = off, 2–10 = show only top K countries by GDP at yearEnd

  // ── Data ─────────────────────────────────────────────────────────────────
  historical: [],    // [{country_code, year, value}]
  predictions: [],   // [{country_code, year, value, ci_lower, ci_upper, is_baseline}]
  loading: false,
  error: null,

  // ── Lasso selection ──────────────────────────────────────────────────────
  selectedPoints: [],

  // ── Actions ──────────────────────────────────────────────────────────────
  setFilter: (key, value) => set({ [key]: value }),

  // Updates a geography filter AND removes any selected countries that no longer match
  setGeoFilter: (key, value) => {
    const state = get()
    const next = {
      continentFilter: key === 'continentFilter' ? value : state.continentFilter,
      regionFilter: key === 'regionFilter' ? value : state.regionFilter,
      economyTypeFilter: key === 'economyTypeFilter' ? value : state.economyTypeFilter,
    }
    const validCodes = new Set(
      state.allCountries
        .filter(c => {
          if (next.continentFilter !== 'All' && c.continent !== next.continentFilter) return false
          if (next.regionFilter !== 'All' && c.region !== next.regionFilter) return false
          if (next.economyTypeFilter !== 'All' && c.economy_type !== next.economyTypeFilter) return false
          return true
        })
        .map(c => c.country_code)
    )
    const nextCodes = state.selectedCodes.filter(code => validCodes.has(code))
    const nextSelectedPoints = state.selectedPoints.filter(p => validCodes.has(p.country_code))
    set({ [key]: value, selectedCodes: nextCodes, selectedPoints: nextSelectedPoints })
    get().loadData(nextCodes)
  },

  toggleCountry: (code) => {
    const { selectedCodes, selectedPoints } = get()
    const removing = selectedCodes.includes(code)
    const next = removing
      ? selectedCodes.filter(c => c !== code)
      : [...selectedCodes, code]
    const nextSelectedPoints = removing
      ? selectedPoints.filter(p => p.country_code !== code)
      : selectedPoints
    set({ selectedCodes: next, selectedPoints: nextSelectedPoints })
    get().loadData(next)
  },

  setSelectedCodes: (codes) => {
    const { selectedPoints } = get()
    const codeSet = new Set(codes)
    const nextSelectedPoints = selectedPoints.filter(p => codeSet.has(p.country_code))
    set({ selectedCodes: codes, selectedPoints: nextSelectedPoints })
    get().loadData(codes)
  },

  loadCountries: async () => {
    try {
      const res = await fetch('/api/countries')
      const data = await res.json()
      const initial = data.slice(0, 6).map(c => c.country_code)
      set({ allCountries: data, selectedCodes: initial })
      get().loadData(initial)
    } catch (e) {
      set({ error: 'Failed to load countries' })
    }
  },

  loadData: async (codes) => {
    if (!codes || codes.length === 0) {
      set({ historical: [], predictions: [] })
      return
    }
    set({ loading: true, error: null })
    try {
      const res = await fetch(`/api/predictions?countries=${codes.join(',')}`)
      const data = await res.json()
      set({ historical: data.historical, predictions: data.predictions, loading: false })
    } catch (e) {
      set({ loading: false, error: 'Failed to load data' })
    }
  },
}))
